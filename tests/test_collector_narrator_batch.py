"""Owned synthetic batch fixtures; no model import, CUDA or host deployment."""
from contextlib import closing
import io
import base64
import json
import os
from pathlib import Path
import sqlite3
import threading
import unittest
from unittest.mock import Mock, patch
import wave

from tests.fixture_retention import FixtureDirectory
from tests.test_collector_narrator_host import HostFixture
from youtube_ops import collector_narrator_host as host


def wav(path, frames, rate=16000, value=1):
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(value.to_bytes(2, 'little', signed=True) * frames)


def successful(parts, output, cancel):
    directory = output.parent / 'segments'; directory.mkdir()
    for index, part in enumerate(parts):
        wav(directory / ('output_%03d.wav' % (index + 1)), 100 + index, value=index + 1)
    return host.join_batch_outputs(directory, output, parts)


class BatchValidationTests(unittest.TestCase):
    def test_exact_line_format_size_and_field_contract(self):
        self.assertEqual(host.validate_segments('One. Two.', ['One.', 'Two.']), ['One.', 'Two.'])
        for text, parts in [('One. Two.', []), ('a', ['a'] * 17), (' One.', [' One.']),
                            ('One. Two.', ['One.\nTwo.']), ('a\tb', ['a\tb']), ('a\x7fb', ['a\x7fb']),
                            ('One.  Two.', ['One.', 'Two.']), ('a' * 12001, ['a' * 12001])]:
            with self.subTest(parts=parts), self.assertRaises(host.NarratorError):
                host.validate_segments(text, parts)

    def test_utf8_batch_request_size_preserves_legacy_limit(self):
        part = '\U0001f600' * 12000
        value = {'idempotency_key': 'a' * 32, 'narrator_id': host.NARRATOR, 'text': part, 'segments': [part]}
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.assertGreater(len(raw), host.LEGACY_MAX_BODY)
        self.assertLess(len(raw), host.MAX_BODY)
        request = host.NarratorHandler.__new__(host.NarratorHandler)
        from email.message import Message
        request.headers = Message()
        request.headers['Content-Length'] = str(len(raw)); request.headers['Content-Type'] = 'application/json'
        request.rfile = io.BytesIO(raw)
        self.assertEqual(request.body(), value)
        del value['segments']
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8') + b' ' * 20000
        request.headers.replace_header('Content-Length', str(len(raw))); request.rfile = io.BytesIO(raw)
        with self.assertRaisesRegex(host.NarratorError, 'request_too_large'):
            request.body()

    def test_fixed_cli_batch_arguments_preserve_narrator_and_settings(self):
        args = host.batch_arguments(Path('owned/input.private.txt'), Path('owned/segments'))
        self.assertEqual(args[:2], [str(host.CLI), 'batch'])
        self.assertEqual(args[args.index('--reference-audio') + 1], str(host.REFERENCE))
        self.assertEqual(args[args.index('--cfg-value') + 1], '2.0')
        self.assertEqual(args[args.index('--inference-timesteps') + 1], '10')
        for flag in ('--no-denoiser', '--no-optimize', '--local-files-only'):
            self.assertIn(flag, args)
        for flag in ('--normalize', '--denoise', '--control', '--prompt-audio', '--lora-path', '--device'):
            self.assertNotIn(flag, args)

    def test_one_owned_cli_process_per_batch_and_exact_pcm_cues(self):
        with FixtureDirectory(prefix='kn-batch-runner-') as directory:
            output = Path(directory) / 'narration.wav'
            runner = host.WindowsScriptRunner()
            def process(args, wav_path, cancel, timeout, environment, log, batch_directory):
                self.assertEqual(args, host.batch_arguments(output.parent / 'batch-input.private.txt', output.parent / 'segments'))
                self.assertEqual(timeout, host.BATCH_TIMEOUT_SECONDS)
                self.assertEqual(environment['TORCH_COMPILE_DISABLE'], '1')
                self.assertEqual((output.parent / 'batch-input.private.txt').read_text(), 'One.\nTwo.\n')
                log.write_text('Loading VoxCPM model...\nModel loaded (from_pretrained).\nBatch finished: 2/2 succeeded\n')
                wav(output.parent / 'segments/output_001.wav', 100, value=1)
                wav(output.parent / 'segments/output_002.wav', 201, value=2)
            with patch.object(runner, '_execute', side_effect=process) as owned:
                cues = runner.batch(['One.', 'Two.'], output, threading.Event())
            owned.assert_called_once()
            self.assertEqual([x['end_sample'] for x in cues], [100, 301])
            self.assertEqual(cues[1]['start_sample'], 100)
            with wave.open(str(output), 'rb') as joined:
                self.assertEqual(joined.readframes(301), b'\x01\x00' * 100 + b'\x02\x00' * 201)
            self.assertTrue((output.parent / 'batch-cli.private.log').exists())

    def test_cli_exit_zero_with_missing_bad_extra_or_mismatched_outputs_fails_closed(self):
        for kind in ('partial', 'bad', 'extra', 'format'):
            with self.subTest(kind=kind), FixtureDirectory(prefix='kn-batch-invalid-') as directory:
                output = Path(directory) / 'narration.wav'
                runner = host.WindowsScriptRunner()
                def process(*args):
                    (output.parent / 'batch-cli.private.log').write_text('Loading VoxCPM model...\nModel loaded (from_pretrained).\nBatch finished: 2/2 succeeded\n')
                    wav(output.parent / 'segments/output_001.wav', 100)
                    if kind == 'partial': return
                    wav(output.parent / 'segments/output_002.wav', 101, 8000 if kind == 'format' else 16000)
                    if kind == 'bad': (output.parent / 'segments/output_002.wav').write_bytes(b'invalid fixture')
                    if kind == 'extra': (output.parent / 'segments/unexpected.txt').write_text('retained fixture')
                with patch.object(runner, '_execute', side_effect=process):
                    with self.assertRaises(host.NarratorError):
                        runner.batch(['One.', 'Two.'], output, threading.Event())
                self.assertTrue((output.parent / 'segments/output_001.wav').exists())
                self.assertFalse(output.exists())

    def test_cli_reported_failure_or_multiple_model_loads_cannot_become_completed(self):
        for extra in ('Failed on line 1: owned failure fixture\n', 'Loading VoxCPM model...\n'):
            with self.subTest(extra=extra), FixtureDirectory(prefix='kn-batch-log-') as directory:
                output = Path(directory) / 'narration.wav'; runner = host.WindowsScriptRunner()
                def process(*args):
                    for index in (1, 2): wav(output.parent / ('segments/output_%03d.wav' % index), 100)
                    (output.parent / 'batch-cli.private.log').write_text('Loading VoxCPM model...\nModel loaded (from_pretrained).\nBatch finished: 2/2 succeeded\n' + extra)
                with patch.object(runner, '_execute', side_effect=process):
                    with self.assertRaisesRegex(host.NarratorError, 'batch_cli_completion_unverified'):
                        runner.batch(['One.', 'Two.'], output, threading.Event())
                self.assertFalse(output.exists())

    def test_fast_completed_cli_cannot_bypass_aggregate_disk_limit_between_polls(self):
        with FixtureDirectory(prefix='kn-batch-fast-limit-') as directory:
            output = Path(directory) / 'narration.wav'; runner = host.WindowsScriptRunner()
            def process(*args):
                for index in (1, 2): wav(output.parent / ('segments/output_%03d.wav' % index), 20)
                (output.parent / 'batch-cli.private.log').write_text('Loading VoxCPM model...\nModel loaded (from_pretrained).\nBatch finished: 2/2 succeeded\n')
            with patch.object(runner, '_execute', side_effect=process), patch.object(host, 'MAX_WAV', 128):
                with self.assertRaisesRegex(host.NarratorError, '^batch_output_limit$'):
                    runner.batch(['One.', 'Two.'], output, threading.Event())
            self.assertFalse(output.exists())
            self.assertEqual(len(list((output.parent / 'segments').iterdir())), 2)

    def test_growing_batch_artifacts_are_bounded_without_following_links(self):
        with FixtureDirectory(prefix='kn-batch-growth-') as directory:
            directory = Path(directory)
            self.assertFalse(host.batch_output_limit(directory))
            first = directory / 'output_001.wav'; first.write_bytes(b'owned fixture')
            self.assertFalse(host.batch_output_limit(directory))
            with patch.object(host, 'MAX_WAV', 1):
                self.assertTrue(host.batch_output_limit(directory))
            (directory / 'unexpected.txt').write_text('owned fixture')
            self.assertTrue(host.batch_output_limit(directory))
        with FixtureDirectory(prefix='kn-batch-growth-') as directory:
            directory = Path(directory)
            for index in range(1, 18): (directory / ('output_%03d.wav' % index)).touch()
            self.assertTrue(host.batch_output_limit(directory))
        with FixtureDirectory(prefix='kn-batch-growth-') as directory:
            directory = Path(directory); (directory / 'output_001.wav').mkdir()
            self.assertTrue(host.batch_output_limit(directory))

    def test_cancelled_before_batch_start_creates_no_files_or_process(self):
        with FixtureDirectory(prefix='kn-batch-cancel-') as directory:
            output = Path(directory) / 'narration.wav'; cancel = threading.Event(); cancel.set()
            runner = host.WindowsScriptRunner()
            with patch.object(runner, '_execute') as process:
                with self.assertRaisesRegex(host.NarratorError, '^cancelled$'):
                    runner.batch(['One.'], output, cancel)
            process.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])


