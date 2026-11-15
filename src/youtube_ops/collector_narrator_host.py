"""Restricted loopback host queue for the existing, reviewed Oxiegen-Narrator."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import getpass
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import threading
import time

from .collector_narration_common import (MAX_WAV, VoiceError, digest, inspect_wav,
    local_spool, read_json, sha256_file, socket_deadline, voice_lease)

NARRATOR = 'oxiegen-narrator'
SERVICE = 'knowledge-network-voxcpm2'
SCRIPT = Path(r'D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1')
REFERENCE = Path(r'D:\tools\audio\voices\Oxiegen-Narrator\reference.wav')
CLI = Path(r'D:\tools\audio\voicestudio\data\engines\voxcpm2\voxcpm2\.venv\Scripts\voxcpm.exe')
CREDENTIAL_TARGET = 'KnowledgeNetworkCollector/OxiegenNarrator/Host'
SETTINGS = {'cfg_value': 2.0, 'inference_timesteps': 10, 'denoiser': False,
            'optimize': False, 'local_files_only': True, 'torch_compile_disable': '1'}
MAX_BODY = 65536
REQUEST_DEADLINE_SECONDS = 30
SCRIPT_TIMEOUT_SECONDS = 900
SPOOL_ACL_CHECK = r'''
$ErrorActionPreference = 'Stop'
try {
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $acl = Get-Acl -LiteralPath ([string]$request.spool)
    $raw = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(), 0)
    if ($null -eq $raw.DiscretionaryAcl -or -not $acl.AreAccessRulesProtected) { throw 'unsafe' }
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $allowed = @($user, 'S-1-5-18', 'S-1-5-32-544')
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed) { throw 'unsafe' }
    $ownFullControl = $false
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.IdentityReference.Value -notin $allowed) { throw 'unsafe' }
        if ($rule.IdentityReference.Value -eq $user -and
            ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -eq
            [Security.AccessControl.FileSystemRights]::FullControl) { $ownFullControl = $true }
    }
    if (-not $ownFullControl) { throw 'unsafe' }
    [Console]::Out.Write('{"ok":true}')
    exit 0
} catch {
    [Console]::Out.Write('{"ok":false}')
    exit 1
}
'''


class NarratorError(RuntimeError):
    def __init__(self, code, status=400, *, uncertain=False):
        super().__init__(code)
        self.status, self.uncertain = status, uncertain


def valid_id(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{32}', value) is not None


def validate_text(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 12000 or any(ord(c) < 32 and c not in '\n\t' for c in text):
        raise NarratorError('invalid_text')


def _system_powershell():
    if os.name != 'nt':
        raise NarratorError('windows_spool_acl_verification_required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel.GetSystemDirectoryW.restype = wintypes.UINT
    directory = ctypes.create_unicode_buffer(32768)
    length = kernel.GetSystemDirectoryW(directory, len(directory))
    if not 0 < length < len(directory):
        raise NarratorError('system_powershell_unavailable')
    return Path(directory.value) / 'WindowsPowerShell/v1.0/powershell.exe'


def verify_spool_acl(spool):
    """Read-only Windows DACL gate. Never silently repair host permissions."""
    path = local_spool(spool)
    try:
        result = subprocess.run([str(_system_powershell()), '-NoLogo', '-NoProfile', '-NonInteractive',
            '-Command', SPOOL_ACL_CHECK], input=json.dumps({'spool': str(path)}, ensure_ascii=True),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
            timeout=10, check=False, shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NarratorError('spool_acl_unverified') from exc
    if result.returncode != 0 or len(result.stdout) > 64 or result.stdout.strip() != '{"ok":true}':
        raise NarratorError('spool_acl_unverified')


def _effective_model_ref():
    """Resolve with the canonical engine interpreter, never importing inference."""
    python = CLI.parent / 'python.exe'
    try:
        result = subprocess.run([str(python), '-I', '-X', 'utf8', '-c',
            'import json; from huggingface_hub.constants import HF_HUB_CACHE; '
            'from pathlib import Path; print(json.dumps(str(Path(HF_HUB_CACHE) / '
            '"models--openbmb--VoxCPM2" / "refs" / "main")))'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
            text=True, encoding='utf-8', check=False, shell=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or len(result.stdout) > 32768:
            raise ValueError('resolver_failed')
        value = json.loads(result.stdout)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError('invalid_ref')
        return Path(value)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise NarratorError('effective_model_reference_unverified') from exc


class NarratorManifest:
    """Local reviewed file evidence, never fields accepted from an API client."""
    def __init__(self, path):
        self.value = read_json(path)
        manifest = self.value
        if manifest.get('schema_version') != 1 or manifest.get('narrator_id') != NARRATOR:
            raise NarratorError('manifest_identity_unverified')
        for key in ('rights_reviewed', 'commercial_use', 'youtube_use', 'voice_consent',
                    'script_reviewed', 'voice_identity_verified', 'independent_runtime_verified'):
            if manifest.get(key) is not True:
                raise NarratorError('manifest_review_incomplete')
        for key in ('reviewed_by', 'reviewed_at', 'model_revision', 'license', 'cli_version'):
            if not isinstance(manifest.get(key), str) or not manifest[key].strip():
                raise NarratorError('manifest_review_incomplete')
        if not re.fullmatch('[a-f0-9]{40}', manifest['model_revision']):
            raise NarratorError('invalid_model_revision')
        if manifest.get('model_id') != 'openbmb/VoxCPM2' or manifest.get('settings') != SETTINGS:
            raise NarratorError('canonical_narrator_configuration_unverified')
        artifacts = manifest.get('artifacts')
        required = {'cli_executable', 'narrator_reference', 'model_checkpoint',
                    'license_evidence', 'consent_evidence', 'inspection_record', 'model_revision_ref'}
        if not isinstance(artifacts, list) or not 7 <= len(artifacts) <= 64:
            raise NarratorError('manifest_artifacts_missing')
        for item in artifacts:
            if (not isinstance(item, dict) or set(item) != {'role', 'path', 'sha256'} or
                not isinstance(item['role'], str) or not re.fullmatch('[a-z_]{1,40}', item['role']) or
                not isinstance(item['path'], str) or not Path(item['path']).is_absolute() or
                not re.fullmatch('[a-f0-9]{64}', str(item['sha256']))):
                raise NarratorError('invalid_manifest_artifact')
        if not required.issubset({item['role'] for item in artifacts}):
            raise NarratorError('manifest_artifacts_missing')
        for role, canonical in (('cli_executable', CLI), ('narrator_reference', REFERENCE)):
            matches = [item for item in artifacts if item['role'] == role]
            if len(matches) != 1 or Path(matches[0]['path']) != canonical:
                raise NarratorError('canonical_narrator_path_mismatch')
        licenses = [item for item in artifacts if item['role'] == 'license_evidence']
        if len(licenses) != 1:
            raise NarratorError('ambiguous_license_evidence')
        self.provenance = {'script_sha256': manifest.get('script_sha256'),
            'config_sha256': digest({'settings': SETTINGS, 'model_id': manifest['model_id'],
                'model_revision': manifest['model_revision'], 'cli_version': manifest['cli_version'],
                'artifacts': sorted([{'role': item['role'], 'sha256': item['sha256']} for item in artifacts], key=lambda item: (item['role'], item['sha256']))}),
            'model_revision': manifest['model_revision'], 'license_evidence_sha256': licenses[0]['sha256']}
        self.verify()

    def verify(self):
        deadline = time.monotonic() + 120
        artifacts = self.value['artifacts']
        refs = [item for item in artifacts if item['role'] == 'model_revision_ref']
        effective = _effective_model_ref()
        try:
            if len(refs) != 1 or Path(refs[0]['path']) != effective or effective.stat().st_size > 128:
                raise ValueError('ref_mismatch')
            revision = effective.read_text(encoding='ascii').strip()
            if revision != self.value['model_revision']:
                raise ValueError('revision_changed')
            snapshot = effective.parent.parent / 'snapshots' / revision
            selected = {path.resolve(strict=True) for path in
                (snapshot / 'model.safetensors', snapshot / 'pytorch_model.bin') if path.is_file()}
            if (snapshot / 'model.safetensors').is_file():
                selected = {(snapshot / 'model.safetensors').resolve(strict=True)}
            checkpoints = [Path(item['path']).resolve(strict=True) for item in artifacts
                           if item['role'] == 'model_checkpoint']
            if not checkpoints or any(path not in selected for path in checkpoints):
                raise ValueError('checkpoint_not_selected')
        except (OSError, ValueError, UnicodeError) as exc:
            raise NarratorError('selected_model_revision_unverified') from exc
        records = [{'path': str(SCRIPT), 'sha256': self.value.get('script_sha256')}, *self.value['artifacts']]
        for item in records:
            path = Path(item['path'])
            if not re.fullmatch('[a-f0-9]{64}', str(item['sha256'])):
                raise NarratorError('invalid_manifest_digest')
            if not path.is_file() or path.is_symlink() or getattr(path.stat(), 'st_file_attributes', 0) & 0x400:
                raise NarratorError('narrator_artifact_unavailable')
            if time.monotonic() >= deadline:
                raise NarratorError('manifest_verification_deadline')
            try:
                actual = sha256_file(path, deadline=deadline)
            except VoiceError as exc:
                raise NarratorError('manifest_verification_deadline') from exc
            if actual != item['sha256']:
                raise NarratorError('narrator_artifact_changed')


def script_arguments(powershell, text, output):
    validate_text(text)
    return [str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-File',
            str(SCRIPT), '-Text', text, '-Output', str(output)]


class WindowsScriptRunner:
    """Start suspended, own the complete process tree, then resume execution."""
    def __call__(self, text, output, cancel):
        if cancel.is_set():
            raise NarratorError('cancelled')
        if os.name != 'nt':
            raise NarratorError('windows_host_required')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        handle = wintypes.HANDLE
        class Startup(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('reserved', wintypes.LPWSTR), ('desktop', wintypes.LPWSTR),
                ('title', wintypes.LPWSTR), ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD),
                ('ys', wintypes.DWORD), ('xc', wintypes.DWORD), ('yc', wintypes.DWORD), ('fill', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('show', wintypes.WORD), ('reserved2size', wintypes.WORD),
                ('reserved2', ctypes.c_void_p), ('stdin', handle), ('stdout', handle), ('stderr', handle)]
        class Process(ctypes.Structure):
            _fields_ = [('process', handle), ('thread', handle), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]
        class BasicLimits(ctypes.Structure):
            _fields_ = [('user', ctypes.c_int64), ('per_job', ctypes.c_int64), ('flags', wintypes.DWORD),
                ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t), ('active_limit', wintypes.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class Limits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io', ctypes.c_uint64 * 6), ('process_memory', ctypes.c_size_t),
                ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        class Accounting(ctypes.Structure):
            _fields_ = [('times', ctypes.c_int64 * 4), ('faults', wintypes.DWORD), ('total', wintypes.DWORD),
                ('active', wintypes.DWORD), ('terminated', wintypes.DWORD)]
        signatures = {
            'CreateJobObjectW': ([ctypes.c_void_p, wintypes.LPCWSTR], handle),
            'SetInformationJobObject': ([handle, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            'AssignProcessToJobObject': ([handle, handle], wintypes.BOOL),
            'ResumeThread': ([handle], wintypes.DWORD), 'TerminateJobObject': ([handle, wintypes.UINT], wintypes.BOOL),
            'TerminateProcess': ([handle, wintypes.UINT], wintypes.BOOL),
            'QueryInformationJobObject': ([handle, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            'WaitForSingleObject': ([handle, wintypes.DWORD], wintypes.DWORD),
            'GetExitCodeProcess': ([handle, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            'CloseHandle': ([handle], wintypes.BOOL),
            'CreateProcessW': ([wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(Startup), ctypes.POINTER(Process)], wintypes.BOOL)}
        for name, (arguments, result) in signatures.items():
            function = getattr(kernel, name); function.argtypes = arguments; function.restype = result
        powershell = _system_powershell()
        command = subprocess.list2cmdline(script_arguments(powershell, text, output))
        if len(command.encode('utf-16-le')) // 2 >= 32767:
            raise NarratorError('narration_command_too_long')
        job, process, assigned = kernel.CreateJobObjectW(None, None), Process(), False
        limits = Limits(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; no child breakaway.
        try:
            if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise NarratorError('process_isolation_unavailable')
            import msvcrt
            with open(os.devnull, 'r+b', buffering=0) as discard:
                null = msvcrt.get_osfhandle(discard.fileno())
                os.set_handle_inheritable(null, True)
                startup = Startup(cb=ctypes.sizeof(Startup), flags=0x100, stdin=null, stdout=null, stderr=null)
                try:
                    created = kernel.CreateProcessW(str(powershell), ctypes.create_unicode_buffer(command), None, None,
                        True, 0x4 | 0x08000000, None, str(output.parent), ctypes.byref(startup), ctypes.byref(process))
                finally:
                    os.set_handle_inheritable(null, False)
            if not created:
                raise NarratorError('narrator_start_failed')
            if not kernel.AssignProcessToJobObject(job, process.process):
                kernel.TerminateProcess(process.process, 1)
                raise NarratorError('process_isolation_unavailable', uncertain=True)
            assigned = True
            if kernel.ResumeThread(process.thread) == 0xffffffff:
                raise NarratorError('narrator_resume_failed', uncertain=True)
            deadline, stop_reason = time.monotonic() + SCRIPT_TIMEOUT_SECONDS, None
            while True:
                accounting = Accounting()
                if not kernel.QueryInformationJobObject(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                    raise NarratorError('process_outcome_unknown', uncertain=True)
                if accounting.active == 0:
                    break
                if stop_reason is None and (cancel.is_set() or time.monotonic() >= deadline or
                    (output.exists() and output.stat().st_size > MAX_WAV)):
                    stop_reason = 'cancelled' if cancel.is_set() else 'generation_timeout_or_size_limit'
                    if not kernel.TerminateJobObject(job, 1):
                        raise NarratorError('process_outcome_unknown', uncertain=True)
                    deadline = time.monotonic() + 5
                elif stop_reason is not None and time.monotonic() >= deadline:
                    raise NarratorError('process_outcome_unknown', uncertain=True)
                time.sleep(.05)
            if stop_reason:
                raise NarratorError(stop_reason)
            exit_code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(process.process, ctypes.byref(exit_code)) or exit_code.value != 0:
                raise NarratorError('narrator_process_failed')
        except NarratorError:
            raise
        except Exception as exc:
            raise NarratorError('process_outcome_unknown', uncertain=bool(process.process)) from exc
        finally:
            if process.process and not assigned:
                kernel.TerminateProcess(process.process, 1)
            for item in (process.thread, process.process, job):
                if item:
                    kernel.CloseHandle(item)


class NarratorStore:
    def __init__(self, spool, manifest, executor=None):
        self.spool, self.manifest = local_spool(spool), manifest
        self.executor = executor or WindowsScriptRunner()
        self.lock, self.stop = threading.RLock(), threading.Event()
        self.active, self.thread = None, None
        self.worker_fault = False
        self.lease = voice_lease(self.spool); self.lease.__enter__()
        try:
            self.db = sqlite3.connect(self.spool / 'host-narrations.sqlite', check_same_thread=False)
            self.db.row_factory = sqlite3.Row
            tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables:
                version = self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone() if 'metadata' in tables else None
                if version is None or version[0] != '1':
                    raise NarratorError('unsupported_host_database_schema')
            self.db.executescript("""PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
                PRAGMA max_page_count=131072;
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,request_sha TEXT NOT NULL,text TEXT NOT NULL,
                    text_sha TEXT NOT NULL,state TEXT NOT NULL,provenance TEXT NOT NULL,audio TEXT,error TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,state TEXT);
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append_only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append_only'); END;""")
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO metadata VALUES('schema_version','1')")
                interrupted = self.db.execute("SELECT id FROM jobs WHERE state='running'").fetchall()
                for row in interrupted:
                    self.db.execute("UPDATE jobs SET state='failed',error='outcome_unknown' WHERE id=?", (row['id'],))
                    self.db.execute("INSERT INTO events(job_id,state) VALUES(?,'failed_outcome_unknown')", (row['id'],))
                if interrupted:
                    self.db.execute("INSERT OR REPLACE INTO metadata VALUES('execution_hold','outcome_unknown')")
        except BaseException:
            if hasattr(self, 'db'):
                self.db.close()
            self.lease.__exit__(None, None, None)
            raise

    def held(self):
        return self.worker_fault or self.db.execute("SELECT 1 FROM metadata WHERE key='execution_hold'").fetchone() is not None

    def health(self):
        with self.lock:
            return {'schema_version': 1, 'service': SERVICE, 'narrator_id': NARRATOR,
                'status': 'blocked' if self.held() else 'ready', 'execution_hold': self.held(),
                'worker_fault': self.worker_fault,
                'queue_depth': self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0],
                'model_state': 'not_probed', 'device': 'not_verified', 'provenance': self.manifest.provenance}

    def get(self, job_id):
        if not valid_id(job_id):
            raise NarratorError('invalid_job_id')
        with self.lock:
            row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                raise NarratorError('job_not_found', 404)
            result = {'id': row['id'], 'state': row['state'], 'narrator_id': NARRATOR,
                'text_sha256': row['text_sha'], 'provenance': json.loads(row['provenance']),
                'error': row['error'], 'cancel_requested': bool(row['cancel_requested'])}
            if row['audio']:
                result['audio'] = json.loads(row['audio'])
            return result

    def submit(self, value):
        if not isinstance(value, dict) or set(value) != {'idempotency_key', 'text', 'narrator_id'}:
            raise NarratorError('invalid_narration_fields')
        if not valid_id(value['idempotency_key']) or value['narrator_id'] != NARRATOR:
            raise NarratorError('invalid_narrator_or_key')
        validate_text(value['text'])
        request_sha = digest(value); job_id = value['idempotency_key']
        with self.lock, self.db:
            existing = self.db.execute('SELECT request_sha FROM jobs WHERE id=?', (job_id,)).fetchone()
            if existing:
                if existing['request_sha'] != request_sha:
                    raise NarratorError('idempotency_conflict', 409)
                return self.get(job_id)
            if self.held():
                raise NarratorError('execution_outcome_requires_reconciliation', 503)
            count = self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0]
            if count >= 64 or self.db.execute('SELECT count(*) FROM jobs').fetchone()[0] >= 10000:
                raise NarratorError('queue_backpressure', 503)
            if shutil.disk_usage(self.spool).free < 256 * 1024 * 1024:
                raise NarratorError('disk_reserve_reached', 503)
            self.db.execute("INSERT INTO jobs(id,request_sha,text,text_sha,state,provenance) VALUES(?,?,?,?,'queued',?)",
                (job_id, request_sha, value['text'], hashlib.sha256(value['text'].encode()).hexdigest(), json.dumps(self.manifest.provenance)))
            self.db.execute("INSERT INTO events(job_id,state) VALUES(?,'queued')", (job_id,))
        return self.get(job_id)

    def cancel(self, job_id):
        with self.lock, self.db:
            value = self.get(job_id)
            if value['state'] == 'queued':
                self.db.execute("UPDATE jobs SET state='cancelled',cancel_requested=1 WHERE id=?", (job_id,))
                self.db.execute("INSERT INTO events(job_id,state) VALUES(?,'cancelled')", (job_id,))
            elif value['state'] == 'running':
                self.db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?', (job_id,))
                if self.active and self.active[0] == job_id:
                    self.active[1].set()
        return self.get(job_id)

    def run_next(self):
        with self.lock, self.db:
            if self.active or self.held():
                return False
            row = self.db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return False
            job_id, text = row['id'], row['text']
            self.db.execute("UPDATE jobs SET state='running' WHERE id=?", (job_id,))
            self.db.execute("INSERT INTO events(job_id,state) VALUES(?,'running')", (job_id,))
            cancel = threading.Event(); self.active = job_id, cancel
        audio, error, state, uncertain = None, None, 'completed', False
        launched, finished = False, False
        try:
            expected = {'idempotency_key': job_id, 'text': text, 'narrator_id': NARRATOR}
            if (row['text_sha'] != hashlib.sha256(text.encode()).hexdigest() or row['request_sha'] != digest(expected) or
                json.loads(row['provenance']) != self.manifest.provenance):
                raise NarratorError('stored_request_integrity_mismatch')
            self.manifest.verify()
            directory = self.spool / job_id
            directory.mkdir()
            local_spool(directory)
            output = directory / 'narration.wav'
            if cancel.is_set():
                raise NarratorError('cancelled')
            launched = True
            self.executor(text, output, cancel)
            finished = True
            if output.stat().st_size > MAX_WAV:
                raise NarratorError('invalid_audio_size')
            pcm = inspect_wav(output)
            with output.open('r+b') as stream:
                stream.flush(); os.fsync(stream.fileno())
            audio = {**pcm, 'duration': pcm['duration_seconds'], 'bytes': output.stat().st_size}
            del audio['duration_seconds']
        except NarratorError as exc:
            state, error, uncertain = ('cancelled' if str(exc) == 'cancelled' else 'failed'), str(exc), exc.uncertain
        except (OSError, ValueError, VoiceError):
            state, error = 'failed', 'audio_or_local_validation_failed'
            uncertain = launched and not finished
        except Exception:
            state, error, uncertain = 'failed', 'outcome_unknown', True
        with self.lock, self.db:
            self.db.execute('UPDATE jobs SET state=?,error=?,audio=? WHERE id=?',
                (state, error, json.dumps(audio) if audio else None, job_id))
            self.db.execute('INSERT INTO events(job_id,state) VALUES(?,?)', (job_id, state))
            if uncertain:
                self.db.execute("INSERT OR REPLACE INTO metadata VALUES('execution_hold','outcome_unknown')")
            self.active = None
        return True

    def audio_path(self, job_id):
        value = self.get(job_id)
        if value['state'] != 'completed':
            raise NarratorError('audio_not_ready', 409)
        path = self.spool / job_id / 'narration.wav'
        if path.is_symlink() or path.stat().st_size != value['audio']['bytes'] or sha256_file(path) != value['audio']['sha256']:
            raise NarratorError('audio_integrity_mismatch', 409)
        return path, value['audio']

    def start(self):
        def work():
            while not self.stop.is_set():
                try:
                    if not self.run_next():
                        self.stop.wait(.1)
                except Exception:
                    with self.lock:
                        self.worker_fault = True
                        try:
                            with self.db:
                                self.db.execute("INSERT OR REPLACE INTO metadata VALUES('execution_hold','worker_fault_requires_reconciliation')")
                        except sqlite3.Error:
                            pass
                    return
        self.thread = threading.Thread(target=work, name='collector-host-narrator', daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        with self.lock:
            if self.active:
                self.active[1].set()
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                raise NarratorError('host_worker_shutdown_pending', uncertain=True)
        self.db.close(); self.lease.__exit__(None, None, None)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NarratorError('duplicate_json_field')
        result[key] = value
    return result


class NarratorHTTPServer(HTTPServer):
    # shortcut: sequential requests can delay health/cancel up to30s; revisit for concurrent operators.
    request_queue_size = 8
    def server_bind(self):
        if os.name == 'nt':
            # Windows SO_REUSEADDR permits another listener to intercept requests.
            self.allow_reuse_address = False
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()
    def __init__(self, address, store, credential):
        if address[0] != '127.0.0.1' or not isinstance(credential, str) or not 32 <= len(credential) <= 2048 or any(ord(c) < 33 or ord(c) > 126 for c in credential):
            raise NarratorError('private_host_auth_configuration_required')
        self.store, self.credential = store, credential.encode()
        super().__init__(address, NarratorHandler)
    def handle_error(self, request, client_address):
        pass  # Request bodies, credentials and private paths never reach console logs.


class NarratorHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, format, *args):
        pass
    def handle(self):
        self.close_connection = True
        self.connection.settimeout(5)
        try:
            with socket_deadline(time.monotonic() + REQUEST_DEADLINE_SECONDS, None, False) as (register, check):
                register(self.connection)
                super().handle()
        except (OSError, VoiceError):
            pass
    def send_error(self, code, message=None, explain=None):
        self.json_reply(code, {'error': 'invalid_http_request'})
    def parse_request(self):
        if not super().parse_request():
            return False
        auth = self.headers.get_all('Authorization', [])
        if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), b'Bearer ' + self.server.credential):
            self.json_reply(401, {'error': 'unauthorized'})
            return False
        return True
    def json_reply(self, status, value):
        data = json.dumps(value, separators=(',', ':')).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data))); self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close'); self.end_headers(); self.wfile.write(data)
        self.close_connection = True
    def body(self):
        if self.headers.get_all('Transfer-Encoding', []) or len(self.headers.get_all('Content-Length', [])) != 1:
            raise NarratorError('fixed_content_length_required')
        size = self.headers.get('Content-Length', '')
        if not re.fullmatch('[0-9]{1,6}', size) or not 0 < int(size) <= MAX_BODY:
            raise NarratorError('request_too_large', 413)
        if len(self.headers.get_all('Content-Type', [])) != 1 or self.headers.get_content_type() != 'application/json':
            raise NarratorError('json_required', 415)
        raw = self.rfile.read(int(size))
        if len(raw) != int(size):
            raise NarratorError('incomplete_request')
        try:
            def reject_constant(value):
                raise NarratorError('non_finite_json')
            return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        except (ValueError, UnicodeError) as exc:
            raise NarratorError('invalid_json') from exc
    def dispatch(self):
        try:
            if self.command == 'GET' and self.path == '/health':
                self.json_reply(200, self.server.store.health()); return
            if self.command == 'POST' and self.path == '/v1/narrations':
                self.json_reply(200, self.server.store.submit(self.body())); return
            match = re.fullmatch('/v1/narrations/([a-f0-9]{32})(/audio|/cancel)?', self.path)
            if not match:
                raise NarratorError('route_not_found', 404)
            job_id, suffix = match.groups()
            if self.command == 'GET' and suffix is None:
                self.json_reply(200, self.server.store.get(job_id))
            elif self.command == 'POST' and suffix == '/cancel':
                if self.body() != {}:
                    raise NarratorError('empty_cancel_body_required')
                self.json_reply(200, self.server.store.cancel(job_id))
            elif self.command == 'GET' and suffix == '/audio':
                path, audio = self.server.store.audio_path(job_id)
                self.send_response(200); self.send_header('Content-Type', 'audio/wav')
                self.send_header('Content-Length', str(audio['bytes'])); self.send_header('Connection', 'close')
                self.send_header('X-Content-SHA256', audio['sha256']); self.end_headers()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(65536), b''):
                        self.wfile.write(block)
            else:
                raise NarratorError('method_not_allowed', 405)
        except NarratorError as exc:
            self.json_reply(exc.status, {'error': str(exc)})
        except (OSError, ValueError, VoiceError):
            self.json_reply(503, {'error': 'host_request_unavailable'})
    do_GET = dispatch
    do_POST = dispatch
    do_PUT = dispatch
    do_DELETE = dispatch
    do_PATCH = dispatch


