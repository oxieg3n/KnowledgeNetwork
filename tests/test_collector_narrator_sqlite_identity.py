"""Disposable public SQLite C-API identity proof; no production helper changes."""
from tests.fixture_retention import FixtureDirectory
import ctypes as c
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import unittest

from youtube_ops import collector_narrator_recovery_probe as probe


class FixtureConnection:
    """Only owns connections opened here, never CPython's private connection memory."""
    def __init__(self, path):
        import _sqlite3
        self.dll_path = Path(_sqlite3.__file__).with_name('sqlite3.dll')
        self.dll = c.CDLL(str(self.dll_path))
        signatures = {
            'sqlite3_open_v2': ([c.c_char_p, c.POINTER(c.c_void_p), c.c_int, c.c_char_p], c.c_int),
            'sqlite3_file_control': ([c.c_void_p, c.c_char_p, c.c_int, c.c_void_p], c.c_int),
            'sqlite3_exec': ([c.c_void_p, c.c_char_p, c.c_void_p, c.c_void_p, c.c_void_p], c.c_int),
            'sqlite3_close_v2': ([c.c_void_p], c.c_int),
            'sqlite3_libversion': ([], c.c_char_p),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.dll, name)
            function.argtypes, function.restype = arguments, result
        if self.dll.sqlite3_libversion().decode('ascii') != sqlite3.sqlite_version:
            raise AssertionError('C-API library differs from the installed standard library')
        self.db = c.c_void_p()
        # READWRITE only: a typo must never create a replacement ledger.
        status = self.dll.sqlite3_open_v2(str(path).encode('utf-8'), c.byref(self.db), 2, None)
        if status:
            self.close()
            raise AssertionError('Fixture READWRITE connection failed: ' + str(status))
        try:
            if self.execute('PRAGMA schema_version'):
                raise AssertionError('Fixture database initialization failed')
        except BaseException:
            self.close()
            raise

    def execute(self, sql):
        return self.dll.sqlite3_exec(self.db, sql.encode('ascii'), None, None, None)

    def main_handle(self):
        handle = probe.HANDLE()
        # Public SQLITE_FCNTL_WIN32_GET_HANDLE; borrowed, SQLite alone closes it.
        status = self.dll.sqlite3_file_control(self.db, b'main', 29, c.byref(handle))
        if status or handle.value in (None, c.c_void_p(-1).value):
            raise AssertionError('Public SQLite handle control failed: ' + str(status))
        return handle.value

    def close(self):
        if self.db:
            if self.dll.sqlite3_close_v2(self.db):
                raise AssertionError('Fixture SQLite close failed')
            self.db = c.c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


@unittest.skipUnless(os.name == 'nt' and c.sizeof(c.c_void_p) == 8, 'Windows x64 bundled SQLite VFS')
class SqliteConnectionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.folder = FixtureDirectory(prefix='kn-sqlite-identity-', trusted_execution=True)
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / 'narrator-control.sqlite'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE fixture(value TEXT)')
            db.execute("INSERT INTO fixture VALUES('original')")

    def test_public_connection_handle_matches_guard_established_before_sqlite_open(self):
        with probe.NamespaceGuard(self.path) as guard:
            with FixtureConnection(self.path) as connection:
                actual = guard.native.metadata(connection.main_handle())
                self.assertEqual(probe.identity(actual), probe.identity(guard.ledger))
                guard.verify()
            guard.verify()

    def test_wrong_connection_cannot_be_hidden_by_matching_basename_and_decoy_handle(self):
        fake = self.root / 'other' / 'narrator-control.sqlite'
        fake.parent.mkdir()
        with closing(sqlite3.connect(fake)) as db:
            db.execute('CREATE TABLE unrelated(value TEXT)')
        with probe.NamespaceGuard(self.path) as guard, self.path.open('rb') as decoy:
            self.assertFalse(decoy.closed)
            with FixtureConnection(fake) as connection:
                actual = guard.native.metadata(connection.main_handle())
                self.assertNotEqual(probe.identity(actual), probe.identity(guard.ledger))
                guard.verify()

    def test_exact_connection_writer_lock_contention_and_actual_write_rollback(self):
        with probe.NamespaceGuard(self.path) as guard, FixtureConnection(self.path) as connection:
            self.assertEqual(connection.execute('BEGIN IMMEDIATE'), 0)
            self.assertEqual(probe.identity(guard.native.metadata(connection.main_handle())),
                             probe.identity(guard.ledger))
            with closing(sqlite3.connect(self.path, timeout=.01)) as other:
                with self.assertRaises(sqlite3.OperationalError):
                    other.execute('BEGIN IMMEDIATE')
            self.assertEqual(connection.execute("INSERT INTO fixture VALUES('must rollback')"), 0)
            guard.verify()
            self.assertEqual(connection.execute('ROLLBACK'), 0)
            self.assertEqual(probe.identity(guard.native.metadata(connection.main_handle())),
                             probe.identity(guard.ledger))
        with closing(sqlite3.connect(self.path, timeout=.01)) as db:
            self.assertEqual(db.execute('SELECT value FROM fixture').fetchall(), [('original',)])
            db.execute('BEGIN IMMEDIATE');db.rollback()
