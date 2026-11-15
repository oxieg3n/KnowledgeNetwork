"""Proposed recovery on retained owned fixtures; no BLACKHAT-BASE execution."""
import ctypes as c
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import types
import unittest
from unittest.mock import patch

from youtube_ops import collector_narrator_recovery as recovery
from youtube_ops import collector_narrator_recovery_probe as probe
from tests.fixture_retention import FixtureDirectory


SOURCE = Path(__file__).resolve().parents[1]/'docs/collector/host-tools/Stop-EmptyNarratorController.ps1'


def definitions(receipts):
    with patch.object(recovery, 'LEGACY', SOURCE), patch.object(recovery, 'RECEIPTS', receipts):
        return recovery._load_legacy()[0]


def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE requests(id TEXT PRIMARY KEY, operation TEXT NOT NULL, state TEXT NOT NULL, response TEXT)')
        db.execute('CREATE TABLE audit(request_id TEXT PRIMARY KEY, owner_sid TEXT NOT NULL, operation TEXT NOT NULL, outcome TEXT NOT NULL, duration_ms INTEGER NOT NULL, result_sha256 TEXT NOT NULL)')


class RecoveryIntegrationContractTests(unittest.TestCase):
    def test_default_entry_denies_before_any_host_path_or_database_access(self):
        with patch.object(recovery, '_load_legacy') as load, patch.object(recovery, '_self_image') as image:
            for approval in (False, None, 1, 'approved'):
                with self.assertRaisesRegex(recovery.RecoveryBlocked, 'live_recovery_not_authorized'):
                    recovery.recover_empty_controller({}, operator_approved=approval)
            load.assert_not_called(); image.assert_not_called()

    def test_approval_boolean_does_not_bypass_missing_recovery_code_deployment(self):
        with patch.object(recovery, '_load_legacy') as load, patch.object(recovery, '_self_image') as image:
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'reviewed_recovery_deployment_unavailable'):
                recovery.recover_empty_controller({}, operator_approved=True)
            load.assert_not_called(); image.assert_not_called()

    def test_pinned_definition_loader_never_compiles_old_main_or_imports_sqlite(self):
        code = definitions(Path('unused-receipts'))
        self.assertNotIn('sqlite3', code)
        self.assertEqual(code['RECEIPTS'], Path('unused-receipts'))
        self.assertIn('RECEIPTS', code['stop_empty'].__code__.co_names)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), recovery.LEGACY_SHA256)
        self.assertEqual(code['STAGE'], 'intent')

    def test_old_source_change_is_denied_without_compilation(self):
        with patch.object(recovery, '_bytes', return_value=b'unreviewed'), patch.object(recovery, 'exec', create=True) as run:
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'legacy_source_changed'):
                recovery._load_legacy()
            run.assert_not_called()


@unittest.skipUnless(os.name == 'nt' and c.sizeof(c.c_void_p) == 8, 'Native Windows x64 SQLite integration')
class NativeConnectionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import _sqlite3
        cls.dll = Path(_sqlite3.__file__).with_name('sqlite3.dll')
        cls.pin = hashlib.sha256(cls.dll.read_bytes()).hexdigest()

    def setUp(self):
        self.fixture = FixtureDirectory(prefix='kn-recovery-integration-')
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.path = self.root/'spool/narrator-control.sqlite'
        initialize(self.path)

    def test_raw_generic_writers_are_rejected_without_weakening_original_masks(self):
        encoded = base64.b64encode(recovery.TRUST_SCRIPT.encode('utf-8')).decode('ascii')
        script = "$source=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"'))\n" + r'''