def main(argv=None):
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector restricted host narrator')
    parser.add_argument('command', choices=('inspect-script', 'validate-manifest', 'validate-spool', 'credential-save', 'serve'))
    parser.add_argument('--manifest', type=Path); parser.add_argument('--spool', type=Path)
    parser.add_argument('--port', type=int, default=39110)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate-spool':
            if not args.spool:
                parser.error('--spool is required')
            verify_spool_acl(args.spool)
            print(json.dumps({'status': 'PASS', 'scope': 'host_spool_acl_only'})); return 0
        if args.command == 'inspect-script':
            files = {'script': SCRIPT, 'reference': REFERENCE, 'cli': CLI}
            print(json.dumps({'status': 'INSPECTED_FILES_ONLY', 'files': {role: sha256_file(path) for role, path in files.items()},
                'model_revision': 'NOT_VERIFIED', 'rights': 'NOT_VERIFIED', 'runtime_parity': 'NOT_TESTED'}))
            return 0
        if args.command == 'credential-save':
            if not __import__('sys').stdin.isatty():
                raise NarratorError('interactive_secret_entry_required')
            from .collector_credentials import write_secret
            secret = getpass.getpass('New app-specific host narrator bearer (at least32 characters): ')
            if len(secret) < 32:
                raise NarratorError('credential_too_short')
            write_secret(CREDENTIAL_TARGET, secret)
            print(json.dumps({'status': 'SAVED'})); return 0
        if not args.manifest:
            parser.error('--manifest is required')
        manifest = NarratorManifest(args.manifest)
        if args.command == 'validate-manifest':
            print(json.dumps({'status': 'PASS', 'provenance': manifest.provenance})); return 0
        if os.name != 'nt' or not args.spool or not 1024 <= args.port <= 65535:
            raise NarratorError('windows_private_host_configuration_required')
        verify_spool_acl(args.spool)
        from .collector_credentials import read_secret
        secret, _ = read_secret(CREDENTIAL_TARGET)
        store = NarratorStore(args.spool, manifest)
        try:
            server = NarratorHTTPServer(('127.0.0.1', args.port), store, secret)
            try:
                store.start(); server.serve_forever(poll_interval=.1)
            finally:
                server.server_close()
        finally:
            store.close()
        return 0
    except (NarratorError, VoiceError, OSError, ValueError, sqlite3.Error) as exc:
        code = str(exc) if isinstance(exc, (NarratorError, VoiceError)) else 'host_configuration_or_storage_unavailable'
        print(json.dumps({'status': 'BLOCKED', 'error': code})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
