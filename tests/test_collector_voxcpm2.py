"""Simulated host protocol tests; no host synthesis or narrator license acceptance."""
from tests.fixture_retention import FixtureDirectory
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import Mock, patch
import wave

from youtube_ops.collector_voxcpm2 import RemoteVoxCPM2Provider, VoiceError, SERVICE, NARRATOR
from youtube_ops.collector_credentials import (Credential, credential_target, read_secret,
                                               read_credential, write_credential)
from youtube_ops.collector_narration_common import checkpoint, inspect_wav, digest


def wav(frames=16000, rate=16000):
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as audio:
        audio.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\x01\x00' * frames)
    return stream.getvalue()


class Response(io.BytesIO):
    def __init__(self, body=b'{}', status=200, mime='application/json'):
        super().__init__(body)
        self.status, self.mime = status, mime
    def getheader(self, name, default=''):
        return self.mime if name == 'Content-Type' else default


class Connection:
    def __init__(self, response):
        self.response, self.requests = response, []
    def request(self, *args): self.requests.append(args)
    def getresponse(self): return self.response
    def close(self): pass


class DirectNarratorTests(unittest.TestCase):
    def setUp(self):
        temporary = FixtureDirectory(); self.addCleanup(temporary.cleanup)
        self.spool = Path(temporary.name)
        self.provenance = {'script_sha256': 'a' * 64, 'config_sha256': 'b' * 64,
                           'model_revision': 'fixture-only', 'license_evidence_sha256': 'c' * 64}
        self.url = 'https://narrator-fixture.invalid:9443'
        self.route = {'schema_version': 1, 'base_url': self.url, 'host_identity': 'BLACKHAT-BASE',
            'transport': 'https', 'auth_mode': 'scoped_bearer', 'pinned_addresses': ['10.23.45.67'],
            'verified_by': 'unit-test-only', 'verified_at': '2026-11-14',
            'transport_evidence_sha256': 'd' * 64, 'expected_provenance': self.provenance}
        self.provider = RemoteVoxCPM2Provider(self.url, self.route, self.spool)
        self.health = {'schema_version': 1, 'service': SERVICE, 'narrator_id': NARRATOR,
                       'status': 'ready', 'execution_hold': False, 'provenance': self.provenance}
        self.posts, self.jobs, self.audio = [], {}, {}
        credential = patch('youtube_ops.collector_voxcpm2.read_credential', return_value=('x' * 32, 7))
        self.credential = credential.start(); self.addCleanup(credential.stop)

    def job(self, key, text, frames=16000):
        data = wav(frames)
        audio = inspect_wav(data)
        audio['duration'] = audio.pop('duration_seconds'); audio['bytes'] = len(data)
        self.audio[key] = data
        return {'id': key, 'state': 'completed', 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'provenance': self.provenance, 'audio': audio}

    def json_host(self, method, path, payload=None, cancel=None):
        if path == '/health': return self.health
        if method == 'POST' and path == '/v1/narrations':
            self.assertEqual(set(payload), {'idempotency_key', 'text', 'narrator_id'})
            self.assertEqual(payload['narrator_id'], NARRATOR)
            self.posts.append(payload)
            key = payload['idempotency_key']
            self.jobs[key] = self.job(key, payload['text'], 8000 if len(self.posts) == 1 else 24000)
            return self.jobs[key]
        key = path.split('/')[3]
        if key not in self.jobs:
            error = VoiceError('NARRATION_NOT_FOUND'); error.http_status = 404; raise error
        if method == 'POST':
            self.assertEqual(payload, {})
            self.jobs[key]['state'] = 'cancelled'
        return self.jobs[key]

    def download(self, method, path, payload=None, *, destination=None, **kwargs):
        self.assertEqual(method, 'GET'); self.assertTrue(path.endswith('/audio'))
        Path(destination).write_bytes(self.audio[path.split('/')[3]])
        return b''

    def test_only_new_environment_and_no_old_service_identity(self):
        with patch.dict(os.environ, {'COLLECTOR_VOICE_PROVIDER': 'voicestudio_remote'}, clear=True):
            with self.assertRaisesRegex(VoiceError, 'NARRATOR_CONFIG'):
                RemoteVoxCPM2Provider.from_environment()
        with patch.object(self.provider, '_json', return_value={**self.health, 'service': 'VoiceStudio'}):
            with self.assertRaisesRegex(VoiceError, 'SERVICE_IDENTITY'): self.provider.status()

    def test_reject_non_https_nonprivate_or_unverified_route(self):
        for url in ('http://fixture.invalid', 'https://user:secret@fixture.invalid', self.url + '/health', 'https://fixture.invalid:0'):
            with self.assertRaises(VoiceError): RemoteVoxCPM2Provider(url, {**self.route, 'base_url': url}, self.spool)
        for address in ('127.0.0.1', '8.8.8.8', '169.254.169.254'):
            with self.assertRaises(VoiceError): RemoteVoxCPM2Provider(self.url, {**self.route, 'pinned_addresses': [address]}, self.spool)

    def test_connects_pinned_literal_without_dns_and_keeps_tls_hostname(self):
        with patch('socket.socket') as make, patch('socket.getaddrinfo') as dns, patch('ssl.create_default_context') as context:
            self.provider._connect(2, lambda value: None)
            dns.assert_not_called()
            make.return_value.connect.assert_called_once_with(('10.23.45.67', 9443))
            context.return_value.wrap_socket.assert_called_once_with(make.return_value,
                server_hostname='narrator-fixture.invalid', do_handshake_on_connect=False)

    def test_auth_namespace_and_unknown_paths_never_forwarded(self):
        connection = Connection(Response())
        with patch.object(self.provider, '_connect', return_value=connection):
            self.provider._request('GET', '/health')
        self.credential.assert_called_with(self.url, 'scoped_bearer', namespace='VoxCPM2')
        self.assertEqual(connection.requests[0][3]['Authorization'], 'Bearer ' + 'x' * 32)
        for method, path in [('GET', '/v1/audio/voices'), ('POST', '/system/run'),
                             ('GET', '/v1/narrations/' + 'a' * 32 + '/audio?path=host'),
                             ('POST', '/v1/narrations/' + 'a' * 32 + '/audio')]:
            with self.assertRaisesRegex(VoiceError, 'UNSUPPORTED_NARRATOR_ENDPOINT'):
                self.provider._request(method, path, {} if method == 'POST' else None)

    def test_short_direct_credential_is_rejected_before_http(self):
        with patch('youtube_ops.collector_voxcpm2.read_credential', side_effect=read_credential), \
                patch('youtube_ops.collector_credentials.read_secret', return_value=('x' * 16, 7)), \
                patch.object(self.provider, '_connect') as connect:
            with self.assertRaisesRegex(ValueError, 'INVALID_NARRATOR_CREDENTIAL'):
                self.provider._request('GET', '/health')
            connect.assert_not_called()

    def test_redirect_auth_and_post_failure_are_redacted_not_retried(self):
        for status in (302, 403, 503):
            with patch.object(self.provider, '_connect', return_value=Connection(Response(b'private failure secret', status))) as connect:
                with self.assertRaises(VoiceError) as error:
                    self.provider._request('POST', '/v1/narrations', {})
                self.assertNotIn('private', str(error.exception)); self.assertEqual(connect.call_count, 1)

    def test_unicode_twelve_thousand_characters_fit_host_frame(self):
        connection = Connection(Response())
        with patch.object(self.provider, '_connect', return_value=connection):
            self.provider._request('POST', '/v1/narrations', {'idempotency_key': 'a' * 32, 'text': '\U0001f600' * 12000, 'narrator_id': NARRATOR})
        self.assertLessEqual(len(connection.requests[0][2]), 65536)

    def test_real_socket_stall_is_interrupted_by_absolute_deadline(self):
        client, peer = socket.socketpair(); self.addCleanup(peer.close); self.addCleanup(client.close)
        class Stalled(Connection):
            def getresponse(self):
                client.recv(1)
                raise OSError('closed fixture')
        def connect(timeout, register):
            register(client); return Stalled(None)
        started = time.monotonic()
        with patch.object(self.provider, '_connect', side_effect=connect), patch('youtube_ops.collector_voxcpm2.REQUEST_SECONDS', .08):
            with self.assertRaisesRegex(VoiceError, 'DEADLINE'):
                self.provider._request('GET', '/health')
        self.assertLess(time.monotonic() - started, 1)

    def test_legacy_measured_segments_recover_without_estimated_word_times(self):
        # Explicit old schema3 intent: those original host IDs must stay recoverable.
        job_id, text, parts = '1' * 32, 'First. Second.', ['First.', 'Second.']
        directory = self.spool / job_id; directory.mkdir()
        identity = digest({'job_id': job_id, 'text': text, 'segments': parts,
                           'endpoint': digest(self.url), 'provenance': self.provenance})
        jobs = []
        for index, part in enumerate(parts):
            key = hashlib.sha256((job_id + '/' + str(index)).encode()).hexdigest()[:32]
            self.posts.append({'idempotency_key': key, 'text': part, 'narrator_id': NARRATOR})
            self.jobs[key] = self.job(key, part, 8000 if index == 0 else 24000)
            jobs.append({name: self.jobs[key][name] for name in ('id', 'state', 'text_sha256')})
        checkpoint(directory / 'request.json', {'text': text, 'segments': parts, 'request_sha256': identity})
        checkpoint(directory / 'narration.json', {'schema_version': 3, 'provider': 'voxcpm2_remote',
            'narrator_id': NARRATOR, 'collector_job_id': job_id, 'request_sha256': identity,
            'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'provenance': self.provenance,
            'host_jobs': jobs, 'cues': [], 'review_only': True, 'publication_eligible': False,
            'listening': 'NOT_TESTED', 'status': 'submission_intent'})
        with patch.object(self.provider, '_json', side_effect=self.json_host), patch.object(self.provider, '_request', side_effect=self.download):
            result = self.provider.generate('1' * 32, 'First. Second.', segments=['First.', 'Second.'])
            repeated = self.provider.generate('1' * 32, 'First. Second.', segments=['First.', 'Second.'])
        self.assertEqual(len(self.posts), 2); self.assertEqual(result, repeated)
        self.assertEqual(result['audio']['frames'], 32000)
        self.assertEqual(result['cues'][0]['end'], .5)
        self.assertEqual(result['cues'][1]['start_sample'], 8000)
        self.assertEqual(result['cues'][1]['end'], 2)
        self.assertFalse(result['publication_eligible']); self.assertEqual(result['listening'], 'NOT_TESTED')
        with patch.object(self.provider, '_json') as network:
            with self.assertRaisesRegex(VoiceError, 'IDEMPOTENCY'):
                self.provider.generate('1' * 32, 'Changed.')
            network.assert_not_called()
        receipt = self.spool / ('1' * 32) / 'narration.json'
        changed = json.loads(receipt.read_text()); changed['cues'][0]['text'] = 'Unrelated caption.'
        checkpoint(receipt, changed)
        with self.assertRaisesRegex(VoiceError, 'LOCAL_RECEIPT_CHANGED'):
            self.provider.generate('1' * 32, 'First. Second.', segments=['First.', 'Second.'])

    def test_uncertain_submission_recovers_by_get_never_reposts(self):
        def lost(method, path, payload=None, cancel=None):
            result = self.json_host(method, path, payload, cancel)
            if method == 'POST': raise VoiceError('NARRATION_TRANSPORT_OUTCOME_UNKNOWN')
            return result
        with patch.object(self.provider, '_json', side_effect=lost), patch.object(self.provider, '_request', side_effect=self.download):
            with self.assertRaisesRegex(VoiceError, 'UNKNOWN'):
                self.provider.generate('2' * 32, 'Original.')
            result = self.provider.generate('2' * 32, 'Original.')
        self.assertEqual(len(self.posts), 1); self.assertEqual(result['status'], 'generated_pending_review')

    def test_unresolved_submission_does_not_repost_when_get_is_not_found(self):
        def unavailable(method, path, payload=None, cancel=None):
            if path == '/health': return self.health
            if method == 'POST':
                self.posts.append(payload); raise VoiceError('NARRATION_TRANSPORT_OUTCOME_UNKNOWN')
            raise VoiceError('NARRATION_NOT_FOUND')
        with patch.object(self.provider, '_json', side_effect=unavailable):
            for _ in range(2):
                with self.assertRaises(VoiceError): self.provider.generate('3' * 32, 'Original.')
        self.assertEqual(len(self.posts), 1)

    def test_changed_provenance_or_execution_hold_blocks_submission(self):
        for changed in ({**self.health, 'provenance': {**self.provenance, 'config_sha256': 'e' * 64}},
                        {**self.health, 'execution_hold': True}):
            with patch.object(self.provider, '_json', return_value=changed) as network:
                with self.assertRaises(VoiceError): self.provider.generate(uuid_hex(), 'Original.')
                self.assertEqual(network.call_count, 1)

    def test_host_text_hash_mismatch_blocks_audio(self):
        def wrong(method, path, payload=None, cancel=None):
            result = self.json_host(method, path, payload, cancel)
            if method == 'POST': return {**result, 'text_sha256': 'e' * 64}
            return result
        with patch.object(self.provider, '_json', side_effect=wrong), patch.object(self.provider, '_request') as download:
            with self.assertRaisesRegex(VoiceError, 'RECEIPT_MISMATCH'):
                self.provider.generate('4' * 32, 'Original.')
            download.assert_not_called()

    def test_invalid_audio_or_nan_duration_retains_unverified_partial_without_final(self):
        job = self.job('5' * 32, 'Original.')
        job['audio']['duration'] = float('nan')
        with patch.object(self.provider, '_request', side_effect=self.download):
            with self.assertRaisesRegex(VoiceError, 'AUDIO_MISMATCH'):
                self.provider._audio(self.spool, 0, job, None)
        retained = list(self.spool.glob('download-*.partial'))
        self.assertEqual(len(retained), 1)
        first = retained[0].read_bytes()
        self.assertEqual(first, wav())
        self.assertFalse((self.spool / 'segment-00.wav').exists())
        connection = Connection(Response(wav(), mime='audio/wav'))
        with patch.object(self.provider, '_connect', return_value=connection), patch('youtube_ops.collector_voxcpm2.MAX_WAV', 100):
            with self.assertRaisesRegex(VoiceError, 'TOO_LARGE'):
                self.provider._audio(self.spool, 0, job, None)
        self.assertEqual(retained[0].read_bytes(), first)
        partials = list(self.spool.glob('download-*.partial'))
        self.assertEqual(len(partials), 2)
        for path in partials:
            receipt = json.loads(path.with_suffix('.retained.json').read_text())
            self.assertEqual(receipt['status'], 'retained_for_reconciliation')
            self.assertFalse(receipt['publication_eligible'])
        self.assertFalse((self.spool / 'segment-00.wav').exists())

    def test_cancel_only_known_host_job_and_reports_observed_state(self):
        key = '6' * 32; self.jobs[key] = self.job(key, 'Original.'); self.jobs[key]['state'] = 'running'
        directory = self.spool / key; directory.mkdir()
        checkpoint(directory / 'narration.json', {'provider': 'voxcpm2_remote', 'collector_job_id': key,
            'host_jobs': [{'id': key, 'text_sha256': self.jobs[key]['text_sha256'], 'state': 'submission_intent'}]})
        with patch.object(self.provider, '_json', side_effect=self.json_host):
            result = self.provider.cancel(key)
        self.assertEqual(result['host_jobs'], [{'id': key, 'state': 'cancelled'}])
        with self.assertRaises(VoiceError): self.provider.cancel('../host')


