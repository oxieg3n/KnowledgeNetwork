"""Argumentless SSH forced commands for the dedicated Collector host identity.

Run this standalone with the pinned Python -I -S. Deployment owns the immutable
runtime/config; the login identity may write only the audit directory.
"""
import ctypes
from ctypes import wintypes
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec')
OPERATIONS = frozenset(('health', 'native-port-9443', 'narrator-status', 'self-test'))
MAX_OUTPUT = 65536
MAX_AUDIT = 16 * 1024 * 1024
TIMEOUT = 20
IDENTITY_SCRIPT = "[Console]::Out.Write([Security.Principal.WindowsIdentity]::GetCurrent().User.Value)"
PORT_SCRIPT = "[Console]::Out.Write(@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -eq 9443).Count)"


class Denied(RuntimeError):
    pass


def digest(path):
    with path.open('rb') as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def local_path(path, *, directory=False):
    if not path.is_absolute() or '..' in path.parts or str(path).startswith('\\\\'):
        raise Denied('untrusted_path')
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400:
            raise Denied('untrusted_path')
    if not (path.is_dir() if directory else path.is_file()):
        raise Denied('untrusted_path')
    return path


def read_object(path):
    local_path(path)
    with path.open('rb') as stream:
        raw = stream.read(MAX_OUTPUT + 1)
    if len(raw) > MAX_OUTPUT:
        raise Denied('file_limit')
    value = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value, dict):
        raise Denied('invalid_object')
    return value, hashlib.sha256(raw).hexdigest()


