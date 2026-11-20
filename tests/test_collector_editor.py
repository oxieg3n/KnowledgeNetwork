from tests.fixture_retention import retain_fixture_entry
from tests.fixture_retention import FixtureDirectory
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

from youtube_ops.collector_editor import OpenShot, EditorError
from youtube_ops.collector_editor_fixture import (build, narration_receipt, attach_narration_to_fixture,
                                                 music_fingerprint, capture_music_baseline)
from youtube_ops.collector_narration_common import inspect_wav


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = FixtureDirectory()
        self.addCleanup(self.temporary.cleanup)
        # Match the canonical paths recorded by the native adapter, including Windows 8.3 TEMP aliases.
        self.root = Path(self.temporary.name).resolve()
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
        operations = [item for item in receipts if item.get('kind') == 'edit.apply' and 'result' in item]
        self.assertEqual(len(operations), 1)
        self.assertFalse(operations[0]['publication_eligible'])
        terminal = self.client.receipts / ('terminal-' + operations[0]['id'] + '.json')
        self.assertEqual(json.loads(terminal.read_text())['id'], operations[0]['id'])
        self.assertEqual(json.loads((self.client.receipts / 'pending-retention.json').read_text())['status'], 'completed')

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
            return {'revision': revision + 1, 'refs': {'title2': {'clip': {'id': 'native-title'}},
                                                     'bedclip': {'id': 'native-music'}}}
        def save(path):
            return {'path': str(path), 'sha256': '0' * 64}
        with patch.object(self.client, 'start', return_value={'session_id': 'fixture'}), \
                patch.object(self.client, 'inspect', return_value={'revision': 1, 'data': {
                    'layers': [{'number': i * 1000000} for i in range(1, 6)]}}), \
                patch.object(self.client, 'apply', side_effect=apply), \
                patch.object(self.client, 'save', side_effect=save), \
                patch('youtube_ops.collector_editor_fixture.capture_music_baseline'), \
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

    def remote_narration_fixture(self, cues=True):
        # Synthetic PCM/receipt is unit-test data, never evidence of host synthesis.
        spool = self.vault / 'voice-job'
        spool.mkdir()
        audio_path = spool / 'narration.wav'
        with wave.open(str(audio_path), 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 32000)
        receipt = {'provider': 'voxcpm2_remote', 'narrator_id': 'oxiegen-narrator', 'status': 'generated_pending_review',
            'review_only': True, 'publication_eligible': False, 'text_sha256': 'c' * 64,
            'provenance': {'script_sha256': 'a' * 64, 'config_sha256': 'b' * 64,
                           'model_revision': 'test-only', 'license_evidence_sha256': 'd' * 64},
            'audio': inspect_wav(audio_path.read_bytes())}
        if cues:
            receipt['cues'] = [
                {'text': 'Measured first segment.', 'start_sample': 0, 'end_sample': 8000, 'start': 0, 'end': .5},
                {'text': 'Measured second segment.', 'start_sample': 8000, 'end_sample': 32000, 'start': .5, 'end': 2}]
        path = spool / 'narration.json'
        path.write_text(json.dumps(receipt))
        return path, receipt

    def fixture_narration_inspection(self):
        return {'revision': 7, 'data': {'width': 1080, 'height': 1920, 'fps': {'num': 30, 'den': 1},
                'layers': [{'number': i * 1000000} for i in range(1, 6)]}}

    def fake_fixture_editor(self):
        state = {'revision': 7, 'next_id': 0, 'commands': [], 'clips': {
            'accent': {'id': 'accent', 'layer': 3000000},
            'music': {'id': 'music', 'layer': 2000000, 'position': 0, 'start': 0, 'end': 50,
                      'volume': {'Points': [{'co': {'X': x, 'Y': y}}
                                           for x, y in [(1, 0), (31, .25), (1440, .25), (1500, 0)]]}},
            'manual': {'id': 'manual', 'layer': 5000000, 'style': {'text': 'Owner title'}}}}
        (self.client.receipts / ('d' * 32 + '.json')).write_text(json.dumps({'kind': 'fixture.music',
            'result': {'ownership': 'managed', 'managed_music': [{'clip_id': 'music',
                         'sha256': music_fingerprint(state['clips']['music'])}]}}))
        def inspect():
            result = self.fixture_narration_inspection()
            result['revision'] = state['revision']
            return result
        def invoke(args):
            if args == ['clip', 'list']:
                return {'data': list(state['clips'].values())}
            clip = state['clips'][args[2]]
            return {'data': clip if args[0] == 'clip' else {'style': clip['style']}}
        def apply(commands, revision):
            self.assertEqual(revision, state['revision'])
            self.client.validate_edits(commands)
            state['commands'].append(commands)
            refs = {}
            for command in commands:
                method, params = command['method'], command['params']
                if method == 'clip.remove':
                    del state['clips'][params['id']]
                elif method in ('clip.add', 'text.add'):
                    state['next_id'] += 1
                    clip_id = 'generated-' + str(state['next_id'])
                    clip = {'id': clip_id, 'layer': params['layer'], 'position': params['position'],
                            'end': params.get('end', params.get('duration'))}
                    if method == 'text.add':
                        clip['style'] = {'text': params['text'], 'font_size': params['font_size']}
                    state['clips'][clip_id] = clip
                    refs[command['as']] = {'clip': {'id': clip_id}} if method == 'text.add' else {'id': clip_id}
                elif method == 'clip.set':
                    clip_id = params['id']
                    if isinstance(clip_id, dict):
                        clip_id = refs[clip_id['$ref'].split('.')[0]]['clip']['id']
                    values = dict(params['values'])
                    if 'volume' in values:
                        values['volume'] = {'Points': [{'co': {'X': 1, 'Y': values['volume']}}]}
                    state['clips'][clip_id].update(values)
                elif method == 'clip.keyframe.set' and params['property'] == 'volume':
                    curve = state['clips'][params['id']]['volume']['Points']
                    frame = round(params['at'] * 30) + 1
                    curve[:] = [point for point in curve if point['co']['X'] != frame]
                    curve.append({'co': {'X': frame, 'Y': params['value']}})
                    curve.sort(key=lambda point: point['co']['X'])
            state['revision'] += 1
            return {'revision': state['revision'], 'refs': refs}
        return state, inspect, invoke, apply

    def test_remote_audio_metadata_and_exact_pcm_cues_are_required(self):
        path, receipt = self.remote_narration_fixture()
        self.assertEqual(narration_receipt(self.client, path)[3]['frames'], 32000)
        receipt['cues'][0]['end'] = 1
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'actual PCM samples'):
            narration_receipt(self.client, path)
        receipt['cues'][0]['end'] = .5
        receipt['audio']['sha256'] = '0' * 64
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            narration_receipt(self.client, path)

    def test_only_approved_voxcpm2_narrator_receipts_can_start_new_import(self):
        path, receipt = self.remote_narration_fixture()
        for field, value in [('provider', 'voicestudio_remote'), ('narrator_id', 'other-narrator')]:
            changed = dict(receipt, **{field: value})
            path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Oxiegen-Narrator'):
                narration_receipt(self.client, path)
        for field in ('script_sha256', 'config_sha256', 'license_evidence_sha256', 'model_revision'):
            changed = json.loads(json.dumps(receipt))
            changed['provenance'][field] = ''
            path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaises(ValueError):
                narration_receipt(self.client, path)

    def test_remote_audio_attaches_to_separate_track_with_measured_captions(self):
        path, receipt = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            result = attach_narration_to_fixture(self.client, path, 7, 'accent')
        commands = state['commands'][0]
        speech = next(command['params'] for command in commands if command.get('as') == 'speech')
        self.assertEqual(speech['layer'], 3000000)
        self.assertEqual(speech['end'], 2)
        captions = [command['params'] for command in commands if command['method'] == 'text.add']
        self.assertEqual([(cue['position'], cue['duration']) for cue in captions], [(0, .5), (.5, 1.5)])
        self.assertEqual([cue['text'] for cue in captions], [cue['text'] for cue in receipt['cues']])
        self.assertIn('MEASURED_SEGMENT', result['caption_alignment'])
        self.assertEqual(result['narrator_id'], 'oxiegen-narrator')
        self.assertEqual(result['provenance'], receipt['provenance'])
        self.assertFalse(result['publication_eligible'])

    def test_receipt_changed_after_validation_is_not_bound_to_native_edit(self):
        path, receipt = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        def changed_inspection():
            changed = dict(receipt, text_sha256='e' * 64)
            path.write_text(json.dumps(changed))
            return inspect()
        with patch.object(self.client, 'inspect', side_effect=changed_inspection), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            with self.assertRaisesRegex(ValueError, 'changed after validation'):
                attach_narration_to_fixture(self.client, path, 7, 'accent')
        self.assertEqual(state['commands'], [])

    def test_historical_attachment_ownership_is_read_without_reexecuting_retired_provider(self):
        path, _ = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            first = attach_narration_to_fixture(self.client, path, 7, 'accent')
            record_path = next(candidate for candidate in self.client.receipts.glob('*.json')
                              if json.loads(candidate.read_text()).get('kind') == 'narration.attach')
            historical = json.loads(record_path.read_text())
            historical['result']['provider'] = 'voicestudio_remote'
            record_path.write_text(json.dumps(historical))
            unchanged_bytes = record_path.read_bytes()
            second = attach_narration_to_fixture(self.client, path, 8, first['speech_clip_id'])
        self.assertEqual(second['provider'], 'voxcpm2_remote')
        self.assertEqual(record_path.read_bytes(), unchanged_bytes)
        self.assertTrue(all(caption['clip_id'] not in state['clips'] for caption in first['generated_captions']))

    def test_missing_measured_cues_does_not_invent_captions(self):
        path, _ = self.remote_narration_fixture(cues=False)
        state, inspect, invoke, apply_native = self.fake_fixture_editor()
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply_native) as apply:
            result = attach_narration_to_fixture(self.client, path, 7, 'accent')
        self.assertIn('BLOCKED', result['caption_alignment'])
        self.assertFalse(any(command['method'] == 'text.add' for command in apply.call_args.args[0]))

    def test_long_measured_paragraph_is_not_given_invented_subtitle_timestamps(self):
        path, receipt = self.remote_narration_fixture()
        receipt['cues'][0]['text'] = 'A' * 120
        path.write_text(json.dumps(receipt))
        state, inspect, invoke, apply_native = self.fake_fixture_editor()
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply_native) as apply:
            result = attach_narration_to_fixture(self.client, path, 7, 'accent')
        self.assertIn('BLOCKED', result['caption_alignment'])
        self.assertFalse(any(command['method'] == 'text.add' for command in apply.call_args.args[0]))

    def test_retake_removes_only_unchanged_owned_captions_and_preserves_manual_text(self):
        path, receipt = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            first = attach_narration_to_fixture(self.client, path, 7, 'accent')
            old_captions = {caption['clip_id'] for caption in first['generated_captions']}
            self.assertEqual(len(old_captions), 2)
            # A save can relocate thumbnail cache paths without changing caption ownership.
            for clip_id in old_captions:
                state['clips'][clip_id]['image'] = 'new-project_assets/thumbnail.png'
            receipt['cues'][0]['text'] = 'The actual retake text.'
            path.write_text(json.dumps(receipt))
            second = attach_narration_to_fixture(self.client, path, 8, first['speech_clip_id'])
            self.assertFalse(old_captions & state['clips'].keys())
            self.assertNotIn(first['speech_clip_id'], state['clips'])
            self.assertEqual(state['clips']['manual']['style']['text'], 'Owner title')
            self.assertEqual(len(second['generated_captions']), 2)
            self.assertTrue(all(caption['clip_id'] in state['clips'] for caption in second['generated_captions']))
            # A real manual correction must block a later retake, not silently delete it.
            manual_caption = second['generated_captions'][0]['clip_id']
            state['clips'][manual_caption]['style']['text'] = 'Owner corrected caption'
            with self.assertRaisesRegex(ValueError, 'preserve manual edits'):
                attach_narration_to_fixture(self.client, path, 9, second['speech_clip_id'])
            self.assertEqual(len(state['commands']), 2)
            self.assertEqual(state['clips'][manual_caption]['style']['text'], 'Owner corrected caption')

    def test_first_music_duck_and_longer_retake_clear_old_restore_points(self):
        path, receipt = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        curve = lambda: {point['co']['X']: point['co']['Y'] for point in state['clips']['music']['volume']['Points']}
        self.assertEqual(curve()[31], .25)  # Existing fixture fade restored normal gain at one second.
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            first = attach_narration_to_fixture(self.client, path, 7, 'accent')
            self.assertEqual(curve()[31], .05)
            self.assertTrue(all(value <= .05 for frame, value in curve().items() if frame <= 61))
            self.assertEqual(curve()[76], .25)  # Two-second speech restored after its half-second fade.
            with wave.open(str(path.with_name('narration.wav')), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0\0' * 64000)
            receipt['audio'] = inspect_wav(path.with_name('narration.wav').read_bytes())
            receipt['cues'][-1].update(end_sample=64000, end=4)
            path.write_text(json.dumps(receipt))
            second = attach_narration_to_fixture(self.client, path, 8, first['speech_clip_id'])
            self.assertNotIn(76, curve())
            self.assertTrue(all(value <= .05 for frame, value in curve().items() if frame <= 121))
            self.assertEqual(curve()[136], .25)
            state['clips']['music']['volume']['Points'][0]['co']['Y'] = .7
            state['revision'] += 1  # Caller inspects a fresh revision after an owner's gain correction.
            with self.assertRaisesRegex(ValueError, 'preserve manual edits'):
                attach_narration_to_fixture(self.client, path, 10, second['speech_clip_id'])
            self.assertEqual(len(state['commands']), 2)
            self.assertEqual(curve()[1], .7)

    def test_manual_music_gain_before_first_attachment_blocks_without_mutation(self):
        path, _ = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        state['clips']['music']['volume']['Points'][1]['co']['Y'] = .8
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            with self.assertRaisesRegex(ValueError, 'preserve manual edits'):
                attach_narration_to_fixture(self.client, path, 7, 'accent')
        self.assertEqual(state['commands'], [])
        self.assertIn('accent', state['clips'])

    def test_unrelated_manual_music_is_not_rewritten_by_narration(self):
        path, _ = self.remote_narration_fixture()
        state, inspect, invoke, apply = self.fake_fixture_editor()
        manual = {'id': 'manual-music', 'layer': 2000000, 'volume': {'Points': [{'co': {'X': 1, 'Y': .8}}]}}
        state['clips']['manual-music'] = manual
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke), \
                patch.object(self.client, 'apply', side_effect=apply):
            with self.assertRaisesRegex(ValueError, 'baseline missing or ambiguous'):
                attach_narration_to_fixture(self.client, path, 7, 'accent')
        self.assertEqual(state['commands'], [])
        self.assertEqual(state['clips']['manual-music'], manual)

    def test_fixture_music_baseline_is_recorded_from_native_volume_readback(self):
        state, inspect, invoke, _ = self.fake_fixture_editor()
        retain_fixture_entry(self.client.receipts / ('d' * 32 + '.json'))
        with patch.object(self.client, 'inspect', side_effect=inspect), \
                patch.object(self.client, '_invoke', side_effect=invoke):
            capture_music_baseline(self.client, 'music', 7)
        receipt = next(json.loads(path.read_text()) for path in self.client.receipts.glob('*.json')
                       if path.name != 'session-test-session.json')
        self.assertEqual(receipt['kind'], 'fixture.music')
        self.assertEqual(receipt['result']['ownership'], 'managed')
        self.assertEqual(receipt['result']['managed_music'][0]['sha256'], music_fingerprint(state['clips']['music']))

    def test_occupied_speech_track_is_not_silently_deleted(self):
        path, _ = self.remote_narration_fixture()
        with patch.object(self.client, 'inspect', return_value=self.fixture_narration_inspection()), \
                patch.object(self.client, '_invoke', return_value={'data': [{'id': 'owner-speech', 'layer': 3000000}]}), \
                patch.object(self.client, 'apply') as apply:
            with self.assertRaisesRegex(ValueError, 'Speech track occupied'):
                attach_narration_to_fixture(self.client, path, 7)
            apply.assert_not_called()


if __name__ == '__main__':
    unittest.main()
