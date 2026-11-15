"""Fixed, local Windows pipe transport for the owner-context narrator controller.

Only JSON bytes cross this boundary. Neither endpoint accepts executable code,
paths, credentials or narration text through this control channel.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import time

ROOT = Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec')
PIPE = r'\\.\pipe\KnowledgeNetworkCollectorNarratorControlV1'
MAX_MESSAGE = 65536
DEADLINE = 180
OPERATIONS = frozenset('narrator-health narrator-validate narrator-start narrator-stop '
    'narrator-credential-ensure narrator-verify narrator-diagnostics narrator-reconcile'.split())
FILES = frozenset(('__init__.py', 'collector_narrator_pipe.py', 'collector_narrator_control.py',
    'collector_narrator_host.py', 'collector_narration_common.py', 'collector_credentials.py'))


class BrokerError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def local_file(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith('\\\\'):
        raise BrokerError('broker_path_denied')
    for item in (path, *path.parents):
        st = item.lstat()
        if item.is_symlink() or getattr(st, 'st_file_attributes', 0) & 0x400:
            raise BrokerError('broker_path_denied')
    if not path.is_file() or path.stat().st_nlink != 1:
        raise BrokerError('broker_path_denied')
    return path


def sha256(path):
    h = hashlib.sha256()
    with local_file(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BrokerError('broker_message_invalid')
        result[key] = value
    return result


def decode(raw):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_MESSAGE:
        raise BrokerError('broker_message_invalid')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise BrokerError('broker_message_invalid') from exc
    if not isinstance(value, dict):
        raise BrokerError('broker_message_invalid')
    return value


def validate_request(value):
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'request_id', 'operation'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or not isinstance(value['request_id'], str) or not re.fullmatch('[a-f0-9]{32}', value['request_id'])
            or not isinstance(value['operation'], str) or value['operation'] not in OPERATIONS):
        raise BrokerError('broker_request_denied')
    return value


def load_config():
    config = decode(local_file(ROOT / 'narrator-broker.json').read_bytes())
    if set(config) != {'schema_version', 'owner_sid', 'bridge_sid', 'server_python_sha256', 'manifest_sha256', 'files'}:
        raise BrokerError('broker_configuration_invalid')
    if type(config['schema_version']) is not int or config['schema_version'] != 1:
        raise BrokerError('broker_configuration_invalid')
    for name in ('owner_sid', 'bridge_sid'):
        if not isinstance(config[name], str) or not re.fullmatch(r'S-1-5-21-(?:\d+-){3}\d+', config[name]):
            raise BrokerError('broker_configuration_invalid')
    if config['owner_sid'] == config['bridge_sid']:
        raise BrokerError('broker_configuration_invalid')
    files = config['files']
    if not isinstance(files, dict) or set(files) != FILES:
        raise BrokerError('broker_configuration_invalid')
    for value in (config['server_python_sha256'], config['manifest_sha256'], *files.values()):
        if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
            raise BrokerError('broker_configuration_invalid')
    for name, expected in files.items():
        if sha256(ROOT / 'runtime/youtube_ops' / name) != expected:
            raise BrokerError('broker_source_changed')
    if sha256(ROOT / 'runtime/python/python.exe') != config['server_python_sha256']:
        raise BrokerError('broker_python_changed')
    return config


def _apis():
    if os.name != 'nt':
        raise BrokerError('broker_windows_required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenThreadToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.GetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    advapi.ImpersonateNamedPipeClient.argtypes = [wintypes.HANDLE]
    advapi.RevertToSelf.argtypes = []
    kernel.GetCurrentThread.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    return kernel, advapi


def _sid_string(pointer, kernel, advapi):
    value = wintypes.LPWSTR()
    if not advapi.ConvertSidToStringSidW(pointer, ctypes.byref(value)):
        raise BrokerError('broker_identity_unverified')
    try:
        return value.value
    finally:
        kernel.LocalFree(value)


def _token_identity(token, kernel, advapi):
    size = wintypes.DWORD()
    advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
    if not 0 < size.value <= 65536:
        raise BrokerError('broker_identity_unverified')
    data = ctypes.create_string_buffer(size.value)
    elevation = wintypes.DWORD()
    if not advapi.GetTokenInformation(token, 1, data, size, ctypes.byref(size)):
        raise BrokerError('broker_identity_unverified')
    sid = _sid_string(ctypes.cast(data, ctypes.POINTER(ctypes.c_void_p))[0], kernel, advapi)
    if not advapi.GetTokenInformation(token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(size)):
        raise BrokerError('broker_identity_unverified')
    return sid, bool(elevation.value)


def windows_identity():
    kernel, advapi = _apis()
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise BrokerError('broker_identity_unverified')
    try:
        return _token_identity(token, kernel, advapi)
    finally:
        kernel.CloseHandle(token)


def allow_bridge_inspection(config):
    """Permit only query access to this controller process and its primary token."""
    kernel, advapi = _apis()
    class Trustee(ctypes.Structure):
        _fields_ = [('multiple', ctypes.c_void_p), ('operation', ctypes.c_int),
                    ('form', ctypes.c_int), ('kind', ctypes.c_int), ('name', ctypes.c_void_p)]
    class Entry(ctypes.Structure):
        _fields_ = [('permissions', wintypes.DWORD), ('mode', ctypes.c_int),
                    ('inheritance', wintypes.DWORD), ('trustee', Trustee)]
    advapi.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
    advapi.SetEntriesInAclW.argtypes = [wintypes.ULONG, ctypes.POINTER(Entry), ctypes.c_void_p,
                                      ctypes.POINTER(ctypes.c_void_p)]
    advapi.SetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
                                     ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    identity, elevated = windows_identity()
    if identity != config['owner_sid'] or elevated:
        raise BrokerError('broker_owner_context_required')
    sid, token = ctypes.c_void_p(), wintypes.HANDLE()
    if not advapi.ConvertStringSidToSidW(config['bridge_sid'], ctypes.byref(sid)):
        raise BrokerError('broker_inspection_acl_unverified')
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x60008, ctypes.byref(token)):
            raise BrokerError('broker_inspection_acl_unverified')
        for handle, rights in ((kernel.GetCurrentProcess(), 0x1000), (token, 8)):
            old, descriptor, updated = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
            if advapi.GetSecurityInfo(handle, 6, 4, None, None, ctypes.byref(old), None, ctypes.byref(descriptor)):
                raise BrokerError('broker_inspection_acl_unverified')
            try:
                if not old:
                    raise BrokerError('broker_inspection_acl_unverified')
                entry = Entry(rights, 1, 0, Trustee(None, 0, 0, 1, sid))
                if (advapi.SetEntriesInAclW(1, ctypes.byref(entry), old, ctypes.byref(updated))
                        or advapi.SetSecurityInfo(handle, 6, 4, None, None, updated, None)):
                    raise BrokerError('broker_inspection_acl_unverified')
            finally:
                if updated: kernel.LocalFree(updated)
                kernel.LocalFree(descriptor)
    finally:
        if token: kernel.CloseHandle(token)
        kernel.LocalFree(sid)


def verify_server(handle, config):
    kernel, advapi = _apis()
    owner, descriptor, pid = ctypes.c_void_p(), ctypes.c_void_p(), wintypes.DWORD()
    if advapi.GetSecurityInfo(handle, 1, 1, ctypes.byref(owner), None, None, None, ctypes.byref(descriptor)):
        raise BrokerError('broker_server_unverified')
    try:
        if _sid_string(owner, kernel, advapi) != config['owner_sid']:
            raise BrokerError('broker_server_unverified')
    finally:
        kernel.LocalFree(descriptor)
    if not kernel.GetNamedPipeServerProcessId(handle, ctypes.byref(pid)):
        raise BrokerError('broker_server_unverified')
    process = kernel.OpenProcess(0x1000, False, pid.value)
    if not process:
        raise BrokerError('broker_server_process_unverified')
    token = wintypes.HANDLE()
    try:
        size = wintypes.DWORD(32768); image = ctypes.create_unicode_buffer(size.value)
        if (not kernel.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(size))
                or Path(image.value) != ROOT / 'runtime/python/python.exe'
                or not advapi.OpenProcessToken(process, 8, ctypes.byref(token))):
            raise BrokerError('broker_server_process_unverified')
        identity, elevated = _token_identity(token, kernel, advapi)
        again = wintypes.DWORD()
        if (identity != config['owner_sid'] or elevated
                or not kernel.GetNamedPipeServerProcessId(handle, ctypes.byref(again)) or again.value != pid.value):
            raise BrokerError('broker_server_unverified')
    finally:
        if token: kernel.CloseHandle(token)
        kernel.CloseHandle(process)


def verify_client(handle, config):
    kernel, advapi = _apis()
    if not advapi.ImpersonateNamedPipeClient(handle):
        raise BrokerError('broker_client_unverified')
    token = wintypes.HANDLE()
    try:
        if not advapi.OpenThreadToken(kernel.GetCurrentThread(), 8, True, ctypes.byref(token)):
            raise BrokerError('broker_client_unverified')
        identity, elevated = _token_identity(token, kernel, advapi)
        if identity != config['bridge_sid'] or elevated:
            raise BrokerError('broker_client_denied')
    finally:
        if token: kernel.CloseHandle(token)
        if not advapi.RevertToSelf():
            os._exit(70)  # Never continue controller work while impersonating a client.


def _wait(ov, deadline, cancel):
    import _winapi
    try:
        while _winapi.WaitForSingleObject(ov.event, 50) == _winapi.WAIT_TIMEOUT:
            if cancel.is_set() or time.monotonic() >= deadline:
                raise BrokerError('broker_outcome_unknown')
        count, error = ov.GetOverlappedResult(False)
        if error or count > MAX_MESSAGE:
            raise BrokerError('broker_message_invalid')
        return count
    except BaseException:
        ov.cancel()
        ov.GetOverlappedResult(True)
        raise


def receive(handle, deadline, cancel):
    import _winapi
    if cancel.is_set() or time.monotonic() >= deadline:
        raise BrokerError('broker_outcome_unknown')
    ov, _ = _winapi.ReadFile(handle, MAX_MESSAGE + 1, overlapped=True)
    _wait(ov, deadline, cancel)
    return decode(bytes(ov.getbuffer()))


def send(handle, value, deadline, cancel):
    import _winapi
    if cancel.is_set() or time.monotonic() >= deadline:
        raise BrokerError('broker_outcome_unknown')
    raw = json.dumps(value, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw) > MAX_MESSAGE:
        raise BrokerError('broker_message_invalid')
    ov, _ = _winapi.WriteFile(handle, raw, overlapped=True)
    if _wait(ov, deadline, cancel) != len(raw):
        raise BrokerError('broker_outcome_unknown')


def broker_request(operation, request_id, cancel):
    import _winapi
    request = validate_request({'schema_version': 1, 'operation': operation, 'request_id': request_id})
    config = load_config()
    identity, elevated = windows_identity()
    if identity != config['bridge_sid'] or elevated:
        raise BrokerError('broker_client_denied')
    deadline = time.monotonic() + DEADLINE
    handle = None
    try:
        while handle is None:
            if cancel.is_set() or time.monotonic() >= deadline:
                raise BrokerError('broker_outcome_unknown')
            try:
                handle = _winapi.CreateFile(PIPE, 0x120103, 0, 0, 3,
                    0x40000000 | 0x100000 | 0x10000, 0)  # Overlapped + identification-only SQOS.
            except OSError as exc:
                if exc.winerror != 231:
                    raise BrokerError('broker_unavailable') from exc
                cancel.wait(.05)
        _winapi.SetNamedPipeHandleState(handle, 2, None, None)
        verify_server(handle, config)
        if cancel.is_set():
            raise BrokerError('broker_cancelled_before_request')
        send(handle, request, deadline, cancel)
        return receive(handle, deadline, cancel)
    except OSError as exc:
        raise BrokerError('broker_outcome_unknown') from exc
    finally:
        if handle is not None:
            _winapi.CloseHandle(handle)


def serve(config, handler, cancel):
    import _winapi
    kernel, advapi = _apis()
    descriptor = ctypes.c_void_p()
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    # No other local user and no network pipe client may enter this boundary.
    sddl = ('O:' + config['owner_sid'] + 'D:P(A;;GA;;;' + config['owner_sid'] + ')'
            '(A;;0x120103;;;' + config['bridge_sid'] + ')(A;;GA;;;SY)(A;;GA;;;BA)')
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
        raise BrokerError('broker_pipe_acl_unverified')
    class Attributes(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('descriptor', ctypes.c_void_p), ('inherit', wintypes.BOOL)]
    attributes = Attributes(ctypes.sizeof(Attributes), descriptor, False)
    handle = None
    try:
        handle = _winapi.CreateNamedPipe(PIPE, 3 | 0x40000000 | 0x80000,
            4 | 2 | 8, 1, MAX_MESSAGE, MAX_MESSAGE, 0, ctypes.addressof(attributes))
        while not cancel.is_set():
            ov = _winapi.ConnectNamedPipe(handle, overlapped=True)
            try:
                _wait(ov, float('inf'), cancel)
                request = receive(handle, time.monotonic() + 10, cancel)
                verify_client(handle, config)  # Impersonation identifies the last message read.
                request = validate_request(request)
                response = handler(request)
                send(handle, response, time.monotonic() + 10, cancel)
            except (BrokerError, OSError, ValueError):
                pass  # No untrusted request body or private exception enters logs.
            finally:
                kernel.DisconnectNamedPipe(handle)
    finally:
        if handle is not None: _winapi.CloseHandle(handle)
        kernel.LocalFree(descriptor)
