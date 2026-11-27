"""Read-only recovery evidence, never a stop/repair authorization or remote endpoint.

Callers must first bind the supplied held process handle to the fixed task,
owner, pinned image and canonical controller (one self.db opened until exit).
Namespace retention does not replace strict handle-based owner/DACL checks.
PSS snapshots contain values, not atomic process ownership. Two matching sweeps,
retained duplicate and the canonical persistent-connection invariant are required.
Timeouts are cooperative checks; synchronous native metadata calls can block.
Native APIs: learn.microsoft.com/windows/win32/api/processsnapshot/ and
learn.microsoft.com/windows/win32/api/fileapi/nf-fileapi-createfilew.
"""
import ctypes as c
import os
from pathlib import Path
import time


class ProbeBlocked(RuntimeError):
    def __init__(self, code, winerror=None):
        super().__init__(code)
        self.winerror = winerror


U32, U64, HANDLE = c.c_uint32, c.c_uint64, c.c_void_p


class FileTime(c.Structure):
    _fields_ = [('low', U32), ('high', U32)]


class FileInformation(c.Structure):
    _fields_ = [('attributes', U32), ('created', FileTime), ('access', FileTime),
                ('write', FileTime), ('volume', U32), ('size_high', U32),
                ('size_low', U32), ('links', U32), ('index_high', U32), ('index_low', U32)]


class FileId(c.Structure):
    _fields_ = [('volume', U64), ('identifier', c.c_ubyte * 16)]


class HandleEntry(c.Structure):
    _fields_ = [('handle', HANDLE), ('flags', U32), ('object_type', U32),
                ('captured', FileTime), ('attributes', U32), ('access', U32),
                ('handle_count', U32), ('pointer_count', U32), ('paged_pool', U32),
                ('nonpaged_pool', U32), ('created', FileTime), ('type_length', c.c_uint16),
                ('type_name', HANDLE), ('name_length', c.c_uint16), ('name', HANDLE),
                ('type_specific', c.c_ubyte * 48)]


class Native:
    def __init__(self):
        if os.name != 'nt' or c.sizeof(HANDLE) != 8:
            raise ProbeBlocked('native_64bit_windows_required')
        if c.sizeof(HandleEntry) != 136 or c.sizeof(FileInformation) != 52 or c.sizeof(FileId) != 24:
            raise ProbeBlocked('native_layout_unverified')
        self.k = c.WinDLL('kernel32', use_last_error=True)
        definitions = {
            'CreateFileW': ([c.c_wchar_p, U32, U32, HANDLE, U32, U32, HANDLE], HANDLE),
            'CloseHandle': ([HANDLE], c.c_int),
            'GetFileType': ([HANDLE], U32),
            'GetFileInformationByHandle': ([HANDLE, c.POINTER(FileInformation)], c.c_int),
            'GetFileInformationByHandleEx': ([HANDLE, c.c_int, HANDLE, U32], c.c_int),
            'GetFinalPathNameByHandleW': ([HANDLE, c.c_wchar_p, U32, U32], U32),
            'GetProcessTimes': ([HANDLE] + [c.POINTER(FileTime)] * 4, c.c_int),
            'WaitForSingleObject': ([HANDLE, U32], U32),
            'GetProcessHandleCount': ([HANDLE, c.POINTER(U32)], c.c_int),
            'GetCurrentProcess': ([], HANDLE),
            'DuplicateHandle': ([HANDLE, HANDLE, HANDLE, c.POINTER(HANDLE), U32, c.c_int, U32], c.c_int),
            'PssCaptureSnapshot': ([HANDLE, U32, U32, c.POINTER(HANDLE)], U32),
            'PssQuerySnapshot': ([HANDLE, c.c_int, HANDLE, U32], U32),
            'PssWalkMarkerCreate': ([HANDLE, c.POINTER(HANDLE)], U32),
            'PssWalkMarkerFree': ([HANDLE], U32),
            'PssWalkSnapshot': ([HANDLE, c.c_int, HANDLE, HANDLE, U32], U32),
            'PssFreeSnapshot': ([HANDLE, HANDLE], U32),
        }
        try:
            for name, (arguments, result) in definitions.items():
                function = getattr(self.k, name)
                function.argtypes, function.restype = arguments, result
        except AttributeError:
            raise ProbeBlocked('native_snapshot_api_unavailable') from None

    def metadata(self, handle):
        info, identity = FileInformation(), FileId()
        if (not self.k.GetFileInformationByHandle(handle, c.byref(info))
                or not self.k.GetFileInformationByHandleEx(handle, 18, c.byref(identity), c.sizeof(identity))):
            raise ProbeBlocked('file_identity_unverified')
        if info.attributes & 0x400:
            raise ProbeBlocked('reparse_object_denied')
        return {'volume': identity.volume, 'file_id': bytes(identity.identifier).hex(),
                'attributes': info.attributes, 'links': info.links}

    def final_path(self, handle):
        buffer = c.create_unicode_buffer(32768)
        count = self.k.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        if not 0 < count < len(buffer):
            raise ProbeBlocked('file_path_unverified')
        return buffer.value

    def running(self, handle, expected_creation):
        values = [FileTime() for _ in range(4)]
        if not self.k.GetProcessTimes(handle, *[c.byref(value) for value in values]):
            raise ProbeBlocked('process_identity_unverified')
        created = (values[0].high << 32) | values[0].low
        if created != expected_creation or self.k.WaitForSingleObject(handle, 0) != 258:
            raise ProbeBlocked('process_identity_changed_or_exited')


