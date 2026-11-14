"""Synthetic manifests and mocked execution; not BLACKHAT-BASE narrator proof."""
from contextlib import ExitStack, closing
from contextlib import redirect_stdout
import base64
import ctypes
from ctypes import wintypes
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import wave

from youtube_ops.collector_narrator_host import (CLI, NARRATOR, SETTINGS, NarratorError,
    NarratorHTTPServer, NarratorManifest, NarratorStore, WindowsScriptRunner, main, script_arguments,
    verify_spool_acl, SPOOL_ACL_CHECK)
from youtube_ops.collector_narration_common import VoiceError, sha256_file


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(b'\x01\x00' * 1600)
    return output.getvalue()


class HostFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.spool = self.root / 'spool'; self.spool.mkdir()
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.script, self.reference, self.cli = (self.root / name for name in ('narrate.ps1', 'reference.wav', 'voxcpm.exe'))
        for path in (self.script, self.reference, self.cli):
            path.write_bytes(b'fixture only; never executable')
        for name, path in (('SCRIPT', self.script), ('REFERENCE', self.reference), ('CLI', self.cli)):
            self.stack.enter_context(patch('youtube_ops.collector_narrator_host.' + name, path))
        self.ref = self.root / 'models--openbmb--VoxCPM2/refs/main'
        self.ref.parent.mkdir(parents=True)
        self.ref.write_text('a' * 40)
        self.checkpoint = self.ref.parent.parent / 'snapshots' / ('a' * 40) / 'model.safetensors'
        self.checkpoint.parent.mkdir(parents=True)
        self.checkpoint.write_bytes(b'fixture weights')
        self.stack.enter_context(patch('youtube_ops.collector_narrator_host._effective_model_ref', return_value=self.ref))
        self.manifest_path = self.root / 'manifest.json'
        artifacts = []
        for role, path in [('cli_executable', self.cli), ('narrator_reference', self.reference),
                           ('model_revision_ref', self.ref), ('model_checkpoint', self.checkpoint),
                           *[(role, self.root / (role + '.private')) for role in
                             ('license_evidence', 'consent_evidence', 'inspection_record')]]:
            if not path.exists():
                path.write_bytes(b'fixture evidence only')
            artifacts.append({'role': role, 'path': str(path), 'sha256': sha256_file(path)})
        self.manifest = {'schema_version': 1, 'narrator_id': NARRATOR, 'settings': SETTINGS,
            'model_id': 'openbmb/VoxCPM2', 'model_revision': 'a' * 40, 'license': 'fixture-only',
            'cli_version': 'fixture-version', 'reviewed_by': 'unit-test', 'reviewed_at': '2026-11-14',
            'script_sha256': sha256_file(self.script), 'artifacts': artifacts,
            **{key: True for key in ('rights_reviewed', 'commercial_use', 'youtube_use', 'voice_consent',
                'script_reviewed', 'voice_identity_verified', 'independent_runtime_verified')}}
        self.write_manifest()

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def store(self, executor=None):
        result = NarratorStore(self.spool, NarratorManifest(self.manifest_path), executor)
        self.addCleanup(lambda: result.close() if getattr(result, 'db', None) is not None else None)
        return result

    def request(self, key='a' * 32, text='Original synthetic sentence.'):
        return {'idempotency_key': key, 'text': text, 'narrator_id': NARRATOR}


