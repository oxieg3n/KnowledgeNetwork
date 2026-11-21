from tests.fixture_retention import FixtureDirectory
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from youtube_ops import collector_narrator_control as control


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = FixtureDirectory(trusted_execution=True)
        self.addCleanup(self.temp.cleanup)
        self.spool = Path(self.temp.name)
        self.helper = Mock()
        self.helper.windows_identity.return_value = ('owner', False)
        self.helper.local_file.side_effect = lambda path: Path(path)
        self.patches = [patch.object(control, 'SPOOL', self.spool),
            patch.object(control, '_helpers', return_value=self.helper),
            patch.object(control, 'verify_spool_acl'), patch.object(control, 'verify_private_paths')]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.broker = control.NarratorControl({'owner_sid': 'owner', 'manifest_sha256': 'a'*64})
        self.addCleanup(self.broker.db.close)

    def request(self, operation='narrator-health', request_id='a'*32):
        return {'schema_version': 1, 'request_id': request_id, 'operation': operation}

    def test_startup_stages_and_private_error_redaction(self):
        from youtube_ops import collector_narrator_pipe as pipe
        review = self.spool / 'review'
        review.mkdir()
        self.helper.load_config.return_value = {'owner_sid': 'owner'}
        self.helper.BrokerError = pipe.BrokerError
        self.helper.allow_bridge_inspection.side_effect = OSError('private-token-reference')
        with patch.object(control, 'NarratorControl', return_value=self.broker):
            with self.assertRaises(OSError):
                control.main()
        logs = list(review.glob('narrator-control-startup-*.private.jsonl'))
        self.assertEqual(len(logs), 1)
        raw = logs[0].read_text()
        self.assertNotIn('private-token-reference', raw)
        events = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual([e['stage'] for e in events], ['inspection_acl', 'failed'])
        self.assertEqual(events[-1]['error'], 'startup_unverified')
        self.helper.serve.assert_not_called()

    def test_startup_reparse_path_denied_before_log_creation(self):
        review = self.spool / 'review'
        review.mkdir()
        self.helper.load_config.return_value = {'owner_sid': 'owner'}
        with patch.object(control, 'NarratorControl', return_value=self.broker), \
                patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(control.ControlBlocked, 'startup_log_path_denied'):
                control.main()
        self.assertEqual(list(review.iterdir()), [])

    def test_startup_ready_callback_and_evidence_limit(self):
        from youtube_ops import collector_narrator_pipe as pipe
        review = self.spool / 'review'
        review.mkdir()
        self.helper.load_config.return_value = {'owner_sid': 'owner'}
        self.helper.BrokerError = pipe.BrokerError
        self.helper.serve.side_effect = lambda config, handler, cancel, ready: ready()
        with patch.object(control, 'NarratorControl', return_value=self.broker):
            control.main()
        log = next(review.glob('narrator-control-startup-*.private.jsonl'))
        self.assertEqual([json.loads(line)['stage'] for line in log.read_text().splitlines()],
                         ['inspection_acl', 'pipe_create', 'pipe_ready', 'stopped'])
        for index in range(99):
            (review / ('narrator-control-startup-fixture%d.private.jsonl' % index)).touch()
        with patch.object(control, 'NarratorControl', return_value=self.broker):
            with self.assertRaisesRegex(control.ControlBlocked, 'startup_evidence_limit'):
                control.main()
        self.assertEqual(len(list(review.iterdir())), 100)

    def test_exact_envelope_and_replay(self):
        with patch.object(self.broker, '_execute', return_value={'ready': True}) as run:
            result = self.broker.handle(self.request())
            self.assertEqual(set(result), {'schema_version', 'request_id', 'operation', 'status', 'result'})
            self.assertEqual(result, self.broker.handle(self.request()))
            run.assert_called_once()

    def test_conflict_denied(self):
        with patch.object(self.broker, '_execute', return_value={}):
            self.broker.handle(self.request())
            result = self.broker.handle(self.request('narrator-start'))
            self.assertEqual(result['error'], 'request_id_conflict')

    def test_request_fields_and_types_closed(self):
        for request in (None, {}, {**self.request(), 'path': 'secret'},
                        {**self.request(), 'schema_version': True}, self.request('shell'), self.request(request_id='../x')):
            self.assertEqual(self.broker.handle(request)['status'], 'BLOCKED')

    def test_identity_change_denied(self):
        self.helper.windows_identity.return_value = ('owner', True)
        self.assertEqual(self.broker.handle(self.request())['error'], 'owner_limited_identity_required')
        self.helper.windows_identity.return_value = ('bridge', False)
        self.assertEqual(self.broker.handle(self.request())['error'], 'owner_limited_identity_required')

    def test_unknown_outcome_not_replayed_or_bypassed(self):
        with patch.object(self.broker, '_execute', side_effect=RuntimeError('private token')) as run:
            response = self.broker.handle(self.request('narrator-start'))
            self.assertNotIn('private', json.dumps(response))
            self.assertEqual(self.broker.handle(self.request('narrator-start'))['error'], 'control_outcome_unknown_do_not_replay')
            self.assertEqual(self.broker.handle(self.request('narrator-start', 'b'*32))['error'], 'control_previous_outcome_unknown')
            run.assert_called_once()

    def test_unowned_listener_stop_never_adopts(self):
        result = self.broker.handle(self.request('narrator-stop'))
        self.assertEqual(result['error'], 'listener_not_owned_by_broker')

    def test_unowned_health_never_sends_credential(self):
        with patch.object(self.broker, '_secret') as secret, patch.object(self.broker, '_request') as request:
            result = self.broker.handle(self.request())
            self.assertEqual(result['error'], 'listener_not_owned_by_broker')
            secret.assert_not_called()
            request.assert_not_called()

    def test_existing_credential_never_rewritten_or_returned(self):
        with patch.object(control.credentials, 'read_secret', return_value=('private'*8, 1)), patch.object(control.credentials, 'write_secret') as write:
            result = self.broker.handle(self.request('narrator-credential-ensure'))
            self.assertEqual(result['status'], 'PASS')
            self.assertNotIn('privateprivate', json.dumps(result))
            write.assert_not_called()

    def test_credential_failure_not_assumed_missing(self):
        with patch.object(control.credentials, 'read_secret', side_effect=ValueError('BLOCKED_VOICE_CREDENTIAL_MISSING')), patch.object(control.ctypes, 'get_last_error', return_value=5, create=True), patch.object(control.credentials, 'write_secret') as write:
            result = self.broker.handle(self.request('narrator-credential-ensure'))
            self.assertEqual(result['error'], 'credential_missing_not_confirmed')
            write.assert_not_called()

    def test_reconcile_is_inspection_only(self):
        with patch.object(self.broker, '_inspect_jobs', return_value={'execution_hold': True}) as inspect:
            result = self.broker.handle(self.request('narrator-reconcile'))['result']
            self.assertEqual(result, {'execution_hold': True, 'inspection_only': True, 'replayed': False, 'control_execution_hold': False, 'unknown_control_requests': 0, 'recent_mutations': [], 'requests': []})
            inspect.assert_called_once_with()

    def test_idle_stop_closes_only_owned_objects(self):
        store, server, thread = Mock(), Mock(), Mock()
        store.lock = __import__('threading').RLock()
        store.active = None
        store.health.return_value = {'queue_depth': 0, 'execution_hold': False}
        thread.is_alive.return_value = False
        self.broker.store, self.broker.server, self.broker.thread = store, server, thread
        self.assertEqual(self.broker._stop(), {'ownership': 'stopped_this_broker'})
        store.close.assert_called_once_with()
        server.shutdown.assert_called_once_with()
        server.server_close.assert_called_once_with()
        self.assertIsNone(self.broker.server)

    def test_held_stop_does_not_cancel_or_close_store(self):
        store, server, thread = Mock(), Mock(), Mock()
        store.lock = __import__('threading').RLock()
        store.active = None
        store.health.return_value = {'queue_depth': 0, 'execution_hold': True}
        thread.is_alive.return_value = False
        self.broker.store, self.broker.server, self.broker.thread = store, server, thread
        with patch.object(control.threading, 'Thread') as restart:
            self.assertRaises(control.ControlBlocked, self.broker._stop)
            restart.return_value.start.assert_called_once_with()
        store.close.assert_not_called()
        server.server_close.assert_not_called()

    def test_confirmed_missing_credential_created_once_and_readback_verified(self):
        missing = ValueError('BLOCKED_VOICE_CREDENTIAL_MISSING')
        with patch.object(control.credentials, 'read_secret', side_effect=[missing, ('generated-secret'*4, 1)]), patch.object(control.ctypes, 'get_last_error', return_value=1168, create=True), patch.object(control.secrets, 'token_urlsafe', return_value='generated-secret'*4), patch.object(control.credentials, 'write_secret') as write:
            result = self.broker.handle(self.request('narrator-credential-ensure'))
            self.assertEqual(result['status'], 'PASS')
            write.assert_called_once_with(control.CREDENTIAL_TARGET, 'generated-secret'*4)
            self.assertNotIn('generated-secret', json.dumps(result))

    def test_reconcile_reports_uncertain_uuid_without_clearing_or_replaying(self):
        with self.broker.db:
            self.broker.db.execute('INSERT INTO requests VALUES(?,?,?,NULL)', ('c'*32, 'narrator-start', 'started'))
        with patch.object(self.broker, '_inspect_jobs', return_value={}):
            result = self.broker.handle(self.request('narrator-reconcile'))['result']
        self.assertTrue(result['control_execution_hold'])
        self.assertEqual(result['unknown_control_requests'], 1)
        self.assertEqual(result['requests'], [{'request_id': 'c'*32, 'operation': 'narrator-start', 'state': 'outcome_unknown'}])
        self.assertEqual(self.broker.db.execute('SELECT state FROM requests WHERE id=?', ('c'*32,)).fetchone()[0], 'started')

    def test_completed_response_lost_reconcile_recovers_uuid_without_replay_bounded(self):
        with patch.object(self.broker, '_execute', return_value={'credential': 'existing_verified'}) as execute:
            self.broker.handle(self.request('narrator-credential-ensure', 'c'*32))
            execute.assert_called_once()
        with patch.object(self.broker, '_inspect_jobs', return_value={}):
            recovered = self.broker.handle(self.request('narrator-reconcile', 'e'*32))['result']
        self.assertEqual(recovered['recent_mutations'], [{'request_id': 'c'*32, 'operation': 'narrator-credential-ensure', 'state': 'finished', 'outcome': 'PASS'}])
        with self.broker.db:
            for index in range(25):
                request_id = f'{index:032x}'
                response = json.dumps({'status': 'BLOCKED', 'error': 'private-error-not-returned'})
                self.broker.db.execute('INSERT INTO requests VALUES(?,?,?,?)', (request_id, 'narrator-start', 'finished', response))
        # Retained history is newest20; test original recoveredUUID within that bound.
        original = '00000000000000000000000000000018'
        with patch.object(self.broker, '_inspect_jobs', return_value={}), patch.object(self.broker, '_credential_ensure') as mutate:
            result = self.broker.handle(self.request('narrator-reconcile', 'd'*32))['result']
            mutate.assert_not_called()
        history = result['recent_mutations']
        self.assertEqual(len(history), 20)
        self.assertEqual(history[0], {'request_id': original, 'operation': 'narrator-start', 'state': 'finished', 'outcome': 'BLOCKED'})
        self.assertNotIn('private-error', json.dumps(result))
        self.assertNotIn('credential', json.dumps(history))

    def test_completed_audit_is_single_identity_duration_digest(self):
        with patch.object(self.broker, '_execute', return_value={'ready': True}):
            response = self.broker.handle(self.request())
            self.broker.handle(self.request())
        audit = self.broker.db.execute('SELECT * FROM audit').fetchall()
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0][:4], ('a'*32, 'owner', 'narrator-health', 'PASS'))
        self.assertGreaterEqual(audit[0][4], 0)
        self.assertEqual(audit[0][5], control.digest(response))

    def test_manifest_pin_before_parsing(self):
        self.helper.sha256.return_value = 'b'*64
        with patch.object(control, 'MANIFEST', self.spool / 'manifest.json'):
            (self.spool / 'manifest.json').write_text('{}')
            self.assertRaises(control.ControlBlocked, self.broker._manifest)

    def test_completed_valid_pcm_is_decoded_and_receipt_checked(self):
        import hashlib
        import wave
        directory = self.spool / ('c'*32)
        directory.mkdir()
        wav = directory / 'narration.wav'
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x00\x01' * 480)
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()
        db = sqlite3.connect(self.spool / 'host-narrations.sqlite')
        db.executescript('CREATE TABLE jobs(id,state,audio); CREATE TABLE metadata(key,value);')
        db.execute('INSERT INTO jobs VALUES(?,?,?)', ('c'*32, 'completed', json.dumps({'bytes': wav.stat().st_size, 'sha256': digest, 'frames': 480, 'sample_rate': 48000, 'channels': 1, 'sample_width': 2, 'duration': .01})))
        db.commit(); db.close()
        self.helper.sha256.return_value = digest
        result = self.broker._inspect_jobs(True)
        self.assertEqual(result, {'jobs': 1, 'completed_verified': 1, 'execution_hold': False, 'pending': 0})

    def test_completed_receipt_metadata_tamper_denied_with_same_wav_digest(self):
        import wave
        directory = self.spool / ('c'*32)
        directory.mkdir()
        wav = directory / 'narration.wav'
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x00\x01' * 480)
        measured = control.inspect_wav(wav)
        recorded = {**measured, 'bytes': wav.stat().st_size, 'duration': measured.pop('duration_seconds')}
        recorded.pop('duration_seconds', None)
        with sqlite3.connect(self.spool / 'host-narrations.sqlite') as db:
            db.executescript('CREATE TABLE jobs(id,state,audio); CREATE TABLE metadata(key,value);')
            for field, value in (('frames', 481), ('duration', .02), ('channels', True), ('sample_rate', 48000.0)):
                bad = {**recorded, field: value}
                db.execute('DELETE FROM jobs')
                db.execute('INSERT INTO jobs VALUES(?,?,?)', ('c'*32, 'completed', json.dumps(bad)))
                db.commit()
                with self.subTest(field=field):
                    self.assertRaises(control.ControlBlocked, self.broker._inspect_jobs, True)
        db.close()

    def test_completed_wav_digest_checked_read_only(self):
        db = sqlite3.connect(self.spool / 'host-narrations.sqlite')
        db.executescript('CREATE TABLE jobs(id,state,audio); CREATE TABLE metadata(key,value);')
        directory = self.spool / ('c'*32)
        directory.mkdir()
        (directory / 'narration.wav').write_bytes(b'not audio')
        db.execute('INSERT INTO jobs VALUES(?,?,?)', ('c'*32, 'completed', json.dumps({'bytes': 9, 'sha256': 'a'*64})))
        db.commit(); db.close()
        self.helper.sha256.return_value = 'b'*64
        self.assertRaises(control.ControlBlocked, self.broker._inspect_jobs, True)


