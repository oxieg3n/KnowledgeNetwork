"""One claimed narration job in the current user session; no scheduler or publication."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time

from .collector_narration_common import VoiceError, local_spool, read_json, sha256_file
from .collector_narration_receipt import read_voxcpm2_receipt
from .collector_narrator_host import verify_spool_acl
from .collector_voxcpm2 import RemoteVoxCPM2Provider, request_identity
from .collector_editor_job import execute as execute_editor, outcome as editor_outcome

IDENTITY = {'provider': 'voxcpm2_remote', 'narrator_id': 'oxiegen-narrator',
            'publication_eligible': False}
ID = re.compile('[a-f0-9]{32}')
SHA = re.compile('[a-f0-9]{64}')
MAX_REPLY = 512 * 1024
CANONICAL_EXE = Path('C:/Program Files/The Knowledge Network Collector/kn-collector.exe')
# Credential storage raises ValueError; provider errors use VoiceError.
SAFE_BLOCK = {'BLOCKED_WINDOWS_CREDENTIAL_STORE', 'BLOCKED_VOICE_CREDENTIAL_MISSING'}


class CompanionError(RuntimeError):
    pass



def _current_identity():
    if os.name != 'nt': raise CompanionError('COMPANION_WINDOWS_USER_SESSION_REQUIRED')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    security = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcessId.argtypes, kernel.GetCurrentProcessId.restype = [], wintypes.DWORD
    kernel.GetCurrentProcess.argtypes, kernel.GetCurrentProcess.restype = [], wintypes.HANDLE
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [ctypes.c_void_p], ctypes.c_void_p
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.OpenProcessToken.restype = wintypes.BOOL
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.GetTokenInformation.restype = wintypes.BOOL
    security.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    security.ConvertSidToStringSidW.restype = wintypes.BOOL
    session, token = wintypes.DWORD(), wintypes.HANDLE()
    if not kernel.ProcessIdToSessionId(kernel.GetCurrentProcessId(), ctypes.byref(session)):
        raise CompanionError('COMPANION_IDENTITY_UNVERIFIED')
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise CompanionError('COMPANION_IDENTITY_UNVERIFIED')
    try:
        length = wintypes.DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(length))
        if ctypes.get_last_error() != 122 or not 1 <= length.value <= 65536:
            raise CompanionError('COMPANION_IDENTITY_UNVERIFIED')
        buffer = ctypes.create_string_buffer(length.value)
        if not security.GetTokenInformation(token, 1, buffer, len(buffer), ctypes.byref(length)):
            raise CompanionError('COMPANION_IDENTITY_UNVERIFIED')
        # TOKEN_USER begins with SID_AND_ATTRIBUTES; its first member is the SID pointer.
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not security.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise CompanionError('COMPANION_IDENTITY_UNVERIFIED')
        try:
            return session.value, text.value
        finally:
            kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)


def _require_user_session():
    session, sid = _current_identity()
    if (type(session) is not int or session in (0, 0xffffffff) or not isinstance(sid, str) or
            not re.fullmatch(r'S-1-(?:[0-9]+-)+[0-9]+', sid) or
            sid in {'S-1-5-18', 'S-1-5-19', 'S-1-5-20'}):
        raise CompanionError('COMPANION_WINDOWS_USER_SESSION_REQUIRED')


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


class ServiceCLI:
    def __init__(self, sha256, spool):
        _require_user_session()
        self.executable, self.sha256 = CANONICAL_EXE, sha256
        self.spool = local_spool(spool)
        verify_spool_acl(self.spool)
        self._verify()

    def _verify(self):
        path = self.executable
        if (os.path.normcase(os.path.abspath(path)) != os.path.normcase(os.path.abspath(CANONICAL_EXE)) or
                not path.is_absolute() or '..' in path.parts or str(path).startswith('\\\\') or
                path.name.lower() != 'kn-collector.exe' or not isinstance(self.sha256, str) or
                not SHA.fullmatch(self.sha256)):
            raise CompanionError('COMPANION_EXECUTABLE_INVALID')
        for part in (path, *path.parents):
            if part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400:
                raise CompanionError('COMPANION_EXECUTABLE_REPARSE')
        if not path.is_file() or sha256_file(path) != self.sha256:
            raise CompanionError('COMPANION_EXECUTABLE_CHANGED')

    def call(self, operation, body=None):
        if operation not in ('claim', 'heartbeat', 'complete') or (body is None) != (operation == 'claim'):
            raise CompanionError('COMPANION_OPERATION_INVALID')
        self._verify()
        # Tokens never enter argv or inherited console streams. The directory inherits the verified DACL.
        temporary = tempfile.mkdtemp(prefix='companion-', dir=self.spool)
        directory = local_spool(temporary)
        # Keep scoped transport evidence; only the owner retires these private files.
        with (directory / 'retention.json').open('x', encoding='utf-8') as record:
            json.dump({'operation': operation, 'status': 'retained_transport_evidence', 'deletion_performed': False}, record)
        argv = [str(self.executable), 'companion-' + operation]
        if body is not None:
            request = directory / 'request.json'
            with request.open('x', encoding='utf-8') as stream:
                json.dump(body, stream, allow_nan=False)
            argv.append(str(request))
        with (directory / 'reply.json').open('w+b') as output:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.DEVNULL, shell=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                deadline = time.monotonic() + 8
                while process.poll() is None:
                    if os.fstat(output.fileno()).st_size > MAX_REPLY or time.monotonic() >= deadline:
                        raise CompanionError('COMPANION_TRANSPORT_UNCERTAIN')
                    time.sleep(.02)
                output.seek(0)
                raw = output.read(MAX_REPLY + 1)
                if len(raw) > MAX_REPLY: raise CompanionError('COMPANION_REPLY_INVALID')
                reply = _json(raw)
                if isinstance(reply, dict) and reply.get('ok') is False:
                    code = reply.get('error')
                    if isinstance(code, str) and re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,95}', code):
                        raise CompanionError('COMPANION_SERVICE_' + code.upper())
                if process.returncode or not isinstance(reply, dict) or reply.get('ok') is not True:
                    raise CompanionError('COMPANION_SERVICE_REJECTED')
                if set(reply) != {'ok', 'result'}: raise CompanionError('COMPANION_REPLY_INVALID')
                return reply['result']
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)


def _result(status, error=None, **hashes):
    result = {**IDENTITY, 'status': status, **hashes}
    if error: result['error'] = error if re.fullmatch('[A-Z][A-Z0-9_]{0,127}', error) else 'COMPANION_OPERATION_FAILED'
    return result


def run_once(service, provider_factory=RemoteVoxCPM2Provider.from_environment, *, heartbeat_seconds=10,
             editor_executor=execute_editor):
    claim = service.call('claim')
    if not isinstance(claim, dict) or set(claim) != {'job', 'inputs', 'lease_token'}:
        raise CompanionError('COMPANION_CLAIM_INVALID')
    job, inputs, token = claim['job'], claim['inputs'], claim['lease_token']
    if job is None and inputs is None and token is None: return {'status': 'idle'}
    if (not isinstance(job, dict) or not isinstance(job.get('job_id'), str) or
            not ID.fullmatch(job['job_id']) or not isinstance(token, str) or not ID.fullmatch(token)):
        raise CompanionError('COMPANION_CLAIM_INVALID')
    lease = {'job_id': job['job_id'], 'lease_token': token}
    def failure(status, code):
        if job.get('job_type') == 'editor.operation':
            operation = inputs.get('operation') if isinstance(inputs, dict) else None
            return editor_outcome(operation, status, code)
        return _result(status, code)
    stop, cancel, lost = threading.Event(), threading.Event(), threading.Event()

    def heartbeat():
        while not stop.wait(heartbeat_seconds):
            try:
                response = service.call('heartbeat', lease)
                if (not isinstance(response, dict) or set(response) != {'cancel_requested'} or
                        type(response['cancel_requested']) is not bool):
                    raise CompanionError('COMPANION_HEARTBEAT_INVALID')
                if response['cancel_requested']: cancel.set()
            except Exception:
                lost.set(); cancel.set(); return

    thread = threading.Thread(target=heartbeat, name='collector-lease', daemon=True)
    thread.start()
    provider, generating = None, False
    try:
        if job.get('job_type') == 'editor.operation':
            result = editor_executor(job['job_id'], inputs, cancel)
        else:
            if job.get('job_type') != 'narration.generate':
                raise CompanionError('COMPANION_JOB_TYPE_DENIED')
            if not isinstance(inputs, dict) or not {'text'} <= set(inputs) <= {'text', 'segments'}:
                raise CompanionError('COMPANION_INPUT_INVALID')
            request_identity(job['job_id'], inputs['text'], inputs.get('segments'))
            provider = provider_factory()
            health = provider.status()  # Read-only preflight; no submission has occurred.
            if not isinstance(health, dict) or health.get('status') != 'PASS':
                raise VoiceError('BLOCKED_NARRATOR_CONFIG')
            if cancel.is_set():
                result = _result('reconciliation_required' if lost.is_set() else 'cancelled', 'COMPANION_CANCELLED_BEFORE_GENERATION')
            else:
                generating = True
                provider.generate(job['job_id'], inputs['text'], segments=inputs.get('segments'), cancel=cancel)
                receipt_path = local_spool(provider.spool / job['job_id']) / 'narration.json'
                _, _, receipt, audio, receipt_hash = read_voxcpm2_receipt(receipt_path, expected_text=inputs['text'], max_text=12000)
                if receipt.get('collector_job_id') != job['job_id']:
                    raise CompanionError('COMPANION_RECEIPT_JOB_MISMATCH')
                result = _result('completed', narration_receipt_sha256=receipt_hash, audio_sha256=audio['sha256'])
    except Exception as exc:
        code = str(exc) if isinstance(exc, (VoiceError, CompanionError, ValueError)) else 'COMPANION_OPERATION_FAILED'
        if not generating and code in {'COMPANION_JOB_TYPE_DENIED', 'COMPANION_INPUT_INVALID',
                                       'INVALID_NARRATION_JOB_ID', 'INVALID_NARRATION_TEXT', 'INVALID_NARRATION_SEGMENTS'}:
            status = 'failed'
        elif not generating and (isinstance(exc, VoiceError) or code in SAFE_BLOCK):
            status = 'blocked'
        else:
            status = 'reconciliation_required'
        result = failure(status, code)
    finally:
        if generating and cancel.is_set():
            try:
                # At most one active segment: health + one cancel POST, each provider-bounded to 30s.
                evidence = read_json(local_spool(provider.spool / job['job_id']) / 'narration.json')
                active = [entry for entry in evidence.get('host_jobs', [])
                          if entry.get('state') in ('submission_intent', 'queued', 'running')]
                if len(active) > 1: raise CompanionError('COMPANION_CANCEL_REQUIRES_RECONCILIATION')
                observed = provider.cancel(job['job_id'])
                jobs = observed.get('host_jobs')
                if (observed.get('provider') == IDENTITY['provider'] and
                        observed.get('collector_job_id') == job['job_id'] and
                        observed.get('status') == 'HOST_STATUS_OBSERVED' and isinstance(jobs, list) and jobs and
                        len(jobs) == len(active) and
                        {item.get('id') for item in jobs} == {item.get('id') for item in active} and
                        all(item.get('state') == 'cancelled' for item in jobs)):
                    result = _result('cancelled', 'COMPANION_HOST_CANCEL_OBSERVED')
                else:
                    result = _result('reconciliation_required', 'COMPANION_REMOTE_CANCEL_UNVERIFIED')
            except Exception:
                result = _result('reconciliation_required', 'COMPANION_REMOTE_CANCEL_UNVERIFIED')
        stop.set(); thread.join(timeout=12)
    if thread.is_alive() or lost.is_set():
        result = failure('reconciliation_required', 'COMPANION_LEASE_LOST')
    elif cancel.is_set() and generating and result['status'] != 'cancelled':
        # A local Event is not evidence that remote inference stopped.
        result = _result('reconciliation_required', 'COMPANION_REMOTE_CANCEL_UNVERIFIED')
    try:
        completed = service.call('complete', {**lease, 'result': result})
        expected_state = 'succeeded' if result['status'] == 'completed' else result['status']
        if (not isinstance(completed, dict) or completed.get('job_id') != job['job_id'] or
                completed.get('state') != expected_state):
            raise CompanionError('COMPANION_COMPLETION_MISMATCH')
    except Exception as exc:
        code = str(exc) if isinstance(exc, CompanionError) and str(exc).startswith('COMPANION_SERVICE_') else 'COMPANION_COMPLETION_UNCERTAIN'
        return failure('reconciliation_required', code)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector one-shot media companion')
    parser.add_argument('--once', required=True, action='store_true')
    parser.add_argument('--collector-sha256', required=True)
    parser.add_argument('--private-spool', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_once(ServiceCLI(args.collector_sha256, args.private_spool))
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] in ('idle', 'completed') else 1
    except Exception as exc:
        code = str(exc) if isinstance(exc, CompanionError) else 'COMPANION_TRANSPORT_UNCERTAIN'
        print(json.dumps(_result('reconciliation_required', code)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
