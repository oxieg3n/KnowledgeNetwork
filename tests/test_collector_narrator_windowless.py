"""Windowless supervisor fixtures; no host access, model load or parity replay."""
import ast
from contextlib import closing
import http.client
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock

from tests.fixture_retention import FixtureDirectory
from tests.test_collector_narrator_batch_update import helper,Adapter,create_database,EXPECTED

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/collector/host-tools/Start-KnowledgeNetworkNarratorWindowless.ps1'


def driver():
    source=SOURCE.read_text().split("$driver=@'\n",1)[1].split("\n'@",1)[0];tree=ast.parse(source)
    constants={'WORK','ROOT','DATA','NEW','PYTHONW','PYTHONW_PIN','STEM','CHECKPOINT','PINS','DATA_PINS','TASK_READ','TASK_CHANGE'}
    nodes=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))
           or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in constants for target in node.targets)]
    ns={'__name__':'owned_windowless_fixture'};exec(compile(ast.Module(body=nodes,type_ignores=[]),'owned-windowless-fixture','exec'),ns)
    return ns,source


class WindowlessTests(unittest.TestCase):
    def test_only_supervisor_launcher_changes_and_separate_pins_remain(self):
        functions,_=driver();installer=(ROOT/'docs/collector/host-tools/Install-KnowledgeNetworkNarratorStandalone.ps1').read_text()
        original=installer.split("$launcher=@'\n",1)[1].split("\n'@",1)[0]
        batch=helper()[0]['new_launcher'](original).encode();windowless=functions['supervisor_launcher'](batch)
        self.assertIn(b"config['supervisor_python_sha256']",windowless)
        self.assertIn(b"code-windowless-v1",windowless)
        self.assertNotEqual(batch,windowless);ast.parse(windowless)
        self.assertEqual(windowless.count(b"store=NarratorStore(ROOT/'data',reviewed,segment_batches=config['segment_batches'])"),1)
        self.assertIn(b"'missing_bearer':absent,'wrong_bearer':wrong,'authenticated_health':code",windowless)

    def test_schema2_exact_jobs_and_unknown_hold_gates_reuse_existing_fence(self):
        functions,_=driver();old=helper()[0];old['idle_native']=functions['schema2_idle']
        with FixtureDirectory(prefix='kn-windowless-schema-') as folder:
            path=Path(folder)/'host-narrations.sqlite';create_database(path)
            with closing(sqlite3.connect(path)) as db,db:
                db.execute('ALTER TABLE jobs ADD COLUMN segments TEXT');db.execute('ALTER TABLE jobs ADD COLUMN cues TEXT');db.execute("UPDATE metadata SET value='2' WHERE key='schema_version'")
            db=Adapter(path)
            try:
                old['prepare_fence'](db,EXPECTED,lambda:None);db.execute('COMMIT')
                self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema_version'"),[('2',)])
                db.execute('BEGIN IMMEDIATE');old['clear_own_fence'](db,EXPECTED);db.execute('COMMIT')
                db.execute("INSERT INTO metadata VALUES('execution_hold','outcome_unknown')")
                with self.assertRaisesRegex(RuntimeError,'schema2_hold_changed'):functions['schema2_idle'](db,EXPECTED)
                self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='execution_hold'"),[('outcome_unknown',)])
            finally:db.close()

    def test_task_contract_rejects_visible_wrong_image_or_fresh_children(self):
        functions,_=driver();config={'owner_sid':'owned-fixture'}
        value={'xml':'owned','sddl':'private','owner_sid':'owned-fixture','enabled':True,'state':4,'logon':3,'runlevel':0,'actions':1,'triggers':0,'multiple':2,'hard_terminate':False,'execution_limit':'PT0S',
               'execute':str(functions['PYTHONW']),'arguments':'-I -S -B '+str(functions['NEW']/'narrator-standalone.py').replace('\\','/'),'working_directory':str(functions['NEW']),
               'instances':1,'listeners':[{'LocalAddress':'127.0.0.1'}],'process_owner':'owned-fixture','image':str(functions['PYTHONW']),'children':[],'pid':123,
               'command_line':subprocess.list2cmdline([str(functions['PYTHONW']),'-I','-S','-B',str(functions['NEW']/'narrator-standalone.py')])}
        ns={'ps':lambda code:dict(value),'write':Mock(),'capture_task_process':lambda pid,read:{**read(),'creation_filetime':12345},'subprocess':subprocess}
        self.assertEqual(functions['task_proof'](ns,config,'owned','private',live=True)['creation_filetime'],12345)
        for edit in ({'image':'python.exe'},{'children':[{'pid':3336}]},{'instances':0},{'runlevel':1},{'process_owner':'other'}):
            ns['capture_task_process']=lambda pid,read,edit=edit:{**read(),**edit,'creation_filetime':12345}
            with self.subTest(edit=edit),self.assertRaises(RuntimeError):functions['task_proof'](ns,config,'owned','private',live=True)

    def test_start_precedes_checks_and_parity_cannot_be_replayed(self):
        _,source=driver();tree=ast.parse(source);main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main');text=ast.get_source_segment(source,main)
        self.assertLess(text.index("change_task(ns,'start'"),text.index("ns['bind_running']"))
        self.assertLess(text.index("with common['voice_lease']"),text.index("connection=ns['Sqlite']"))
        self.assertIn("ns['idle_native']=schema2_idle",text)
        for forbidden in ("ns['parity_task']",'WindowsScriptRunner','gpu_baseline','nvidia-smi','TerminateProcess','tailscale'):
            self.assertNotIn(forbidden,source)
        self.assertIn("if db_guard:db_guard.close()",text);self.assertIn("if lock_guard:lock_guard.close()",text)
        self.assertIn("updated=dict(config,supervisor_python_sha256=PYTHONW_PIN)",text)

    def test_ready_poll_tolerates_create_new_before_complete_json_without_restart(self):
        functions,_=driver();path=Mock();base=Mock()
        base.glob.side_effect=lambda pattern:[] if 'failed' in pattern else [path]
        path.read_text.side_effect=[FileNotFoundError(),'{',json.dumps({'status':'complete'})]
        functions['time']=Mock(monotonic=Mock(return_value=0))
        self.assertEqual(functions['await_ready'](base),(path,{'status':'complete'}))
        self.assertEqual(path.read_text.call_count,3)
        self.assertEqual(functions['time'].sleep.call_count,2)


