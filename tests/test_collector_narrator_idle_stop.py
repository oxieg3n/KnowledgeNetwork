"""Empty-controller stop tests; no BLACKHAT-BASE operations or inference."""
import contextlib
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid


SOURCE = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Stop-EmptyNarratorController.ps1'


def embedded():
    source = SOURCE.read_text(encoding='utf-8-sig').split("$pythonSource = @'\n", 1)[1].split("\n'@", 1)[0]
    namespace = {'__name__': 'idle_stop_test'}
    exec(compile(source, str(SOURCE), 'exec'), namespace)
    return namespace


class IdleStopTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.code = embedded()
        self.code.update(ROOT=self.root, SPOOL=self.root / 'spool',
                         PYTHON=self.root / 'runtime/python/python.exe',
                         LAUNCHER=self.root / 'runtime/narrator-control-launch.py',
                         INTENT=self.root / 'broker-update-v1/update-intent.private.json')
        self.code['SPOOL'].mkdir()
        self.code['INTENT'].parent.mkdir()
        self.dbpath = self.code['SPOOL'] / 'narrator-control.sqlite'
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db:
            db.execute('CREATE TABLE requests(id TEXT PRIMARY KEY, operation TEXT NOT NULL, state TEXT NOT NULL, response TEXT)')
            db.execute('CREATE TABLE audit(request_id TEXT PRIMARY KEY, owner_sid TEXT NOT NULL, operation TEXT NOT NULL, outcome TEXT NOT NULL, duration_ms INTEGER NOT NULL, result_sha256 TEXT NOT NULL)')
        self.expected = {'owner_sid': 'S-1-5-21-1-2-3-1001', 'python_sha256': 'a' * 64,
                         'task_xml_sha256': hashlib.sha256(b'<Task/>').hexdigest()}
        self.intent = {'schema_version': 1, 'status': 'FULL_REPAIR_PREPARED',
                       'owner_sid': self.expected['owner_sid'], 'task_state': 'Running',
                       'publication_paused': True, 'task_xml': '<Task/>'}
        self.write_intent()
        self.process = {'pid': 123, 'owner_sid': self.expected['owner_sid'], 'command_line': 'fixture',
                        'creation_filetime': '100', 'parent_pid': 1, 'parents': []}
        self.snapshot = {'state': 4, 'instance_id': str(uuid.uuid4()), 'engine_pid': 123,
                         'processes': [self.process], 'listener_pids': []}
        self.calls = []
        self.code['argv'] = lambda _: [str(self.code['PYTHON']), '-I', '-S', '-B', str(self.code['LAUNCHER'])]
        owner = self
        class Held:
            pid, created = 123, 100
            def __init__(self, *args): pass
            def wait(self, remaining): owner.assertGreater(remaining, 0)
            def close(self): pass
        self.code['HeldProcess'] = Held
        self.code['task_call'] = self.task_call

    def write_intent(self):
        self.code['INTENT'].write_text(json.dumps(self.intent))

    def task_call(self, action, expected, **kwargs):
        self.calls.append(action)
        # A competing connection cannot acquire a writer lock at any native step.
        with contextlib.closing(sqlite3.connect(self.dbpath, timeout=.01)) as other:
            with self.assertRaises(sqlite3.OperationalError): other.execute('BEGIN IMMEDIATE')
        if action == 'query': return self.snapshot
        if action == 'stop': return {'stop_requested_once': True}
        if action == 'ready': return {'state': 3, 'instances': 0}
        self.fail('Unexpected action')

    def test_zero_ledger_lock_held_through_one_stop_and_exit(self):
        result = self.code['stop_empty'](self.expected)
        self.assertEqual(result, {'status': 'STOPPED_EMPTY_CONTROLLER',
                                 'held_process_signaled': True, 'task_state': 'Ready'})
        self.assertEqual(self.calls, ['query', 'stop', 'ready'])
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db:
            self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone(), (0,))
            self.assertEqual(db.execute('SELECT count(*) FROM audit').fetchone(), (0,))
        intent = json.loads((self.code['INTENT'].parent / 'empty-stop-intent.private.json').read_text())
        self.assertEqual(intent['stop_attempts'], 1)
        with self.assertRaises(FileExistsError): self.code['stop_empty'](self.expected)
        self.assertEqual(self.calls.count('stop'), 1)

    def test_any_request_or_audit_row_denies_before_task_query(self):
        for table in ['requests', 'audit']:
            with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db:
                if table == 'requests': db.execute("INSERT INTO requests VALUES('x','narrator-start','started',NULL)")
                else: db.execute("INSERT INTO audit VALUES('x','owner','op','PASS',1,'hash')")
            with self.assertRaisesRegex(self.code['Blocked'], 'controller_not_empty'):
                self.code['stop_empty'](self.expected)
            self.assertEqual(self.calls, [])
            with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db: db.execute('DELETE FROM ' + table)

    def test_journal_uncertainty_and_owned_listener_deny_before_stop(self):
        journal = Path(str(self.dbpath) + '-journal'); journal.write_bytes(b'unknown')
        with self.assertRaisesRegex(self.code['Blocked'], 'control_database_journal_uncertain'):
            self.code['stop_empty'](self.expected)
        journal.unlink()
        self.snapshot['listener_pids'] = [123]
        with self.assertRaisesRegex(self.code['Blocked'], 'controller_owns_api_listener'):
            self.code['stop_empty'](self.expected)
        self.assertNotIn('stop', self.calls)

    def test_task_or_process_uncertainty_denies_and_preserves_unmanaged_listener(self):
        self.snapshot['listener_pids'] = [999]
        self.snapshot['engine_pid'] = 999
        with self.assertRaisesRegex(self.code['Blocked'], 'task_association_unverified'):
            self.code['stop_empty'](self.expected)
        self.assertNotIn('stop', self.calls)
        self.snapshot['engine_pid'] = 123
        self.assertEqual(self.code['stop_empty'](self.expected)['status'], 'STOPPED_EMPTY_CONTROLLER')

    def test_wrong_intent_schema_or_identity_prevents_native_actions(self):
        for edit in [{'schema_version': True}, {'owner_sid': 'other'}, {'task_xml': '<Changed/>'},
                     {'status': 'COMPLETED'}, {'task_state': 'Ready'}, {'publication_paused': False}]:
            self.code['INTENT'].write_text(json.dumps({**self.intent, **edit}))
            with self.assertRaisesRegex(self.code['Blocked'], 'prepared_update_intent_unverified'):
                self.code['stop_empty'](self.expected)
            self.assertEqual(self.calls, [])

    def test_stop_uncertainty_never_retries_or_falls_back(self):
        original = self.code['task_call']
        def uncertain(action, *args, **kwargs):
            if action == 'stop':
                self.calls.append(action)
                raise self.code['Blocked']('task_stop_outcome_unverified')
            return original(action, *args, **kwargs)
        self.code['task_call'] = uncertain
        with self.assertRaisesRegex(self.code['Blocked'], 'task_stop_outcome_unverified'):
            self.code['stop_empty'](self.expected)
        self.assertEqual(self.calls, ['query', 'stop'])
        text = SOURCE.read_text()
        self.assertNotIn('TerminateProcess', text)
        self.assertNotIn('Stop-Process', text)
        self.assertNotIn('PROCESS_TERMINATE', text)

    def test_changed_table_shape_or_trigger_denies_before_query(self):
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db:
            db.execute('CREATE TRIGGER unexpected AFTER INSERT ON requests BEGIN DELETE FROM requests; END')
        with self.assertRaisesRegex(self.code['Blocked'], 'control_database_schema_unverified'):
            self.code['stop_empty'](self.expected)
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db, db:
            db.execute('DROP TRIGGER unexpected')
            db.execute('ALTER TABLE requests ADD COLUMN unexpected TEXT')
        with self.assertRaisesRegex(self.code['Blocked'], 'control_database_schema_unverified'):
            self.code['stop_empty'](self.expected)
        self.assertEqual(self.calls, [])

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows PowerShell 5 STDIN source entry')
    def test_ps5_stdin_entry_preserves_quotes_and_records_blocked_stage(self):
        text = SOURCE.read_text(encoding='utf-8-sig')
        program = text.split("$pythonSource = @'\n", 1)[1].split("\n'@", 1)[0]
        program = program.replace("ROOT=Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec')",
                                  'ROOT=Path(' + repr(self.root.as_posix()) + ')')
        self.intent['status'] = 'WRONG'; self.write_intent()
        entry = text[text.index('$encodedPayload='):text.index('$result=$output|ConvertFrom-Json')]
        python = Path(getattr(sys, '_base_executable', sys.executable))
        script = self.root / 'entry.ps1'
        script.write_text("$ErrorActionPreference='Stop'\n$python='" + python.as_posix() + "'\n"
            + "$pythonSource=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
            + base64.b64encode(program.encode()).decode() + "'))\n"
            + "$payload=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
            + base64.b64encode(json.dumps(self.expected).encode()).decode() + "'))\n" + entry
            + '\n[Console]::Out.Write(($output -join "`n"))\nexit 0\n')
        system = ctypes.create_unicode_buffer(32768)
        self.assertGreater(ctypes.windll.kernel32.GetSystemDirectoryW(system, len(system)), 0)
        ps = Path(system.value) / 'WindowsPowerShell/v1.0/powershell.exe'
        command = "& ([ScriptBlock]::Create([IO.File]::ReadAllText('" + str(script).replace("'", "''") + "')))"
        result = subprocess.run([str(ps), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', command],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode:
            private = Path(__file__).resolve().parents[2] / 'KnowledgeNetwork-Private'; private.mkdir(exist_ok=True)
            with (private / ('idle-stop-entry-' + uuid.uuid4().hex + '.private.json')).open('x') as stream:
                json.dump({'stdout': result.stdout.decode('utf-8', errors='replace'),
                           'stderr': result.stderr.decode('utf-8', errors='replace')}, stream)
        self.assertEqual(result.returncode, 0, 'Production STDIN entry did not compile/run')
        value = json.loads(result.stdout)
        self.assertEqual(value['status'], 'BLOCKED')
        self.assertEqual(value['stage'], 'intent')
        self.assertEqual(value['error'], 'prepared_update_intent_unverified')
        recorded = json.loads((self.code['INTENT'].parent / 'empty-stop-result.private.json').read_text())
        self.assertEqual(recorded['stage'], 'intent')


@unittest.skipUnless(os.name == 'nt' and os.environ.get('KN_NARRATOR_IDLE_STOP_FIXTURE') == '1',
                     'opt-in isolated FORGE Limited task, never host/narration')
class NativeIdleStopTests(unittest.TestCase):
    def test_native_limited_task_association_stop_and_disabled_run_denial(self):
        code = embedded()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            system = ctypes.create_unicode_buffer(32768)
            self.assertGreater(ctypes.windll.kernel32.GetSystemDirectoryW(system, len(system)), 0)
            powershell = Path(system.value) / 'WindowsPowerShell/v1.0/powershell.exe'
            acl = subprocess.run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$acl=Get-Acl -LiteralPath $r.path
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
Set-Acl -LiteralPath $r.path -AclObject $acl
'''], input=json.dumps({'path': str(root)}).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(acl.returncode, 0, 'New isolated fixture ACL setup failed')
            spool = root / 'spool'; spool.mkdir()
            runtime = root / 'runtime'; runtime.mkdir()
            launcher = runtime / 'narrator-control-launch.py'; marker = root / 'ready'; exit_flag = root / 'exit'
            launcher.write_text('import time\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ").write_text('ready')\n"
                + 'deadline=time.monotonic()+60\nwhile not Path(' + repr(str(exit_flag)) + ').exists() and time.monotonic()<deadline:time.sleep(.05)\n')
            dbpath = spool / 'narrator-control.sqlite'
            with contextlib.closing(sqlite3.connect(dbpath)) as db, db:
                db.execute('CREATE TABLE requests(id TEXT PRIMARY KEY, operation TEXT NOT NULL, state TEXT NOT NULL, response TEXT)')
                db.execute('CREATE TABLE audit(request_id TEXT PRIMARY KEY, owner_sid TEXT NOT NULL, operation TEXT NOT NULL, outcome TEXT NOT NULL, duration_ms INTEGER NOT NULL, result_sha256 TEXT NOT NULL)')
            upgrade = root / 'broker-update-v1'; upgrade.mkdir()
            python = Path(getattr(sys, '_base_executable', sys.executable))
            name = 'KNCollectorIdleStopTest-' + uuid.uuid4().hex
            def ps(source):
                result = subprocess.run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
                self.assertEqual(result.returncode, 0, 'Native fixture operation failed; no private output shown')
                return json.loads(result.stdout.decode('utf-8-sig')) if result.stdout.strip() else None
            setup = r'''
$ErrorActionPreference='Stop';$name='@NAME@';$path='\'+$name+'\'
$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$s=New-Object -ComObject Schedule.Service;$s.Connect();$f=$s.GetFolder('\').CreateFolder($name)
$action=New-ScheduledTaskAction -Execute '@PYTHON@' -Argument '-I -S -B @LAUNCHER@' -WorkingDirectory '@ROOT@'
$principal=New-ScheduledTaskPrincipal -UserId $owner -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -DisallowHardTerminate -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$definition=New-ScheduledTask -Action $action -Principal $principal -Settings $settings
Register-ScheduledTask -TaskPath $path -TaskName NativeFixture -InputObject $definition -ErrorAction Stop|Out-Null
$xml=Export-ScheduledTask -TaskPath $path -TaskName NativeFixture
Start-ScheduledTask -TaskPath $path -TaskName NativeFixture
@{owner_sid=$owner;xml=$xml}|ConvertTo-Json -Compress
'''.replace('@NAME@', name).replace('@PYTHON@', python.as_posix()).replace('@LAUNCHER@', launcher.as_posix()).replace('@ROOT@', root.as_posix())
            try:
                metadata = ps(setup)
                deadline = time.monotonic() + 10
                while not marker.exists() and time.monotonic() < deadline: time.sleep(.05)
                if not marker.exists():
                    diagnostic = ps("$ErrorActionPreference='Stop';$t=Get-ScheduledTask -TaskPath '\\" + name + "\\' -TaskName NativeFixture;$i=$t|Get-ScheduledTaskInfo;@{state=$t.State.ToString();last_result=$i.LastTaskResult}|ConvertTo-Json -Compress")
                    private = Path(__file__).resolve().parents[2] / 'KnowledgeNetwork-Private'
                    private.mkdir(exist_ok=True)
                    with (private / (name + '-startup.private.json')).open('x') as stream:
                        json.dump({**diagnostic, 'task_xml': metadata['xml'], 'launcher': str(launcher),
                                   'launcher_exists': launcher.exists(), 'launcher_source': launcher.read_text(),
                                   'python': str(python), 'python_exists': python.exists()}, stream)
                self.assertTrue(marker.exists(), 'Limited fixture never reached its ready marker')
                expected = {'owner_sid': metadata['owner_sid'], 'python_sha256': hashlib.sha256(python.read_bytes()).hexdigest(),
                            'task_xml_sha256': hashlib.sha256(metadata['xml'].encode()).hexdigest()}
                (upgrade / 'update-intent.private.json').write_text(json.dumps({'schema_version': 1,
                    'status': 'FULL_REPAIR_PREPARED', 'owner_sid': expected['owner_sid'], 'task_state': 'Running',
                    'publication_paused': True, 'task_xml': metadata['xml']}))
                code.update(ROOT=root, SPOOL=spool, PYTHON=python, LAUNCHER=launcher,
                            INTENT=upgrade / 'update-intent.private.json')
                code['TASK_SCRIPT'] = code['TASK_SCRIPT'].replace(
                    "C:/ProgramData/KnowledgeNetworkCollector/HostExec", root.as_posix()).replace(
                    '$python="$root/runtime/python/python.exe"', '$python="' + python.as_posix() + '"').replace(
                    '\\KnowledgeNetworkCollector\\', '\\' + name + '\\').replace(
                    "GetFolder('\\KnowledgeNetworkCollector')", "GetFolder('\\" + name + "')").replace(
                    "$name='NarratorControl'", "$name='NativeFixture'")
                snapshots = []
                original_call = code['task_call']
                def trace(action, *args, **kwargs):
                    value = original_call(action, *args, **kwargs)
                    if action == 'query': snapshots.append(value)
                    return value
                code['task_call'] = trace
                result = code['stop_empty'](expected)
                snapshot = snapshots[0]
                self.assertEqual(result['status'], 'STOPPED_EMPTY_CONTROLLER')
                disabled = ps(r'''
$ErrorActionPreference='Stop';$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\@NAME@').GetTask('NativeFixture');$t.Enabled=$false
$denied=$false
try{$null=$t.Run($null)}catch{$e=$_.Exception;while($null -ne $e){if($e.HResult -eq -2147216602){$denied=$true};$e=$e.InnerException}}
@{disabled_run_denied=$denied}|ConvertTo-Json -Compress
'''.replace('@NAME@', name))
                self.assertTrue(disabled['disabled_run_denied'])
                private = Path(__file__).resolve().parents[2] / 'KnowledgeNetwork-Private'
                private.mkdir(exist_ok=True)
                with (private / (name + '.private.json')).open('x') as stream:
                    json.dump({'scope': 'FORGE_BENIGN_LIMITED_FIXTURE_ONLY', 'snapshot': snapshot,
                               'result': result, 'disabled_run_denied': True, 'inference': False}, stream, indent=2)
            finally:
                exit_flag.write_text('exit')
                ps(r'''
$ErrorActionPreference='Stop';$name='@NAME@';$path='\'+$name+'\'
$s=New-Object -ComObject Schedule.Service;$s.Connect();$f=$null
try{$f=$s.GetFolder('\'+$name)}catch{if($_.Exception.HResult -ne -2147024894){throw};exit 0}
$tasks=$f.GetTasks(1)
if($tasks.Count -gt 1){throw 'Unexpected fixture folder membership; preserve.'}
if($tasks.Count -eq 1){
 $t=$f.GetTask('NativeFixture');$deadline=[DateTime]::UtcNow.AddSeconds(5)
 while($t.State -eq 4 -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 50}
 if($t.State -notin @(1,3) -or $t.GetInstances(0).Count -ne 0){throw 'Fixture did not exit cooperatively; preserve.'}
 Unregister-ScheduledTask -TaskPath $path -TaskName NativeFixture -Confirm:$false
}
$s.GetFolder('\').DeleteFolder($name,0)
'''.replace('@NAME@', name))


if __name__ == '__main__':
    unittest.main()
