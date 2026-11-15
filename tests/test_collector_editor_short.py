"""Retained native-editor protocol fixtures; no editor process or media render."""
from fractions import Fraction
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import wave

from PIL import Image
from tests.fixture_retention import FixtureDirectory
from youtube_ops import collector_editor as editor
from youtube_ops import collector_editor_fixture as fixture


class ShortTimingTests(unittest.TestCase):
    def test_body_budget_preserves_legacy_and_reserves_both_bookends(self):
        self.assertEqual(fixture.body_timing(), ([0, 480, 990, 1500], Fraction(50)))
        edges, duration = fixture.body_timing(1218)
        self.assertEqual(edges, [0, 406, 812, 1218])
        self.assertEqual(duration, Fraction(203, 5))
        self.assertEqual(48 + edges[-1] + 234, 1500)
        for invalid in (True, 0, 1501, 1400, 1067, 1369, 1218.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                fixture.body_timing(invalid)

    def test_overlong_measured_speech_is_refused_before_any_native_action(self):
        client = Mock()
        evidence = (None, None, {}, {'frames': 649601, 'sample_rate': 16000}, None)
        with patch.object(fixture, 'narration_receipt', return_value=evidence):
            with self.assertRaisesRegex(ValueError, 'Measured narration exceeds'):
                fixture.attach_narration_to_fixture(client, Path('unused'), 7, body_frames=1218)
        client.inspect.assert_not_called()
        client.apply.assert_not_called()


class EditorArtifactTests(unittest.TestCase):
    def setUp(self):
        self.folder = FixtureDirectory(prefix='kn-editor-short-')
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.exe = self.root / 'openshot-qt-cmd.exe'
        self.exe.write_bytes(b'synthetic executable identity; never executed')
        self.vault = self.root / 'vault'; self.vault.mkdir()
        self.client = editor.OpenShot(self.exe, editor.digest(self.exe), self.vault, 'retained-session')
        editor.write_json(self.client.receipts / 'session-retained-session.json', {
            'session_id': self.client.session, 'executable_sha256': editor.digest(self.exe),
            'font_directory': str(self.client.font_directory) if self.client.font_directory else None})
        self.profile = {'revision': 7, 'data': {'width': 12, 'height': 20, 'fps': {'num': 30, 'den': 1}}}

    def thumbnail_result(self, arguments, revision=7):
        self.assertEqual(arguments[:2], ['timeline', 'thumbnail'])
        path = Path(arguments[arguments.index('--output') + 1])
        frame = int(arguments[arguments.index('--frame') + 1])
        width, height = (int(arguments[arguments.index('--' + key) + 1]) for key in ('width', 'height'))
        Image.new('RGB', (width, height), '#203343').save(path)
        return {'revision': revision, 'data': {'path': str(path), 'image_bytes': path.stat().st_size,
            'width': width, 'height': height, 'fps': 30.0, 'timebase': 'timeline',
            'tiles': [{'frame': frame, 'seconds': (frame - 1) / 30}]}}

    def test_thumbnail_records_composed_frame_context_and_preserves_terminal_intent(self):
        path = self.vault / 'body-first.png'
        with patch.object(self.client, 'inspect', return_value=self.profile), \
                patch.object(self.client, 'audit_sources', return_value=[]), \
                patch.object(self.client, '_invoke', side_effect=self.thumbnail_result) as invoke:
            result = self.client.thumbnail(path)
        self.assertEqual(result['artifact']['sha256'], editor.digest(path))
        self.assertEqual(result['artifact']['revision'], 7)
        self.assertEqual(result['artifact']['frame'], 1)
        self.assertEqual(invoke.call_count, 1)
        self.assertFalse(self.client._pending().exists())
        terminal = list(self.client.receipts.glob('terminal-*.json'))
        self.assertEqual(len(terminal), 2)
        evidence = json.loads(next(self.client.receipts.glob('terminal-*.retained.json')).read_text())
        self.assertEqual(evidence['status'], 'retained_terminal_evidence')
        self.assertEqual(evidence['sha256'], editor.digest(self.client.receipts / evidence['retained']))
        self.assertEqual(json.loads((self.client.receipts / 'pending-retention.json').read_text())['status'], 'completed')

    def test_changed_native_revision_retains_png_and_original_pending(self):
        path = self.vault / 'changed-frame.png'
        with patch.object(self.client, 'inspect', return_value=self.profile), \
                patch.object(self.client, 'audit_sources', return_value=[]), \
                patch.object(self.client, '_invoke', side_effect=lambda args: self.thumbnail_result(args, 8)):
            with self.assertRaisesRegex(editor.EditorError, 'thumbnail_context_unverified'):
                self.client.thumbnail(path)
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(self.client._pending().read_text())['kind'], 'timeline.thumbnail')
        self.assertFalse(list(self.client.receipts.glob('terminal-*.json')))

    def test_nonfinite_native_timing_is_not_accepted_as_a_verified_frame(self):
        path = self.vault / 'invalid-time.png'
        def invalid(arguments):
            result = self.thumbnail_result(arguments)
            result['data']['fps'] = float('nan')
            return result
        with patch.object(self.client, 'inspect', return_value=self.profile), \
                patch.object(self.client, 'audit_sources', return_value=[]), \
                patch.object(self.client, '_invoke', side_effect=invalid):
            with self.assertRaisesRegex(editor.EditorError, 'thumbnail_context_unverified'):
                self.client.thumbnail(path)
        self.assertTrue(path.exists())
        self.assertTrue(self.client._pending().exists())

    def test_start_and_recovered_start_retain_both_definite_terminal_intents(self):
        with patch.object(self.client, '_invoke', return_value={'session_id': 'started-session'}):
            self.client.start()
        self.assertFalse((self.client.receipts / 'start-pending.json').exists())
        first = next(path for path in self.client.receipts.glob('terminal-*.json')
                     if not path.name.endswith('.retained.json'))
        original = first.read_bytes()
        self.client._enroll('recovered-session')
        intent = {'id': 'e' * 32, 'kind': 'session.start', 'session_id': 'recovered-session'}
        editor.write_json(self.client.receipts / 'start-pending.json', intent)
        with patch.object(self.client, '_invoke', return_value={'data': {'session_id': 'recovered-session'}}):
            self.client.recover_start()
        self.assertFalse((self.client.receipts / 'start-pending.json').exists())
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(json.loads((self.client.receipts / ('terminal-' + 'e' * 32 + '.json')).read_text()), intent)

    def test_existing_output_and_invalid_ranges_never_invoke_native(self):
        with patch.object(self.client, 'inspect', return_value=self.profile), \
                patch.object(self.client, '_invoke') as invoke:
            for values in ({'frame': True}, {'frame': 0}, {'width': 4097}, {'width': 4096, 'height': 4096}):
                with self.subTest(values=values), self.assertRaises(ValueError):
                    self.client.thumbnail(self.vault / 'unused.png', **values)
            existing = self.vault / 'existing.png'; existing.write_bytes(b'preserve original')
            with self.assertRaises(ValueError):
                self.client.thumbnail(existing)
        invoke.assert_not_called()
        self.assertEqual(existing.read_bytes(), b'preserve original')

    def test_retirement_collision_preserves_original_pending_and_existing_terminal(self):
        intent = self.client._intent('edit.apply', {'fixture': True})
        pending = self.client._pending(); original = pending.read_bytes()
        terminal = self.client.receipts / ('terminal-' + intent['id'] + '.json')
        terminal.write_bytes(b'prior terminal; do not overwrite')
        with self.assertRaisesRegex(editor.EditorError, 'pending_retention_collision'):
            self.client._complete(intent, {'revision': 8})
        self.assertEqual(pending.read_bytes(), original)
        self.assertEqual(terminal.read_bytes(), b'prior terminal; do not overwrite')

    def test_post_move_verification_failure_durably_blocks_new_mutations(self):
        intent = self.client._intent('edit.apply', {'fixture': True})
        pending = self.client._pending()
        original = editor._receipt_metadata(pending)
        with patch.object(editor, '_receipt_metadata', side_effect=[original, {**original, 'bytes': original['bytes'] + 1}]):
            with self.assertRaisesRegex(editor.EditorError, 'pending_retention_requires_reconciliation'):
                self.client._complete(intent, {'revision': 8})
        self.assertFalse(pending.exists())
        self.assertTrue((self.client.receipts / ('terminal-' + intent['id'] + '.json')).exists())
        with self.assertRaisesRegex(editor.EditorError, 'pending_retention_requires_reconciliation'):
            self.client._intent('edit.apply', {'next': True})
        with patch.object(self.client, '_invoke') as invoke:
            with self.assertRaisesRegex(editor.EditorError, 'pending_retention_requires_reconciliation'):
                self.client.start()
            invoke.assert_not_called()
        with patch.object(self.client, 'inspect', return_value=self.profile), \
                patch.object(self.client, '_invoke', return_value={'data': []}):
            self.assertEqual(self.client.reconcile()['pending_retention']['status'], 'pending')

    def test_second_client_cannot_replace_another_clients_unverified_retirement_hold(self):
        other = editor.OpenShot(self.exe, editor.digest(self.exe), self.vault, 'other-session')
        editor.write_json(other.receipts / 'session-other-session.json', {
            'session_id': other.session, 'executable_sha256': editor.digest(self.exe),
            'font_directory': str(other.font_directory) if other.font_directory else None})
        first = self.client._intent('edit.apply', {'client': 'first'})
        second = other._intent('edit.apply', {'client': 'second'})
        metadata = editor._receipt_metadata
        interleaved = False
        def fault_after_move(path):
            nonlocal interleaved
            value = metadata(path)
            if path.name == 'terminal-' + first['id'] + '.json':
                with self.assertRaisesRegex(editor.EditorError, '^pending_retention_busy$'):
                    other._complete(second, {'revision': 9})
                interleaved = True
                return {**value, 'bytes': value['bytes'] + 1}
            return value
        with patch.object(editor, '_receipt_metadata', side_effect=fault_after_move):
            with self.assertRaisesRegex(editor.EditorError, '^pending_retention_requires_reconciliation$'):
                self.client._complete(first, {'revision': 8})
        self.assertTrue(interleaved)
        self.assertFalse(self.client._pending().exists())
        self.assertTrue(other._pending().exists())
        with self.assertRaisesRegex(editor.EditorError, '^pending_retention_requires_reconciliation$'):
            other._complete(second, {'revision': 9})
        state = self.client._retention_state()
        self.assertEqual((state['status'], state['intent_id']), ('pending', first['id']))
        self.assertFalse((other.receipts / ('terminal-' + second['id'] + '.json')).exists())
        for client in (self.client, other):
            with self.assertRaisesRegex(editor.EditorError, '^pending_retention_requires_reconciliation$'):
                client._intent('edit.apply', {'next': True})

    def test_fractional_duration_tone_has_exact_body_sample_count(self):
        path = self.vault / 'body-bed.wav'
        fixture.tone(path, 165, 1218 / 30)
        with wave.open(str(path), 'rb') as stream:
            self.assertEqual((stream.getframerate(), stream.getnchannels(), stream.getsampwidth(), stream.getnframes()),
                             (16000, 1, 2, 649600))

    def test_short_body_builder_retimes_all_owned_visual_audio_and_effect_ranges(self):
        client = Mock(vault=self.vault, session='fixture-session')
        client.start.return_value = {'session_id': 'fixture-session'}
        client.inspect.return_value = {'revision': 1, 'data': {'layers': [{'number': i} for i in range(5)]}}
        commands = []
        def apply(values, revision):
            commands.extend(values)
            return {'revision': 2, 'refs': {'bedclip': {'id': 'bed'}, 'accentclip': {'id': 'accent'},
                                           'title2': {'clip': {'id': 'title2'}}}}
        client.apply.side_effect = apply
        client.save.side_effect = lambda path: {'path': str(path), 'sha256': 'a' * 64}
        client.reopen.return_value = {'revision': 2}
        with patch.object(fixture, 'capture_music_baseline'), \
                patch.object(fixture, 'tone', side_effect=lambda path, frequency, seconds: path.write_bytes(b'synthetic music fixture')):
            result = fixture.build(client, self.vault / 'short-body', width=12, height=20, body_frames=1218)
        scenes = [command['params'] for command in commands if command.get('as', '').startswith('background')]
        self.assertEqual([round(scene['position'] * 30) for scene in scenes], [0, 406, 812])
        self.assertEqual([round(scene['end'] * 30) for scene in scenes], [406, 406, 406])
        for name in ('overlay', 'bedclip', 'accentclip'):
            clip = next(command['params'] for command in commands if command.get('as') == name)
            self.assertEqual(clip['end'], 40.6)
        self.assertTrue(any(command['method'] == 'clip.keyframe.set' and command['params']['at'] == 39.6
                            for command in commands))
        self.assertEqual(result['end_frame'], 1218)
        self.assertEqual(result['bookend_budget']['assembled_frames'], 1500)
        self.assertFalse(result['bookend_budget']['assembled'])
        self.assertFalse(result['publication_eligible'])
        self.assertIn('unbranded technical', result['branding'])


if __name__ == '__main__':
    unittest.main()
