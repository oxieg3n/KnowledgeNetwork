"""Forced-command framing and bounded handlers; no host deployment or inference."""
import io
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