@unittest.skipUnless(os.name=='nt' and os.environ.get('COLLECTOR_NATIVE_WINDOWLESS')=='1','Opt-in own pythonw loopback fixture; no host or model')
class NativeWindowlessTests(unittest.TestCase):
    def test_native_parser(self):
        code="$e=$null;$t=$null;$null=[Management.Automation.Language.Parser]::ParseFile([Console]::In.ReadToEnd(),[ref]$t,[ref]$e);if($e.Count){$e|Out-String;exit 1};'PARSE_PASS'"
        r=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],input=str(SOURCE),capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_pythonw_listener_no_console_no_children_and_authentication(self):
        pythonw=Path(getattr(sys,'_base_executable',sys.executable)).with_name('pythonw.exe')
        self.assertTrue(pythonw.is_file())
        with FixtureDirectory(prefix='kn-pythonw-listener-',trusted_execution=True) as folder:
            folder=Path(folder);ready=folder/'ready.json';stop=folder/'stop';script=folder/'server.py'
            script.write_text('''import ctypes,json,os,sys,threading,time
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
HERE=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  code=200 if self.headers.get('Authorization')=='Bearer owned-synthetic-windowless-fixture' else 401
  self.send_response(code);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')
server=HTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05});thread.start()
kernel=ctypes.WinDLL('kernel32');kernel.GetConsoleWindow.argtypes=[];kernel.GetConsoleWindow.restype=ctypes.c_void_p
(HERE/'ready.json').write_text(json.dumps({'pid':os.getpid(),'image':sys.executable,'console':kernel.GetConsoleWindow(),'port':server.server_port}))
deadline=time.monotonic()+20
while not (HERE/'stop').exists() and time.monotonic()<deadline:time.sleep(.02)
server.shutdown();thread.join();server.server_close()
''',encoding='utf-8')
            with (folder/'stdout.private.log').open('xb') as out,(folder/'stderr.private.log').open('xb') as err:
                child=subprocess.Popen([str(pythonw),'-I','-S','-B',str(script)],stdout=out,stderr=err,cwd=folder)
                try:
                    deadline=time.monotonic()+5
                    while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    self.assertTrue(ready.exists());value=json.loads(ready.read_text())
                    self.assertEqual(value['pid'],child.pid);self.assertEqual(Path(value['image']).resolve(),pythonw.resolve());self.assertIsNone(value['console'])
                    statuses=[]
                    for auth in (None,'Bearer wrong','Bearer owned-synthetic-windowless-fixture'):
                        c=http.client.HTTPConnection('127.0.0.1',value['port'],timeout=3)
                        try:c.request('GET','/',headers={} if auth is None else {'Authorization':auth});r=c.getresponse();statuses.append(r.status);r.read()
                        finally:c.close()
                    self.assertEqual(statuses,[401,401,200])
                    code="@((Get-CimInstance Win32_Process -Filter 'ParentProcessId="+str(child.pid)+"')).Count|ConvertTo-Json -Compress"
                    r=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=10)
                    self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout),0)
                finally:
                    stop.write_text('owned fixture stop')
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)


if __name__=='__main__':unittest.main()
