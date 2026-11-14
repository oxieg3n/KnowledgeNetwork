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
        (self.client.receipts / 'session-test-session.json').write_text(json.dumps({
            'session_id': 'test-session', 'executable_sha256': self.sha,
            'font_directory': str(self.client.font_directory)}))
        self.media = self.vault / 'owned.mp4'
        self.media.write_bytes(b'synthetic test')

    def test_wrong_executable_digest_is_rejected(self):
        with self.assertRaisesRegex(EditorError, 'executable_hash_mismatch'):
            OpenShot(self.exe, '0' * 64, self.vault)

    def test_cold_start_timeout_owns_session_and_prevents_duplicate_start(self):
        session_id = 'c' * 32
        with patch.object(self.client, '_invoke', side_effect=EditorError('startup_timeout', session_id)):
            with self.assertRaisesRegex(EditorError, 'startup_timeout'):
                self.client.start()
        restarted = OpenShot(self.exe, self.sha, self.vault)
        with patch.object(restarted, '_invoke') as invoke:
            with self.assertRaisesRegex(EditorError, 'startup_reconciliation_required'):
                restarted.start()
            invoke.assert_not_called()
        with patch.object(restarted, '_invoke', return_value={'data': {'session_id': session_id}}) as invoke:
            recovered = restarted.recover_start()
            self.assertEqual(recovered['session_id'], session_id)
            self.assertEqual(invoke.call_args.args[0], ['session', 'status'])
        self.assertFalse((restarted.receipts / 'start-pending.json').exists())

    def test_native_invocation_uses_fixed_executable_and_no_shell(self):
        def launch(args, **kwargs):
            self.assertEqual(args[:2], [str(self.exe.resolve()), '--cli'])
            self.assertIn('--session', args)
            self.assertFalse(kwargs['shell'])
            if self.client.font_directory is not None:
                self.assertEqual(kwargs['env']['QT_QPA_FONTDIR'], str(self.client.font_directory))
            kwargs['stdout'].write(b'{"ok":true,"result":{"revision":3}}')
            process = unittest.mock.Mock()
            process.poll.return_value = 0
            process.returncode = 0
            return process
        with patch('youtube_ops.collector_editor.subprocess.Popen', side_effect=launch):
            self.assertEqual(self.client.inspect(), {'revision': 3})

    def test_unmanaged_native_session_and_replaced_executable_are_denied(self):
        unmanaged = OpenShot(self.exe, self.sha, self.vault, 'another-users-session')
        with patch('youtube_ops.collector_editor.subprocess.Popen') as launch:
            with self.assertRaisesRegex(EditorError, 'unmanaged_native_session'):
                unmanaged.inspect()
            self.exe.write_bytes(b'replaced executable')
            with self.assertRaisesRegex(EditorError, 'executable_hash_mismatch'):
                self.client.inspect()
            launch.assert_not_called()

    def test_native_errors_do_not_return_private_error_messages(self):
        def launch(args, **kwargs):
            kwargs['stderr'].write(b'{"ok":false,"error":{"code":"validation_error","message":"private registry token"}}')
            process = unittest.mock.Mock()
            process.poll.return_value = 1
            process.returncode = 1
            return process
        with patch('youtube_ops.collector_editor.subprocess.Popen', side_effect=launch):
            with self.assertRaisesRegex(EditorError, '^validation_error$'):
                self.client.inspect()

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
            {'method': 'effects.set', 'params': {'id': 'x', 'values': {'saturation': {'path': 'evil'}}}},
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
                    if p.name not in {Path(args[3][1:]).name, 'session-test-session.json'}]
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
            if args == ['project', 'get']:
                return {'revision': 4}
            if args[:2] == ['operation', 'get']:
                return {'data': {'method': 'project.save', 'state': 'completed',
                                 'revision_before': 4, 'revision_after': 5}}
            project.write_text('{"native": "project"}')
            return {'revision': 5, 'operation_id': 'save-operation'}
        with patch.object(self.client, '_invoke', side_effect=native_save), \
                patch.object(self.client, 'audit_sources', return_value={}):
            saved = self.client.save(project)
        with patch.object(self.client, '_invoke', return_value={'revision': 4}) as invoke:
            self.client.reopen(project, saved['sha256'])
            self.assertEqual(invoke.call_args.args[0], ['project', 'open', str(project)])
        project.write_text('{"native": "externally changed"}')
        with self.assertRaisesRegex(EditorError, 'untrusted_or_changed_project'):
            self.client.reopen(project, saved['sha256'])

    def test_save_rejects_edit_between_audit_and_native_save(self):
        with patch.object(self.client, 'audit_sources', return_value={}), \
                patch.object(self.client, '_invoke', side_effect=[{'revision': 4}, {
                    'revision': 6, 'operation_id': 'save-operation'}, {'data': {
                    'method': 'project.save', 'state': 'completed', 'revision_before': 5}}]):
            with self.assertRaisesRegex(EditorError, 'revision_changed_during_save'):
                self.client.save(self.vault / 'conflict.osp')
        self.assertTrue(self.client._pending().exists())

    def test_export_does_not_wait_or_repeat_and_binds_snapshot_context(self):
        with patch.object(self.client, '_invoke', side_effect=[{'revision': 9}, {
                'revision': 9, 'data': {'job_id': 'export1', 'revision': 9}}]) as invoke, \
                patch.object(self.client, 'audit_sources', return_value={}):
            self.client.export(self.vault / 'review.mp4', 1500)
        self.assertEqual(invoke.call_count, 2)
        args = invoke.call_args.args[0]
        self.assertNotIn('--wait', args)
        self.assertEqual(args[-4:], ['--start-frame', '1', '--end-frame', '1500'])
        receipts = [json.loads(p.read_text()) for p in self.client.receipts.glob('*.json')
                    if p.name != 'session-test-session.json']
        self.assertEqual(receipts[0]['details']['snapshot_context'], {'revision': 9})

    def test_old_windows_session_cannot_claim_new_offscreen_font_configuration(self):
        if self.client.font_directory is None:
            self.skipTest('Windows offscreen font configuration only')
        (self.client.receipts / 'session-test-session.json').write_text(json.dumps({
            'session_id': 'test-session', 'executable_sha256': self.sha}))
        with patch.object(self.client, '_invoke') as invoke:
            with self.assertRaisesRegex(EditorError, 'new_font_configured_session_required'):
                self.client.export(self.vault / 'old-session.mp4', 1500)
            invoke.assert_not_called()

    def test_concurrent_gui_edit_cancels_different_export_snapshot(self):
        with patch.object(self.client, '_invoke', side_effect=[{'revision': 9}, {
                'revision': 10, 'data': {'job_id': 'export1', 'revision': 10}}, {'data': {'state': 'cancelled'}}]) as invoke, \
                patch.object(self.client, 'audit_sources', return_value={}):
            with self.assertRaisesRegex(EditorError, 'revision_changed_during_export'):
                self.client.export(self.vault / 'review.mp4', 1500)
        self.assertEqual(invoke.call_args.args[0], ['export', 'cancel', 'export1'])
        self.assertTrue(self.client._pending().exists())

    def test_gui_added_external_or_changed_reader_paths_block_export(self):
        outside = self.root / 'outside.mp4'
        outside.write_bytes(b'existing private file outside vault')
        asset_receipt = self.client.receipts / ('a' * 32 + '.json')
        asset_receipt.write_text(json.dumps({'details': {'imported_assets': [{
            'path': str(self.media), 'sha256': hashlib.sha256(self.media.read_bytes()).hexdigest()}]}}))
        def reply(args):
            if args == ['file', 'list']:
                return {'data': [{'id': 'file1'}]}
            if args == ['file', 'get', 'file1']:
                return {'data': {'reader': {'type': 'FFmpegReader', 'path': str(self.media)}}}
            return {'data': []}
        with patch.object(self.client, '_invoke', side_effect=reply):
            self.assertIn(str(self.media), self.client.audit_sources())
            self.media.write_bytes(b'externally modified media')
            with self.assertRaisesRegex(EditorError, 'unregistered_or_changed_native_asset'):
                self.client.audit_sources()
        with patch.object(self.client, '_invoke', side_effect=[{'data': [{'id': 'f'}]}, {
                'data': {'reader': {'type': 'FFmpegReader', 'path': str(outside)}}}]):
            with self.assertRaises(ValueError):
                self.client.audit_sources()

    def test_native_text_readers_need_no_external_resource_registration(self):
        # v4.1.1 direct_text.reader_json deliberately emits a pathless reader.
        native_text = {'type': 'QtTextReader', 'path': '', 'media_type': 'image',
                       'direct_text': {'text': 'Plain lower third', 'font_family': 'Segoe UI'},
                       'font': 'Segoe UI,36,-1,5,50,0,0,0,0,0'}
        def reply(args):
            if args[1] == 'list':
                return {'data': [{'id': args[0] + '1'}]}
            if args[0] == 'file':
                return {'data': native_text}
            return {'data': {'reader': native_text, 'thumbnail': 'outside-cache-thumbnail.png'}}
        with patch.object(self.client, '_invoke', side_effect=reply):
            self.assertEqual(self.client.audit_sources(), {})
            native_text['path'] = str(self.vault / 'untrusted.svg')
            with self.assertRaises((ValueError, OSError)):
                self.client.audit_sources()

    def test_owned_fixture_preserves_native_layers_and_labels_missing_acceptance(self):
        batches = []
        def apply(commands, revision):
            self.client.validate_edits(commands)
            batches.append(commands)
            return {'revision': revision + 1, 'refs': {'title2': {'clip': {'id': 'native-title'}}}}
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
