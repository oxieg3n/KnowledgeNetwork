"""Mock remote-provider tests; these never establish host API acceptance."""
import io
import ctypes
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import wave

from youtube_ops.collector_voice import (RemoteVoiceStudioProvider, VoiceError, digest,
    inspect_wav, prepare_request, verify_rights, checkpoint)
from youtube_ops.collector_credentials import credential_target, validate_secret
from youtube_ops.collector_credentials import Credential, read_credential, write_credential


def wav_bytes(frames=16000):
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(b'\x01\x00' * frames)
    return output.getvalue()


class Response(io.BytesIO):
    def __init__(self, data=b'{}', status=200, mime='application/json', retry='0'):
        super().__init__(data)
        self.status, self.mime, self.retry = status, mime, retry

    def getheader(self, name, default=''):
        return {'Content-Type': self.mime, 'Retry-After': self.retry}.get(name, default)


class Connection:
    def __init__(self, response):
        self.response, self.requests, self.closed = response, [], False
    def request(self, *args):
        self.requests.append(args)
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True


class RemoteVoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spool = Path(self.tmp.name)
        self.url = 'https://voice-fixture.invalid:443'
        self.route = {'schema_version': 1, 'base_url': self.url, 'host_identity': 'BLACKHAT-BASE',
            'pinned_addresses': ['10.23.45.67'], 'transport': 'https', 'verified_by': 'fixture',
            'verified_at': '2026-11-14', 'transport_evidence_sha256': 'a' * 64, 'auth_mode': 'share_pin'}
        self.provider = RemoteVoiceStudioProvider(self.url, self.route, self.spool)
        self.credential = patch('youtube_ops.collector_voice.read_credential', return_value=('123456', 7))
        self.credential.start(); self.addCleanup(self.credential.stop)

    def catalog(self):
        return ({'info': {'version': 'fixture'}, 'paths': {'/v1/audio/speech': {'post': {}}}},
            {'voices': [{'type': 'profile', 'voice_id': 'profile-fixture'}], 'engines': [
                {'id': 'fixture', 'available': True, 'active_model_id': 'model-fixture',
                 'execution_evidence': {'evidence_state': 'loaded', 'actual_execution_device': 'cpu'}}]})

    def evidence(self):
        schema, catalog = self.catalog()
        _, _, fingerprint = self.provider.selected_capabilities(schema, catalog, 'fixture', 'profile-fixture')
        return {'schema_version': 2, 'engine_id': 'fixture', 'voice_id': 'profile-fixture',
            'model_id': 'model-fixture', 'model_revision': 'test', 'license': 'fixture-only',
            'reviewed_by': 'test', 'reviewed_at': '2026-11-14', 'voice_basis': 'fixture',
            'rights_reviewed': True, 'commercial_use': True, 'youtube_use': True, 'voice_consent': True,
            'evidence_urls': ['https://example.org/fixture'], 'capability_fingerprint': fingerprint,
            'host_model_evidence_sha256': 'b' * 64,
            'model_artifacts': [{'logical_name': 'host-fixture-model', 'sha256': 'c' * 64}]}

    def auth(self):
        checkpoint(self.spool / 'remote-auth.json', {'endpoint_sha256': digest(self.url),
            'route_sha256': digest(self.route),
            'credential_version': 7, 'invalid_status': 401, 'valid_status': 200, 'auth_mode': 'share_pin'})

    def test_no_local_loopback_public_route_or_root_credentials(self):
        for address in ('127.0.0.1', '::1', '8.8.8.8', '169.254.169.254'):
            route = {**self.route, 'pinned_addresses': [address]}
            with self.assertRaises(VoiceError):
                RemoteVoiceStudioProvider(self.url, route, self.spool)
        with self.assertRaisesRegex(VoiceError, 'ROOT'):
            RemoteVoiceStudioProvider(self.url, {**self.route, 'auth_mode': 'root_key'}, self.spool)
        with self.assertRaisesRegex(VoiceError, 'ROOT'):
            RemoteVoiceStudioProvider(self.url, {**self.route, 'auth_mode': 'scoped_bearer'}, self.spool)

    def test_http_requires_verified_route_and_no_plaintext_bearer(self):
        url = 'http://voice-fixture.invalid:3901'
        route = {**self.route, 'base_url': url}
        with self.assertRaisesRegex(VoiceError, 'TRANSPORT'):
            RemoteVoiceStudioProvider(url, route, self.spool)
        RemoteVoiceStudioProvider(url, {**route, 'transport': 'tailscale_http'}, self.spool)
        with self.assertRaisesRegex(VoiceError, 'PLAINTEXT_BEARER'):
            RemoteVoiceStudioProvider(url, {**route, 'transport': 'isolated_link_http',
                'auth_mode': 'scoped_bearer', 'route_scoped': True}, self.spool)

    def test_dns_rebinding_rejected_before_socket_connect(self):
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]
        with patch('socket.getaddrinfo', return_value=answer), patch('socket.create_connection') as connect:
            with self.assertRaisesRegex(VoiceError, 'DESTINATION_CHANGED'):
                self.provider._connect(1)
            connect.assert_not_called()

    def test_unknown_paths_redirects_and_auth_failures_are_redacted(self):
        with self.assertRaises(VoiceError):
            self.provider._request('/system/info')
        with self.assertRaises(VoiceError):
            self.provider._request('/api/settings/license/pockettts')
        for path in ('/models', '/model/loaded', '/.well-known/voicestudio-speech'):
            with patch.object(self.provider, '_connect', return_value=Connection(Response())):
                self.provider._json(path)
            with self.assertRaises(VoiceError):
                self.provider._request(path, {})
        for status, code in ((302, 'REDIRECT'), (401, 'AUTH'), (403, 'AUTH')):
            with patch.object(self.provider, '_connect', return_value=Connection(Response(b'private secret', status))):
                with self.assertRaisesRegex(VoiceError, code):
                    self.provider._request('/health')

    def test_mixed_capability_permissions_preserve_good_catalog(self):
        schema, catalog = self.catalog()
        schema['paths'].update({path: {'get': {}} for path in
            ('/.well-known/voicestudio-speech', '/model/loaded', '/models')})
        connections = [Connection(Response(b'{"protocol":"fixture.speech"}')),
                       Connection(Response(b'private server error body', status=403)),
                       Connection(Response(b'{"models":[{"repo_id":"fixture-model","downloaded":true}]}'))]
        with patch.object(self.provider, 'discover', return_value=(schema, catalog)), patch.object(self.provider, '_connect', side_effect=connections) as connect:
            result = self.provider.inspect_capabilities()
        self.assertEqual(connect.call_count, 3)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertFalse(result['complete'])
        saved = json.loads((self.spool / 'host-capabilities.private.json').read_text())
        self.assertEqual(saved['/model/loaded'], {'status': 'BLOCKED', 'error': 'BLOCKED_VOICE_AUTH', 'http_status': 403})
        self.assertTrue(saved['/models']['data']['models'][0]['downloaded'])
        self.assertEqual(saved['/.well-known/voicestudio-speech']['status'], 'PASS')
        self.assertNotIn('private server error body', json.dumps(saved))

    def test_mandatory_discovery_auth_failure_is_not_partial_success(self):
        with patch.object(self.provider, 'discover', side_effect=VoiceError('BLOCKED_VOICE_AUTH')), patch.object(self.provider, '_connect') as connect:
            with self.assertRaisesRegex(VoiceError, 'BLOCKED_VOICE_AUTH'):
                self.provider.inspect_capabilities()
            connect.assert_not_called()
        self.assertFalse((self.spool / 'host-capabilities.private.json').exists())

    def test_bounded_read_retry_but_never_post_retry(self):
        connections = [Connection(Response(status=429)), Connection(Response())]
        with patch.object(self.provider, '_connect', side_effect=connections) as connect, patch('time.sleep'):
            self.provider._request('/health')
            self.assertEqual(connect.call_count, 2)
        with patch.object(self.provider, '_connect', return_value=Connection(Response(status=503))) as connect:
            with self.assertRaisesRegex(VoiceError, 'UNAVAILABLE'):
                self.provider._request('/v1/audio/speech', {'input': 'fixture'})
            self.assertEqual(connect.call_count, 1)
        with patch.object(self.provider, '_connect', return_value=Connection(Response(status=429, retry='60'))) as connect:
            with self.assertRaisesRegex(VoiceError, 'BACKPRESSURE'):
                self.provider._request('/health')
            self.assertEqual(connect.call_count, 1)

    def test_wav_stream_limit_is_enforced_without_loading_response(self):
        connection = Connection(Response(wav_bytes(), mime='audio/wav'))
        with patch.object(self.provider, '_connect', return_value=connection), patch('youtube_ops.collector_voice.MAX_WAV', 100):
            with self.assertRaisesRegex(VoiceError, 'TOO_LARGE'):
                self.provider._request('/v1/audio/speech', {}, destination=self.spool / 'too-large.wav')

    def test_tls_uses_default_verification_and_original_hostname(self):
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.23.45.67', 443))]
        with patch('socket.getaddrinfo', return_value=answer), patch('socket.create_connection') as connect, patch('ssl.create_default_context') as context:
            self.provider._connect(3)
            connect.assert_called_once_with(('10.23.45.67', 443), 3)
            context.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='voice-fixture.invalid')

    def test_stream_wav_and_reject_json_audio(self):
        path = self.spool / 'stream.wav'
        connection = Connection(Response(wav_bytes(), mime='audio/wav'))
        with patch.object(self.provider, '_connect', return_value=connection):
            self.provider._request('/v1/audio/speech', {'input': 'fixture'}, destination=path)
        self.assertEqual(inspect_wav(path)['frames'], 16000)
        self.assertEqual(connection.requests[0][3]['X-OmniVoice-Pin'], '123456')
        self.assertTrue(connection.closed)
        with patch.object(self.provider, '_connect', return_value=Connection(Response())):
            with self.assertRaisesRegex(VoiceError, 'CONTENT_TYPE'):
                self.provider._request('/v1/audio/speech', {}, destination=self.spool / 'bad.wav')

    def test_auth_bootstrap_observes_invalid_and_valid_requests(self):
        connections = [Connection(Response(status=401)), Connection(Response(b'{"voices":[]}'))]
        with patch.object(self.provider, '_connect', side_effect=connections):
            self.assertEqual(self.provider.verify_auth()['status'], 'PASS')
        receipt = json.loads((self.spool / 'remote-auth.json').read_text())
        self.assertEqual(receipt['credential_version'], 7)
        self.assertNotIn('123456', json.dumps(receipt))
        with patch.object(self.provider, '_connect', return_value=Connection(Response())):
            with self.assertRaisesRegex(VoiceError, 'NOT_ENFORCED'):
                self.provider.verify_auth()

    def test_host_model_evidence_never_opens_host_path(self):
        evidence = self.evidence()
        verify_rights(evidence, 'fixture', 'profile-fixture')
        evidence['model_artifacts'][0]['path'] = 'C:/host/model'
        with self.assertRaisesRegex(VoiceError, 'HOST_MODEL_EVIDENCE'):
            verify_rights(evidence, 'fixture', 'profile-fixture')

    def test_generation_is_idempotent_and_cues_use_real_pcm(self):
        self.auth()
        text, job_id = 'First sentence. Second sentence.', '1' * 32
        parts = ['First sentence.', 'Second sentence.']
        def synth(path, payload, *, destination, **kwargs):
            saved = json.loads((self.spool / job_id / 'narration.json').read_text())
            self.assertEqual(saved['status'], 'generation_intent')
            Path(destination).write_bytes(wav_bytes(8000 if payload['input'].startswith('First') else 24000))
        with patch.object(self.provider, 'discover', return_value=self.catalog()), patch.object(self.provider, '_request', side_effect=synth) as request:
            result = self.provider.generate(job_id, text, self.evidence(), segments=parts)
            self.assertEqual(request.call_count, 2)
            repeated = self.provider.generate(job_id, text, self.evidence(), segments=parts)
            self.assertEqual(request.call_count, 2)
        self.assertEqual(result, repeated)
        self.assertEqual(result['audio']['frames'], 32000)
        self.assertEqual(result['cues'][0]['end'], .5)
        self.assertEqual(result['cues'][1]['start_sample'], 8000)
        self.assertEqual(result['cues'][1]['end'], 2)
        self.assertFalse(result['publication_eligible'])
        with self.assertRaisesRegex(VoiceError, 'IDEMPOTENCY'):
            self.provider.generate(job_id, 'Different.', self.evidence())

    def test_timeout_is_preserved_and_never_replayed(self):
        self.auth()
        with patch.object(self.provider, 'discover', return_value=self.catalog()), patch.object(self.provider, '_request', side_effect=VoiceError('VOICE_TRANSPORT_RESULT_UNKNOWN')) as request:
            with self.assertRaisesRegex(VoiceError, 'UNKNOWN'):
                self.provider.generate('2' * 32, 'Original sentence.', self.evidence())
            with self.assertRaisesRegex(VoiceError, 'RECONCILIATION'):
                self.provider.generate('2' * 32, 'Original sentence.', self.evidence())
            self.assertEqual(request.call_count, 1)
        saved = json.loads((self.spool / ('2' * 32) / 'narration.json').read_text())
        self.assertEqual(saved['status'], 'blocked_remote_voice')
        self.assertEqual(saved['error'], 'VOICE_TRANSPORT_RESULT_UNKNOWN')

    def test_changed_host_capability_or_credential_version_blocks_post(self):
        self.auth()
        evidence = self.evidence(); evidence['capability_fingerprint'] = 'd' * 64
        with patch.object(self.provider, 'discover', return_value=self.catalog()), patch.object(self.provider, '_request') as request:
            with self.assertRaisesRegex(VoiceError, 'HOST_MODEL_CHANGED'):
                self.provider.generate('4' * 32, 'Original.', evidence)
            request.assert_not_called()
        with patch('youtube_ops.collector_voice.read_credential', return_value=('123456', 8)), patch.object(self.provider, '_request') as request:
            with self.assertRaisesRegex(VoiceError, 'AUTH_NOT_VERIFIED'):
                self.provider.generate('5' * 32, 'Original.', self.evidence())
            request.assert_not_called()

    def test_prepared_request_can_be_adopted_without_losing_identity(self):
        self.auth()
        prepare_request(self.spool, '6' * 32, 'Original.')
        def synth(path, payload, *, destination, **kwargs):
            Path(destination).write_bytes(wav_bytes())
        with patch.object(self.provider, 'discover', return_value=self.catalog()), patch.object(self.provider, '_request', side_effect=synth):
            result = self.provider.generate('6' * 32, 'Original.', self.evidence())
        self.assertEqual(result['status'], 'generated_pending_review')
        self.assertTrue((self.spool / ('6' * 32) / 'request.json').exists())

    def test_single_active_lease_enforces_backpressure(self):
        with self.provider._lease():
            with self.assertRaisesRegex(VoiceError, 'BACKPRESSURE'):
                with self.provider._lease():
                    self.fail('second lease acquired')

    def test_prepare_without_endpoint_preserves_identity_no_stdout_text(self):
        result = prepare_request(self.spool, '3' * 32, 'Private original script.')
        self.assertNotIn('text', result)
        self.assertEqual(result['status'], 'blocked_remote_voice')
        self.assertEqual(prepare_request(self.spool, '3' * 32, 'Private original script.'), result)
        with self.assertRaisesRegex(VoiceError, 'IDEMPOTENCY'):
            prepare_request(self.spool, '3' * 32, 'Changed script.')

    def test_segment_bounds_cannot_be_bypassed_with_whitespace(self):
        with self.assertRaisesRegex(VoiceError, 'SEGMENTS'):
            self.provider.generate('7' * 32, 'Original.', self.evidence(), segments=['Original.' + ' ' * 4096])

    def test_pcm_json_and_truncation_rejected(self):
        for data in (b'{}', wav_bytes()[:-2]):
            with self.assertRaises(VoiceError):
                inspect_wav(data)


