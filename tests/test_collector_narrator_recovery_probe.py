"""Isolated Windows evidence fixtures; never inspect or stop the live host task."""
import ctypes as c
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from youtube_ops import collector_narrator_recovery_probe as probe


CHILD = r"""
import os,sqlite3,sys
connection=sqlite3.connect(sys.argv[1],timeout=.1)
connection.execute('CREATE TABLE IF NOT EXISTS fixture(value TEXT)');connection.commit()
print(os.getpid(),flush=True)
for line in sys.stdin:
    command=line.strip()
    if command=='exit':break
    if command=='lock':connection.execute('BEGIN IMMEDIATE')
    elif command=='unlock':connection.rollback()
    elif command=='close':connection.close()
    else:raise RuntimeError('invalid fixture command')
    print('DONE',flush=True)
connection.close()
"""


class ProbeContractTests(unittest.TestCase):
    def test_nonwindows_fails_without_native_loading(self):
        with patch.object(probe.os, 'name', 'posix'):
            with self.assertRaisesRegex(probe.ProbeBlocked, 'native_64bit_windows_required'):
                probe.Native()

    def test_module_has_no_execution_entry_or_mutating_api(self):
        source = Path(probe.__file__).read_text(encoding='utf-8')
        for denied in ('OpenProcess(', 'ReadFile(', 'WriteFile(', 'TerminateProcess',
                       'AdjustTokenPrivileges', 'SetSecurityInfo', '__main__', 'sqlite3.connect'):
            self.assertNotIn(denied, source)
        self.assertEqual(c.sizeof(probe.FileInformation), 52)
        self.assertEqual(c.sizeof(probe.FileId), 24)


