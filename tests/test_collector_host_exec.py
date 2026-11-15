"""Forced-command framing and bounded handlers; no host deployment or inference."""
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from youtube_ops import collector_host_exec as host

SID = 'S-1-5-21-100-200-300-1001'


class HostExecTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'runtime').mkdir(); (self.root / 'audit').mkdir(); (self.root / 'receipts').mkdir()
        self.patch = patch.object(host, 'ROOT', self.root); self.patch.start(); self.addCleanup(self.patch.stop)
        self.config = {'schema_version': 1, 'execution_sid': SID, 'forge_address': '100.100.100.10',
                       'python_sha256': '1' * 64, 'powershell_sha256': '2' * 64}
        self.env = {'SSH_ORIGINAL_COMMAND': 'health', 'SSH_CONNECTION': '100.100.100.10 12345 100.100.100.20 22230'}

    def test_exact_allowlist_and_source_identity(self):
        for operation in host.OPERATIONS:
            self.assertEqual(host.authorize(self.config, dict(self.env, SSH_ORIGINAL_COMMAND=operation), SID, False), operation)
        for command in ('', ' health', 'health ', 'health\n', 'health;whoami', 'powershell', 'cmd /c whoami',
                        'native-port-443', '../health', 'self-test x', 'HEALTH', 'health\x00', 'hеalth'):
            with self.subTest(command=command), self.assertRaisesRegex(host.Denied, 'command_denied'):
                host.authorize(self.config, dict(self.env, SSH_ORIGINAL_COMMAND=command), SID, False)
        for env in (dict(self.env, SSH_TTY=''), dict(self.env, SSH_CONNECTION='100.100.100.11 1 100.100.100.20 22230'),
                    dict(self.env, SSH_CONNECTION='100.100.100.10 0 100.100.100.20 22230'),
                    dict(self.env, SSH_CONNECTION=self.env['SSH_CONNECTION']+'\n')):
            with self.assertRaises(host.Denied): host.authorize(self.config, env, SID, False)
        for identity, elevated in ((SID, True), (SID+'0', False)):
            with self.assertRaisesRegex(host.Denied, 'execution_identity_denied'):
                host.authorize(self.config, self.env, identity, elevated)

    def test_configuration_is_closed_and_pins_are_required(self):
        for config in (dict(self.config, command='anything'), dict(self.config, python_sha256='bad'),
                       dict(self.config, forge_address='8.8.8.8'), dict(self.config, execution_sid='administrator')):
            with self.assertRaises(host.Denied): host.authorize(config, self.env, SID, False)

    def test_local_json_limits_paths_and_reparse_denial(self):
        path = self.root / 'file.json'; path.write_text('{"status":"ready"}')
        self.assertEqual(host.read_object(path)[0], {'status': 'ready'})
        path.write_bytes(b' ' * (host.MAX_OUTPUT + 1))
        with self.assertRaisesRegex(host.Denied, 'file_limit'): host.read_object(path)
        with self.assertRaisesRegex(host.Denied, 'untrusted_path'): host.local_path(Path('../outside'))
        path.write_text('{}')
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(host.Denied, 'untrusted_path'): host.read_object(path)
        for raw in ('{"status":"ready","status":"blocked"}', '{"status":NaN}'):
            path.write_text(raw)
            with self.assertRaises(host.Denied): host.read_object(path)

    def broker_fixture(self, body=None, *, error=None):
        folder = self.root / 'runtime/youtube_ops'; folder.mkdir(exist_ok=True)
        source = ('def broker_request(operation, request_id, cancel):\n' +
                  ('    raise Error()\n' if error else
                   '    return {"schema_version":1,"request_id":request_id,"operation":operation,"status":"PASS","result":{"live_authenticated":True}}\n'))
        if error:
            source = f'class Error(Exception):\n    code={error!r}\n' + source
        if body:
            source = 'def broker_request(operation, request_id, cancel):\n    ' + body + '\n'
        path = folder / 'collector_narrator_pipe.py'; path.write_bytes(source.encode())
        (self.root / 'narrator-broker.json').write_text(json.dumps({
            'schema_version': 1, 'files': {'collector_narrator_pipe.py': hashlib.sha256(source.encode()).hexdigest()}}))
        return path

    def test_broker_operations_and_original_request_identity(self):
        self.broker_fixture()
        request_id = 'a' * 32
        for operation in host.BROKER_OPERATIONS:
            result = host.perform(operation, self.config, SID, threading.Event(), request_id)
            self.assertEqual(result['request_id'], request_id)
            self.assertTrue(result['result']['live_authenticated'])
        for operation in ('narrator-start x', 'narrator-start;whoami', '../narrator-start'):
            with self.assertRaisesRegex(host.Denied, 'broker_request_denied'):
                host.broker_operation(operation, request_id, threading.Event())

    def test_broker_transport_replacement_and_pinned_capture(self):
        path = self.broker_fixture()
        path.write_text('raise RuntimeError("unreviewed replacement")')
        with self.assertRaisesRegex(host.BrokerDenied, 'broker_transport_changed'):
            host.broker_operation('narrator-health', 'a' * 32, threading.Event())
        self.broker_fixture()
        original_compile = compile
        def replace_after_capture(source, filename, mode):
            path.write_text('raise RuntimeError("unreviewed replacement")')
            return original_compile(source, filename, mode)
        with patch('builtins.compile', side_effect=replace_after_capture):
            result = host.broker_operation('narrator-health', 'a' * 32, threading.Event())
        self.assertTrue(result['result']['live_authenticated'])

    def test_broker_cancellation_timeout_permission_and_response_checks(self):
        request_id = 'a' * 32
        cancel = threading.Event(); cancel.set()
        with self.assertRaisesRegex(host.BrokerDenied, 'broker_cancelled_before_request'):
            host.broker_operation('narrator-start', request_id, cancel)
        for code in ('broker_timeout_outcome_unknown', 'broker_cancelled_outcome_unknown', 'broker_permission_denied'):
            self.broker_fixture(error=code)
            with self.assertRaisesRegex(host.BrokerDenied, code) as failure:
                host.broker_operation('narrator-start', request_id, threading.Event())
            self.assertEqual(failure.exception.request_id, request_id)
        for body, error in (
                ('return {"schema_version":1,"request_id":"b"*32,"operation":operation,"status":"PASS","result":{}}', 'broker_response_mismatch'),
                ('return {"schema_version":1,"request_id":request_id,"operation":operation,"status":"PASS","result":{"text":"x"*65536}}', 'broker_response_invalid'),
                ('return {"schema_version":1,"request_id":request_id,"operation":operation,"status":"BLOCKED","error":"private token and path"}', 'broker_response_invalid'),
                ('return {"schema_version":1,"request_id":request_id,"operation":operation,"status":"BLOCKED","error":"narrator_unmanaged"}', 'narrator_unmanaged')):
            self.broker_fixture(body)
            with self.assertRaisesRegex(host.BrokerDenied, error):
                host.broker_operation('narrator-health', request_id, threading.Event())

    def run_broker_main(self, *, audit=None):
        (self.root / 'config.json').write_text(json.dumps(self.config))
        executable = self.root / 'runtime/python-fixture.exe'
        executable.write_bytes(b'regular test interpreter identity; never executed')
        with patch.object(host.sys, 'executable', str(executable)), \
             patch.object(host, '__file__', str(self.root / 'runtime/collector_host_exec.py')), \
             patch.object(host.sys, 'argv', ['dispatcher.py']), \
             patch.dict(host.os.environ, dict(self.env, SSH_ORIGINAL_COMMAND='narrator-start'), clear=True), \
             patch.object(host, 'windows_identity', return_value=(SID, False)), \
             patch.object(host, 'digest', return_value='1' * 64), \
             patch.object(host, 'own_process_tree', return_value=1), \
             patch.object(host, 'ensure_quiescent'), \
             patch.object(host.sys, 'stdout', new_callable=io.StringIO) as output:
            if audit:
                with patch.object(host, 'audit', side_effect=audit): code = host.main()
            else:
                code = host.main()
        return code, json.loads(output.getvalue())

    def test_broker_main_fixture_uses_regular_executable_not_runner_symlink(self):
        self.broker_fixture(error='broker_timeout_outcome_unknown')
        original = host.sys.executable
        with patch.object(host.sys, 'executable', str(self.root / 'missing-runner-link')):
            code, response = self.run_broker_main()
            self.assertEqual(host.sys.executable, str(self.root / 'missing-runner-link'))
        self.assertEqual(host.sys.executable, original)
        executable = self.root / 'runtime/python-fixture.exe'
        self.assertTrue(executable.is_file()); self.assertFalse(executable.is_symlink())
        self.assertEqual(host.local_path(executable), executable)
        self.assertEqual(code, 1)
        self.assertEqual(response['error'], 'broker_timeout_outcome_unknown')

    def test_broker_main_audits_same_request_and_never_exposes_permission_error(self):
        self.broker_fixture(error='broker_timeout_outcome_unknown')
        code, response = self.run_broker_main()
        self.assertEqual(code, 1); self.assertEqual(response['error'], 'broker_timeout_outcome_unknown')
        records = [json.loads(x) for x in (self.root / 'audit/execution.jsonl').read_text().splitlines()]
        self.assertEqual({r['request_id'] for r in records}, {response['request_id']})
        self.assertEqual(records[-1]['operation'], 'narrator-start')
        with patch.object(host, 'broker_operation', side_effect=PermissionError('SECRET must not be returned')):
            _, response = self.run_broker_main()
        self.assertEqual(response['error'], 'operation_unverified'); self.assertNotIn('SECRET', json.dumps(response))
        with patch.object(host, 'broker_operation') as forward:
            code, response = self.run_broker_main(audit=host.Denied('audit_busy'))
        self.assertEqual(code, 1); forward.assert_not_called()

    @unittest.skipUnless(os.name == 'nt' and os.environ.get('KN_CONTROL_TASK_FIXTURE') == '1', 'opt-in isolated native Task Scheduler fixture')
    def test_native_control_task_validation_and_single_start(self):
        receipt = Path(__file__).resolve().parents[1] / 'output/host-exec-control-task-fixture-v2.json'
        if receipt.exists(): self.skipTest('Native fixture receipt already preserved')
        with tempfile.TemporaryDirectory(prefix='kn-control-task-') as folder:
            base=Path(folder); (base/'runtime').mkdir()
            marker=base/'marker.txt'
            (base/'runtime/narrator-control-launch.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("limited fixture only")\n')
            ps = r'''
$ErrorActionPreference='Stop'
$fixture=$env:KN_CONTROL_FIXTURE.Replace('\','/');$exe=$env:KN_CONTROL_PYTHON.Replace('\','/')
$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;$fake='S-1-5-21-1-2-3-1002'
foreach ($item in @(Get-Item -LiteralPath $fixture)+@(Get-ChildItem -LiteralPath $fixture -Recurse -Force)) {
 $acl=Get-Acl -LiteralPath $item.FullName
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($owner),'FullControl','Allow'))
 Set-Acl -LiteralPath $item.FullName -AclObject $acl
}
@{owner_sid=$owner;bridge_sid=$fake} | ConvertTo-Json | Set-Content -LiteralPath "$fixture/narrator-broker.json" -Encoding UTF8
$id='KNCollectorControlDispatchTest-'+[guid]::NewGuid().ToString('N')
if ($id -cnotmatch '^KNCollectorControlDispatchTest-[a-f0-9]{32}$') { throw 'Fixture name' }
$path='\'+$id+'\';$name='NarratorControl'
$service=New-Object -ComObject Schedule.Service;$service.Connect();$top=$service.GetFolder('\')
$sddl="O:${owner}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${owner})(A;;0x1200a9;;;${fake})"
$folder=$null;$registered=$false;$started=$false
$script=$env:KN_CONTROL_SCRIPT.Replace('C:/ProgramData/KnowledgeNetworkCollector/HostExec',$fixture).Replace("[Security.Principal.WindowsIdentity]::GetCurrent().User.Value",("'"+$fake+"'")).Replace("'\KnowledgeNetworkCollector'",("'\"+$id+"'"))
# Replace the literal source expression, not its expanded caller variable.
$script=$script.Replace('$python="$root/runtime/python/python.exe"',('$python="'+$exe+'"'))
function Invoke-Fixture([string]$Action) {
 $out=[IO.StringWriter]::new();$saved=[Console]::Out
 try { [Console]::SetOut($out);. ([ScriptBlock]::Create($script.Replace('__ACTION__',$Action))) } finally { [Console]::SetOut($saved) }
 return ($out.ToString() | ConvertFrom-Json)
}
function Register-Fixture([string]$Mode) {
 $action=New-ScheduledTaskAction -Execute $exe -Argument "-I -S -B $fixture/runtime/narrator-control-launch.py" -WorkingDirectory "$fixture/runtime"
 if ($Mode -eq 'action') { $action=New-ScheduledTaskAction -Execute $exe -Argument '-V' -WorkingDirectory "$fixture/runtime" }
 if ($Mode -eq 'extra') { $action=@($action,$action) }
 $level=if ($Mode -eq 'elevated') {'Highest'} else {'Limited'}
 $principal=New-ScheduledTaskPrincipal -UserId $owner -LogonType Interactive -RunLevel $level
 $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DisallowHardTerminate
 Register-ScheduledTask -TaskPath $path -TaskName $name -InputObject (New-ScheduledTask -Action $action -Principal $principal -Settings $settings) -Force | Out-Null
 $folder.GetTask($name).SetSecurityDescriptor($sddl,16)
}
try {
 $folder=$top.CreateFolder($id,$sddl)
 Register-Fixture good;$registered=$true
 $result=Invoke-Fixture ''
 if ($result.state -ne 3 -or $result.start_requested) { throw 'Actual status failed' }
 foreach ($mode in @('action','elevated','extra')) {
  Register-Fixture $mode;$denied=$false
  try { $null=Invoke-Fixture '' } catch { $denied=$true }
  if (-not $denied) { throw 'Changed native task accepted' }
 }
 Register-Fixture good
 $start='if ($state -ne 3) { throw "task_not_ready" };$null=$t.Run($null);$requested=$true'
 $result=Invoke-Fixture $start
 $started=$true
 if (-not $result.start_requested) { throw 'Run not requested' }
 $deadline=[DateTime]::UtcNow.AddSeconds(20)
 while (-not (Test-Path -LiteralPath "$fixture/marker.txt") -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
 if (-not (Test-Path -LiteralPath "$fixture/marker.txt")) { throw ('Benign marker missing, native result '+$folder.GetTask($name).LastTaskResult) }
 while ($folder.GetTask($name).State -eq 4 -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
 if ($folder.GetTask($name).State -eq 4) { throw 'Fixture still running' }
} finally {
 if ($registered) { Unregister-ScheduledTask -TaskPath $path -TaskName $name -Confirm:$false }
 if ($null -ne $folder) { $top.DeleteFolder($id,0) }
}
if (@(Get-ScheduledTask | Where-Object TaskPath -ceq $path).Count) { throw 'Cleanup failed' }
@{status='PASS_FORGE_NATIVE_FIXED_TASK_VALIDATOR';positive_status=$true;invalid_action_denied=$true;elevation_denied=$true;extra_action_denied=$true;benign_start=$started;cleaned=$true} | ConvertTo-Json -Compress
'''
            result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',ps], env=dict(os.environ,KN_CONTROL_FIXTURE=folder,KN_CONTROL_PYTHON=sys.executable,KN_CONTROL_SCRIPT=host.CONTROL_TASK_SCRIPT),capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with receipt.open('x',encoding='utf-8') as stream: stream.write(result.stdout)

    @patch.dict(sys.modules, {'_winapi': Mock()})
    def test_control_task_fixed_commands_and_closed_results(self):
        for operation in host.CONTROL_OPERATIONS:
            start = operation.endswith('-start')
            result = {'state': 3, 'last_result': 0, 'start_requested': start}
            with patch.object(host, 'fixed_powershell', return_value=json.dumps(result)) as runner:
                if start:
                    value = host.perform(operation, self.config, SID, threading.Event())
                    self.assertTrue(value['start_requested']); self.assertFalse(value['broker_ready'])
                    self.assertEqual(runner.call_args.args[0].count('$t.Run('), 1)
                else:
                    import _winapi
                    with patch.object(_winapi, 'WaitNamedPipe') as waited, patch.object(_winapi, 'CreateFile') as opened:
                        value = host.perform(operation, self.config, SID, threading.Event())
                    self.assertEqual(value['pipe_snapshot'], 'available_not_authenticated')
                    self.assertEqual(value['pipe_winerror'], 0)
                    waited.assert_called_once_with(r'\\.\pipe\KnowledgeNetworkCollectorNarratorControlV1', 0); opened.assert_not_called()
                    self.assertNotIn('$t.Run(', runner.call_args.args[0])
                runner.assert_called_once()
        import _winapi
        for code, category in ((2, 'absent'), (121, 'busy'), (231, 'busy'), (5, 'access_denied')):
            error=OSError('private diagnostic must not be returned');error.winerror=code
            raw=json.dumps({'state': 4, 'last_result': 0, 'start_requested': False})
            with patch.object(host, 'fixed_powershell', return_value=raw), patch.object(_winapi, 'WaitNamedPipe', side_effect=error), patch.object(_winapi, 'CreateFile') as opened:
                value=host.control_task_operation('narrator-control-status', self.config, threading.Event())
            self.assertEqual(value['pipe_snapshot'], category);self.assertEqual(value['pipe_winerror'], code)
            self.assertNotIn('private', json.dumps(value));opened.assert_not_called()
        for response in ({'state': True, 'last_result': 0, 'start_requested': True},
                         {'state': 4, 'last_result': 0, 'start_requested': True},
                         {'state': 3, 'last_result': 0, 'start_requested': True, 'secret': 'denied'}):
            with patch.object(host, 'fixed_powershell', return_value=json.dumps(response)) as runner:
                with self.assertRaisesRegex(host.Denied, 'control_start_outcome_unknown'):
                    host.control_task_operation('narrator-control-start', self.config, threading.Event())
                runner.assert_called_once()
        for error in ('operation_timeout', 'cancelled', 'operation_failed'):
            with patch.object(host, 'fixed_powershell', side_effect=host.Denied(error)) as runner:
                with self.assertRaisesRegex(host.Denied, 'control_start_outcome_unknown'):
                    host.control_task_operation('narrator-control-start', self.config, threading.Event())
                runner.assert_called_once()
        with self.assertRaisesRegex(host.Denied, 'command_denied'):
            host.control_task_operation('narrator-control-start anything', self.config, threading.Event())
        script=host.CONTROL_TASK_SCRIPT
        for guard in ('InteractiveToken','LeastPrivilege','IgnoreNew','ExecutionTimeLimit','AllowHardTerminate',
                      'DisallowStartIfOnBatteries','RestartOnFailure','GetSecurityDescriptor(7)','0x1200A9'):
            self.assertIn(guard, script)

    def test_snapshot_is_fixed_and_never_claims_live_auth(self):
        with self.assertRaisesRegex(host.Denied, 'narrator_snapshot_missing'):
            host.perform('narrator-status', self.config, SID, threading.Event())
        snapshot = self.root / 'receipts/narrator-status.json'
        snapshot.write_text(json.dumps({'status': 'PASS_LOCAL_AUTH_ONLY', 'secret': 'must never return'}))
        result = host.perform('narrator-status', self.config, SID, threading.Event())
        self.assertFalse(result['live_authenticated']); self.assertNotIn('secret', json.dumps(result))
        self.assertEqual(result['scope'], 'retained_snapshot_only')

    def test_native_port_occupied_does_not_bind(self):
        with patch.object(host, 'fixed_powershell', return_value='1'), patch.object(host.socket, 'socket') as socket:
            result = host.perform('native-port-9443', self.config, SID, threading.Event())
        self.assertFalse(result['available_snapshot']); socket.assert_not_called()

    def test_native_port_checks_both_families_and_never_listens(self):
        first, second = Mock(), Mock()
        with patch.object(host, 'fixed_powershell', return_value='0'), \
             patch.object(host.socket, 'SO_EXCLUSIVEADDRUSE', 4, create=True), \
             patch.object(host.socket, 'socket', side_effect=[first, second]):
            result = host.perform('native-port-9443', self.config, SID, threading.Event())
        self.assertTrue(result['available_snapshot'])
        first.bind.assert_called_once_with(('0.0.0.0', 9443)); second.bind.assert_called_once_with(('::', 9443))
        first.listen.assert_not_called(); second.listen.assert_not_called()
        first.close.assert_called_once(); second.close.assert_called_once()

    def test_native_bind_failure_closes_sockets(self):
        first = Mock(); first.bind.side_effect = OSError('private path must not appear')
        with patch.object(host, 'fixed_powershell', return_value='0'), \
             patch.object(host.socket, 'SO_EXCLUSIVEADDRUSE', 4, create=True), \
             patch.object(host.socket, 'socket', return_value=first):
            with self.assertRaisesRegex(host.Denied, '^native_bind_unavailable$'):
                host.perform('native-port-9443', self.config, SID, threading.Event())
        first.close.assert_called_once()

    def test_fixed_powershell_cancellation_and_timeout_kill_owned_root(self):
        cancel = threading.Event(); cancel.set()
        with patch.object(host.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(host.Denied, 'cancelled'):
                host.fixed_powershell(host.IDENTITY_SCRIPT, self.config, cancel)
        launch.assert_not_called()
        for cancelled, timeout, error in ((False, -1, 'operation_timeout'),):
            process = Mock(); process.poll.return_value = None
            cancel = threading.Event()
            if cancelled: cancel.set()
            with patch.object(host, 'local_path', side_effect=lambda p: p), \
                 patch.object(host, 'digest', return_value='2' * 64), \
                 patch.object(host.subprocess, 'Popen', return_value=process) as launch:
                with self.assertRaisesRegex(host.Denied, error):
                    host.fixed_powershell(host.IDENTITY_SCRIPT, self.config, cancel, timeout=timeout)
            process.kill.assert_called_once(); process.wait.assert_called_once_with(timeout=5)
            kwargs = launch.call_args.kwargs
            self.assertFalse(kwargs['shell']); self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertNotIn('SSH_ORIGINAL_COMMAND', kwargs['env'])

    def test_unconfirmed_child_shutdown_fails_closed(self):
        process = Mock(); process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired('fixed operation', 5)
        with patch.object(host, 'local_path', side_effect=lambda p: p), \
             patch.object(host, 'digest', return_value='2' * 64), \
             patch.object(host.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(host.Denied, 'process_outcome_unverified'):
                host.fixed_powershell(host.IDENTITY_SCRIPT, self.config, threading.Event(), timeout=-1)

    def test_self_test_compares_actual_child_sid(self):
        with patch.object(host, 'fixed_powershell', return_value=SID):
            self.assertEqual(host.perform('self-test', self.config, SID, threading.Event())['fixed_powershell'], 'PASS')
        with patch.object(host, 'fixed_powershell', return_value=SID+'0'):
            with self.assertRaisesRegex(host.Denied, 'powershell_identity_mismatch'):
                host.perform('self-test', self.config, SID, threading.Event())

    def test_audit_redacted_record_is_durable_json(self):
        with patch.object(host.os, 'fsync', wraps=os.fsync) as sync:
            host.audit({'operation': 'denied', 'outcome': 'command_denied', 'execution_sid': SID})
        sync.assert_called_once()
        self.assertEqual(json.loads((self.root / 'audit/execution.jsonl').read_text())['operation'], 'denied')

    def test_audit_limit_and_hardlinks_fail_closed_without_truncation(self):
        path = self.root / 'audit/execution.jsonl'
        path.write_bytes(b'x' * 100)
        with patch.object(host, 'MAX_AUDIT', 100):
            with self.assertRaisesRegex(host.Denied, 'audit_limit'): host.audit({'operation': 'health'})
        self.assertEqual(path.read_bytes(), b'x' * 100)
        linked = self.root / 'other'
        os.link(path, linked)
        with self.assertRaisesRegex(host.Denied, 'audit_path_untrusted'): host.audit({'operation': 'health'})
        self.assertEqual(linked.read_bytes(), b'x' * 100)

    def test_main_denies_extra_arguments_before_execution(self):
        with patch.object(host.sys, 'argv', ['dispatcher.py', 'whoami']), \
             patch.object(host, 'audit') as audit, patch.object(host, 'perform') as perform, \
             patch.object(host.sys, 'stdout', new_callable=io.StringIO) as output:
            self.assertEqual(host.main(), 1)
        perform.assert_not_called(); self.assertNotIn('whoami', output.getvalue())
        self.assertEqual(audit.call_args.args[0]['operation'], 'denied')

    def native(self, code):
        path = str(Path(host.__file__).absolute())
        prefix = ('import importlib.util,sys,json,threading,subprocess\n'
                  f'spec=importlib.util.spec_from_file_location("host",{path!r})\n'
                  'm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n'
                  f'm.ROOT=m.Path({str(self.root)!r})\n'
                  'owned=m.own_process_tree()\n')
        return subprocess.run([sys.executable, '-I', '-S', '-c', prefix + code],
                              capture_output=True, text=True, timeout=10)

    @unittest.skipUnless(os.name == 'nt', 'actual Windows job/process API')
    def test_native_powershell_identity_and_job_quiescence(self):
        r = self.native('sid,admin=m.windows_identity()\n'
                        'config={"powershell_sha256":m.digest(m.Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"))}\n'
                        'result=m.perform("self-test",config,sid,threading.Event())\n'
                        'm.ensure_quiescent(owned)\n'
                        'print(json.dumps({"result":result["fixed_powershell"],"sid_format":sid.startswith("S-1-5-")}))\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {'result': 'PASS', 'sid_format': True})

    @unittest.skipUnless(os.name == 'nt', 'actual Windows job/process API')
    def test_native_timeout_and_output_cap(self):
        for script, timeout, error in (("Start-Sleep -Seconds 3", .1, 'operation_timeout'),
                                       ("[Console]::Out.Write('x' * 70000); Start-Sleep -Seconds 3", 5, 'output_limit')):
            r = self.native('config={"powershell_sha256":m.digest(m.Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"))}\n'
                            'try:\n'
                            f' m.fixed_powershell({script!r},config,threading.Event(),timeout={timeout})\n'
                            'except m.Denied as e: print(str(e))\n')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), error)
        r = self.native('config={"powershell_sha256":m.digest(m.Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"))}\n'
                        'cancel=threading.Event();threading.Timer(.1,cancel.set).start()\n'
                        'try:\n m.fixed_powershell("Start-Sleep -Seconds 3",config,cancel)\n'
                        'except m.Denied as e: print(str(e))\n')
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(r.stdout.strip(), 'cancelled')

    def test_concurrent_audit_records_do_not_overwrite(self):
        path = self.root / 'audit/execution.jsonl'; path.write_bytes(b'')
        source = str(Path(host.__file__).absolute())
        prefix = ('import importlib.util\n'
                  f's=importlib.util.spec_from_file_location("host",{source!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
                  f'm.ROOT=m.Path({str(self.root)!r})\n')
        processes = [subprocess.Popen([sys.executable, '-I', '-S', '-c', prefix +
                     f'm.audit({{"event":"test","id":str({n})}})\n'],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE) for n in range(2)]
        for process in processes:
            _, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, errors.decode())
        records = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(records), 2); self.assertEqual(len({r['id'] for r in records}), 2)

    @unittest.skipUnless(os.name == 'nt', 'Windows file lock deadline')
    def test_audit_lock_deadline_preserves_records(self):
        path = self.root / 'audit/execution.jsonl'; path.write_bytes(b'prior\n')
        with patch('msvcrt.locking', side_effect=PermissionError()), \
             patch.object(host.time, 'monotonic', side_effect=[0, 3]):
            with self.assertRaisesRegex(host.Denied, 'audit_busy'):
                host.audit({'operation': 'health'})
        self.assertEqual(path.read_bytes(), b'prior\n')

    @unittest.skipUnless(os.name == 'nt', 'actual Windows job/process API')
    def test_native_job_exit_terminates_descendant(self):
        marker = self.root / 'escaped.txt'
        child = f'import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).write_text("escaped")'
        r = self.native(f'subprocess.Popen([sys.executable,"-I","-S","-c",{child!r}])\nprint("started")\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        time.sleep(1.5)
        self.assertFalse(marker.exists(), 'Descendant survived owning dispatcher exit')


if __name__ == '__main__':
    unittest.main()