$ErrorActionPreference='Stop';$t=$null;$e=$null
$tree=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$t,[ref]$e)
if($e.Count){throw 'Preflight parse failed'}
$fn=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq 'Assert-NoGenericWriters')
if($fn.Count -ne 1){throw 'Missing generic writer check'}
. ([ScriptBlock]::Create($fn[0].Extent.Text))
$trusted=@('owner','S-1-5-18','S-1-5-32-544','installer')
foreach($mask in @(0x10000000,0x40000000,0x50000000)){
 $rule=[pscustomobject]@{IdentityReference=[pscustomobject]@{Value='untrusted'};AccessControlType='Allow';FileSystemRights=$mask;PropagationFlags=[Security.AccessControl.PropagationFlags]::None}
 $denied=$false;try{Assert-NoGenericWriters @($rule) $trusted}catch{$denied=$true}
 if(-not $denied){throw 'Raw generic writer passed'}
 $rule.PropagationFlags=[Security.AccessControl.PropagationFlags]::InheritOnly
 Assert-NoGenericWriters @($rule) $trusted
 $rule.PropagationFlags=[Security.AccessControl.PropagationFlags]::None;$rule.IdentityReference.Value='owner'
 Assert-NoGenericWriters @($rule) $trusted
 $rule.IdentityReference.Value='untrusted';$rule.AccessControlType='Deny'
 Assert-NoGenericWriters @($rule) $trusted
}
'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def connection(self, stack, *, mismatch=False):
        guard = stack.enter_context(probe.NamespaceGuard(self.path))
        controller = types.SimpleNamespace(candidate={'identity': dict(guard.ledger)}, recheck=guard.verify)
        if mismatch:
            controller.candidate['identity']['file_id'] = '00'*16
        library = recovery._SqliteLibrary(self.dll, self.pin)
        stack.callback(library.close)
        connection = recovery._Connection(library, guard, controller, time.monotonic()+20)
        stack.callback(connection.close)
        return guard, connection

    def test_guard_before_connection_and_static_schema_queries_use_exact_handle(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            guard, db = self.connection(stack)
            self.assertEqual(db.execute('BEGIN IMMEDIATE').fetchall(), [])
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone(), ('delete',))
            self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone(), (0,))
            self.assertEqual(len(db.execute('PRAGMA table_info(audit)').fetchall()), 6)
            self.assertEqual({row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")},
                             {'requests', 'audit'})
            self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(requests)')],
                             ['id', 'operation', 'state', 'response'])
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'recovery_sql_denied'):
                db.execute('DELETE FROM requests')
            with closing(sqlite3.connect(self.path, timeout=.01)) as competitor:
                with self.assertRaises(sqlite3.OperationalError):
                    competitor.execute('BEGIN IMMEDIATE')
            guard.verify()
        with closing(sqlite3.connect(self.path, timeout=.01)) as db:
            db.execute('BEGIN IMMEDIATE'); db.rollback()

    def test_mismatched_controller_file_id_closes_helper_before_any_lock(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'helper_controller_ledger_mismatch'):
                self.connection(stack, mismatch=True)
        with closing(sqlite3.connect(self.path, timeout=.01)) as db:
            db.execute('BEGIN IMMEDIATE'); db.rollback()

    def test_mismatched_borrowed_handle_is_rejected_and_never_closed_by_observer(self):
        from contextlib import ExitStack
        fake = self.root/'other/narrator-control.sqlite'; initialize(fake)
        with ExitStack() as stack:
            guard = stack.enter_context(probe.NamespaceGuard(self.path))
            controller = types.SimpleNamespace(candidate={'identity': dict(guard.ledger)}, recheck=guard.verify)
            library = recovery._SqliteLibrary(self.dll, self.pin); stack.callback(library.close)
            handle = guard.native.k.CreateFileW(str(fake), 0x80, 7, None, 3, 0x02000000, None)
            self.assertNotIn(handle, (None, c.c_void_p(-1).value))
            stack.callback(guard.native.k.CloseHandle, handle)
            def wrong_handle(_db, _name, _opcode, output):
                c.cast(output, c.POINTER(probe.HANDLE)).contents.value = handle
                return 0
            with patch.object(library.dll, 'sqlite3_file_control', side_effect=wrong_handle):
                with self.assertRaisesRegex(recovery.RecoveryBlocked, 'helper_controller_ledger_mismatch'):
                    recovery._Connection(library, guard, controller, time.monotonic()+20)
            self.assertNotEqual(probe.identity(guard.native.metadata(handle)), probe.identity(guard.ledger))
            with closing(sqlite3.connect(self.path, timeout=.01)) as db:
                db.execute('BEGIN IMMEDIATE'); db.rollback()

    def test_readwrite_open_readonly_fallback_is_denied(self):
        from contextlib import ExitStack
        native = probe.Native()
        native.k.SetFileAttributesW.argtypes = [c.c_wchar_p, probe.U32]
        native.k.SetFileAttributesW.restype = c.c_int
        self.assertTrue(native.k.SetFileAttributesW(str(self.path), 1))
        with ExitStack() as stack:
            guard = stack.enter_context(probe.NamespaceGuard(self.path))
            controller = types.SimpleNamespace(candidate={'identity': dict(guard.ledger)}, recheck=guard.verify)
            library = recovery._SqliteLibrary(self.dll, self.pin); stack.callback(library.close)
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'helper_sqlite_readonly'):
                recovery._Connection(library, guard, controller, time.monotonic()+20)

    def test_deadline_interrupt_preserves_rollback_and_releases_exact_writer_lock(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            _, db = self.connection(stack)
            db.execute('BEGIN IMMEDIATE')
            db.deadline = time.monotonic()-1
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'recovery_deadline'):
                db.execute('SELECT count(*) FROM requests')
            db.rollback()
            with closing(sqlite3.connect(self.path, timeout=.01)) as competitor:
                competitor.execute('BEGIN IMMEDIATE'); competitor.rollback()

    def test_active_writer_causes_block_without_schema_or_data_mutation(self):
        from contextlib import ExitStack
        before = self.path.read_bytes()
        with closing(sqlite3.connect(self.path, timeout=.01)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            with ExitStack() as stack:
                _, db = self.connection(stack)
                with self.assertRaisesRegex(recovery.RecoveryBlocked, 'recovery_sql_busy_or_failed'):
                    db.execute('BEGIN IMMEDIATE')
            writer.rollback()
        self.assertEqual(self.path.read_bytes(), before)

    def test_closed_wal_header_blocks_before_helper_open(self):
        from contextlib import ExitStack
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone(), ('wal',))
        self.assertFalse(Path(str(self.path)+'-wal').exists())
        before = self.path.read_bytes()
        with ExitStack() as stack:
            guard = stack.enter_context(probe.NamespaceGuard(self.path))
            controller = types.SimpleNamespace(candidate={'identity': dict(guard.ledger)}, recheck=guard.verify)
            library = recovery._SqliteLibrary(self.dll, self.pin); stack.callback(library.close)
            with patch.object(library.dll, 'sqlite3_open_v2') as opening:
                with self.assertRaisesRegex(recovery.RecoveryBlocked, 'format_or_journal_uncertain'):
                    recovery._Connection(library, guard, controller, time.monotonic()+20)
                opening.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_prior_stop_intent_is_never_replayed(self):
        code = definitions(self.root/'receipts'); code['RECEIPTS'].mkdir()
        code.update(SPOOL=self.path.parent, INTENT=self.root/'original/update-intent.private.json')
        code['INTENT'].parent.mkdir()
        marker = code['INTENT'].parent/'empty-stop-intent.private.json'
        marker.write_text('retained original outcome', encoding='utf-8')
        expected = {'owner_sid': 'S-1-5-21-1-2-3-1001', 'python_sha256': 'a'*64, 'task_xml_sha256': 'b'*64}
        with patch.object(recovery, '_snapshot_process') as query:
            with self.assertRaisesRegex(recovery.RecoveryBlocked, 'previous_recovery_outcome'):
                recovery._run(code, expected, self.dll, self.pin)
            query.assert_not_called()
        self.assertEqual(marker.read_text(), 'retained original outcome')
        self.assertEqual(list(code['RECEIPTS'].iterdir()), [])

    def test_each_sidecar_blocks_before_task_query_without_removing_it(self):
        expected = {'owner_sid': 'S-1-5-21-1-2-3-1001', 'python_sha256': 'a'*64, 'task_xml_sha256': 'b'*64}
        for suffix in ('-journal', '-wal', '-shm'):
            folder = self.root/suffix[1:]; path = folder/'spool/narrator-control.sqlite'
            initialize(path)
            code = definitions(folder/'receipts'); code['RECEIPTS'].mkdir()
            code.update(SPOOL=path.parent, INTENT=folder/'original/update-intent.private.json')
            marker = Path(str(path)+suffix); marker.write_bytes(b'uncertain fixture sidecar')
            with patch.object(recovery, '_snapshot_process') as query:
                with self.assertRaisesRegex(recovery.RecoveryBlocked, 'control_database_journal_uncertain'):
                    recovery._run(code, expected, self.dll, self.pin)
                query.assert_not_called()
            self.assertEqual(marker.read_bytes(), b'uncertain fixture sidecar')