def identity(info):
    return info['volume'], info['file_id']


class NamespaceGuard:
    """Retain exact root-to-leaf objects; callers still verify their ACLs."""
    def __init__(self, path):
        self.native, self.entries = Native(), []
        self.path = Path(path)
        if (not self.path.is_absolute() or len(self.path.drive) != 2
                or self.path.drive[1] != ':' or len(self.path.parts) > 16
                or any(part in ('.', '..') or ':' in part or part.rstrip(' .') != part
                       for part in self.path.parts[1:])):
            raise ProbeBlocked('fixed_local_path_required')
        try:
            for part in [*reversed(self.path.parents), self.path]:
                # READ_DATA/LIST_DIRECTORY activates sharing checks; metadata-only does not.
                handle = self.native.k.CreateFileW(str(part), 0x20081, 3, None, 3, 0x02200000, None)
                if handle in (None, c.c_void_p(-1).value):
                    raise ProbeBlocked('namespace_retention_unavailable')
                self.entries.append((part, handle, None))
                metadata = self.native.metadata(handle)
                is_leaf = part == self.path
                if bool(metadata['attributes'] & 16) == is_leaf or (is_leaf and metadata['links'] != 1):
                    raise ProbeBlocked('namespace_object_unverified')
                self.entries[-1] = part, handle, metadata
            self.verify()
        except BaseException:
            self.close()
            raise

    @property
    def ledger(self):
        return self.entries[-1][2]

    def verify(self):
        if not self.entries:
            raise ProbeBlocked('namespace_guard_closed')
        for part, held, expected in self.entries:
            current = self.native.metadata(held)
            if (identity(current) != identity(expected)
                    or bool(current['attributes'] & 16) != bool(expected['attributes'] & 16)
                    or (part == self.path and current['links'] != 1)):
                raise ProbeBlocked('held_namespace_changed')
            other = self.native.k.CreateFileW(str(part), 0x20081, 3, None, 3, 0x02200000, None)
            if other in (None, c.c_void_p(-1).value):
                raise ProbeBlocked('namespace_reopen_unavailable')
            try:
                current = self.native.metadata(other)
                if (identity(current) != identity(expected)
                        or bool(current['attributes'] & 16) != bool(expected['attributes'] & 16)
                        or (part == self.path and current['links'] != 1)):
                    raise ProbeBlocked('namespace_replaced')
            finally:
                self.native.k.CloseHandle(other)

    def close(self):
        for _, handle, _ in reversed(self.entries):
            self.native.k.CloseHandle(handle)
        self.entries.clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _ledger_handles(native, process, expected_creation, deadline):
    """One bounded exact-process walk; never enumerate other processes or memory."""
    native.running(process, expected_creation)
    count, snapshot, marker, candidate = U32(), HANDLE(), HANDLE(), None
    unsupported, unknown_files, result = [], [], None
    if not native.k.GetProcessHandleCount(process, c.byref(count)) or count.value > 512:
        raise ProbeBlocked('process_handle_bound')
    try:
        # No clone, memory, thread, name or trace capture.
        status = native.k.PssCaptureSnapshot(process, 4, 0, c.byref(snapshot))
        if status:
            raise ProbeBlocked('handle_snapshot_unavailable', status)
        if (native.k.PssQuerySnapshot(snapshot, 4, c.byref(count), c.sizeof(count))
                or count.value > 512):
            raise ProbeBlocked('snapshot_handle_bound')
        if native.k.PssWalkMarkerCreate(None, c.byref(marker)):
            raise ProbeBlocked('snapshot_marker_unavailable')
        seen = 0
        while True:
            if time.monotonic() >= deadline:
                raise ProbeBlocked('probe_deadline')
            entry = HandleEntry()
            status = native.k.PssWalkSnapshot(snapshot, 2, marker, c.byref(entry), c.sizeof(entry))
            if status == 259:
                break
            if status or seen >= 512:
                raise ProbeBlocked('snapshot_walk_unverified')
            seen += 1
            file_type = False
            if entry.flags & 1:
                if not entry.type_name or not 0 < entry.type_length <= 256 or entry.type_length % 2:
                    raise ProbeBlocked('snapshot_type_unverified')
                name = c.wstring_at(entry.type_name, entry.type_length // 2).removesuffix('\0')
                if not name or '\0' in name:
                    raise ProbeBlocked('snapshot_type_unverified')
                if name != 'File':
                    continue
                file_type = True
            duplicate = HANDLE()
            if not native.k.DuplicateHandle(process, entry.handle, native.k.GetCurrentProcess(),
                                             c.byref(duplicate), 0, False, 2):
                error = c.get_last_error()
                # Regular file handles are duplicable; unsupported object types are partial coverage.
                if error == 50 and not file_type:
                    unsupported.append(entry.handle)
                    continue
                raise ProbeBlocked('source_handle_changed', error)
            retain = False
            try:
                if not file_type:
                    raise ProbeBlocked('snapshot_type_changed')
                c.set_last_error(0)
                kind = native.k.GetFileType(duplicate)
                if kind == 0 and not c.get_last_error():
                    unknown_files.append(entry.handle)
                    continue
                if kind not in (1, 2, 3):
                    raise ProbeBlocked('duplicated_handle_type_unverified', c.get_last_error())
                if kind != 1:
                    continue
                path = native.final_path(duplicate)
                if Path(path).name.casefold() != 'narrator-control.sqlite':
                    continue
                info = native.metadata(duplicate)
                if info['attributes'] & 16 or info['links'] != 1 or candidate is not None:
                    raise ProbeBlocked('ledger_handle_ambiguous')
                candidate = {'handle': duplicate.value, 'source_handle': entry.handle,
                             'path': path, 'identity': info}
                retain = True
            finally:
                if not retain:
                    native.k.CloseHandle(duplicate)
        if seen != count.value or candidate is None:
            raise ProbeBlocked('ledger_handle_not_proven')
        native.running(process, expected_creation)
        candidate['unsupported_handles'] = tuple(unsupported)
        candidate['unknown_file_handles'] = tuple(unknown_files)
        candidate['snapshot_handles'] = seen
        result, candidate = candidate, None
        return result
    finally:
        if candidate:
            native.k.CloseHandle(candidate['handle'])
        cleanup_failed = bool(marker and native.k.PssWalkMarkerFree(marker))
        cleanup_failed |= bool(snapshot and native.k.PssFreeSnapshot(native.k.GetCurrentProcess(), snapshot))
        if cleanup_failed:
            if result:
                native.k.CloseHandle(result['handle'])
            raise ProbeBlocked('snapshot_cleanup_unverified')


class LedgerBinding:
    """Evidence only: the pinned controller's one persistent self.db is prerequisite."""
    def __init__(self, process_handle, expected_creation, guard, timeout=5):
        if not isinstance(guard, NamespaceGuard) or not 0 < timeout <= 10:
            raise ProbeBlocked('bounded_guard_required')
        self.native, self.guard, self.process = guard.native, guard, process_handle
        self.created, self.candidate = expected_creation, None
        try:
            deadline = time.monotonic() + timeout
            guard.verify()
            self.candidate = _ledger_handles(self.native, self.process, self.created, deadline)
            self.recheck(deadline)
        except BaseException:
            self.close()
            raise

    def recheck(self, deadline=None):
        if self.candidate is None:
            raise ProbeBlocked('ledger_binding_closed')
        self.guard.verify()
        other = _ledger_handles(self.native, self.process, self.created,
                                time.monotonic() + 5 if deadline is None else deadline)
        try:
            if (self.candidate['unsupported_handles'] != other['unsupported_handles']
                    or self.candidate['unknown_file_handles'] != other['unknown_file_handles']
                    or self.candidate['source_handle'] != other['source_handle']
                    or self.candidate['path'].casefold() != other['path'].casefold()
                    or identity(self.candidate['identity']) != identity(other['identity'])
                    or identity(other['identity']) != identity(self.guard.ledger)):
                raise ProbeBlocked('controller_ledger_identity_mismatch')
            self.native.running(self.process, self.created)
            self.guard.verify()
        finally:
            self.native.k.CloseHandle(other['handle'])

    def close(self):
        if self.candidate is not None:
            self.native.k.CloseHandle(self.candidate['handle'])
            self.candidate = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
