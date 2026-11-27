"""One reviewed model load per synthetic batch; no host/GPU execution."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import wave

from tests.fixture_retention import FixtureDirectory
from youtube_ops import collector_voxcpm2 as voice
from youtube_ops.collector_narration_common import checkpoint, inspect_wav
from youtube_ops.collector_narration_receipt import read_voxcpm2_receipt
from tests.test_collector_voxcpm2 import Connection, Response


class BatchClientTests(unittest.TestCase):
    def setUp(self):
        folder = FixtureDirectory(prefix='kn-batch-client-')
        self.addCleanup(folder.cleanup)
        self.spool = Path(folder.name)
        self.key = 'a' * 32
        self.parts, self.text = ['First.', 'Second.'], 'First. Second.'
        self.proof = {'script_sha256': 'a' * 64, 'config_sha256': 'b' * 64,
                      'model_revision': 'synthetic-batch-only', 'license_evidence_sha256': 'c' * 64}
        url = 'https://batch-fixture.invalid:9443'
        route = {'schema_version': 1, 'base_url': url, 'host_identity': 'BLACKHAT-BASE',
                 'transport': 'https', 'auth_mode': 'scoped_bearer', 'pinned_addresses': ['10.20.30.40'],
                 'verified_by': 'synthetic-test', 'verified_at': '2026-11-20',
                 'transport_evidence_sha256': 'd' * 64, 'expected_provenance': self.proof}
        self.provider = voice.RemoteVoxCPM2Provider(url, route, self.spool)
        self.health = {'schema_version': 1, 'service': voice.SERVICE, 'narrator_id': voice.NARRATOR,
                       'status': 'ready', 'execution_hold': False, 'provenance': self.proof, 'segment_batches': True}
        data = io.BytesIO()
        with wave.open(data, 'wb') as stream:
            stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x01\x00' * 2400)
        # Preserve the host's exact WAV envelope; local PCM re-encoding loses this chunk.
        raw = data.getvalue() + b'JUNK' + struct.pack('<I', 4) + b'keep'
        self.data = raw[:4] + struct.pack('<I', len(raw) - 8) + raw[8:]
        self.posts, self.gets, self.downloads, self.jobs = [], [], [], {}
        self.mutate = lambda value: value
        self.lose_post = False
        for name, effect in (('_json', self.json_host), ('_request', self.download)):
            mocked = patch.object(self.provider, name, side_effect=effect)
            mocked.start(); self.addCleanup(mocked.stop)

    def host_job(self, payload):
        audio = inspect_wav(self.data)
        audio['duration'] = audio.pop('duration_seconds'); audio['bytes'] = len(self.data)
        return {'id': payload['idempotency_key'], 'state': 'completed',
                'execution_mode': voice.BATCH_EXECUTION_MODE,
                'text_sha256': hashlib.sha256(payload['text'].encode()).hexdigest(),
                'provenance': self.proof, 'audio': audio,
                'cues': [{'text': self.parts[0], 'start_sample': 0, 'end_sample': 800, 'start': 0, 'end': .1},
                         {'text': self.parts[1], 'start_sample': 800, 'end_sample': 2400, 'start': .1, 'end': .3}]}

    def json_host(self, method, path, payload=None, cancel=None):
        if path == '/health': return deepcopy(self.health)
        if method == 'POST':
            self.assertEqual(path, '/v1/narrations')
            self.assertEqual(set(payload), {'idempotency_key', 'text', 'narrator_id', 'segments'})
            self.posts.append(deepcopy(payload))
            self.jobs[payload['idempotency_key']] = self.mutate(self.host_job(payload))
            if self.lose_post:
                self.lose_post = False
                raise voice.VoiceError('NARRATION_TRANSPORT_OUTCOME_UNKNOWN')
            return deepcopy(self.jobs[payload['idempotency_key']])
        self.gets.append(path)
        key = path.split('/')[3]
        if key not in self.jobs:
            error = voice.VoiceError('NARRATION_NOT_FOUND'); error.http_status = 404
            raise error
        return deepcopy(self.jobs[key])

    def download(self, method, path, payload=None, *, destination=None, **options):
        self.assertEqual((method, path), ('GET', '/v1/narrations/' + self.key + '/audio'))
        self.downloads.append(path)
        Path(destination).write_bytes(self.data)
        return b''

    def generate(self, **options):
        return self.provider.generate(self.key, self.text, segments=self.parts, **options)

    def test_new_multi_segment_batch_posts_once_downloads_exact_full_wav_and_is_readable(self):
        result = self.generate()
        self.assertEqual(self.posts, [{'idempotency_key': self.key, 'text': self.text,
                                     'narrator_id': voice.NARRATOR, 'segments': self.parts}])
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(result['request_mode'], voice.BATCH_MODE)
        self.assertEqual(result['execution_mode'], 'cli_segment_batch_v1')
        self.assertEqual([job['id'] for job in result['host_jobs']], [self.key])
        self.assertEqual(result['host_jobs'][0]['audio_sha256'], result['audio']['sha256'])
        path = self.spool / self.key / 'narration.wav'
        self.assertEqual(path.read_bytes(), self.data)
        self.assertEqual(result['audio']['sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(result['cues'][1]['start_sample'], 800)
        receipt = read_voxcpm2_receipt(path.with_name('narration.json'), expected_text=self.text)
        self.assertEqual(receipt[2], result)
        self.assertFalse(list(path.parent.glob('segment-*.wav')))
        self.assertEqual(self.generate(), result)
        self.assertEqual(len(self.posts), 1); self.assertEqual(len(self.downloads), 1)

    def test_new_multi_requires_literal_true_capability_and_never_fans_out(self):
        for index, capability in enumerate((None, False, 1, 'true')):
            with self.subTest(capability=capability):
                self.health['segment_batches'] = capability
                with self.assertRaisesRegex(voice.VoiceError, 'SEGMENT_BATCH_UNSUPPORTED'):
                    self.provider.generate(f'{index:032x}', self.text, segments=self.parts)
        self.assertEqual(self.posts, []); self.assertEqual(self.downloads, [])

    def test_uncertain_post_recovers_same_batch_by_get_despite_capability_hold_drift(self):
        self.lose_post = True
        with self.assertRaisesRegex(voice.VoiceError, 'OUTCOME_UNKNOWN'): self.generate()
        self.health.update(segment_batches=False, execution_hold=True, status='blocked')
        result = self.generate()
        self.assertEqual(result['status'], 'generated_pending_review')
        self.assertEqual(self.gets, ['/v1/narrations/' + self.key])
        self.assertEqual(len(self.posts), 1); self.assertEqual(len(self.downloads), 1)

    def test_missing_uncertain_batch_remains_held_without_new_id_or_post(self):
        self.lose_post = True
        with self.assertRaises(voice.VoiceError): self.generate()
        self.jobs.clear()
        with self.assertRaisesRegex(voice.VoiceError, 'NOT_FOUND'): self.generate()
        self.assertEqual(len(self.posts), 1); self.assertEqual(self.downloads, [])
        receipt = json.loads((self.spool / self.key / 'narration.json').read_text())
        self.assertEqual(receipt['host_jobs'][0]['id'], self.key)
        self.assertEqual(receipt['request_mode'], voice.BATCH_MODE)

    def test_changed_inputs_or_removed_batch_mode_cannot_reinterpret_original_intent(self):
        self.lose_post = True
        with self.assertRaises(voice.VoiceError): self.generate()
        with self.assertRaisesRegex(voice.VoiceError, 'IDEMPOTENCY'):
            self.provider.generate(self.key, 'First. Changed.', segments=['First.', 'Changed.'])
        path = self.spool / self.key / 'narration.json'
        receipt = json.loads(path.read_text()); receipt.pop('request_mode')
        checkpoint(path, receipt)
        with self.assertRaisesRegex(voice.VoiceError, 'IDEMPOTENCY'): self.generate()
        self.assertEqual(len(self.posts), 1); self.assertEqual(self.gets, [])

    def test_invalid_cues_are_rejected_before_download(self):
        changes = (
            lambda j: j['cues'][0].update(text='Different.'),
            lambda j: j['cues'][0].update(start_sample=True),
            lambda j: j['cues'][1].update(start_sample=801),
            lambda j: j['cues'][1].update(end_sample=2399, end=2399 / 8000),
            lambda j: j['cues'][0].update(end=float('nan')),
            lambda j: j['cues'][1].update(end=float('inf')),
            lambda j: j['cues'][1].update(start=.2),
            lambda j: j.update(cues=[]),
        )
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.key = f'{index + 30:032x}'
                def mutate(value):
                    change(value)
                    return value
                self.mutate = mutate
                with self.assertRaisesRegex(voice.VoiceError, 'BATCH_CUES_INVALID'): self.generate()
        self.assertEqual(self.downloads, [])

    def test_wrong_host_identity_text_digest_or_provenance_never_downloads(self):
        for index, change in enumerate((lambda j: j.update(id='b' * 32),
                                        lambda j: j.update(text_sha256=hashlib.sha256(self.parts[0].encode()).hexdigest()),
                                        lambda j: j.update(provenance={**self.proof, 'model_revision': 'other'}))):
            with self.subTest(index=index):
                self.key = f'{index + 50:032x}'
                def mutate(value):
                    change(value)
                    return value
                self.mutate = mutate
                with self.assertRaisesRegex(voice.VoiceError, 'RECEIPT_MISMATCH'): self.generate()
        self.assertEqual(self.downloads, [])

    def test_missing_or_wrong_host_execution_mode_blocks_before_poll_or_download(self):
        for index, mode in enumerate((None, 'canonical_narrate_ps1', True)):
            with self.subTest(mode=mode):
                self.key = f'{index + 80:032x}'
                def mutate(value):
                    value.update(state='running')
                    if mode is None: value.pop('execution_mode')
                    else: value['execution_mode'] = mode
                    return value
                self.mutate = mutate
                with self.assertRaisesRegex(voice.VoiceError, 'HOST_EXECUTION_MODE_MISMATCH'): self.generate()
        self.assertEqual(self.gets, [])
        self.assertEqual(self.downloads, [])
        self.assertEqual(len(self.posts), 3)  # Each distinct job got one batch attempt, never a fan-out.

    def test_polled_execution_mode_drift_remains_same_job_without_fallback(self):
        def host(method, path, payload=None, cancel=None):
            value = self.json_host(method, path, payload, cancel)
            if method == 'POST':
                self.jobs[self.key]['execution_mode'] = 'canonical_narrate_ps1'
                return {**value, 'state': 'running'}
            return value
        with patch.object(self.provider, '_json', side_effect=host), patch.object(voice.time, 'sleep'):
            with self.assertRaisesRegex(voice.VoiceError, 'HOST_EXECUTION_MODE_MISMATCH'): self.generate()
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.gets, ['/v1/narrations/' + self.key])
        self.assertEqual(self.downloads, [])

    def test_completed_receipt_cannot_relabel_cli_batch_as_canonical_script_execution(self):
        self.generate()
        path = self.spool / self.key / 'narration.json'
        receipt = json.loads(path.read_text()); receipt['execution_mode'] = 'canonical_narrate_ps1'
        checkpoint(path, receipt)
        with patch.object(self.provider, '_json') as network:
            with self.assertRaisesRegex(voice.VoiceError, 'LOCAL_RECEIPT_CHANGED'): self.generate()
            network.assert_not_called()

    def test_checkpoint_failure_after_verified_batch_wav_recovers_without_second_download(self):
        original_checkpoint = voice.checkpoint
        failed = False
        def checkpoint_once(path, value):
            nonlocal failed
            if path.name == 'narration.json' and value.get('status') == 'generated_pending_review' and not failed:
                failed = True
                raise OSError('synthetic checkpoint interruption')
            return original_checkpoint(path, value)
        with patch.object(voice, 'checkpoint', side_effect=checkpoint_once):
            with self.assertRaisesRegex(voice.VoiceError, 'LOCAL_EVIDENCE_INVALID'): self.generate()
        path = self.spool / self.key / 'narration.wav'
        original, file_id = path.read_bytes(), path.stat().st_ino
        self.assertEqual(self.generate()['status'], 'generated_pending_review')
        self.assertEqual((path.read_bytes(), path.stat().st_ino), (original, file_id))
        self.assertEqual(len(self.posts), 1); self.assertEqual(len(self.downloads), 1)

    def test_batch_digest_mismatch_retains_download_without_final_or_fallback(self):
        def mutate(value):
            value['audio']['sha256'] = 'f' * 64
            return value
        self.mutate = mutate
        with self.assertRaisesRegex(voice.VoiceError, 'AUDIO_MISMATCH'): self.generate()
        directory = self.spool / self.key
        self.assertFalse((directory / 'narration.wav').exists())
        retained = list(directory.glob('download-*.partial'))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), self.data)
        self.assertTrue(retained[0].with_suffix('.retained.json').exists())
        self.assertEqual(len(self.posts), 1)

    def test_batch_cancel_uses_only_the_original_full_text_host_identity(self):
        self.lose_post = True
        with self.assertRaises(voice.VoiceError): self.generate()
        def cancelled(method, path, payload=None, cancel=None):
            if path == '/health': return self.health
            self.assertEqual((method, path, payload), ('POST', '/v1/narrations/' + self.key + '/cancel', {}))
            return {**self.jobs[self.key], 'state': 'cancelled'}
        with patch.object(self.provider, '_json', side_effect=cancelled) as request:
            result = self.provider.cancel(self.key)
        self.assertEqual(result['host_jobs'], [{'id': self.key, 'state': 'cancelled'}])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(len(self.posts), 1)

    def test_batch_cancel_rejects_other_valid_job_id_before_any_network_call(self):
        self.lose_post = True
        with self.assertRaises(voice.VoiceError): self.generate()
        path = self.spool / self.key / 'narration.json'
        receipt = json.loads(path.read_text())
        receipt['host_jobs'][0]['id'] = 'b' * 32
        checkpoint(path, receipt)
        with patch.object(self.provider, '_json') as network:
            with self.assertRaisesRegex(voice.VoiceError, 'LOCAL_RECEIPT_CHANGED'):
                self.provider.cancel(self.key)
            network.assert_not_called()

    def test_batch_deadline_covers_manifest_and_runner_without_weakening_legacy_deadline(self):
        payload = {'idempotency_key': self.key, 'text': self.text}
        done = self.host_job(payload); queued = {**done, 'state': 'running'}
        self.jobs[self.key] = done
        with patch.object(voice.time, 'monotonic', side_effect=[0, 601]), patch.object(voice.time, 'sleep'):
            result = self.provider._complete(self.key, done['text_sha256'], self.proof, queued, None,
                                            poll_seconds=voice.BATCH_POLL_SECONDS)
        self.assertEqual(result['state'], 'completed')
        self.gets.clear()
        with patch.object(voice.time, 'monotonic', side_effect=[0, 601]), patch.object(voice.time, 'sleep'):
            with self.assertRaisesRegex(voice.VoiceError, 'POLL_DEADLINE'):
                self.provider._complete(self.key, done['text_sha256'], self.proof, queued, None)
        self.assertEqual(self.gets, [])

    def test_noncanonical_batch_text_is_blocked_without_silent_wire_normalization(self):
        with self.assertRaisesRegex(voice.VoiceError, 'INVALID_NARRATION_BATCH_SEGMENTS'):
            self.provider.generate(self.key, 'First.\nSecond.', segments=self.parts)
        self.assertEqual(self.posts, [])

    def test_batch_cli_lines_reject_padding_controls_and_del_before_post(self):
        for index, first in enumerate((' First.', 'First. ', 'Fi\trst.', 'Fi\nrst.', 'Fi\x7frst.')):
            with self.subTest(first=repr(first)):
                parts = [first, 'Second.']
                with self.assertRaisesRegex(voice.VoiceError, 'INVALID_NARRATION_BATCH_SEGMENTS'):
                    self.provider.generate(f'{index + 70:032x}', ' '.join(parts), segments=parts)
        self.assertEqual(self.posts, [])

    def test_valid_twelve_thousand_unicode_batch_fits_bounded_transport(self):
        parts = ['\U0001f600' * 5999, '\U0001f600' * 6000]
        payload = {'idempotency_key': self.key, 'text': ' '.join(parts),
                   'narrator_id': voice.NARRATOR, 'segments': parts}
        voice.request_identity(self.key, payload['text'], parts)
        connection = Connection(Response())
        with patch.object(self.provider, '_connect', return_value=connection), \
                patch.object(voice, 'read_credential', return_value=('x' * 32, 1)):
            voice.RemoteVoxCPM2Provider._request(self.provider, 'POST', '/v1/narrations', payload)
        encoded = connection.requests[0][2]
        self.assertGreater(len(encoded), 65536)
        self.assertLessEqual(len(encoded), voice.BATCH_MAX_BODY)
        self.assertEqual(json.loads(encoded), payload)
        with patch.object(self.provider, '_connect') as connect, \
                patch.object(voice, 'read_credential', return_value=('x' * 32, 1)):
            with self.assertRaisesRegex(voice.VoiceError, 'INPUT_TOO_LARGE'):
                voice.RemoteVoxCPM2Provider._request(self.provider, 'POST', '/v1/narrations',
                    {**payload, 'text': '\U0001f600' * 40000})
            connect.assert_not_called()

    def test_encoded_body_preflight_precedes_submission_intent(self):
        with patch.object(voice, 'BATCH_MAX_BODY', 20):
            with self.assertRaisesRegex(voice.VoiceError, 'INPUT_TOO_LARGE'): self.generate()
        receipt = json.loads((self.spool / self.key / 'narration.json').read_text())
        self.assertEqual(receipt['host_jobs'], [])
        self.assertEqual(self.posts, [])
