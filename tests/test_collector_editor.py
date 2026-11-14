import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from youtube_ops.collector_editor import OpenShot, EditorError
from youtube_ops.collector_editor_fixture import build


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.exe = self.root / 'openshot-qt-cmd.exe'
        self.exe.write_bytes(b'test executable fixture, never executed')
        self.sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.client = OpenShot(self.exe, self.sha, self.vault, 'test-session')
        self.media = self.vault / 'owned.mp4'
        self.media.write_bytes(b'synthetic test')

    def test_wrong_executable_digest_is_rejected(self):
        with self.assertRaisesRegex(EditorError, 'executable_hash_mismatch'):
            OpenShot(self.exe, '0' * 64, self.vault)

    def test_paths_cannot_escape_vault_or_load_project_as_media(self):
        for path in [self.root / 'private.mp4', self.vault / '..' / 'private.mp4',
                     self.vault / 'project.osp', Path('relative.mp4')]:
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                self.client.validate_edits([{'method': 'file.import', 'params': {'path': str(path)}}])

    def test_structural_properties_and_shell_commands_are_denied(self):
        bad = [
            {'method': 'shell', 'params': {'command': 'whoami'}},
            {'method': 'clip.set', 'params': {'id': 'x', 'values': {'reader': {'path': 'https://evil'}}}},
            {'method': 'effects.add', 'params': {'clip_id': 'x', 'type': 'UnapprovedPlugin'}},
            {'method': 'clip.keyframe.set', 'params': {'id': 'x', 'property': 'reader.path'}},
            {'method': 'text.add', 'params': {'text': 'okay', 'script': 'bad'}},
        ]
        for command in bad:
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.client.validate_edits([command])

    def test_apply_sends_native_revision_batch_and_durable_receipt(self):
        commands = [{'method': 'file.import', 'as': 'source', 'params': {'path': str(self.media)}},
                    {'method': 'clip.add', 'params': {'file_id': {'$ref': 'source.id'}, 'layer': 1000000}},
                    {'method': 'clip.keyframe.set', 'params': {'id': 'c', 'property': 'volume',
                       'space': 'clip', 'unit': 'seconds', 'at': 0, 'value': 0.2}}]
        with patch.object(self.client, '_invoke', return_value={'revision': 8}) as invoke:
            self.assertEqual(self.client.apply(commands, 7), {'revision': 8})
        args = invoke.call_args.args[0]
        self.assertEqual(args[:3], ['edit', 'apply', '--json'])
        self.assertEqual(args[-2:], ['--expect-revision', '7'])
        self.assertFalse(self.client._pending().exists())
        receipts = [json.loads(p.read_text()) for p in self.client.receipts.glob('*.json')
                    if p.name != Path(args[3][1:]).name]
        self.assertEqual(len(receipts), 1)
        self.assertFalse(receipts[0]['publication_eligible'])

    def test_uncertain_edit_blocks_replay_even_after_client_restart(self):
        edits = [{'method': 'clip.split', 'params': {'id': 'c', 'at': 1}}]
        with patch.object(self.client, '_invoke', side_effect=EditorError('native_timeout_reconcile_required')):
            with self.assertRaises(EditorError):
                self.client.apply(edits, 1)
        restarted = OpenShot(self.exe, self.sha, self.vault, 'test-session')
        with patch.object(restarted, '_invoke') as invoke:
            with self.assertRaisesRegex(EditorError, 'unresolved_native_operation'):
                restarted.apply(edits, 1)
            invoke.assert_not_called()

    def test_bounded_edits_reject_nonfinite_numbers(self):
        with self.assertRaises(ValueError):
            self.client.validate_edits([{'method': 'clip.set', 'params': {'id': 'x', 'values': {'volume': float('nan')}}}])
        with self.assertRaises(ValueError):
            self.client.apply([{'method': 'clip.remove', 'params': {'id': 'x'}}], True)

    def test_saved_native_project_hash_required_for_reopen(self):
        project = self.vault / 'saved.osp'
        def native_save(args):
            project.write_text('{"native": "project"}')
            return {'revision': 4}
        with patch.object(self.client, '_invoke', side_effect=native_save):
            saved = self.client.save(project)
        with patch.object(self.client, '_invoke', return_value={'revision': 4}) as invoke:
            self.client.reopen(project, saved['sha256'])
            self.assertEqual(invoke.call_args.args[0], ['project', 'open', str(project)])
        project.write_text('{"native": "externally changed"}')
        with self.assertRaisesRegex(EditorError, 'untrusted_or_changed_project'):
            self.client.reopen(project, saved['sha256'])

    def test_export_does_not_wait_or_repeat_and_binds_snapshot_context(self):
        with patch.object(self.client, '_invoke', side_effect=[{'revision': 9}, {'job_id': 'export1'}]) as invoke:
            self.client.export(self.vault / 'review.mp4', 1500)
        self.assertEqual(invoke.call_count, 2)
        args = invoke.call_args.args[0]
        self.assertNotIn('--wait', args)
        self.assertEqual(args[-4:], ['--start-frame', '1', '--end-frame', '1500'])
        receipts = [json.loads(p.read_text()) for p in self.client.receipts.glob('*.json')]
        self.assertEqual(receipts[0]['details']['snapshot_context'], {'revision': 9})

    def test_owned_fixture_preserves_native_layers_and_labels_missing_acceptance(self):
        batches = []
        def apply(commands, revision):
            self.client.validate_edits(commands)
            batches.append(commands)
            return {'revision': revision + 1, 'refs': {'title2': {'id': 'native-title'}}}
        def save(path):
            return {'path': str(path), 'sha256': '0' * 64}
        with patch.object(self.client, 'start', return_value={'session_id': 'fixture'}), \
                patch.object(self.client, 'inspect', return_value={'revision': 1, 'data': {
                    'layers': [{'number': i * 1000000} for i in range(1, 6)]}}), \
                patch.object(self.client, 'apply', side_effect=apply), \
                patch.object(self.client, 'save', side_effect=save), \
                patch.object(self.client, 'reopen', return_value={'revision': 3}):
            result = build(self.client, self.vault / 'fixture')
        with wave.open(str(self.vault / 'fixture' / 'original-ambient.wav')) as audio:
            self.assertEqual(audio.getnframes() / audio.getframerate(), 50)
        self.assertEqual((self.vault / 'fixture' / 'scene-0.png').read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        layers = {item['params']['layer'] for item in batches[0] if item['method'] == 'clip.add'}
        self.assertEqual(len(layers), 4)
        self.assertTrue(any(item['method'] == 'effects.add' for item in batches[0]))
        self.assertIn('NOT TESTED', result['manual_edit'])
        self.assertIn('BLOCKED', result['voice'])
        self.assertFalse(result['publication_eligible'])


if __name__ == '__main__':
    unittest.main()
