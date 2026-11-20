"""Acceptance orchestration contracts; retained fixtures, no renderer or inference."""
from tests.fixture_retention import FixtureDirectory
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import wave

from youtube_ops import collector_final_short as short
from youtube_ops import collector_editor as editor


class FinalShortTests(unittest.TestCase):
    def test_measured_samples_are_quantized_once_then_intro_offset_added(self):
        cues = [{'text': 'Measured speech.', 'start_sample': 0, 'end_sample': 145920}]
        result = short.caption_frames(cues, 48000)
        self.assertEqual(result[0]['first_frame'], 48)
        self.assertEqual(result[0]['end_frame'], round(Fraction(145920*30, 48000)) + 48)
        self.assertEqual(short.INTRO_FRAMES + short.BODY_FRAMES + short.OUTRO_FRAMES, 1500)
        for end in (0, 48000*41):
            with self.assertRaises(ValueError):
                short.caption_frames([{**cues[0], 'end_sample': end}], 48000)

    def test_original_script_has_bounded_natural_captions(self):
        self.assertEqual(len(short.SEGMENTS), 8)
        self.assertTrue(all(0 < len(text) <= 96 for text in short.SEGMENTS))
        self.assertGreater(len(' '.join(short.SEGMENTS).split()), 75)
        self.assertLess(len(' '.join(short.SEGMENTS).split()), 110)

    def test_music_headroom_does_not_extend_the_body_timeline(self):
        with FixtureDirectory(prefix='kn-music-headroom-') as folder:
            path = Path(folder)/'original.wav'
            short._music(path)
            with wave.open(str(path)) as source:
                body_samples = short.BODY_FRAMES * source.getframerate() // short.FPS
                self.assertEqual(source.getnframes(), body_samples + source.getframerate())
                source.setpos(body_samples)
                self.assertEqual(source.readframes(source.getframerate()), bytes(source.getframerate()*2))
            self.assertEqual(short.BODY_FRAMES, 1218)

    def test_finalization_does_not_replay_an_existing_intent(self):
        with FixtureDirectory(prefix='kn-final-short-') as folder:
            directory = Path(folder)
            (directory/'finalization-intent.json').write_text('{}')
            client = Mock(session='owned')
            client.inspect.return_value = {'revision': 7}
            with self.assertRaisesRegex(ValueError, 'already attempted'):
                short.finish(client, {'status': 'INCOMPLETE_BODY_ONLY', 'session_id': 'owned',
                    'revision': 7, 'directory': str(directory)}, 'unused', 'unused', 'unused', 'unused')
            client.apply.assert_not_called()

    def test_native_invocation_retains_exact_private_output_after_close(self):
        with FixtureDirectory(prefix='kn-native-output-') as folder:
            root = Path(folder).resolve()
            exe = root/'openshot-qt-cmd.exe'; exe.write_bytes(b'not executed')
            vault = root/'vault'; vault.mkdir()
            client = editor.OpenShot(exe, editor.digest(exe), vault)
            def launch(args, **kwargs):
                self.assertEqual(kwargs['env']['KN_COLLECTOR_RETAIN_ARTIFACTS'], '1')
                kwargs['stdout'].write(b'{"ok":true,"result":{"session_id":"owned"}}')
                kwargs['stderr'].write(b'private diagnostic preserved')
                process = Mock(returncode=0)
                process.poll.return_value = 0
                return process
            with patch.object(editor.subprocess, 'Popen', side_effect=launch):
                result = client._invoke(['session', 'start'], session=False)
            self.assertEqual(result['session_id'], 'owned')
            invocation = list(client.receipts.glob('invoke-*'))
            self.assertEqual(len(invocation), 1)
            self.assertEqual((invocation[0]/'stderr.private.log').read_bytes(), b'private diagnostic preserved')
            self.assertTrue((invocation[0]/'stdout.private.log').is_file())

    def test_native_gui_selection_is_explicit_and_forwarded_once(self):
        with FixtureDirectory(prefix='kn-native-show-') as folder:
            root = Path(folder).resolve()
            exe = root/'openshot-qt-cmd.exe'; exe.write_bytes(b'not executed')
            vault = root/'vault'; vault.mkdir()
            client = editor.OpenShot(exe, editor.digest(exe), vault)
            with patch.object(client, '_invoke', return_value={'session_id': 'owned'}) as invoke:
                client.start(show=True)
            invoke.assert_called_once_with(['session', 'start', '--show'], session=False)
            with self.assertRaises(ValueError):
                client.start(show='yes')

    def test_thumbnail_post_audit_accepts_only_its_exact_existing_pending(self):
        with FixtureDirectory(prefix='kn-thumbnail-pending-') as folder:
            root = Path(folder).resolve()
            exe = root/'openshot-qt-cmd.exe'; exe.write_bytes(b'not executed')
            vault = root/'vault'; vault.mkdir()
            client = editor.OpenShot(exe, editor.digest(exe), vault)
            client._enroll('owned')
            intent = client._intent('timeline.thumbnail', {'frame': 1})
            with patch.object(client, '_invoke', return_value={'data': []}):
                with self.assertRaisesRegex(editor.EditorError, 'unresolved_native_operation'):
                    client.audit_sources()
                self.assertEqual(client.audit_sources(pending_intent=intent), {})
                with self.assertRaisesRegex(editor.EditorError, 'unresolved_native_operation'):
                    client.audit_sources(pending_intent={**intent, 'kind': 'edit.apply'})

    def test_pending_hardlink_is_rejected_before_decoding_its_contents(self):
        with FixtureDirectory(prefix='kn-thumbnail-hardlink-') as folder:
            root = Path(folder).resolve()
            exe = root/'openshot-qt-cmd.exe'; exe.write_bytes(b'not executed')
            vault = root/'vault'; vault.mkdir()
            client = editor.OpenShot(exe, editor.digest(exe), vault)
            client._enroll('owned')
            intent = client._intent('timeline.thumbnail', {'frame': 1})
            pending = client._pending()
            (root/'retained-hardlink').hardlink_to(pending)
            pending.write_bytes(b'\xff not JSON; metadata must reject before decode')
            with self.assertRaisesRegex(editor.EditorError, 'pending_retention_source_unverified'):
                client.audit_sources(pending_intent=intent)


if __name__ == '__main__':
    unittest.main()
