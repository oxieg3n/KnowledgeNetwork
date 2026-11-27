from tests.fixture_retention import FixtureDirectory
import builtins
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from youtube_ops.collector_narration_common import inspect_wav
from youtube_ops.collector_narration_receipt import read_voxcpm2_receipt
from youtube_ops.render import render


class NarrationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = FixtureDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.text = 'First part. Second part.'
        self.wav = self.root / 'narration.wav'
        with wave.open(str(self.wav), 'wb') as stream:
            stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\0\0' * 32000)
        self.receipt = {'provider': 'voxcpm2_remote', 'narrator_id': 'oxiegen-narrator',
            'status': 'generated_pending_review', 'review_only': True, 'publication_eligible': False,
            'text_sha256': hashlib.sha256(self.text.encode()).hexdigest(),
            'provenance': {'script_sha256': 'a' * 64, 'config_sha256': 'b' * 64,
                           'model_revision': 'unit-test-only', 'license_evidence_sha256': 'c' * 64},
            'audio': inspect_wav(self.wav), 'cues': [
                {'text': 'First part.', 'start_sample': 0, 'end_sample': 8000, 'start': 0, 'end': .5},
                {'text': 'Second part.', 'start_sample': 8000, 'end_sample': 32000, 'start': .5, 'end': 2}]}
        self.path = self.root / 'narration.json'
        self.write_receipt()
        self.spec = {'format': 'short', 'technical_test': True, 'review_purpose': 'owner_private_review',
                     'scenes': [{'title': 'Unit fixture', 'narration': self.text, 'caption': 'Unit fixture only'}]}

    def write_receipt(self):
        self.path.write_text(json.dumps(self.receipt), encoding='utf-8')

    def test_scene_text_hash_and_measured_cue_words_both_match(self):
        verified = read_voxcpm2_receipt(self.path, expected_text=self.text)
        self.assertEqual(verified[3]['frames'], 32000)
        self.assertEqual(verified[4], hashlib.sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'exact scene text'):
            read_voxcpm2_receipt(self.path, expected_text='A different scene.')
        self.receipt['cues'][0]['text'] = 'Invented words.'
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'cue text'):
            read_voxcpm2_receipt(self.path, expected_text=self.text)

    def test_renderer_default_keeps_4096_limit_but_companion_can_validate_12000(self):
        text = 'x' * 12000
        self.receipt['text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        self.receipt['cues'] = [{'text': text, 'start_sample': 0, 'end_sample': 32000, 'start': 0, 'end': 2}]
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'cue text'):
            read_voxcpm2_receipt(self.path, expected_text=text)
        self.assertEqual(read_voxcpm2_receipt(self.path, expected_text=text, max_text=12000)[3]['frames'], 32000)

    def test_pcm_changed_after_receipt_is_rejected(self):
        changed = bytearray(self.wav.read_bytes()); changed[-1] ^= 1
        self.wav.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            read_voxcpm2_receipt(self.path, expected_text=self.text)

    def test_noncontiguous_or_nonfinite_cue_times_are_rejected(self):
        self.receipt['cues'][1]['start_sample'] += 1
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            read_voxcpm2_receipt(self.path)
        self.receipt['cues'][1]['start_sample'] -= 1
        self.receipt['cues'][1]['start'] = float('nan')
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'actual PCM samples'):
            read_voxcpm2_receipt(self.path)

    def test_relative_or_linked_receipt_is_not_opened(self):
        with self.assertRaisesRegex(ValueError, 'Absolute local'):
            read_voxcpm2_receipt(Path('narration.json'))
        target = self.root / 'original.json'
        self.path.rename(target)
        try:
            os.symlink(target, self.path)
        except OSError:
            self.skipTest('OS did not permit creating a local test symlink')
        with self.assertRaisesRegex(ValueError, 'reparse'):
            read_voxcpm2_receipt(self.path)

    def test_missing_cues_blocks_renderer_before_output(self):
        self.receipt['cues'] = []
        self.write_receipt()
        output = self.root / 'not-created'
        with self.assertRaisesRegex(ValueError, 'caption alignment is blocked'):
            render(self.spec, output, narration_receipts=[self.path])
        self.assertFalse(output.exists())

    def test_retired_provider_blocks_renderer_before_output(self):
        self.receipt['provider'] = 'voicestudio_remote'
        self.write_receipt()
        output = self.root / 'not-created'
        with self.assertRaisesRegex(ValueError, 'Oxiegen-Narrator'):
            render(self.spec, output, narration_receipts=[self.path])
        self.assertFalse(output.exists())

    def test_pcm_changed_during_copy_stops_before_encoding(self):
        output = self.root / 'render'
        def changed_copy(source, destination):
            changed = bytearray(Path(source).read_bytes()); changed[-1] ^= 1
            Path(destination).write_bytes(changed)
        with patch.dict(sys.modules, {'PIL': SimpleNamespace(__version__='unit-test')}), \
                patch('youtube_ops.render.shutil.copyfile', side_effect=changed_copy), \
                patch('youtube_ops.render.run') as encode:
            with self.assertRaisesRegex(ValueError, 'WAV changed after receipt validation'):
                render(self.spec, output, narration_receipts=[self.path])
            encode.assert_not_called()

    def test_renderer_uses_verified_pcm_and_actual_cues_without_piper_import(self):
        # Mock encoding/graphics only; this is not a rendered-media acceptance test.
        output = self.root / 'render'
        font = self.root / 'unit-font.ttf'; font.write_bytes(b'unit font placeholder')
        real_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name.split('.')[0] in ('piper', 'onnxruntime'):
                raise AssertionError('New renders must not import local speech engines')
            return real_import(name, *args, **kwargs)
        def encode(args, **kwargs):
            if str(args[-1]).endswith('.mp4'):
                Path(args[-1]).write_bytes(b'mocked encoded media')
            return subprocess.CompletedProcess(args, 0, '', '')
        info = {'format': {'duration': '2'}, 'streams': [
            {'codec_type': 'video', 'codec_name': 'h264', 'pix_fmt': 'yuv420p',
             'width': 1080, 'height': 1920, 'avg_frame_rate': '30/1'},
            {'codec_type': 'audio', 'codec_name': 'aac'}]}
        with patch.dict(sys.modules, {'PIL': SimpleNamespace(__version__='unit-test')}), \
                patch('builtins.__import__', side_effect=guarded_import), \
                patch('youtube_ops.render.card'), patch('youtube_ops.render.write_captions') as captions, \
                patch('youtube_ops.render.run', side_effect=encode), patch('youtube_ops.render.probe', return_value=info), \
                patch('youtube_ops.render.assemble_segments', side_effect=lambda _, final, **kw: final.write_bytes(b'mock final')):
            result = render(self.spec, output, font_path=str(font), narration_receipts=[self.path])
        self.assertEqual((output / 'scene-00.wav').read_bytes(), self.wav.read_bytes())
        self.assertEqual(captions.call_args.args[1], self.receipt['cues'])
        self.assertEqual(result['voice']['narrator_id'], 'oxiegen-narrator')
        self.assertEqual(result['voice']['scenes'][0]['audio'], self.receipt['audio'])
        self.assertTrue(result['review_only'])
        self.assertFalse(result['publication_eligible'])


if __name__ == '__main__':
    unittest.main()