class HostStoreTests(HostFixture):
    def test_manifest_requires_reviewed_canonical_files_and_settings(self):
        verified = NarratorManifest(self.manifest_path)
        self.assertEqual(set(verified.provenance), {'script_sha256', 'config_sha256', 'model_revision', 'license_evidence_sha256'})
        self.manifest['voice_consent'] = False; self.write_manifest()
        with self.assertRaisesRegex(NarratorError, 'review_incomplete'):
            NarratorManifest(self.manifest_path)
        self.manifest['voice_consent'] = True
        self.manifest['settings'] = {**SETTINGS, 'cfg_value': 99}; self.write_manifest()
        with self.assertRaisesRegex(NarratorError, 'configuration_unverified'):
            NarratorManifest(self.manifest_path)

    def test_selected_ref_or_cache_change_blocks_unchanged_old_checkpoint(self):
        for change_cache in (False, True):
            self.ref.write_text('a' * 40)
            executor = Mock()
            store = self.store(executor)
            key = ('b' if change_cache else 'a') * 32
            store.submit(self.request(key))
            if change_cache:
                with patch('youtube_ops.collector_narrator_host._effective_model_ref', return_value=self.root / 'other/refs/main'):
                    store.run_next()
            else:
                self.ref.write_text('b' * 40)
                store.run_next()
            executor.assert_not_called()
            self.assertEqual(store.get(key)['state'], 'failed')
            store.close()

    def test_checkpoint_outside_selected_snapshot_is_denied(self):
        old = self.root / 'old-model.safetensors'
        old.write_bytes(self.checkpoint.read_bytes())
        for artifact in self.manifest['artifacts']:
            if artifact['role'] == 'model_checkpoint':
                artifact['path'] = str(old)
        self.write_manifest()
        with self.assertRaisesRegex(NarratorError, 'selected_model_revision_unverified'):
            NarratorManifest(self.manifest_path)

    def test_model_revision_cannot_leak_private_path_or_control_characters(self):
        for revision in ('C:/private/model', '\\\\host\\cache', 'revision\nprivate', 'a' * 257):
            self.manifest['model_revision'] = revision; self.write_manifest()
            with self.subTest(revision=revision[:10]), self.assertRaisesRegex(NarratorError, 'invalid_model_revision'):
                NarratorManifest(self.manifest_path)

    def test_changed_canonical_script_or_reference_never_executes(self):
        for path in (self.script, self.reference):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                store = self.store(Mock())
                store.submit(self.request())
                path.write_bytes(b'changed fixture')
                store.run_next()
                self.assertEqual(store.get('a' * 32)['state'], 'failed')
                self.assertEqual(store.get('a' * 32)['error'], 'narrator_artifact_changed')
                store.executor.assert_not_called()
                store.close(); store.db = None
                path.write_bytes(original)
                with closing(sqlite3.connect(self.spool / 'host-narrations.sqlite')) as db:
                    db.execute('DELETE FROM jobs')
                    db.commit()

    def test_idempotency_conflict_and_exact_audio_provenance(self):
        executor = Mock(side_effect=lambda text, output, cancel: output.write_bytes(wav_bytes()))
        store = self.store(executor)
        accepted = store.submit(self.request())
        self.assertEqual(accepted['id'], 'a' * 32)
        self.assertNotIn('text', accepted)
        self.assertEqual(store.submit(self.request())['id'], accepted['id'])
        with self.assertRaisesRegex(NarratorError, 'idempotency_conflict'):
            store.submit(self.request(text='Changed.'))
        store.run_next()
        completed = store.get(accepted['id'])
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(completed['audio']['frames'], 1600)
        self.assertEqual(completed['audio']['duration'], .1)
        self.assertEqual(completed['text_sha256'], hashlib.sha256(self.request()['text'].encode()).hexdigest())
        self.assertEqual(completed['provenance'], store.manifest.provenance)
        path, audio = store.audio_path(accepted['id'])
        self.assertEqual(sha256_file(path), audio['sha256'])
        store.submit(self.request()); self.assertFalse(store.run_next()); executor.assert_called_once()

    def test_unknown_fields_paths_injection_and_oversized_text_rejected(self):
        store = self.store(Mock())
        for value in ({**self.request(), 'output': 'C:/escape.wav'},
                      {**self.request(), 'command': 'whoami'},
                      {**self.request(), 'narrator_id': 'other'},
                      self.request(text='x' * 12001), self.request(text='a\x00b'), self.request(key='../escape')):
            with self.subTest(value=value.keys()), self.assertRaises(NarratorError):
                store.submit(value)
        text = 'Literal $(whoami); & anything " quoted ` text'
        args = script_arguments('fixed-powershell.exe', text, self.spool / 'narration.wav')
        self.assertEqual(args[args.index('-Text') + 1], text)
        self.assertNotIn('-Command', args)
        self.assertNotIn('-ExecutionPolicy', args)
        store.executor.assert_not_called()

    def test_queued_cancel_and_running_cancel_wait_for_owned_executor(self):
        store = self.store(Mock())
        store.submit(self.request()); self.assertEqual(store.cancel('a' * 32)['state'], 'cancelled')
        self.assertFalse(store.run_next())
        entered = threading.Event()
        def execute(text, output, cancel):
            entered.set(); cancel.wait(2)
            if cancel.is_set():
                raise NarratorError('cancelled')
            self.fail('cancellation was not forwarded')
        store.executor = execute; store.submit(self.request('b' * 32))
        thread = threading.Thread(target=store.run_next); thread.start(); self.assertTrue(entered.wait(1))
        response = store.cancel('b' * 32)
        self.assertTrue(response['cancel_requested'])
        thread.join(2); self.assertFalse(thread.is_alive())
        self.assertEqual(store.get('b' * 32)['state'], 'cancelled')

    def test_restart_marks_running_unknown_and_blocks_different_key(self):
        store = self.store(Mock()); store.submit(self.request())
        with store.db:
            store.db.execute("UPDATE jobs SET state='running'")
        store.close(); store.db = None
        restarted = self.store(Mock())
        self.assertEqual(restarted.get('a' * 32)['error'], 'outcome_unknown')
        self.assertTrue(restarted.health()['execution_hold'])
        with self.assertRaisesRegex(NarratorError, 'requires_reconciliation'):
            restarted.submit(self.request('b' * 32))
        self.assertFalse(restarted.run_next()); restarted.executor.assert_not_called()

    def test_uncertain_executor_error_holds_all_gpu_dispatch(self):
        store = self.store(Mock(side_effect=NarratorError('process_outcome_unknown', uncertain=True)))
        store.submit(self.request()); store.submit(self.request('b' * 32))
        store.run_next(); self.assertTrue(store.health()['execution_hold'])
        self.assertFalse(store.run_next()); store.executor.assert_called_once()

    def test_singleton_prevents_second_host_worker(self):
        store = self.store(Mock())
        with self.assertRaises(VoiceError):
            NarratorStore(self.spool, NarratorManifest(self.manifest_path), Mock())
        self.assertEqual(store.health()['queue_depth'], 0)

    def test_worker_database_fault_latches_blocked_health_and_new_submissions(self):
        store = self.store(Mock())
        with patch.object(store, 'run_next', side_effect=sqlite3.OperationalError('private database detail')):
            store.start(); store.thread.join(2)
        self.assertFalse(store.thread.is_alive())
        self.assertTrue(store.health()['worker_fault'])
        self.assertEqual(store.health()['status'], 'blocked')
        with self.assertRaisesRegex(NarratorError, 'requires_reconciliation'):
            store.submit(self.request())
        self.assertTrue(store.held())
        store.executor.assert_not_called()

    def test_corrupted_stored_request_or_provenance_never_executes(self):
        for column, replacement in (('text', 'tampered'), ('text_sha', '0' * 64),
                                    ('request_sha', '0' * 64), ('provenance', '{}')):
            with self.subTest(column=column):
                store = self.store(Mock()); key = format(len(column), '032x')
                store.submit(self.request(key))
                with store.db:
                    store.db.execute('UPDATE jobs SET ' + column + '=? WHERE id=?', (replacement, key))
                store.run_next()
                self.assertEqual(store.get(key)['error'], 'stored_request_integrity_mismatch')
                store.executor.assert_not_called()
                store.close(); store.db = None

    def test_unsupported_database_schema_is_not_mutated(self):
        path = self.spool / 'host-narrations.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE foreign_data(value TEXT)'); db.execute("INSERT INTO foreign_data VALUES('preserve')")
            db.commit()
        original = path.read_bytes()
        with self.assertRaisesRegex(NarratorError, 'unsupported_host_database_schema'):
            NarratorStore(self.spool, NarratorManifest(self.manifest_path), Mock())
        self.assertEqual(path.read_bytes(), original)


