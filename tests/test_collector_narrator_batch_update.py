"""Retained standalone-update fixtures; no live host, scheduler task or inference."""
import ast
import copy
from contextlib import closing
import ctypes
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tests.fixture_retention import FixtureDirectory
from youtube_ops import collector_narrator_recovery_probe as probe

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/collector/host-tools/Update-KnowledgeNetworkNarratorBatch.ps1'
INSTALLER=ROOT/'docs/collector/host-tools/Install-KnowledgeNetworkNarratorStandalone.ps1'
EXPECTED=['%032x'%value for value in range(1,10)]


def helper():
    text=SOURCE.read_text(encoding='utf-8')
    source=text.split("$helper=@'\n",1)[1].split("\n'@",1)[0]
    tree=ast.parse(source)
    # Import only definitions and constants. The fixed host bootstrap's top-level
    # source-pin reads/main invocation are intentionally never run in fixtures.
    constants={'ROOT','WORK','DATA','DB','PYTHON','TASK','NAMES','TASK_PROOF','CODE_VALIDATION','VALIDATOR_SHA256'}
    nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))
           or isinstance(node,(ast.Import,ast.ImportFrom)) and not any(alias.name=='collector_narrator_recovery_probe' for alias in node.names)
           or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in constants for target in node.targets)]
    namespace={'probe':probe,'__name__':'kn_owned_update_fixture','FENCE':'batch_update_v1_'+'a'*32}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'owned-update-fixture','exec'),namespace)
    return namespace,source


class Adapter:
    """Real SQLite connection with the public C-API fixture's string row types."""
    def __init__(self,path):self.db=sqlite3.connect(path,isolation_level=None,timeout=.03)
    def execute(self,sql):
        return [tuple(None if value is None else str(value) for value in row) for row in self.db.execute(sql).fetchall()]
    def close(self):self.db.close()


def create_database(path):
    with closing(sqlite3.connect(path)) as db,db:
        db.executescript('''PRAGMA journal_mode=WAL;
            CREATE TABLE jobs(id TEXT PRIMARY KEY,request_sha TEXT NOT NULL,text TEXT NOT NULL,
                text_sha TEXT NOT NULL,state TEXT NOT NULL,provenance TEXT NOT NULL,audio TEXT,error TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT INTO metadata VALUES('schema_version','1');
            CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,state TEXT);''')
        db.executemany("INSERT INTO jobs(id,request_sha,text,text_sha,state,provenance) VALUES(?,'sha','owned','sha','completed','{}')",[(job,) for job in EXPECTED])
        db.execute("INSERT INTO events(job_id,state) VALUES(?,'completed')",(EXPECTED[0],))


class BatchUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory=FixtureDirectory(prefix='kn-batch-update-')
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'host-narrations.sqlite'
        create_database(self.path)
        self.code,self.source=helper()
        self.db=Adapter(self.path);self.addCleanup(self.db.close)

    def test_two_phase_fence_retains_writer_lock_and_consistent_original_backup(self):
        backup=self.path.with_name('original.backup.sqlite')
        snapshot=self.code['prepare_fence'](self.db,EXPECTED,lambda:self.code['backup_locked'](self.path,backup))
        self.assertEqual(snapshot['jobs'],EXPECTED)
        with closing(sqlite3.connect(backup)) as original:
            self.assertEqual(original.execute('SELECT count(*) FROM jobs').fetchone()[0],9)
            self.assertEqual(original.execute("SELECT value FROM metadata WHERE key='execution_hold'").fetchall(),[])
        with closing(sqlite3.connect(self.path,timeout=.03)) as blocked:
            with self.assertRaises(sqlite3.OperationalError):blocked.execute('BEGIN IMMEDIATE')
        self.db.execute('ROLLBACK')
        self.assertEqual(self.db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[(self.code['FENCE'],)])

    def test_post_that_checked_before_fence_cannot_write_through_second_lock(self):
        self.code['prepare_fence'](self.db,EXPECTED,lambda:None)
        errors=[]
        def pending_post():
            with closing(sqlite3.connect(self.path,timeout=.03)) as request:
                try:request.execute("INSERT INTO jobs VALUES('"+'b'*32+"','x','owned','x','queued','{}',NULL,NULL,0)");request.commit()
                except sqlite3.OperationalError as error:errors.append(str(error))
        thread=threading.Thread(target=pending_post);thread.start();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs'),[('9',)])
        self.db.execute('ROLLBACK')

    def test_intervening_job_aborts_before_stop_and_preserves_committed_fence(self):
        def old_request_wins_gap():
            with closing(sqlite3.connect(self.path)) as request,request:
                request.execute("INSERT INTO jobs VALUES('"+'b'*32+"','x','owned','x','queued','{}',NULL,NULL,0)")
        with self.assertRaisesRegex(RuntimeError,'ledger_not_exactly_completed'):
            self.code['prepare_fence'](self.db,EXPECTED,lambda:None,old_request_wins_gap)
        self.db.execute('ROLLBACK')
        self.assertEqual(self.db.execute("SELECT state FROM jobs WHERE id='"+'b'*32+"'"),[('queued',)])
        self.assertEqual(self.db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[(self.code['FENCE'],)])

    def test_event_drift_in_gap_blocks_even_when_job_states_unchanged(self):
        def changed():
            with closing(sqlite3.connect(self.path)) as writer,writer:writer.execute("INSERT INTO events(job_id,state) VALUES(NULL,'owned-drift')")
        with self.assertRaisesRegex(RuntimeError,'ledger_changed_after_fence'):
            self.code['prepare_fence'](self.db,EXPECTED,lambda:None,changed)
        self.db.execute('ROLLBACK')
        self.assertEqual(self.db.execute('SELECT count(*) FROM events'),[('2',)])

    def test_unknown_hold_or_active_job_never_gets_cleared(self):
        for kind in ('hold','active'):
            with self.subTest(kind=kind):
                self.db.execute("INSERT OR REPLACE INTO metadata VALUES('execution_hold','outcome_unknown')" if kind=='hold' else "UPDATE jobs SET state='running' WHERE id='"+EXPECTED[0]+"'")
                backups=[]
                with self.assertRaises(RuntimeError):self.code['prepare_fence'](self.db,EXPECTED,lambda:backups.append(True))
                self.assertEqual(backups,[])
                self.assertEqual(self.db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[('outcome_unknown',)])

    def test_clear_fence_only_accepts_own_exact_hold_and_expected_state(self):
        self.code['prepare_fence'](self.db,EXPECTED,lambda:None)
        self.code['clear_own_fence'](self.db,EXPECTED)
        self.db.execute('COMMIT')
        self.db.execute("INSERT INTO metadata VALUES('execution_hold','outcome_unknown')")
        with self.assertRaisesRegex(RuntimeError,'ledger_hold_changed'):self.code['clear_own_fence'](self.db,EXPECTED)
        self.assertEqual(self.db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[('outcome_unknown',)])

    def test_active_writer_blocks_before_backup_or_fence_mutation(self):
        with closing(sqlite3.connect(self.path,isolation_level=None)) as writer:
            writer.execute('BEGIN IMMEDIATE');backups=[]
            with self.assertRaises(sqlite3.OperationalError):self.code['prepare_fence'](self.db,EXPECTED,lambda:backups.append(True))
            self.assertEqual(backups,[]);writer.rollback()
        self.assertEqual(self.db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[])

    def test_launcher_reuses_identity_and_auth_checks_with_unique_startup_and_batch_gate(self):
        original=INSTALLER.read_text().split("$launcher=@'\n",1)[1].split("\n'@",1)[0]
        updated=self.code['new_launcher'](original)
        ast.parse(updated)
        self.assertIn("identity!={'sid':config['owner_sid'],'elevated':False}",updated)
        self.assertIn("REVIEW=ROOT/'data/batch-update-v1/startup'/uuid.uuid4().hex",updated)
        self.assertIn("segment_batches=config['segment_batches']",updated)
        self.assertLess(updated.index("sha(parity)!=config['parity_receipt_sha256']"),updated.index('store=NarratorStore'))
        self.assertIn('absent!=401 or wrong!=401 or code!=200',updated)
        parity=self.code['parity_source'](updated,['Owned first sentence.','Owned second sentence.'])
        ast.parse(parity)
        self.assertNotIn('store=NarratorStore',parity)
        self.assertNotIn('secret,_=read_secret',parity)
        self.assertEqual(parity.count('WindowsScriptRunner().batch('),1)
        self.assertIn("'listening':'NOT_TESTED'",parity)

    def test_fixed_scope_no_network_changes_deletion_or_legacy_repair_and_capture_before_mutation(self):
        text=SOURCE.read_text()
        for forbidden in ('Remove-Item','rmtree','unlink(', 'os.remove(', 'Stop-EmptyNarratorController', 'tailscale serve','New-NetFirewallRule','NarratorControl\''):
            self.assertNotIn(forbidden,text)
        self.assertLess(text.index('Capture-File (Join-Path $bundlePath'),text.index('New-PrivateDirectory $work'))
        main=ast.parse(self.source)
        function=next(node for node in main.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        body=ast.get_source_segment(self.source,function)
        self.assertLess(body.index('with probe.NamespaceGuard(DB)'),body.index('connection=Sqlite(DB,guard)'))
        self.assertLess(body.index('EXACT_HELD_PROCESS_EXIT_CONFIRMED'),body.index('prepare_code(package'))
        self.assertLess(body.index('parity_task(config)'),body.index('new_config.update(segment_batches=True'))
        self.assertIn("'automatic_database_restore':False",text)
        self.assertNotIn('Set-ExecutionPolicy',text)
        self.assertNotIn('CreationDate.ToFileTimeUtc()',self.code['TASK_PROOF'])
        self.assertIn('ReadAllBytes(',self.code['CODE_VALIDATION'])
        self.assertIn('[ScriptBlock]::Create($text)',self.code['CODE_VALIDATION'])

    def test_actual_task_validation_rejects_identity_flags_children_and_action_drift(self):
        config={'owner_sid':'S-1-5-21-1-2-3-1001'}
        python=str(self.code['PYTHON']);script=str(self.code['ROOT']/'code/narrator-standalone.py').replace('\\','/')
        valid={'pid':123,'creation_filetime':456,'owner_sid':config['owner_sid'],'process_owner':config['owner_sid'],'state':4,'enabled':True,'logon':3,'runlevel':0,
               'actions':1,'triggers':0,'multiple':2,'hard_terminate':False,'execution_limit':'PT0S','execute':python,'image':python,
               'arguments':'-I -S -B '+script,'working_directory':str(self.code['ROOT']/'code'),'children':[],
               'command_line':subprocess.list2cmdline([python,'-I','-S','-B',script])}
        self.code['ps']=lambda code:copy.deepcopy(valid)
        self.code['capture_task_process']=lambda pid,read_current:read_current()
        self.assertEqual(self.code['task_proof'](config),valid)
        new_code=self.code['WORK']/'code'
        updated={**valid,'working_directory':str(new_code),'arguments':'-I -S -B '+str(new_code/'narrator-standalone.py').replace('\\','/'),
                 'command_line':subprocess.list2cmdline([python,'-I','-S','-B',str(new_code/'narrator-standalone.py')])}
        self.code['ps']=lambda code:copy.deepcopy(updated)
        self.assertEqual(self.code['task_proof'](config,new_code),updated)
        with self.assertRaisesRegex(RuntimeError,'fixed_code_directory_required'):self.code['task_proof'](config,Path('C:/unrelated'))
        self.code['ps']=lambda code:copy.deepcopy(valid)
        for edit in ({'owner_sid':'other'},{'process_owner':'other'},{'runlevel':1},{'logon':5},{'actions':2},{'triggers':1},
                     {'children':[{'pid':12}]},{'execute':'other.exe'},{'image':'other.exe'},
                     {'arguments':'-i -s -b '+script},{'command_line':valid['command_line']+' extra'},
                     {'enabled':False},{'multiple':0},{'hard_terminate':True}):
            with self.subTest(edit=edit):
                self.code['ps']=lambda code,edit=edit:{**valid,**edit}
                with self.assertRaises(RuntimeError):self.code['task_proof'](config)

    def test_uncertain_held_process_exit_never_prepares_code_or_starts_any_task(self):
        for stop_ok,wait_code,error in ((False,0,'exact_held_process_stop_failed'),(True,258,'exact_process_exit_unknown')):
            with self.subTest(error=error),FixtureDirectory(prefix='kn-update-uncertain-') as directory:
                root=Path(directory);data=root/'data';data.mkdir();(data/'review').mkdir();(root/'code').mkdir();work=root/'batch-update-v1';work.mkdir()
                db=data/'host-narrations.sqlite';create_database(db)
                python=Path(sys.executable)
                config={'owner_sid':'S-1-5-21-1-2-3-1001','server_python_sha256':self.code['sha'](python)}
                (root/'code/config.json').write_text(json.dumps(config))
                (data/'review/startup-ready.private.json').write_text(json.dumps({'pid':99}))
                (work/'batch-update-bundle.private.json').write_text(json.dumps({'expected_job_ids':EXPECTED}))
                native=SimpleNamespace(k=SimpleNamespace(TerminateProcess=Mock(return_value=stop_ok),WaitForSingleObject=Mock(return_value=wait_code),CloseHandle=Mock()),running=Mock())
                guard=SimpleNamespace(native=native,ledger={'volume':1,'file_id':'fixture'},__enter__=None)
                class Guard:
                    def __enter__(self):return guard
                    def __exit__(self,*args):return False
                calls=[];task={'pid':99,'creation_filetime':100,'xml':'original'}
                self.code.update(ROOT=root,DATA=data,DB=db,WORK=work,PYTHON=python,
                    sys=SimpleNamespace(executable=str(python),flags=SimpleNamespace(isolated=True,no_site=True,dont_write_bytecode=True)),
                    ps=lambda code:{'sid':config['owner_sid'],'elevated':True},verify_bundle=lambda *args:None,
                    task_proof=lambda config:dict(task),preserve_old_code=lambda *args:None,
                    probe=SimpleNamespace(NamespaceGuard=lambda path:Guard()),bind_running=lambda *args:77,
                    held_process_owner=lambda *args:None,Sqlite=lambda path,guard:Adapter(path),
                    task_operation=lambda op,*args:(calls.append(op) or {'xml':'disabled','enabled':False}),
                    make_private_data=Mock(side_effect=AssertionError('code setup must not run')),
                    prepare_code=Mock(side_effect=AssertionError('code setup must not run')))
                with self.assertRaisesRegex(RuntimeError,error):self.code['main']()
                self.assertEqual(calls,['disable'])
                self.code['make_private_data'].assert_not_called();self.code['prepare_code'].assert_not_called()
                record=json.loads((work/'update-review/blocked.private.json').read_text())
                self.assertFalse(record['old_process_exit_confirmed']);self.assertTrue(record['fence_committed'])
                with closing(sqlite3.connect(db)) as unchanged:
                    self.assertEqual(unchanged.execute('SELECT count(*) FROM jobs').fetchone()[0],9)
                    self.assertEqual(unchanged.execute("SELECT value FROM metadata WHERE key='execution_hold'").fetchone()[0],self.code['FENCE'])


@unittest.skipUnless(os.name=='nt' and os.environ.get('COLLECTOR_NATIVE_BATCH_UPDATE')=='1','Opt-in serialized native fixture; no host/task/GPU changes')
class NativeBatchUpdateTests(unittest.TestCase):
    def test_native_parser(self):
        code="$e=$null;$t=$null;$null=[Management.Automation.Language.Parser]::ParseFile([Console]::In.ReadToEnd(),[ref]$t,[ref]$e);if($e.Count){$e|Out-String;exit 1};'PARSE_PASS'"
        result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],input=str(SOURCE),capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_native_public_sqlite_handle_identity_and_writer_lock(self):
        functions,_=helper()
        with FixtureDirectory(prefix='kn-update-native-',trusted_execution=True) as folder:
            path=Path(folder)/'host-narrations.sqlite';create_database(path)
            wrong=Path(folder)/'wrong.sqlite';create_database(wrong)
            with probe.NamespaceGuard(path) as guard:
                connection=functions['Sqlite'](path,guard)
                try:
                    functions['prepare_fence'](connection,EXPECTED,lambda:None)
                    with closing(sqlite3.connect(path,timeout=.03)) as other:
                        with self.assertRaises(sqlite3.OperationalError):other.execute('BEGIN IMMEDIATE')
                    with self.assertRaisesRegex(RuntimeError,'sqlite_ledger_mismatch'):
                        functions['Sqlite'](wrong,guard)
                    with self.assertRaises(OSError):path.rename(path.with_name('renamed.sqlite'))
                    connection.execute('ROLLBACK')
                finally:connection.close()

    def test_restricted_child_invokes_only_captured_digest_verified_utf8(self):
        functions,_=helper()
        with FixtureDirectory(prefix='kn-update-policy-',trusted_execution=True) as folder:
            root=Path(folder);validator=root/'validator.ps1'
            validator.write_text('param([string]$OwnerSid)\n@{owner_sid=$OwnerSid;captured_validator=$true}|ConvertTo-Json -Compress',encoding='utf-8')
            original='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/assert-code.ps1'
            prefix="$ErrorActionPreference='Stop';if((Get-ExecutionPolicy) -cne 'Restricted'){throw 'Fixture requires effective Restricted policy.'};"
            calls=[];current=validator
            def run(command,payload=None):
                process=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Restricted','-Command',prefix+command],input=None if payload is None else json.dumps(payload),capture_output=True,text=True,timeout=20)
                index=len(calls);calls.append(process)
                (root/('child-%02d.stdout.log'%index)).write_text(process.stdout,encoding='utf-8')
                (root/('child-%02d.stderr.log'%index)).write_text(process.stderr,encoding='utf-8')
                return process
            direct=run("& '"+validator.as_posix()+"' -OwnerSid 'owned-fixture'")
            self.assertNotEqual(direct.returncode,0,'File-script negative control unexpectedly executed')
            self.assertNotIn('captured_validator',direct.stdout)
            def invoke(command,value):
                self.assertEqual(command.count(original),1)
                result=run(command.replace(original,current.as_posix()),value)
                if result.returncode:raise RuntimeError('fixed_powershell_operation_failed')
                return json.loads(result.stdout)
            functions['ps']=invoke
            functions['VALIDATOR_SHA256']=functions['sha'](validator)
            functions['assert_new_code']('owned-fixture')
            self.assertEqual(json.loads(calls[-1].stdout),{'captured_validator':True,'owner_sid':'owned-fixture'})
            functions['VALIDATOR_SHA256']='0'*64
            with self.assertRaisesRegex(RuntimeError,'fixed_powershell_operation_failed'):functions['assert_new_code']('owned-fixture')
            self.assertNotIn('captured_validator',calls[-1].stdout)
            invalid=root/'invalid-utf8.ps1';invalid.write_bytes(b'\xff\xfe\x80')
            current=invalid;functions['VALIDATOR_SHA256']=functions['sha'](invalid)
            with self.assertRaisesRegex(RuntimeError,'fixed_powershell_operation_failed'):functions['assert_new_code']('owned-fixture')
            self.assertNotIn('captured_validator',calls[-1].stdout)

    def test_native_exact_child_ledger_writer_fence_and_confirmed_exit(self):
        functions,_=helper()
        with FixtureDirectory(prefix='kn-update-process-',trusted_execution=True) as folder:
            path=Path(folder)/'host-narrations.sqlite';create_database(path)
            other=Path(folder)/'other.sqlite';create_database(other)
            ready=Path(folder)/'child-ready.json'
            source=('import sqlite3,sys,os,json;from pathlib import Path;'
                    'db=sqlite3.connect('+repr(str(path))+');db.execute("PRAGMA schema_version").fetchall();'
                    'Path('+repr(str(ready))+').write_text(json.dumps({"pid":os.getpid(),"python":sys.executable}));'
                    'sys.stdin.buffer.read(1);db.close()')
            with (Path(folder)/'child.stdout.log').open('xb') as out,(Path(folder)/'child.stderr.log').open('xb') as err:
                # A Windows venv redirector PID does not own the interpreter's DB.
                python=Path(getattr(sys,'_base_executable',sys.executable))
                child=subprocess.Popen([str(python),'-I','-S','-B','-c',source],stdin=subprocess.PIPE,stdout=out,stderr=err,cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    deadline=time.monotonic()+5
                    while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(ready.exists())
                    report=json.loads(ready.read_text())
                    self.assertEqual(report['pid'],child.pid)
                    self.assertEqual(Path(report['python']).resolve(),python.resolve())
                    with probe.NamespaceGuard(path) as guard:
                        native=guard.native
                        times=[probe.FileTime() for _ in range(4)]
                        self.assertTrue(native.k.GetProcessTimes(int(child._handle),*[ctypes.byref(value) for value in times]))
                        created=(times[0].high<<32)|times[0].low
                        captured=functions['capture_task_process'](child.pid,lambda:{'pid':child.pid})
                        self.assertEqual(captured['creation_filetime'],created)
                        with self.assertRaisesRegex(RuntimeError,'fixed_listener_pid_changed'):
                            functions['capture_task_process'](child.pid,lambda:{'pid':child.pid+1})
                        handles=functions['live_ledger_handles'](native,int(child._handle),created,guard.ledger)
                        self.assertEqual(len(handles),1)
                        self.assertEqual(functions['live_ledger_handles'](native,int(child._handle),created,guard.ledger),handles)
                        with probe.NamespaceGuard(other) as wrong:
                            with self.assertRaisesRegex(RuntimeError,'live_ledger_not_unique'):
                                functions['live_ledger_handles'](native,int(child._handle),created,wrong.ledger)
                        with self.assertRaises(probe.ProbeBlocked):functions['live_ledger_handles'](native,int(child._handle),created+1,guard.ledger)
                        connection=functions['Sqlite'](path,guard)
                        try:
                            functions['prepare_fence'](connection,EXPECTED,lambda:None)
                            native.k.TerminateProcess.argtypes=[probe.HANDLE,probe.U32];native.k.TerminateProcess.restype=ctypes.c_int
                            self.assertTrue(native.k.TerminateProcess(int(child._handle),0))
                            self.assertEqual(native.k.WaitForSingleObject(int(child._handle),5000),0)
                            self.assertEqual(child.wait(timeout=5),0)
                            functions['idle_native'](connection,EXPECTED,functions['FENCE'])
                            connection.execute('COMMIT')
                        finally:connection.close()
                finally:
                    if child.poll() is None:
                        child.stdin.write(b'x');child.stdin.flush();child.wait(timeout=5)
                    child.stdin.close()


if __name__=='__main__':unittest.main()
