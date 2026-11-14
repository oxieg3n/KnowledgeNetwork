"""Synthetic manifests and mocked execution; not BLACKHAT-BASE narrator proof."""
from contextlib import ExitStack, closing
import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import wave

from youtube_ops.collector_narrator_host import (CLI, NARRATOR, SETTINGS, NarratorError,
    NarratorHTTPServer, NarratorManifest, NarratorStore, script_arguments)
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
        self.manifest_path = self.root / 'manifest.json'
        artifacts = []
        for role, path in [('cli_executable', self.cli), ('narrator_reference', self.reference),
                           *[(role, self.root / (role + '.private')) for role in
                             ('model_checkpoint', 'license_evidence', 'consent_evidence', 'inspection_record')]]:
            if not path.exists():
                path.write_bytes(b'fixture evidence only')
            artifacts.append({'role': role, 'path': str(path), 'sha256': sha256_file(path)})
        self.manifest = {'schema_version': 1, 'narrator_id': NARRATOR, 'settings': SETTINGS,
            'model_id': 'openbmb/VoxCPM2', 'model_revision': 'fixture-revision', 'license': 'fixture-only',
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


if __name__ == '__main__':
    unittest.main()