class SpoolACLTests(HostFixture):
    def test_constant_command_receives_path_as_json_stdin_without_interpolation(self):
        path = self.spool / "literal $(Write-Output private); 'x"
        path.mkdir()
        result = subprocess.CompletedProcess([], 0, '{"ok":true}')
        with patch('youtube_ops.collector_narrator_host._system_powershell', return_value='fixed-system-powershell.exe'), \
             patch('youtube_ops.collector_narrator_host.subprocess.run', return_value=result) as run:
            verify_spool_acl(path)
        arguments, options = run.call_args.args[0], run.call_args.kwargs
        self.assertEqual(arguments[-1], SPOOL_ACL_CHECK)
        self.assertNotIn(str(path), arguments)
        self.assertEqual(json.loads(options['input']), {'spool': str(path)})
        self.assertFalse(options['shell']); self.assertEqual(options['timeout'], 10)
        self.assertNotIn('-File', arguments); self.assertNotIn('-ExecutionPolicy', arguments)

    def test_denied_or_invalid_acl_output_is_redacted_and_fail_closed(self):
        for result in (subprocess.CompletedProcess([], 1, '{"ok":false}'),
                       subprocess.CompletedProcess([], 0, 'private unexpected output'),
                       subprocess.CompletedProcess([], 0, '{"ok":true}' + ' ' * 65)):
            with patch('youtube_ops.collector_narrator_host._system_powershell', return_value='fixed-system-powershell.exe'), \
                 patch('youtube_ops.collector_narrator_host.subprocess.run', return_value=result):
                with self.assertRaisesRegex(NarratorError, '^spool_acl_unverified$'):
                    verify_spool_acl(self.spool)

    def test_acl_timeout_is_redacted_and_fail_closed(self):
        with patch('youtube_ops.collector_narrator_host._system_powershell', return_value='fixed-system-powershell.exe'), \
             patch('youtube_ops.collector_narrator_host.subprocess.run', side_effect=subprocess.TimeoutExpired('private command', 10)):
            with self.assertRaisesRegex(NarratorError, '^spool_acl_unverified$'):
                verify_spool_acl(self.spool)

    def test_serve_rejects_acl_before_opening_database_or_listener(self):
        output = io.StringIO()
        with patch('youtube_ops.collector_narrator_host.NarratorManifest'), \
             patch('youtube_ops.collector_narrator_host.os') as system, \
             patch('youtube_ops.collector_narrator_host.verify_spool_acl', side_effect=NarratorError('spool_acl_unverified')), \
             patch('youtube_ops.collector_narrator_host.NarratorStore') as store, \
             patch('youtube_ops.collector_narrator_host.NarratorHTTPServer') as server, redirect_stdout(output):
            system.name = 'nt'
            self.assertEqual(main(['serve', '--manifest', str(self.manifest_path), '--spool', str(self.spool)]), 1)
        store.assert_not_called(); server.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {'status': 'BLOCKED', 'error': 'spool_acl_unverified'})
        self.assertFalse((self.spool / 'host-narrations.sqlite').exists())