@unittest.skipUnless(os.name == 'nt' and os.environ.get('KN_NARRATOR_RECOVERY_FIXTURE') == '1',
                     'root-serialized retained disposable FORGE Limited task')
class NativeBoundRecoveryTests(unittest.TestCase):
    def exercise(self, fault=None):
        from tests import test_collector_narrator_idle_stop as idle
        write_text = Path.write_text
        owner = self
        state = {'actions': [], 'native_stops': 0, 'native': probe.Native(), 'process': None}
        state['native'].k.OpenProcess.argtypes = [probe.U32, c.c_int, probe.U32]
        state['native'].k.OpenProcess.restype = probe.HANDLE

        def instrumented():
            code = definitions(Path('unused'))
            original_stop = code['stop_empty']

            def proposed(expected):
                code['stop_empty'] = original_stop
                code['RECEIPTS'] = code['ROOT']/'recovery-receipts'; code['RECEIPTS'].mkdir()
                state.update(code=code, expected=expected)
                old_call = code['task_call']
                before = code['INTENT'].read_bytes()
                backup = code['INTENT'].parent/'protected-backup.fixture'
                backup.write_bytes(b'original fixture backup')
                if fault == 'wrong-ledger':
                    code['SPOOL'] = code['ROOT']/'wrong-spool'
                    initialize(code['SPOOL']/'narrator-control.sqlite')

                def trace(action, *arguments, **kwargs):
                    state['actions'].append(action)
                    if action == 'stop':
                        if fault == 'before':
                            raise code['Blocked']('task_stop_outcome_unverified')
                        state['native_stops'] += 1
                    result = old_call(action, *arguments, **kwargs)
                    if action == 'query' and state['process'] is None:
                        candidates = [item for item in result['processes']
                            if Path(code['argv'](item['command_line'])[-1]) == code['LAUNCHER']]
                        owner.assertEqual(len(candidates), 1)
                        process = candidates[0]
                        state['pid'] = process['pid']
                        state['process'] = state['native'].k.OpenProcess(0x101000, False, process['pid'])
                        owner.assertTrue(state['process'])
                        times = [probe.FileTime() for _ in range(4)]
                        owner.assertTrue(state['native'].k.GetProcessTimes(state['process'], *[c.byref(t) for t in times]))
                        state['created'] = (times[0].high << 32) | times[0].low
                    if action == 'stop' and fault == 'after':
                        raise code['Blocked']('task_stop_outcome_unverified')
                    return result

                code['task_call'] = trace
                import _sqlite3
                dll = Path(_sqlite3.__file__).with_name('sqlite3.dll')
                pin = hashlib.sha256(dll.read_bytes()).hexdigest()
                try:
                    return recovery._run(code, expected, dll, pin)
                finally:
                    owner.assertEqual(code['INTENT'].read_bytes(), before)
                    owner.assertEqual(backup.read_bytes(), b'original fixture backup')
                    owner.assertFalse((code['INTENT'].parent/'empty-stop-intent.private.json').exists())

            code['stop_empty'] = proposed
            return code

        def fixture_write(path, text, *arguments, **kwargs):
            if path.name == 'narrator-control-launch.py' and path.parent.name == 'runtime':
                database = path.parent.parent/'spool/narrator-control.sqlite'
                owner.assertTrue(text.startswith('import time\nfrom pathlib import Path\nPath('))
                text = ('import sqlite3\n_fixture_db=sqlite3.connect(' + repr(database.as_uri()+'?mode=rw')
                    + ",uri=True)\n_fixture_db.execute('SELECT count(*) FROM requests').fetchone()\n"
                    + ("_fixture_db.execute('BEGIN IMMEDIATE')\n" if fault == 'writer' else '') + text)
            elif path.name == 'exit' and fault is not None and state['process']:
                code, native = state['code'], state['native']
                try:
                    if fault == 'after':
                        owner.assertEqual(native.k.WaitForSingleObject(state['process'], 5000), 0)
                    else:
                        native.running(state['process'], state['created'])
                    times = [probe.FileTime() for _ in range(4)]
                    owner.assertTrue(native.k.GetProcessTimes(state['process'], *[c.byref(t) for t in times]))
                    owner.assertEqual((times[0].high << 32) | times[0].low, state['created'])
                    result = json.loads((code['RECEIPTS']/'recovery-result.private.json').read_text())
                    owner.assertEqual(result['status'], 'BLOCKED')
                    owner.assertEqual(result['stop_intent_present'], fault in ('before', 'after'))
                    with closing(sqlite3.connect(path.parent/'spool/narrator-control.sqlite', timeout=.01)) as db:
                        if fault == 'writer':
                            with owner.assertRaises(sqlite3.OperationalError):
                                db.execute('BEGIN IMMEDIATE')
                        else:
                            db.execute('BEGIN IMMEDIATE'); db.rollback()
                except BaseException as error:
                    state['cleanup_error'] = error
                # Do not prevent the original cooperative exit/task teardown if an assertion fails.
            return write_text(path, text, *arguments, **kwargs)

        retained_temp = types.SimpleNamespace(TemporaryDirectory=lambda: FixtureDirectory(prefix='kn-integrated-task-', trusted_execution=True))
        fixture = idle.NativeIdleStopTests('test_native_limited_task_association_stop_and_disabled_run_denial')
        try:
            with patch.object(idle, 'embedded', instrumented), patch.object(idle, 'tempfile', retained_temp), \
                    patch.object(Path, 'write_text', fixture_write):
                if fault is None:
                    fixture.test_native_limited_task_association_stop_and_disabled_run_denial()
                else:
                    expected = 'controller_ledger_identity_mismatch' if fault == 'wrong-ledger' else (
                        'recovery_sql_busy_or_failed' if fault == 'writer' else 'task_stop_outcome_unverified')
                    with self.assertRaisesRegex(RuntimeError, expected):
                        fixture.test_native_limited_task_association_stop_and_disabled_run_denial()
        finally:
            if state['process']:
                state['native'].k.CloseHandle(state['process'])
        if state.get('cleanup_error') is not None:
            raise state['cleanup_error']
        self.assertEqual(state['native_stops'], 1 if fault in (None, 'after') else 0)
        self.assertEqual(state['actions'], ['query', 'query', 'stop', 'ready'] if fault is None else (
            ['query', 'query', 'stop'] if fault in ('before', 'after') else ['query']))
        code = state['code']
        before_actions = list(state['actions'])
        with self.assertRaisesRegex(recovery.RecoveryBlocked, 'recovery_receipts_not_empty'):
            recovery._run(code, state['expected'], Path('unused'), '0'*64)
        self.assertEqual(state['actions'], before_actions)

    def test_exact_running_controller_and_capi_helper_stop_once_under_same_guard(self):
        self.exercise()

    def test_fault_before_stop_retains_running_controller_and_never_retries(self):
        self.exercise('before')

    def test_lost_ack_after_native_stop_preserves_hold_and_never_retries(self):
        self.exercise('after')

    def test_active_controller_writer_prevents_stop(self):
        self.exercise('writer')

    def test_incorrect_ledger_prevents_helper_open_and_stop(self):
        self.exercise('wrong-ledger')


if __name__ == '__main__':
    unittest.main()