@unittest.skipUnless(os.name == 'nt' and c.sizeof(c.c_void_p) == 8, 'Native Windows x64 evidence')
class NativeRecoveryProbeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='kn-recovery-probe-')
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.spool = self.root / 'kit' / 'spool'
        self.spool.mkdir(parents=True)
        self.path = self.spool / 'narrator-control.sqlite'
        self.native = probe.Native()
        self.native.k.OpenProcess.argtypes = [probe.U32, c.c_int, probe.U32]
        self.native.k.OpenProcess.restype = probe.HANDLE
        self.child = subprocess.Popen([getattr(sys, '_base_executable', sys.executable),
            '-u', '-c', CHILD, str(self.path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.addCleanup(self.cleanup_child)
        self.assertEqual(int(self.child.stdout.readline()), self.child.pid)
        self.process = self.native.k.OpenProcess(0x100440, False, self.child.pid)
        self.assertTrue(self.process)
        self.addCleanup(lambda: self.native.k.CloseHandle(self.process))
        values = [probe.FileTime() for _ in range(4)]
        self.assertTrue(self.native.k.GetProcessTimes(self.process, *[c.byref(v) for v in values]))
        self.created = (values[0].high << 32) | values[0].low

    def cleanup_child(self):
        if self.child.poll() is None:
            try:
                self.child.stdin.write('exit\n');self.child.stdin.flush()
                self.child.wait(timeout=5)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.child.kill();self.child.wait(timeout=5)
        for stream in (self.child.stdin, self.child.stdout, self.child.stderr):
            stream.close()

    def command(self, value):
        self.child.stdin.write(value + '\n');self.child.stdin.flush()
        self.assertEqual(self.child.stdout.readline().strip(), 'DONE')

    def count_handles(self):
        count = probe.U32()
        self.assertTrue(self.native.k.GetProcessHandleCount(self.native.k.GetCurrentProcess(), c.byref(count)))
        return count.value

    def test_actual_running_controller_file_identity_and_sqlite_lock_coexist(self):
        with probe.NamespaceGuard(self.path) as guard:
            before = self.count_handles()
            with probe.LedgerBinding(self.process, self.created, guard) as binding:
                self.assertEqual(probe.identity(binding.candidate['identity']), probe.identity(guard.ledger))
                self.assertTrue(binding.candidate['path'].endswith('narrator-control.sqlite'))
                self.assertLessEqual(binding.candidate['snapshot_handles'], 512)
                self.assertIsInstance(binding.candidate['unsupported_handles'], tuple)
                with closing(sqlite3.connect(self.path, timeout=.01)) as writer:
                    writer.execute('BEGIN IMMEDIATE')
                    binding.recheck()
                    with closing(sqlite3.connect(self.path, timeout=.01)) as competitor:
                        with self.assertRaises(sqlite3.OperationalError):
                            competitor.execute('BEGIN IMMEDIATE')
                    writer.rollback()
            self.assertEqual(self.count_handles(), before)
        with self.assertRaisesRegex(probe.ProbeBlocked, 'namespace_guard_closed'):
            guard.verify()

    def test_fake_ledger_after_directory_rename_is_not_controllers_actual_file(self):
        old = self.root / 'old-kit'
        # SQLite's normal live handle prevents a rename: a guard is not historical proof.
        try:
            self.spool.parent.rename(old)
        except PermissionError:
            # Move a different empty namespace into the expected location instead.
            other = self.root / 'replacement' / 'spool'
            other.mkdir(parents=True)
            fake = other / 'narrator-control.sqlite'
        else:
            self.spool.mkdir(parents=True)
            fake = self.path
        with closing(sqlite3.connect(fake)) as db:
            db.execute('CREATE TABLE fixture(value TEXT)')
        with probe.NamespaceGuard(fake) as guard:
            with self.assertRaisesRegex(probe.ProbeBlocked, 'controller_ledger_identity_mismatch'):
                probe.LedgerBinding(self.process, self.created, guard)

    def test_guard_blocks_ordinary_ancestor_leaf_rename_and_detects_hardlink(self):
        with probe.NamespaceGuard(self.path) as guard:
            for old, new in [(self.spool.parent, self.root/'renamed-kit'),
                             (self.path, self.spool/'renamed.sqlite')]:
                with self.assertRaises(OSError):
                    old.rename(new)
            guard.verify()
        linked = self.spool/'linked.sqlite'
        with probe.NamespaceGuard(self.path) as guard:
            os.link(self.path, linked)
            with self.assertRaisesRegex(probe.ProbeBlocked, 'held_namespace_changed'):
                guard.verify()
        linked.unlink()
        os.link(self.path, linked)
        with self.assertRaisesRegex(probe.ProbeBlocked, 'namespace_object_unverified'):
            probe.NamespaceGuard(self.path)
        linked.unlink()

    def test_contention_and_exit_are_blocked_without_replay_or_task_action(self):
        self.command('lock')
        with probe.NamespaceGuard(self.path) as guard, probe.LedgerBinding(self.process, self.created, guard) as binding:
            with closing(sqlite3.connect(self.path, timeout=.01)) as writer:
                with self.assertRaises(sqlite3.OperationalError):
                    writer.execute('BEGIN IMMEDIATE')
            self.command('unlock')
            self.child.stdin.write('exit\n');self.child.stdin.flush();self.child.wait(timeout=5)
            with self.assertRaisesRegex(probe.ProbeBlocked, 'process_identity_changed_or_exited'):
                binding.recheck()
        with closing(sqlite3.connect(self.path, timeout=.01)) as db:
            db.execute('BEGIN IMMEDIATE');db.rollback()

    def test_probe_duplicates_do_not_release_the_running_controllers_sqlite_lock(self):
        self.command('lock')
        with probe.NamespaceGuard(self.path) as guard:
            with probe.LedgerBinding(self.process, self.created, guard) as binding:
                binding.recheck()
            with closing(sqlite3.connect(self.path, timeout=.01)) as writer:
                with self.assertRaises(sqlite3.OperationalError):
                    writer.execute('BEGIN IMMEDIATE')
            self.command('unlock')
            with closing(sqlite3.connect(self.path, timeout=.01)) as writer:
                writer.execute('BEGIN IMMEDIATE');writer.rollback()

    def test_wrong_creation_missing_rights_deadline_and_cleanup_fail_closed(self):
        before = self.count_handles()
        with probe.NamespaceGuard(self.path) as guard:
            with self.assertRaisesRegex(probe.ProbeBlocked, 'process_identity_changed_or_exited'):
                probe.LedgerBinding(self.process, self.created + 1, guard)
            with self.assertRaisesRegex(probe.ProbeBlocked, 'probe_deadline'):
                probe._ledger_handles(self.native, self.process, self.created, time.monotonic() - 1)
            limited = self.native.k.OpenProcess(0x101000, False, self.child.pid)
            try:
                with self.assertRaisesRegex(probe.ProbeBlocked, 'handle_snapshot_unavailable') as blocked:
                    probe.LedgerBinding(limited, self.created, guard)
                self.assertEqual(blocked.exception.winerror, 5)
            finally:
                self.native.k.CloseHandle(limited)
        self.assertEqual(self.count_handles(), before)

    def test_unsupported_set_change_or_access_denial_is_not_treated_as_complete(self):
        with probe.NamespaceGuard(self.path) as guard:
            original = probe._ledger_handles
            for field in ('unsupported_handles', 'unknown_file_handles'):
                calls = 0
                def changed(*arguments):
                    nonlocal calls
                    result = original(*arguments);calls += 1
                    if calls == 2:
                        result[field] += (0x123456,)
                    return result
                with patch.object(probe, '_ledger_handles', side_effect=changed):
                    with self.assertRaisesRegex(probe.ProbeBlocked, 'controller_ledger_identity_mismatch'):
                        probe.LedgerBinding(self.process, self.created, guard)
            # A captured regular file that cannot be duplicated must not be skipped.
            for error in (5, 6):
                with patch.object(self.native.k, 'DuplicateHandle', side_effect=lambda *_, code=error: (c.set_last_error(code), 0)[1]):
                    with self.assertRaisesRegex(probe.ProbeBlocked, 'source_handle_changed') as blocked:
                        probe._ledger_handles(self.native, self.process, self.created, time.monotonic() + 5)
                    self.assertEqual(blocked.exception.winerror, error)
            with patch.object(self.native.k, 'GetFileType', side_effect=lambda *_: (c.set_last_error(5), 0)[1]):
                with self.assertRaisesRegex(probe.ProbeBlocked, 'duplicated_handle_type_unverified'):
                    probe._ledger_handles(self.native, self.process, self.created, time.monotonic() + 5)

    def test_guarded_namespace_rejects_reparse(self):
        # Junction creation uses only the brand-new disposable test namespace.
        target = self.root / 'target';target.mkdir()
        junction = self.root / 'junction'
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(target)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 0)
        try:
            with closing(sqlite3.connect(target/'narrator-control.sqlite')) as db:
                db.execute('CREATE TABLE fixture(value TEXT)')
            with self.assertRaisesRegex(probe.ProbeBlocked, 'reparse_object_denied'):
                probe.NamespaceGuard(junction/'narrator-control.sqlite')
        finally:
            os.rmdir(junction)

    def rename_posix(self, source, target):
        self.native.k.SetFileInformationByHandle.argtypes = [probe.HANDLE, c.c_int, probe.HANDLE, probe.U32]
        self.native.k.SetFileInformationByHandle.restype = c.c_int
        handle = self.native.k.CreateFileW(str(source), 0x10080, 7, None, 3, 0x02000000, None)
        if handle in (None, c.c_void_p(-1).value):
            return False, c.get_last_error()
        name = str(target).encode('utf-16-le')
        class Rename(c.Structure):
            _fields_ = [('flags', probe.U32), ('root', probe.HANDLE), ('length', probe.U32), ('name', c.c_ubyte * (len(name) + 2))]
        self.assertEqual((Rename.root.offset, Rename.length.offset, Rename.name.offset), (8, 16, 20))
        # Terminate the Win32 name explicitly; alignment padding varies with path length.
        terminated = (c.c_ubyte * (len(name) + 2))()
        c.memmove(terminated, name, len(name))
        info = Rename(3, None, len(name), terminated)
        self.assertEqual(bytes(info.name)[-2:], b'\0\0')
        try:
            succeeded = bool(self.native.k.SetFileInformationByHandle(handle, 22, c.byref(info), c.sizeof(info)))
            return succeeded, 0 if succeeded else c.get_last_error()
        finally:
            self.native.k.CloseHandle(handle)

    def test_posix_rename_capability_and_guarded_source_and_targets(self):
        # A successful unguarded replacement proves flags/structure/API support.
        boundary_covered = False
        for suffix in range(4):
            control_source = self.root/('control-source' + '_' * suffix)
            control_target = self.root/('control-target' + '_' * suffix)
            payload = b'new-' + str(suffix).encode('ascii')
            control_source.write_bytes(payload);control_target.write_bytes(b'old')
            with probe.NamespaceGuard(control_source) as source_guard:
                source_identity = probe.identity(source_guard.ledger)
            # The old exact-length WCHAR payload has no implicit trailing padding here.
            byte_length = len(str(control_target).encode('utf-16-le'))
            if (20 + byte_length) % 8 == 0:
                class LegacyUnterminated(c.Structure):
                    _fields_ = [('flags', probe.U32), ('root', probe.HANDLE), ('length', probe.U32),
                                ('name', c.c_ubyte * byte_length)]
                legacy = LegacyUnterminated(3, None, byte_length,
                    (c.c_ubyte * byte_length).from_buffer_copy(str(control_target).encode('utf-16-le')))
                self.assertEqual(c.sizeof(legacy), 20 + byte_length)
                self.assertNotEqual(bytes(legacy.name)[-2:], b'\0\0')
                boundary_covered = True
            supported, error = self.rename_posix(control_source, control_target)
            if suffix == 0 and not supported and error in (1, 50, 87):
                self.skipTest('POSIX rename API/flags unavailable on this Windows fixture')
            self.assertTrue(supported, 'Unguarded POSIX rename positive control failed: ' + str(error))
            self.assertEqual(control_target.read_bytes(), payload)
            self.assertFalse(control_source.exists())
            with probe.NamespaceGuard(control_target) as target_guard:
                self.assertEqual(probe.identity(target_guard.ledger), source_identity)
        self.assertTrue(boundary_covered, 'Positive controls must exercise the no-padding WCHAR boundary')
        source = self.spool / 'replacement.sqlite'
        source.write_bytes(b'replacement fixture')
        replacement_directory = self.root / 'replacement-directory'
        replacement_directory.mkdir()
        with probe.NamespaceGuard(self.path) as guard:
            for old, new in ((self.path, self.spool/'renamed.sqlite'),
                             (self.spool.parent, self.root/'renamed-kit')):
                succeeded, error = self.rename_posix(old, new)
                self.assertFalse(succeeded)
                self.assertIn(error, (5, 32))
                guard.verify()
            succeeded, error = self.rename_posix(replacement_directory, self.spool.parent)
            self.assertFalse(succeeded)
            self.assertIn(error, (5, 32, 145, 183))
            guard.verify()
            succeeded, error = self.rename_posix(source, self.path)
            if succeeded:
                with self.assertRaisesRegex(probe.ProbeBlocked, 'namespace_replaced'):
                    guard.verify()
            else:
                self.assertIn(error, (5, 32))
                guard.verify()


if __name__ == '__main__':
    unittest.main()