class HostHTTPTests(HostFixture):
    def setUp(self):
        super().setUp()
        self.store_value = self.store(Mock(side_effect=lambda text, output, cancel: output.write_bytes(wav_bytes())))
        self.token = 'synthetic-host-credential-12345678901234567890'
        self.server = NarratorHTTPServer(('127.0.0.1', 0), self.store_value, self.token)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(1)

    def http(self, method, path, value=None, token=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        body = json.dumps(value).encode() if value is not None else None
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + self.token
        connection.request(method, path, body, headers)
        response = connection.getresponse(); data = response.read(); status = response.status; connection.close()
        return status, data

    def test_auth_required_for_health_audio_mutations_and_unknown_methods(self):
        for method, path in (('GET', '/health'), ('POST', '/v1/narrations'),
                             ('GET', '/v1/narrations/' + 'a' * 32 + '/audio'), ('TRACE', '/anything')):
            self.assertEqual(self.http(method, path, token=False)[0], 401)
        status, body = self.http('GET', '/health')
        self.assertEqual(status, 200)
        health = json.loads(body); self.assertEqual(health['service'], 'knowledge-network-voxcpm2')
        self.assertNotIn(str(self.root), body.decode()); self.assertNotIn(self.token, body.decode())

    def test_authenticated_submit_get_audio_and_cancel_contract(self):
        status, body = self.http('POST', '/v1/narrations', self.request())
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)['id'], 'a' * 32)
        self.store_value.run_next()
        status, body = self.http('GET', '/v1/narrations/' + 'a' * 32)
        self.assertEqual(json.loads(body)['state'], 'completed')
        status, audio = self.http('GET', '/v1/narrations/' + 'a' * 32 + '/audio')
        self.assertEqual(status, 200); self.assertEqual(audio, wav_bytes())
        status, body = self.http('POST', '/v1/narrations/' + 'a' * 32 + '/cancel', {})
        self.assertEqual(json.loads(body)['state'], 'completed')

    def test_duplicate_smuggling_headers_and_nonfinite_json_fail_closed(self):
        requests = [
            'Content-Length: 2\r\nContent-Length: 2\r\n',
            'Content-Length: 2\r\nTransfer-Encoding: chunked\r\n',
            'Content-Length: 2\r\nTransfer-Encoding:\r\n']
        for extra in requests:
            with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=2) as stream:
                stream.sendall(('POST /v1/narrations HTTP/1.1\r\nHost: fixture\r\nAuthorization: Bearer ' + self.token +
                    '\r\nContent-Type: application/json\r\n' + extra + '\r\n{}').encode())
                self.assertIn(b' 400 ', stream.recv(4096).split(b'\r\n')[0])
        for raw in (b'{"x":NaN}', b'{"text":"a","text":"b"}'):
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
            connection.request('POST', '/v1/narrations', raw, {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            response = connection.getresponse(); self.assertEqual(response.status, 400); response.read(); connection.close()
        self.store_value.executor.assert_not_called()

    def test_nonloopback_bind_and_small_secret_are_denied(self):
        for address, token in ((('0.0.0.0', 0), self.token), (('127.0.0.1', 0), 'short')):
            with self.assertRaises(NarratorError):
                NarratorHTTPServer(address, self.store_value, token)


def native_runner_smoke(output_directory):
    """Opt-in Forge process-boundary proof only. Never calls the host narrator."""
    if os.name != 'nt':
        raise RuntimeError('Windows is required')
    output = Path(output_directory).absolute()
    output.mkdir(exist_ok=False)
    checks = []
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def alive(pid):
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() in (87, 1168):
                return False
            raise RuntimeError('child_liveness_not_verified')
        try:
            state = kernel.WaitForSingleObject(handle, 0)
            if state not in (0, 0x102):
                raise RuntimeError('child_liveness_not_verified')
            return state == 0x102
        finally:
            kernel.CloseHandle(handle)

    for name in ('completed', 'cancelled', 'timeout'):
        destination = output / (name + '.wav')
        child_file = output / (name + '-child.pid')
        cancel, watcher_stop = threading.Event(), threading.Event()
        started = time.monotonic()
        if name == 'completed':
            code = "[IO.File]::WriteAllBytes('" + str(destination).replace("'", "''") + "',[Convert]::FromBase64String('" + base64.b64encode(wav_bytes()).decode() + "'))"
        else:
            code = ("$p=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') "
                "-ArgumentList '-NoLogo -NoProfile -NonInteractive -Command Start-Sleep -Seconds 10' "
                "-WindowStyle Hidden -PassThru; [IO.File]::WriteAllText('" +
                str(child_file).replace("'", "''") + "',[string]$p.Id); Start-Sleep -Seconds 30")
        def fixture_arguments(powershell, text, allocated_output):
            return [str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code]
        def trigger_cancel():
            deadline = time.monotonic() + 8
            while not watcher_stop.wait(.02) and not child_file.exists() and time.monotonic() < deadline:
                pass
            if not watcher_stop.is_set():
                cancel.set()
        thread = None
        if name == 'cancelled':
            thread = threading.Thread(target=trigger_cancel, daemon=True); thread.start()
        actual = 'completed'
        try:
            with patch('youtube_ops.collector_narrator_host.script_arguments', side_effect=fixture_arguments), \
                 patch('youtube_ops.collector_narrator_host.SCRIPT_TIMEOUT_SECONDS', 3 if name == 'timeout' else 12):
                WindowsScriptRunner()('synthetic fixture only', destination, cancel)
        except NarratorError as error:
            actual = str(error)
        finally:
            watcher_stop.set()
            if thread:
                thread.join(1)
        expected = {'completed': 'completed', 'cancelled': 'cancelled', 'timeout': 'generation_timeout_or_size_limit'}[name]
        child_stopped = None
        if name != 'completed':
            child_stopped = child_file.exists() and not alive(int(child_file.read_text()))
        passed = actual == expected and (destination.read_bytes() == wav_bytes() if name == 'completed' else child_stopped)
        checks.append({'name': name, 'status': 'PASS' if passed else 'FAILED', 'actual': actual,
                       'elapsed_seconds': time.monotonic() - started, 'child_stopped': child_stopped})
    report = {'status': 'PASS' if all(check['status'] == 'PASS' for check in checks) else 'FAILED',
        'scope': 'FORGE_SYNTHETIC_WINDOWS_RUNNER_ONLY', 'checks': checks,
        'host_narrator_parity': 'NOT_TESTED', 'gpu_inference': 'NOT_TESTED'}
    (output / 'native-runner-results.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--native-runner-smoke':
        raise SystemExit(native_runner_smoke(sys.argv[2]))
    unittest.main()
