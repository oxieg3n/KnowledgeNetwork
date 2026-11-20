"""Retain only freshly owned test namespaces; never delete or auto-archive them."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid
from datetime import datetime, timezone


PRIVATE = Path(__file__).resolve().parents[2] / 'KnowledgeNetwork-Private'
OWNED_ROOTS = set()


class FixtureDirectory:
    """TemporaryDirectory-shaped fixture with explicit, non-destructive teardown.

    Callers close their processes/tasks/handles first. The receipt makes no claim
    that a namespace is obsolete or safe to move; that requires separate review.
    """
    def __init__(self, prefix='kn-retained-', *, trusted_execution=False, dir=None):
        if not prefix.startswith('kn-') or any(c in prefix for c in '/\\:'):
            raise ValueError('Bounded project fixture prefix required')
        if type(trusted_execution) is not bool:
            raise ValueError('Explicit fixture execution classification required')
        self.trusted_execution = trusted_execution
        # Projects has writable ancestors. Executed fixture scripts stay in the
        # owner's protected OS temp namespace; their retained index stays here.
        if dir is not None and not trusted_execution:
            raise ValueError('Custom fixture placement requires explicit execution classification')
        directory = dir
        if not trusted_execution:
            directory = PRIVATE / 'fixtures'
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.name = tempfile.mkdtemp(prefix=prefix, dir=directory)
        OWNED_ROOTS.add(Path(self.name).absolute())
        self._identity = self._id(Path(self.name).lstat())
        self.receipt = None
        self.outcome = 'See test runner result'

    @staticmethod
    def _id(info):
        return info.st_dev, info.st_ino

    def cleanup(self):
        if self.receipt is not None:
            return
        root = Path(self.name)
        record = {'schema_version': 1, 'status': 'RETAINED_PENDING_REFERENCE_REVIEW',
                  'original_path': str(root), 'archive_performed': False,
                  'deletion_performed': False, 'outcome': self.outcome,
                  'trusted_execution_namespace_requested': self.trusted_execution,
                  'recorded_at': datetime.now(timezone.utc).isoformat(), 'files': []}
        total = 0
        try:
            initial = root.lstat()
            reparse = stat.S_ISLNK(initial.st_mode) or getattr(initial, 'st_file_attributes', 0) & 0x400
            if self._id(initial) != self._identity or reparse:
                raise ValueError('fixture_root_identity_changed')
            for folder, directories, files in os.walk(root, followlinks=False):
                for name in list(directories):
                    path = Path(folder) / name
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                        directories.remove(name)
                        files.append(name)
                for name in files:
                    if len(record['files']) >= 256:
                        raise ValueError('fixture_inventory_bound')
                    path = Path(folder) / name
                    before = path.lstat()
                    entry = {'relative_path': str(path.relative_to(root)), 'size': before.st_size,
                             'links': before.st_nlink, 'sha256': None}
                    if stat.S_ISLNK(before.st_mode) or getattr(before, 'st_file_attributes', 0) & 0x400:
                        entry['status'] = 'REPARSE_RETAINED_NOT_FOLLOWED'
                    elif stat.S_ISREG(before.st_mode):
                        total += before.st_size
                        if before.st_size > 16 * 1024 * 1024 or total > 64 * 1024 * 1024:
                            raise ValueError('fixture_hash_bound')
                        digest = hashlib.sha256()
                        with path.open('rb') as stream:
                            remaining = 16 * 1024 * 1024 + 1
                            while remaining:
                                data = stream.read(min(65536, remaining))
                                if not data:
                                    break
                                digest.update(data)
                                remaining -= len(data)
                            if not remaining:
                                raise ValueError('fixture_hash_bound')
                        after = path.lstat()
                        if (self._id(before), before.st_size, before.st_mtime_ns) != (self._id(after), after.st_size, after.st_mtime_ns):
                            raise ValueError('fixture_file_changed')
                        entry['sha256'] = digest.hexdigest()
                        entry['status'] = 'RETAINED'
                    else:
                        entry['status'] = 'NONREGULAR_RETAINED'
                    record['files'].append(entry)
        except (OSError, ValueError) as error:
            record['status'] = 'RETAINED_INSPECTION_INCOMPLETE'
            record['error_class'] = type(error).__name__
        directory = PRIVATE / 'fixture-retention'
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = directory / (uuid.uuid4().hex + '.private.json')
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        self.receipt = destination

    def __enter__(self):
        return self.name

    def __exit__(self, error_type, *_):
        self.outcome = 'PASS' if error_type is None else error_type.__name__
        self.cleanup()


def retain_fixture_entry(path):
    """Move one fresh fixture entry aside to simulate absence; never follow links.

    This is explicit test fault injection, not an obsolete-file archive or a
    cleanup operation. Only namespaces created by this process are eligible.
    """
    import ctypes
    path = Path(path).absolute()
    roots = [root for root in OWNED_ROOTS if path.is_relative_to(root) and path != root]
    if not roots:
        raise ValueError('Entry is not in a freshly owned fixture')
    root = max(roots, key=lambda value: len(value.parts))
    for parent in path.parents:
        item = parent.lstat()
        if stat.S_ISLNK(item.st_mode) or getattr(item, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Fixture parent is a reparse point')
        if parent == root:
            break
    def metadata(entry):
        info = entry.lstat()
        security = None
        if os.name == 'nt':
            # Reparse entry security is retained by same-volume rename. Querying
            # it by path would follow a possibly deliberately broken test link.
            if not (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400):
                get = ctypes.WinDLL('advapi32', use_last_error=True).GetFileSecurityW
                get.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p,
                                ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
                get.restype = ctypes.c_int
                size = ctypes.c_uint32()
                get(str(entry), 7, None, 0, ctypes.byref(size))
                if not 0 < size.value <= 65536:
                    raise ValueError('Fixture security unavailable')
                data = ctypes.create_string_buffer(size.value)
                if not get(str(entry), 7, data, len(data), ctypes.byref(size)):
                    raise ValueError('Fixture security unavailable')
                security = hashlib.sha256(data.raw[:size.value]).hexdigest()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            content = {'link': os.readlink(entry)}
        elif stat.S_ISREG(info.st_mode) and info.st_size <= 16 * 1024 * 1024:
            content = {'sha256': hashlib.sha256(entry.read_bytes()).hexdigest()}
        else:
            raise ValueError('Fixture entry type or size unsupported')
        return {'identity': [info.st_dev, info.st_ino], 'size': info.st_size,
                'mode': info.st_mode, 'owner': info.st_uid, 'group': info.st_gid,
                'security_sha256': security, **content}
    before = metadata(path)
    destination_root = root / ('.fixture-state-retained-' + uuid.uuid4().hex)
    destination_root.mkdir()
    target = destination_root / path.name
    path.rename(target)
    if metadata(target) != before:
        raise ValueError('Retained fixture entry changed; preserve both paths for review')
    with (destination_root / 'retention.private.json').open('x', encoding='utf-8') as stream:
        json.dump({'original': str(path), 'retained': str(target), 'metadata': before,
                   'reason': 'explicit absence/replacement fault injection',
                   'archive_performed': False, 'deletion_performed': False}, stream)
    return target