class BatchStoreTests(HostFixture):
    def new_store(self, executor=None, enabled=True):
        value = host.NarratorStore(self.spool, host.NarratorManifest(self.manifest_path), executor, segment_batches=enabled)
        self.addCleanup(lambda: value.close() if getattr(value, 'db', None) is not None else None)
        return value

    def batch_request(self, key='a' * 32, parts=None):
        parts = ['One.', 'Two.'] if parts is None else parts
        return {**self.request(key, ' '.join(parts)), 'segments': parts}

    def test_default_legacy_is_not_activated_by_request_fields(self):
        store = self.new_store(Mock(), enabled=False)
        self.assertFalse(store.health()['segment_batches'])
        self.assertEqual(store.schema, '1')
        with self.assertRaisesRegex(host.NarratorError, 'not_enabled'):
            store.submit(self.batch_request())
        self.assertFalse((self.spool / 'host-narrations.schema1.backup.sqlite').exists())
        store.submit(self.request()); self.assertEqual(store.health()['queue_depth'], 1)

    def test_batch_idempotency_completed_cues_and_legacy_requests_share_existing_queue(self):
        executor = Mock(); executor.batch = Mock(side_effect=successful)
        store = self.new_store(executor)
        value = store.submit(self.batch_request())
        self.assertTrue(store.health()['segment_batches'])
        self.assertEqual(store.submit(self.batch_request())['id'], value['id'])
        with self.assertRaisesRegex(host.NarratorError, 'idempotency_conflict'):
            store.submit(self.batch_request(parts=['Changed.', 'Text.']))
        store.run_next(); result = store.get(value['id'])
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['execution_mode'], 'cli_segment_batch_v1')
        self.assertEqual([x['text'] for x in result['cues']], ['One.', 'Two.'])
        self.assertEqual(result['cues'][-1]['end_sample'], result['audio']['frames'])
        self.assertEqual(result['audio']['frames'], 201)
        executor.batch.assert_called_once(); executor.assert_not_called()
        self.assertFalse(store.run_next())
        store.submit(self.request('b' * 32))
        executor.side_effect = lambda text, output, cancel: wav(output, 100)
        store.run_next(); self.assertEqual(store.get('b' * 32)['state'], 'completed')
        self.assertNotIn('cues', store.get('b' * 32))
        self.assertNotIn('execution_mode', store.get('b' * 32))
        self.assertEqual(store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)

    def test_invalid_fields_and_stored_segment_tampering_never_execute(self):
        executor = Mock(); store = self.new_store(executor)
        for change in ({'segments': ['One.\nTwo.']}, {'path': 'other'}, {'model': 'other'}, {'segments': ['wrong']}):
            with self.subTest(change=change), self.assertRaises(host.NarratorError):
                store.submit({**self.batch_request(), **change})
        store.submit(self.batch_request())
        with store.db: store.db.execute('UPDATE jobs SET segments=?', (json.dumps(['Changed.', 'Text.']),))
        store.run_next()
        self.assertEqual(store.get('a' * 32)['state'], 'failed')
        executor.assert_not_called(); executor.batch.assert_not_called()

    def test_known_partial_failure_does_not_complete_or_retry_and_preserves_artifacts(self):
        def partial(parts, output, cancel):
            directory = output.parent / 'segments'; directory.mkdir()
            wav(directory / 'output_001.wav', 100)
            raise host.NarratorError('batch_outputs_incomplete_or_unexpected')
        executor = Mock(); executor.batch = Mock(side_effect=partial)
        store = self.new_store(executor); store.submit(self.batch_request()); store.run_next()
        self.assertEqual(store.get('a' * 32)['state'], 'failed')
        self.assertFalse(store.health()['execution_hold'])
        self.assertFalse(store.run_next()); executor.batch.assert_called_once()
        self.assertTrue((self.spool / ('a' * 32) / 'segments/output_001.wav').exists())

    def test_uncertain_batch_holds_all_dispatch_and_restart_preserves_original_id(self):
        executor = Mock(); executor.batch = Mock(side_effect=host.NarratorError('process_outcome_unknown', uncertain=True))
        store = self.new_store(executor); request = self.batch_request(); store.submit(request); store.run_next()
        self.assertTrue(store.health()['execution_hold'])
        self.assertFalse(store.run_next()); executor.batch.assert_called_once()
        store.close(); store.db = None
        restarted = self.new_store(Mock())
        self.assertTrue(restarted.health()['execution_hold'])
        self.assertEqual(restarted.submit(request)['id'], 'a' * 32)
        with self.assertRaisesRegex(host.NarratorError, 'requires_reconciliation'):
            restarted.submit(self.batch_request('b' * 32))

    def test_running_batch_cancellation_and_restart_running_hold(self):
        entered = threading.Event()
        def cancel(parts, output, event):
            entered.set(); event.wait(2)
            if event.is_set(): raise host.NarratorError('cancelled')
            raise AssertionError('Cancellation not forwarded')
        executor = Mock(); executor.batch = Mock(side_effect=cancel)
        store = self.new_store(executor); store.submit(self.batch_request())
        thread = threading.Thread(target=store.run_next); thread.start(); self.assertTrue(entered.wait(1))
        self.assertTrue(store.cancel('a' * 32)['cancel_requested']); thread.join(2)
        self.assertFalse(thread.is_alive()); self.assertEqual(store.get('a' * 32)['state'], 'cancelled')
        store.submit(self.batch_request('b' * 32))
        with store.db: store.db.execute("UPDATE jobs SET state='running' WHERE id=?", ('b' * 32,))
        store.close(); store.db = None
        restarted = self.new_store(Mock())
        self.assertEqual(restarted.get('b' * 32)['error'], 'outcome_unknown')
        self.assertTrue(restarted.health()['execution_hold'])

    def test_idle_migration_preserves_old_rows_events_and_consistent_backup(self):
        legacy = self.new_store(Mock(side_effect=lambda text, output, cancel: wav(output, 100)), enabled=False)
        legacy.submit(self.request()); legacy.run_next()
        rows = [tuple(row) for row in legacy.db.execute('SELECT * FROM jobs')]
        events = [tuple(row) for row in legacy.db.execute('SELECT * FROM events')]
        legacy.close(); legacy.db = None
        upgraded = self.new_store(Mock())
        self.assertEqual(upgraded.schema, '2')
        self.assertEqual([tuple(row)[:9] for row in upgraded.db.execute('SELECT * FROM jobs')], rows)
        self.assertEqual([tuple(row) for row in upgraded.db.execute('SELECT * FROM events')], events)
        with closing(sqlite3.connect(self.spool / 'host-narrations.schema1.backup.sqlite')) as backup:
            self.assertEqual(backup.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '1')
            self.assertEqual(backup.execute('SELECT * FROM jobs').fetchall(), rows)
        self.assertTrue((self.spool / 'schema2-migration.private.json').is_file())
        self.assertTrue((self.spool / 'schema2-migration-completed.private.json').is_file())

    def test_pending_or_prior_migration_evidence_blocks_upgrade(self):
        legacy = self.new_store(Mock(), enabled=False); legacy.submit(self.request()); legacy.close(); legacy.db = None
        with self.assertRaisesRegex(host.NarratorError, 'requires_idle'):
            self.new_store(Mock())
        self.assertFalse((self.spool / 'host-narrations.schema1.backup.sqlite').exists())
        with closing(sqlite3.connect(self.spool / 'host-narrations.sqlite')) as db:
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '1')
            db.execute("UPDATE jobs SET state='cancelled'"); db.commit()
        (self.spool / 'host-narrations.schema1.backup.sqlite').write_bytes(b'preserved previous attempt')
        with self.assertRaisesRegex(host.NarratorError, 'requires_reconciliation'):
            self.new_store(Mock())
        self.assertEqual((self.spool / 'host-narrations.schema1.backup.sqlite').read_bytes(), b'preserved previous attempt')

    def test_missing_commit_receipt_after_schema_commit_blocks_reopen_without_data_loss(self):
        legacy = self.new_store(Mock(), enabled=False); legacy.close(); legacy.db = None
        original_open = Path.open
        def fail_commit(path, *args, **kwargs):
            if path.name == 'schema2-migration-completed.private.json': raise OSError('owned fixture injected write failure')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_commit), self.assertRaises(OSError):
            self.new_store(Mock())
        with closing(sqlite3.connect(self.spool / 'host-narrations.sqlite')) as db:
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '2')
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        self.assertTrue((self.spool / 'host-narrations.schema1.backup.sqlite').exists())
        with self.assertRaises((OSError, host.VoiceError)):
            self.new_store(Mock())

    def test_active_writer_prevents_schema_change_and_preserves_rows(self):
        legacy = self.new_store(Mock(), enabled=False); legacy.close(); legacy.db = None
        with closing(sqlite3.connect(self.spool / 'host-narrations.sqlite')) as writer:
            writer.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                self.new_store(Mock())
            writer.rollback()
            self.assertEqual(writer.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '1')
        self.assertFalse((self.spool / 'host-narrations.schema1.backup.sqlite').exists())

    def test_failed_second_alter_rolls_back_schema_and_retains_original_backup(self):
        legacy = self.new_store(Mock(), enabled=False); legacy.close(); legacy.db = None
        class Failing(host.NarratorStore):
            def _migrate_batches(self):
                count = [0]
                def authorize(action, first, second, database, trigger):
                    if action == sqlite3.SQLITE_ALTER_TABLE:
                        count[0] += 1
                        if count[0] == 2: return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                self.db.set_authorizer(authorize)
                return super()._migrate_batches()
        with self.assertRaises(sqlite3.DatabaseError):
            Failing(self.spool, host.NarratorManifest(self.manifest_path), Mock(), segment_batches=True)
        with closing(sqlite3.connect(self.spool / 'host-narrations.sqlite')) as db:
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '1')
            self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(jobs)')], host.JOB_COLUMNS)
        self.assertTrue((self.spool / 'host-narrations.schema1.backup.sqlite').is_file())
        self.assertFalse((self.spool / 'schema2-migration-completed.private.json').exists())