class CredentialValidationTests(unittest.TestCase):
    def test_target_is_bound_to_endpoint_without_exposing_it(self):
        target = credential_target('https://fixture.invalid')
        self.assertNotIn('fixture.invalid', target)
        self.assertNotEqual(target, credential_target('https://other.invalid'))

    def test_pin_and_admin_session_validation(self):
        validate_secret('123456', 'share_pin')
        for secret, mode in (('12345', 'share_pin'), ('123456\r\n', 'share_pin'),
                             ('ovs_admin_session_private', 'scoped_bearer'), ('root', 'root_key')):
            with self.assertRaises(ValueError):
                validate_secret(secret, mode)

    def test_mock_credwrite_uses_user_generic_store_not_plaintext_file(self):
        from unittest.mock import Mock
        api = Mock()
        seen = {}
        def write(pointer, flags):
            record = ctypes.cast(pointer, ctypes.POINTER(Credential)).contents
            seen.update(type=record.Type, persist=record.Persist, target=record.TargetName,
                        blob=ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize).decode('utf-16-le'))
            return True
        api.CredWriteW.side_effect = write
        with patch('youtube_ops.collector_credentials._api', return_value=api):
            write_credential('https://fixture.invalid', '123456', 'share_pin')
        self.assertEqual(seen, {'type': 1, 'persist': 2,
            'target': credential_target('https://fixture.invalid'), 'blob': '123456'})

    def test_mock_credread_frees_native_memory_and_reports_version(self):
        from unittest.mock import Mock
        api = Mock()
        blob = (ctypes.c_ubyte * 12).from_buffer_copy('123456'.encode('utf-16-le'))
        record = Credential(CredentialBlobSize=12, CredentialBlob=blob)
        record.LastWritten.dwLowDateTime = 42
        def read(target, kind, flags, result):
            ctypes.cast(result, ctypes.POINTER(ctypes.POINTER(Credential)))[0] = ctypes.pointer(record)
            return True
        api.CredReadW.side_effect = read
        with patch('youtube_ops.collector_credentials._api', return_value=api):
            self.assertEqual(read_credential('https://fixture.invalid', 'share_pin'), ('123456', 42))
        api.CredFree.assert_called_once()


if __name__ == '__main__':
    unittest.main()
