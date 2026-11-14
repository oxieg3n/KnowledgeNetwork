import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import wave

from youtube_ops.collector_voice import VoiceError, VoiceStudio, inspect_wav, verify_rights


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\x01\x00' * 16000)
    return out.getvalue()


class VoiceTests(unittest.TestCase):
    def test_endpoint_rejects_remote_credentials_and_ambiguous_hosts(self):
        for url in ('http://localhost:3900', 'http://127.0.0.1.evil:3900',
                    'http://example.org:3900', 'http://user:pass@127.0.0.1:3900',
                    'http://127.0.0.1:3900/path', 'http://127.0.0.1:3900?x=y',
                    'http://127.0.0.1:99999', 'http://127.0.0.1'):
            with self.subTest(url=url), self.assertRaises(VoiceError):
                VoiceStudio(url)
        VoiceStudio('http://[::1]:3900')

    def test_audio_requires_real_complete_pcm(self):
        self.assertEqual(inspect_wav(wav_bytes())['duration_seconds'], 1)
        for data in (b'{"error":"bad"}', wav_bytes()[:-2]):
            with self.assertRaises(VoiceError):
                inspect_wav(data)

    def evidence(self, tmp):
        model = Path(tmp) / 'model.bin'
        model.write_bytes(b'fixture model, not speech weights')
        return {'schema_version': 1, 'engine_id': 'fixture', 'voice_id': 'profile-1',
                'model_id': 'fixture-model', 'model_revision': 'revision-1', 'license': 'fixture-only',
                'reviewed_by': 'test', 'reviewed_at': '2026-11-14', 'voice_basis': 'test synthetic',
                'rights_reviewed': True, 'commercial_use': True, 'youtube_use': True,
                'voice_consent': True, 'evidence_urls': ['https://example.org/fixture'],
                'model_artifacts': [{'path': str(model), 'sha256': hashlib.sha256(model.read_bytes()).hexdigest()}]}

    def catalog(self):
        return ({'info': {'version': 'test'}, 'paths': {'/v1/audio/speech': {'post': {}}}},
                {'voices': [{'type': 'profile', 'voice_id': 'profile-1'}],
                 'engines': [{'id': 'fixture', 'available': True,
                              'execution_evidence': {'evidence_state': 'loaded'}}]})

    def test_rights_require_exact_local_model_and_no_unknowns(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = self.evidence(tmp)
            verify_rights(evidence, 'fixture', 'profile-1')
            evidence['commercial_use'] = False
            with self.assertRaises(VoiceError):
                verify_rights(evidence, 'fixture', 'profile-1')
            evidence['commercial_use'] = True
            Path(evidence['model_artifacts'][0]['path']).write_bytes(b'changed')
            with self.assertRaisesRegex(VoiceError, 'BLOCKED_MODEL_CHANGED'):
                verify_rights(evidence, 'fixture', 'profile-1')

    def test_generation_checkpoints_before_request_and_keeps_review_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = self.evidence(tmp)
            output = Path(tmp) / 'audio'
            client = VoiceStudio()
            def request(path, payload, **kwargs):
                self.assertEqual(json.loads((output / 'narration.json').read_text())['status'], 'generation_intent')
                self.assertEqual(payload['model'], 'fixture')
                self.assertEqual(payload['voice'], 'profile-1')
                return wav_bytes(), 'audio/wav'
            with patch.object(client, 'discover', return_value=self.catalog()), patch.object(client, '_request', side_effect=request):
                result = client.generate('Local test sentence.', evidence, output)
            self.assertFalse(result['publication_eligible'])
            self.assertEqual(result['listening'], 'NOT_TESTED')
            self.assertEqual(result['audio']['duration_seconds'], 1)
            self.assertTrue((output / 'narration.wav').is_file())
            with patch.object(client, 'discover', return_value=self.catalog()), self.assertRaises(FileExistsError):
                client.generate('Local test sentence.', evidence, output)

    def test_alias_is_not_selected_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = self.evidence(tmp)
            evidence['voice_id'] = 'alloy'
            client = VoiceStudio()
            with patch.object(client, 'discover', return_value=self.catalog()), self.assertRaisesRegex(VoiceError, 'BLOCKED_VOICE_PROFILE'):
                client.generate('Test.', evidence, Path(tmp) / 'audio')

    def test_available_engine_does_not_prove_local_loaded_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema, catalog = self.catalog()
            catalog['engines'][0]['execution_evidence']['evidence_state'] = 'not_loaded'
            client = VoiceStudio()
            with patch.object(client, 'discover', return_value=(schema, catalog)), self.assertRaisesRegex(VoiceError, 'BLOCKED_VOICE_MODEL_NOT_LOADED'):
                client.generate('Test.', self.evidence(tmp), Path(tmp) / 'audio')
            self.assertFalse((Path(tmp) / 'audio').exists())

    def test_timeout_persists_unknown_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = self.evidence(tmp)
            output = Path(tmp) / 'audio'
            client = VoiceStudio()
            with patch.object(client, 'discover', return_value=self.catalog()), patch.object(client, '_request', side_effect=VoiceError('VOICE_TIMEOUT_RESULT_UNKNOWN')) as request:
                with self.assertRaises(VoiceError):
                    client.generate('Test.', evidence, output)
                self.assertEqual(request.call_count, 1)
            self.assertFalse(json.loads((output / 'narration.json').read_text())['retry_automatically'])
            self.assertFalse((output / 'narration.wav').exists())

    def test_json_response_is_not_saved_as_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = VoiceStudio()
            with patch.object(client, 'discover', return_value=self.catalog()), patch.object(client, '_request', return_value=(b'{}', 'application/json')):
                with self.assertRaisesRegex(VoiceError, 'INVALID_AUDIO_CONTENT_TYPE'):
                    client.generate('Test.', self.evidence(tmp), Path(tmp) / 'audio')
            self.assertFalse((Path(tmp) / 'audio/narration.wav').exists())

    def test_auth_failure_is_redacted(self):
        client = VoiceStudio(token='private-test')
        error = urllib.error.HTTPError(client.base_url, 401, 'private server detail', {}, None)
        with patch.object(client.opener, 'open', side_effect=error), self.assertRaisesRegex(VoiceError, '^BLOCKED_VOICE_AUTH$'):
            client._request('/health')

    def test_unknown_route_and_redirect_are_blocked(self):
        client = VoiceStudio()
        with self.assertRaisesRegex(VoiceError, 'UNSUPPORTED_ENDPOINT'):
            client._request('//example.org')
        from youtube_ops.collector_voice import NoRedirect
        with self.assertRaisesRegex(VoiceError, 'BLOCKED_REDIRECT'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org')


if __name__ == '__main__':
    unittest.main()