@unittest.skipUnless(os.name == 'nt' and os.environ.get('COLLECTOR_NATIVE_BATCH_PROCESS') == '1',
                     'Opt-in serialized FORGE native process fixture, no inference')
class NativeBatchProcessTests(unittest.TestCase):
    def test_live_growing_segment_limit_stops_only_owned_child_and_retains_partial(self):
        with FixtureDirectory(prefix='kn-batch-native-limit-', trusted_execution=True) as directory:
            output = Path(directory) / 'narration.wav'
            def arguments(input_path, destination):
                escaped = str(destination).replace("'", "''")
                code = ("[IO.File]::WriteAllBytes('" + escaped + "/output_001.wav',[byte[]]::new(8192));Start-Sleep -Seconds 30")
                return [str(host._system_powershell()), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code]
            with patch.object(host, 'batch_arguments', side_effect=arguments), patch.object(host, 'MAX_WAV', 4096):
                with self.assertRaisesRegex(host.NarratorError, '^generation_timeout_or_size_limit$'):
                    host.WindowsScriptRunner().batch(['One.'], output, threading.Event())
            process = json.loads((output.parent / 'batch-process.private.json').read_text())
            self.assertEqual(process['owned_active_processes'], 0)
            self.assertEqual(process['outcome'], 'generation_timeout_or_size_limit')
            self.assertTrue((output.parent / 'segments/output_001.wav').exists())
            self.assertEqual((output.parent / 'segments/output_001.wav').stat().st_size, 8192)
            self.assertFalse(output.exists())

    def test_owned_batch_process_environment_private_log_and_pcm(self):
        with FixtureDirectory(prefix='kn-batch-native-', trusted_execution=True) as directory:
            output = Path(directory) / 'narration.wav'
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as stream:
                stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                stream.writeframes(b'\x01\x00' * 100)
            encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
            def arguments(input_path, destination):
                escaped = str(destination).replace("'", "''")
                code = ("$ErrorActionPreference='Stop';if($env:TORCH_COMPILE_DISABLE -cne '1'){exit 9};"
                    "Write-Output 'Loading VoxCPM model...';Write-Output 'Model loaded (from_pretrained).';"
                    "$b=[Convert]::FromBase64String('" + encoded + "');"
                    "[IO.File]::WriteAllBytes('" + escaped + "/output_001.wav',$b);"
                    "[IO.File]::WriteAllBytes('" + escaped + "/output_002.wav',$b);"
                    "Write-Output 'TORCH_COMPILE_DISABLE=1';Write-Output 'Batch finished: 2/2 succeeded'")
                return [str(host._system_powershell()), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code]
            with patch.object(host, 'batch_arguments', side_effect=arguments):
                cues = host.WindowsScriptRunner().batch(['One.', 'Two.'], output, threading.Event())
            self.assertEqual(cues[-1]['end_sample'], 200)
            self.assertIn('TORCH_COMPILE_DISABLE=1', (output.parent / 'batch-cli.private.log').read_text())
            self.assertEqual(host.inspect_wav(output)['frames'], 200)
            process = json.loads((output.parent / 'batch-process.private.json').read_text())
            self.assertEqual(process['owned_active_processes'], 0)
            self.assertEqual(process['exit_code'], 0)
            self.assertEqual(process['model_lifecycle'], 'batch_process_exit')


if __name__ == '__main__':
    unittest.main()