def windows_identity():
    if os.name != 'nt':
        raise Denied('windows_required')
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    token, size = wintypes.HANDLE(), wintypes.DWORD()
    if not api.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise Denied('identity_unverified')
    try:
        api.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise Denied('identity_unverified')
        user = ctypes.create_string_buffer(size.value)
        sid = wintypes.LPWSTR()
        elevation = wintypes.DWORD()
        if not api.GetTokenInformation(token, 1, user, size, ctypes.byref(size)):
            raise Denied('identity_unverified')
        if not api.ConvertSidToStringSidW(ctypes.cast(user, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.byref(sid)):
            raise Denied('identity_unverified')
        try:
            value = sid.value
        finally:
            kernel.LocalFree(sid)
        if not api.GetTokenInformation(token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(size)):
            raise Denied('identity_unverified')
        api.GetTokenInformation(token, 2, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise Denied('identity_unverified')
        groups = ctypes.create_string_buffer(size.value)
        if not api.GetTokenInformation(token, 2, groups, size, ctypes.byref(size)):
            raise Denied('identity_unverified')
        class Group(ctypes.Structure):
            _fields_ = [('sid', ctypes.c_void_p), ('attributes', wintypes.DWORD)]
        class Header(ctypes.Structure):
            _fields_ = [('count', wintypes.DWORD), ('groups', Group * 1)]
        count = ctypes.cast(groups, ctypes.POINTER(wintypes.DWORD))[0]
        if count > (size.value - Header.groups.offset) // ctypes.sizeof(Group):
            raise Denied('identity_unverified')
        admin = False
        for group in (Group * count).from_buffer(groups, Header.groups.offset):
            group_sid = wintypes.LPWSTR()
            if not api.ConvertSidToStringSidW(group.sid, ctypes.byref(group_sid)):
                raise Denied('identity_unverified')
            try:
                admin |= group_sid.value == 'S-1-5-32-544'  # Includes deny-only filtered admin tokens.
            finally:
                kernel.LocalFree(group_sid)
        return value, bool(elevation.value) or admin
    finally:
        kernel.CloseHandle(token)


def authorize(config, env, identity, elevated):
    if set(config) != {'schema_version', 'execution_sid', 'forge_address', 'python_sha256', 'powershell_sha256'}:
        raise Denied('invalid_configuration')
    if type(config['schema_version']) is not int or config['schema_version'] != 1 or not re.fullmatch(r'S-1-5-21-(?:\d+-){3}\d+', str(config['execution_sid'])):
        raise Denied('invalid_configuration')
    for name in ('python_sha256', 'powershell_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', str(config[name])):
            raise Denied('invalid_configuration')
    if identity != config['execution_sid'] or elevated:
        raise Denied('execution_identity_denied')
    if 'SSH_TTY' in env:
        raise Denied('pty_denied')
    command = env.get('SSH_ORIGINAL_COMMAND', '')
    if command not in OPERATIONS:
        raise Denied('command_denied')
    connection = env.get('SSH_CONNECTION', '')
    if not re.fullmatch(r'[^\s]+ [0-9]{1,5} [^\s]+ [0-9]{1,5}', connection):
        raise Denied('source_denied')
    source, source_port, destination, destination_port = connection.split(' ')
    try:
        configured = ipaddress.ip_address(config['forge_address'])
        if ipaddress.ip_address(source) != configured or not all(0 < int(p) < 65536 for p in (source_port, destination_port)):
            raise ValueError()
        ipaddress.ip_address(destination)
        if not any(configured in ipaddress.ip_network(n) for n in
                   ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10', 'fd7a:115c:a1e0::/48')):
            raise ValueError()
    except ValueError as exc:
        raise Denied('source_denied') from exc
    return command


def own_process_tree():
    """Own this dispatcher before spawning anything; descendants inherit the job."""
    if os.name != 'nt':
        raise Denied('windows_required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Basic(ctypes.Structure):
        _fields_ = [('user', ctypes.c_int64), ('job', ctypes.c_int64), ('flags', wintypes.DWORD),
                    ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('active', wintypes.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
    class Limits(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', ctypes.c_uint64 * 6), ('process_memory', ctypes.c_size_t),
                    ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    limits = Limits(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE, no breakaway.
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise Denied('process_ownership_unavailable')
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        raise Denied('process_ownership_unavailable')
    # Deliberately retain the handle until process exit: closing it here kills us.
    return handle


def fixed_powershell(script, config, cancel, *, timeout=TIMEOUT):
    if cancel.is_set():
        raise Denied('cancelled')
    executable = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
    if digest(local_path(executable)) != config['powershell_sha256']:
        raise Denied('powershell_changed')
    environment = {'SystemRoot': 'C:/Windows', 'WINDIR': 'C:/Windows',
                   'PATH': 'C:/Windows/System32', 'PSModulePath': 'C:/Windows/System32/WindowsPowerShell/v1.0/Modules'}
    # Regular files bound memory even if a helper unexpectedly floods either stream.
    with tempfile.TemporaryFile(dir=ROOT / 'audit') as output, tempfile.TemporaryFile(dir=ROOT / 'audit') as error:
        process = subprocess.Popen([str(executable), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
            stdin=subprocess.DEVNULL, stdout=output, stderr=error, cwd=str(ROOT / 'runtime'),
            env=environment, shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if cancel.is_set():
                    raise Denied('cancelled')
                if time.monotonic() >= deadline:
                    raise Denied('operation_timeout')
                if os.fstat(output.fileno()).st_size + os.fstat(error.fileno()).st_size > MAX_OUTPUT:
                    raise Denied('output_limit')
                time.sleep(.02)
            if process.returncode or os.fstat(error.fileno()).st_size:
                raise Denied('operation_failed')
            output.seek(0); value = output.read(MAX_OUTPUT + 1)
            if len(value) > MAX_OUTPUT:
                raise Denied('output_limit')
            return value.decode('utf-8-sig').strip()
        finally:
            if process.poll() is None:
                try:
                    process.kill(); process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise Denied('process_outcome_unverified') from exc


def ensure_quiescent(handle):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Accounting(ctypes.Structure):
        _fields_ = [('times', ctypes.c_int64 * 4), ('faults', wintypes.DWORD), ('total', wintypes.DWORD),
                    ('active', wintypes.DWORD), ('terminated', wintypes.DWORD)]
    kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                wintypes.DWORD, ctypes.c_void_p]
    result = Accounting()
    if not kernel.QueryInformationJobObject(handle, 1, ctypes.byref(result), ctypes.sizeof(result), None):
        raise Denied('process_outcome_unverified')
    if result.active != 1:  # Only this dispatcher may remain before reporting success.
        raise Denied('owned_children_active')


def perform(operation, config, identity, cancel):
    if operation == 'health':
        return {'execution_sid': identity, 'elevated': False, 'capabilities': sorted(OPERATIONS)}
    if operation == 'self-test':
        if fixed_powershell(IDENTITY_SCRIPT, config, cancel) != identity:
            raise Denied('powershell_identity_mismatch')
        return {'execution_sid': identity, 'fixed_powershell': 'PASS'}
    if operation == 'narrator-status':
        path = ROOT / 'receipts/narrator-status.json'
        if not path.exists():
            raise Denied('narrator_snapshot_missing')
        value, sha = read_object(path)
        if not re.fullmatch('[A-Za-z_]{1,64}', str(value.get('status', ''))):
            raise Denied('invalid_narrator_snapshot')
        return {'scope': 'retained_snapshot_only', 'live_authenticated': False,
                'snapshot_status': value['status'], 'artifact_sha256': sha}
    if operation == 'native-port-9443':
        count = fixed_powershell(PORT_SCRIPT, config, cancel)
        if not re.fullmatch('[0-9]{1,5}', count):
            raise Denied('native_port_unverified')
        if int(count):
            return {'port': 9443, 'available_snapshot': False, 'listeners': int(count)}
        sockets = []
        try:
            for family, address in ((socket.AF_INET, '0.0.0.0'), (socket.AF_INET6, '::')):
                item = socket.socket(family, socket.SOCK_STREAM); sockets.append(item)
                item.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                if family == socket.AF_INET6:
                    item.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                item.bind((address, 9443))
            return {'port': 9443, 'available_snapshot': True, 'listeners': 0, 'listener_started': False}
        except OSError as exc:
            raise Denied('native_bind_unavailable') from exc
        finally:
            for item in sockets:
                item.close()
    raise Denied('command_denied')


def audit(record):
    folder = local_path(ROOT / 'audit', directory=True)
    path = folder / 'execution.jsonl'
    before = None
    if path.exists():
        local_path(path); before = path.lstat()
        if before.st_nlink != 1 or getattr(before, 'st_file_attributes', 0) & 0x400:
            raise Denied('audit_path_untrusted')
        if before.st_size >= MAX_AUDIT:
            raise Denied('audit_limit')
    data = (json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, 'O_BINARY', 0) | (os.O_CREAT | os.O_EXCL if before is None else 0)
    with os.fdopen(os.open(path, flags, 0o600), 'ab', buffering=0) as stream:
        current = os.fstat(stream.fileno())
        if current.st_nlink != 1 or (before and (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)):
            raise Denied('audit_path_untrusted')
        if os.name == 'nt':
            import msvcrt
            deadline = time.monotonic() + 2
            while True:
                try:
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise Denied('audit_busy')
                    time.sleep(.02)
            try:
                if os.fstat(stream.fileno()).st_size + len(data) > MAX_AUDIT:
                    raise Denied('audit_limit')
                stream.write(data); os.fsync(stream.fileno())
            finally:
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            if os.fstat(stream.fileno()).st_size + len(data) > MAX_AUDIT:
                raise Denied('audit_limit')
            stream.write(data); os.fsync(stream.fileno())


def main():
    request, started, identity, operation = uuid.uuid4().hex, time.monotonic(), 'unverified', 'denied'
    cancel = threading.Event()
    for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: cancel.set())
    try:
        if len(sys.argv) != 1 or Path(__file__).absolute() != ROOT / 'runtime/collector_host_exec.py':
            raise Denied('runtime_path_denied')
        config, config_sha = read_object(ROOT / 'config.json')
        identity, elevated = windows_identity()
        operation = authorize(config, os.environ, identity, elevated)
        if digest(local_path(Path(sys.executable))) != config['python_sha256']:
            raise Denied('python_changed')
        owner = own_process_tree()
        audit({'event': 'start', 'request_id': request, 'execution_sid': identity,
               'operation': operation, 'config_sha256': config_sha})
        result = perform(operation, config, identity, cancel)
        ensure_quiescent(owner)
        audit({'event': 'finish', 'request_id': request, 'execution_sid': identity,
               'operation': operation, 'outcome': 'PASS',
               'result_sha256': hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest(),
               'duration_ms': round((time.monotonic() - started) * 1000)})
        print(json.dumps({'status': 'PASS', 'operation': operation, 'result': result}), flush=True)
        return 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, Denied) else 'operation_unverified'
        try:
            audit({'event': 'finish', 'request_id': request, 'execution_sid': identity,
                   'operation': operation, 'outcome': code, 'duration_ms': round((time.monotonic() - started) * 1000)})
        except Exception:
            code = 'audit_unavailable'
        print(json.dumps({'status': 'BLOCKED', 'error': code}), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