def uuid_hex():
    import uuid
    return uuid.uuid4().hex


class DirectCredentialTests(unittest.TestCase):
    def test_namespace_is_separate_and_invalid_names_are_rejected(self):
        self.assertNotEqual(credential_target('https://fixture.invalid'), credential_target('https://fixture.invalid', 'VoxCPM2'))
        with self.assertRaises(ValueError): credential_target('https://fixture.invalid', '../Other')

    def test_fixed_host_target_uses_same_protected_store(self):
        api = Mock(); blob = (ctypes.c_ubyte * 64).from_buffer_copy(('x' * 32).encode('utf-16-le'))
        record = Credential(CredentialBlobSize=64, CredentialBlob=blob)
        def read(target, kind, flags, result):
            self.assertEqual(target, 'KnowledgeNetworkCollector/OxiegenNarrator/Host')
            ctypes.cast(result, ctypes.POINTER(ctypes.POINTER(Credential)))[0] = ctypes.pointer(record)
            return True
        api.CredReadW.side_effect = read
        with patch('youtube_ops.collector_credentials._api', return_value=api):
            self.assertEqual(read_secret('KnowledgeNetworkCollector/OxiegenNarrator/Host')[0], 'x' * 32)
        api.CredFree.assert_called_once()


if __name__ == '__main__': unittest.main()
