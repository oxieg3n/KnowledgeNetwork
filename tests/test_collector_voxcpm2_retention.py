"""Synthetic transport and retained artifacts; no host inference or deletion."""
from tests.fixture_retention import FixtureDirectory
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

from youtube_ops import collector_voxcpm2 as voice
from youtube_ops.collector_narration_common import inspect_wav


def wav(sample=b'\x01\x00'):
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        stream.writeframes(sample * 1600)
    return output.getvalue()


class SyntheticTransport(voice.RemoteVoxCPM2Provider):
    def __init__(self, spool):
        self.proof = {'script_sha256': 'a' * 64, 'config_sha256': 'b' * 64,
                      'model_revision': 'synthetic-transport-only', 'license_evidence_sha256': 'c' * 64}
        url = 'https://retention-fixture.invalid:9443'
        route = {'schema_version': 1, 'base_url': url, 'host_identity': 'BLACKHAT-BASE',
                 'transport': 'https', 'auth_mode': 'scoped_bearer', 'pinned_addresses': ['10.20.30.40'],
                 'verified_by': 'synthetic-test', 'verified_at': '2026-11-15',
                 'transport_evidence_sha256': 'd' * 64, 'expected_provenance': self.proof}
        super().__init__(url, route, spool)
        self.posts, self.jobs, self.data = [], {}, wav()

    def _json(self, method, path, payload=None, cancel=None):
        if path == '/health':
            return {'schema_version': 1, 'service': voice.SERVICE, 'narrator_id': voice.NARRATOR,
                    'status': 'ready', 'execution_hold': False, 'provenance': self.proof}
        if method == 'POST':
            self.posts.append(dict(payload))
            key = payload['idempotency_key']
            audio = inspect_wav(self.data)
            audio['duration'] = audio.pop('duration_seconds'); audio['bytes'] = len(self.data)
            self.jobs[key] = {'id': key, 'state': 'completed', 'provenance': self.proof,
                             'text_sha256': hashlib.sha256(payload['text'].encode()).hexdigest(), 'audio': audio}
            return self.jobs[key]
        return self.jobs[path.split('/')[3]]

    def _request(self, method, path, payload=None, *, destination=None, **options):
        if method != 'GET' or not path.endswith('/audio'):
            raise AssertionError('Unexpected synthetic transport request')
        Path(destination).write_bytes(self.data)
        return b''


class NarrationRetentionTests(unittest.TestCase):
    def setUp(self):
        self.folder = FixtureDirectory(prefix='kn-voxcpm-retention-')
        self.addCleanup(self.folder.cleanup)
        self.spool = Path(self.folder.name)
        self.provider = SyntheticTransport(self.spool)
        self.job = '1' * 32

    def test_failed_download_retained_with_digest_then_same_job_recovers_by_get(self):
        def disconnected(*arguments, destination=None, **options):
            Path(destination).write_bytes(b'partial synthetic transport')
            raise voice.VoiceError('NARRATOR_DISCONNECTED')
        with patch.object(self.provider, '_request', side_effect=disconnected):
            with self.assertRaisesRegex(voice.VoiceError, '^NARRATOR_DISCONNECTED$'):
                self.provider.generate(self.job, 'Private synthetic transport test.')
        directory = self.spool / self.job
        partials = list(directory.glob('download-*.partial'))
        self.assertEqual(len(partials), 1)
        retained = json.loads(partials[0].with_suffix('.retained.json').read_text())
        self.assertEqual(retained['sha256'], hashlib.sha256(partials[0].read_bytes()).hexdigest())
        self.assertEqual(retained['hash_evidence'], 'measured_stable')
        result = self.provider.generate(self.job, 'Private synthetic transport test.')
        self.assertEqual(result['status'], 'generated_pending_review')
        self.assertEqual(len(self.provider.posts), 1)
        self.assertTrue(partials[0].exists())

    def test_checkpoint_failure_after_final_wav_recovers_exact_bytes_without_post_or_overwrite(self):
        checkpoint = voice.checkpoint
        failed = False
        def fail_once(path, value):
            nonlocal failed
            if path.name == 'narration.json' and value.get('status') == 'generated_pending_review' and not failed:
                failed = True
                raise OSError('synthetic checkpoint fault')
            return checkpoint(path, value)
        with patch.object(voice, 'checkpoint', side_effect=fail_once):
            with self.assertRaisesRegex(voice.VoiceError, '^NARRATION_LOCAL_EVIDENCE_INVALID$'):
                self.provider.generate(self.job, 'Exact checkpoint recovery.')
        final = self.spool / self.job / 'narration.wav'
        original, identity = final.read_bytes(), final.stat().st_ino
        result = self.provider.generate(self.job, 'Exact checkpoint recovery.')
        self.assertEqual(result['status'], 'generated_pending_review')
        self.assertEqual(final.read_bytes(), original)
        self.assertEqual(final.stat().st_ino, identity)
        self.assertEqual(len(self.provider.posts), 1)
        duplicate = list(final.parent.glob('joined-*.partial'))
        self.assertEqual(len(duplicate), 1)
        self.assertEqual(duplicate[0].read_bytes(), original)
        self.assertTrue(duplicate[0].with_suffix('.retained.json').exists())

    def test_mismatched_existing_final_stays_blocked_and_all_join_attempts_are_retained(self):
        directory = self.spool / self.job
        directory.mkdir()
        final = directory / 'narration.wav'
        original = wav(b'\x02\x00')
        final.write_bytes(original)
        for _ in range(2):
            with self.assertRaisesRegex(voice.VoiceError, '^NARRATION_LOCAL_OUTPUT_REQUIRES_RECONCILIATION$'):
                self.provider.generate(self.job, 'Preserve the prior final.')
        self.assertEqual(final.read_bytes(), original)
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(len(list(directory.glob('joined-*.partial'))), 2)
        self.assertEqual(len(list(directory.glob('joined-*.retained.json'))), 2)

    def test_nonregular_existing_final_is_not_opened_or_replaced(self):
        directory = self.spool / self.job
        directory.mkdir()
        final = directory / 'narration.wav'
        final.mkdir()
        with self.assertRaisesRegex(voice.VoiceError, '^NARRATION_LOCAL_OUTPUT_REQUIRES_RECONCILIATION$'):
            self.provider.generate(self.job, 'Preserve the unexpected final directory.')
        self.assertTrue(final.is_dir())
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(len(list(directory.glob('joined-*.retained.json'))), 1)

    def test_unverified_partial_is_left_in_place_without_reading_outside_the_size_bound(self):
        path = self.spool / ('download-' + 'a' * 32 + '.partial')
        path.write_bytes(b'fixture only')
        stat = path.lstat()
        from types import SimpleNamespace
        oversized = SimpleNamespace(**{key: getattr(stat, key) for key in
            ('st_dev', 'st_ino', 'st_mtime_ns', 'st_nlink', 'st_mode')}, st_size=voice.MAX_WAV + 1)
        original_lstat = Path.lstat
        def fake_lstat(value, *arguments, **options):
            return oversized if value == path else original_lstat(value, *arguments, **options)
        with patch.object(Path, 'lstat', fake_lstat):
            voice.retain_partial(path, 'synthetic oversized metadata')
        value = json.loads(path.with_suffix('.retained.json').read_text())
        self.assertIsNone(value['sha256'])
        self.assertEqual(value['hash_evidence'], 'not_measured')
        self.assertEqual(path.read_bytes(), b'fixture only')


if __name__ == '__main__':
    unittest.main()