class NativePrivateAclTests(unittest.TestCase):
    def test_real_native_child_acl_denied_without_repair(self):
        import os
        import subprocess
        if os.name != 'nt':
            self.skipTest('Windows native ACL test')
        from youtube_ops.collector_narrator_pipe import windows_identity
        sid, _ = windows_identity()
        with FixtureDirectory(trusted_execution=True) as temporary:
            root = Path(temporary)
            script = r"""
$ErrorActionPreference='Stop'
$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$a=Get-Acl -LiteralPath $r.path
$a.SetAccessRuleProtection($true,$false)
foreach($rule in @($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))) {$a.RemoveAccessRuleSpecific($rule)}
foreach($sid in @($r.sid,'S-1-5-18','S-1-5-32-544')) {
 $rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')
 $a.AddAccessRule($rule)
}
Set-Acl -LiteralPath $r.path -AclObject $a
"""
            result = subprocess.run([str(control._system_powershell()), '-NoProfile', '-NonInteractive', '-Command', script], input=json.dumps({'path': str(root), 'sid': sid}), text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            child = root / 'private.json'
            child.write_text('{}')
            with patch.object(control, 'SPOOL', root):
                control.verify_private_paths([root, child], sid)
                poison = r"""
$ErrorActionPreference='Stop'
$p=[Console]::In.ReadToEnd()
$a=Get-Acl -LiteralPath $p
$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Read','Allow'))
Set-Acl -LiteralPath $p -AclObject $a
"""
                result = subprocess.run([str(control._system_powershell()), '-NoProfile', '-NonInteractive', '-Command', poison], input=str(child), text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0)
                before = child.read_bytes()
                self.assertRaises(control.ControlBlocked, control.verify_private_paths, [root, child], sid)
                self.assertEqual(child.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
