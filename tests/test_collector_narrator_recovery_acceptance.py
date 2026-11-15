"""Opt-in composition on a disposable FORGE Limited task, never BLACKHAT-BASE."""
import ctypes as c
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from youtube_ops import collector_narrator_recovery_probe as probe
from tests import test_collector_narrator_idle_stop as idle


@unittest.skipUnless(os.name == 'nt' and os.environ.get('KN_NARRATOR_IDLE_STOP_FIXTURE') == '1',
                     'opt-in disposable FORGE Limited task, never host/narration')
class ComposedRecoveryAcceptanceTests(unittest.TestCase):
    def exercise_existing_native_fixture(self, fault=None):
        factory, write_text = idle.embedded, Path.write_text
        owner = self
        state = {'stop_attempts': 0, 'actual_stop_calls': 0, 'bound': False, 'rollback': False,
                 'verify_process': None, 'native': None, 'actions': []}
        codes = []

        def instrumented():
            code = factory(); codes.append(code)
            original_held, original_call = code['HeldProcess'], code['task_call']

            class BoundController(original_held):
                def __init__(self, *arguments):
                    self.guard = self.binding = self.probe_process = self.native = None
                    super().__init__(*arguments)
                    try:
                        self.native = probe.Native()
                        self.native.k.OpenProcess.argtypes = [probe.U32, c.c_int, probe.U32]
                        self.native.k.OpenProcess.restype = probe.HANDLE
                        self.probe_process = self.native.k.OpenProcess(0x100440, False, self.pid)
                        owner.assertTrue(self.probe_process)
                        self.guard = probe.NamespaceGuard(code['SPOOL'] / 'narrator-control.sqlite')
                        self.binding = probe.LedgerBinding(self.probe_process, self.created, self.guard)
                        state.update(bound=True, controller=self, pid=self.pid, created=self.created)
                        state['native'] = self.native
                        state['verify_process'] = self.native.k.OpenProcess(0x101000, False, self.pid)
                        owner.assertTrue(state['verify_process'])
                        self.native.running(state['verify_process'], self.created)
                    except BaseException:
                        self.close(); raise

                def close(self):
                    if self.binding is not None:
                        self.binding.close(); self.binding = None
                    if self.guard is not None:
                        self.guard.close(); self.guard = None
                    if self.probe_process:
                        self.native.k.CloseHandle(self.probe_process); self.probe_process = None
                    super().close()

            def task_call(action, *arguments, **options):
                state['actions'].append(action)
                with closing(sqlite3.connect(code['SPOOL'] / 'narrator-control.sqlite', timeout=.01)) as other:
                    with owner.assertRaises(sqlite3.OperationalError):
                        other.execute('BEGIN IMMEDIATE')
                if action == 'stop':
                    state['stop_attempts'] += 1
                    owner.assertEqual(state['stop_attempts'], 1)
                    owner.assertTrue(state['bound'])
                    state['controller'].binding.recheck()
                    if fault == 'before':
                        # Fault injection occurs before the real Scheduler call.
                        raise code['Blocked']('task_stop_outcome_unverified')
                    state['actual_stop_calls'] += 1
                result = original_call(action, *arguments, **options)
                if action == 'stop' and fault == 'after':
                    # The native Scheduler stop occurred; its acknowledgement is lost.
                    raise code['Blocked']('task_stop_outcome_unverified')
                return result

            code.update(HeldProcess=BoundController, task_call=task_call)
            return code

        def fixture_write(path, text, *arguments, **options):
            if path.name == 'narrator-control-launch.py' and path.parent.name == 'runtime':
                self.assertTrue(text.startswith('import time\nfrom pathlib import Path\nPath('))
                database = path.parent.parent / 'spool/narrator-control.sqlite'
                text = ('import sqlite3\n_fixture_db=sqlite3.connect(' + repr(database.as_uri() + '?mode=rw')
                        + ",uri=True)\n_fixture_db.execute('SELECT count(*) FROM requests').fetchone()\n" + text)
            elif path.name == 'exit' and fault is not None and state['stop_attempts']:
                code = codes[0]; native = state['controller'].native
                if fault == 'before':
                    native.running(state['verify_process'], state['created'])
                else:
                    self.assertEqual(native.k.WaitForSingleObject(state['verify_process'], 5000), 0)
                    times = [probe.FileTime() for _ in range(4)]
                    self.assertTrue(native.k.GetProcessTimes(state['verify_process'], *[c.byref(t) for t in times]))
                    self.assertEqual((times[0].high << 32) | times[0].low, state['created'])
                with closing(sqlite3.connect(code['SPOOL'] / 'narrator-control.sqlite', timeout=.01)) as db:
                    db.execute('BEGIN IMMEDIATE'); db.rollback()
                intent = json.loads((code['INTENT'].parent / 'empty-stop-intent.private.json').read_text())
                self.assertEqual(intent['stop_attempts'], 1)
                state['rollback'] = True
            return write_text(path, text, *arguments, **options)

        fixture = idle.NativeIdleStopTests('test_native_limited_task_association_stop_and_disabled_run_denial')
        try:
            with patch.object(idle, 'embedded', instrumented), patch.object(Path, 'write_text', fixture_write):
                if fault is not None:
                    with self.assertRaisesRegex(RuntimeError, 'task_stop_outcome_unverified'):
                        fixture.test_native_limited_task_association_stop_and_disabled_run_denial()
                else:
                    fixture.test_native_limited_task_association_stop_and_disabled_run_denial()
        finally:
            if state['verify_process']:
                state['native'].k.CloseHandle(state['verify_process'])
        self.assertTrue(state['bound'])
        self.assertEqual(state['stop_attempts'], 1)
        self.assertEqual(state['actual_stop_calls'], 0 if fault == 'before' else 1)
        self.assertEqual(state['actions'], ['query', 'stop'] if fault else ['query', 'stop', 'ready'])
        if fault is not None:
            self.assertTrue(state['rollback'])

    def test_bound_limited_controller_stops_once_with_namespace_and_writer_lock_held(self):
        self.exercise_existing_native_fixture()

    def test_uncertain_stop_reply_retains_live_controller_and_rolls_back_writer_lock(self):
        self.exercise_existing_native_fixture('before')

    def test_lost_acknowledgement_after_native_stop_preserves_exit_proof_without_retry(self):
        self.exercise_existing_native_fixture('after')


if __name__ == '__main__':
    unittest.main()
