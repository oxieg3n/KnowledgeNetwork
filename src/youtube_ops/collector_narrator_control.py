"""Owner-only fixed narrator lifecycle control; never a general execution bridge."""
from __future__ import annotations

import ctypes
from contextlib import closing
import signal
import hmac
import hashlib
import http.client
import json
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import subprocess
import threading
import time

from . import collector_credentials as credentials
from .collector_narration_common import digest, inspect_wav, socket_deadline
from .collector_narrator_host import (CREDENTIAL_TARGET, NarratorManifest,
    NarratorStore, NarratorHTTPServer, SETTINGS, verify_spool_acl, _system_powershell)

SPOOL = Path('D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001')
MANIFEST = SPOOL / 'review/narrator-manifest.LOCAL-USE-CANDIDATE.private.json'
OPERATIONS = frozenset('narrator-health narrator-validate narrator-start narrator-stop narrator-credential-ensure narrator-verify narrator-diagnostics narrator-reconcile'.split())


PRIVATE_ACL_CHECK = r"""
$ErrorActionPreference='Stop'
try {
 $r=[Console]::In.ReadToEnd() | ConvertFrom-Json
 $allowed=@([string]$r.owner_sid,'S-1-5-18','S-1-5-32-544')
 foreach($path in @($r.paths)) {
  $acl=Get-Acl -LiteralPath ([string]$path)
  $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
  if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed) {throw 'unsafe'}
  $ownerFull=$false
  $ownerInherit=$false
  foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
   if($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or $rule.IdentityReference.Value -notin $allowed) {throw 'unsafe'}
   if($rule.IdentityReference.Value -eq $r.owner_sid -and ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -eq [Security.AccessControl.FileSystemRights]::FullControl) {
    if(($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -eq 0) {$ownerFull=$true}
    if(($rule.InheritanceFlags -band [Security.AccessControl.InheritanceFlags]::ContainerInherit) -and ($rule.InheritanceFlags -band [Security.AccessControl.InheritanceFlags]::ObjectInherit) -and ($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::NoPropagateInherit) -eq 0) {$ownerInherit=$true}
   }
  }
  if(-not $ownerFull -or ([string]$path -eq [string]$r.spool -and -not $ownerInherit)) {throw 'unsafe'}
 }
 [Console]::Out.Write('{"ok":true}')
 exit 0
} catch { [Console]::Out.Write('{"ok":false}'); exit 1 }
"""


def verify_private_paths(paths, owner_sid):
    """Read-only private ACL gate; never repair preexisting private evidence."""
    paths = list(dict.fromkeys(str(path) for path in paths))
    if not 1 <= len(paths) <= 10000:
        raise ControlBlocked('private_acl_inspection_limit')
    payload = json.dumps({'paths': paths, 'owner_sid': owner_sid, 'spool': str(SPOOL)})
    if len(payload) > 4 * 1024 * 1024:
        raise ControlBlocked('private_acl_inspection_limit')
    try:
        result = subprocess.run([str(_system_powershell()), '-NoLogo', '-NoProfile',
            '-NonInteractive', '-Command', PRIVATE_ACL_CHECK], input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
            timeout=10, check=False, shell=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        raise ControlBlocked('private_file_acl_unverified') from None
    if result.returncode or result.stdout != '{"ok":true}':
        raise ControlBlocked('private_file_acl_unverified')


class ControlBlocked(RuntimeError):
    pass


def _helpers():
    # No configuration reads or native identity calls at module import time.
    from . import collector_narrator_pipe
    return collector_narrator_pipe


class NarratorControl:
    def __init__(self, config):
        self.config = config
        self.lock = threading.RLock()
        self.store = self.server = self.thread = None
        self._identity()
        verify_spool_acl(SPOOL)
        self._paths()
        self.db = sqlite3.connect(SPOOL / 'narrator-control.sqlite', timeout=2, check_same_thread=False)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA busy_timeout=2000')
        self.db.execute('CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, operation TEXT NOT NULL, state TEXT NOT NULL, response TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS audit(request_id TEXT PRIMARY KEY, owner_sid TEXT NOT NULL, operation TEXT NOT NULL, outcome TEXT NOT NULL, duration_ms INTEGER NOT NULL, result_sha256 TEXT NOT NULL)')
        # A prior started action may have mutated the host. Never replay it.
        self.db.commit()

    def _identity(self):
        sid, elevated = _helpers().windows_identity()
        if sid != self.config['owner_sid'] or elevated:
            raise ControlBlocked('owner_limited_identity_required')

    def _paths(self):
        helper = _helpers()
        if not SPOOL.is_dir():
            raise ControlBlocked('spool_unavailable')
        for directory in (SPOOL, *SPOOL.parents):
            if directory.is_symlink() or getattr(directory.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ControlBlocked('spool_path_denied')
        private = [SPOOL]
        for name in ('narrator-control.sqlite', 'narrator-control.sqlite-wal',
                     'narrator-control.sqlite-shm', 'narrator-control.sqlite-journal'):
            path = SPOOL / name
            if path.exists():
                helper.local_file(path)
                private.append(path)
        verify_private_paths(private, self.config['owner_sid'])

    def _manifest(self, full=False):
        helper = _helpers()
        path = helper.local_file(MANIFEST)
        verify_private_paths([MANIFEST.parent, path], self.config['owner_sid'])
        with path.open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ControlBlocked('manifest_size_invalid')
        if hashlib.sha256(raw).hexdigest() != self.config['manifest_sha256']:
            raise ControlBlocked('manifest_changed')
        value = json.loads(raw.decode('utf-8-sig'))
        if full:
            manifest = NarratorManifest(path)
            if manifest.value != value:
                raise ControlBlocked('manifest_changed')
            return manifest
        artifacts = value['artifacts']
        licenses = [item for item in artifacts if item['role'] == 'license_evidence']
        if len(licenses) != 1:
            raise ControlBlocked('manifest_provenance_invalid')
        return {'script_sha256': value['script_sha256'],
            'config_sha256': digest({'settings': SETTINGS, 'model_id': value['model_id'],
                'model_revision': value['model_revision'], 'cli_version': value['cli_version'],
                'artifacts': sorted([{'role': item['role'], 'sha256': item['sha256']} for item in artifacts], key=lambda item: (item['role'], item['sha256']))}),
            'model_revision': value['model_revision'], 'license_evidence_sha256': licenses[0]['sha256']}

    def _secret(self):
        secret, _ = credentials.read_secret(CREDENTIAL_TARGET)
        credentials.validate_secret(secret, 'scoped_bearer')
        if len(secret) < 32:
            raise ControlBlocked('credential_invalid')
        return secret

    def _credential_ensure(self):
        try:
            self._secret()
            return {'credential': 'existing_verified', 'secret_returned': False}
        except ValueError as exc:
            if str(exc) != 'BLOCKED_VOICE_CREDENTIAL_MISSING':
                raise ControlBlocked('credential_unverified') from None
            # Existing helper conflates all native failures; confirm ERROR_NOT_FOUND.
            if ctypes.get_last_error() != 1168:
                raise ControlBlocked('credential_missing_not_confirmed')
        secret = secrets.token_urlsafe(48)
        credentials.write_secret(CREDENTIAL_TARGET, secret)
        if not hmac.compare_digest(self._secret(), secret):
            raise ControlBlocked('credential_readback_failed')
        return {'credential': 'created_verified', 'secret_returned': False}

    def _request(self, auth):
        connection = http.client.HTTPConnection('127.0.0.1', 39110, timeout=10)
        try:
            with socket_deadline(time.monotonic() + 10, None, False) as (register, check):
                connection.connect()
                register(connection.sock)
                connection.request('GET', '/health', headers={} if auth is None else {'Authorization': 'Bearer ' + auth})
                response = connection.getresponse()
                raw = response.read(65537)
                check()
                if len(raw) > 65536:
                    raise ControlBlocked('health_response_size_invalid')
                return response.status, json.loads(raw) if response.status == 200 else None
        finally:
            connection.close()

    def _health(self):
        if self.server is None:
            raise ControlBlocked('listener_not_owned_by_broker')
        code, value = self._request(self._secret())
        if (code != 200 or not isinstance(value, dict) or
                value.get('service') != 'knowledge-network-voxcpm2' or
                value.get('narrator_id') != 'oxiegen-narrator' or
                value.get('provenance') != self._manifest()):
            raise ControlBlocked('authenticated_health_unverified')
        return {key: value[key] for key in ('status', 'execution_hold', 'queue_depth', 'provenance')}

    def _inspect_jobs(self, verify_audio=False):
        deadline = time.monotonic() + 110
        path = SPOOL / 'host-narrations.sqlite'
        if not path.exists():
            return {'jobs': 0, 'completed_verified': 0, 'execution_hold': False, 'pending': 0}
        _helpers().local_file(path)
        private = [path]
        for suffix in ('-wal', '-shm', '-journal'):
            if Path(str(path) + suffix).exists():
                _helpers().local_file(Path(str(path) + suffix))
                private.append(Path(str(path) + suffix))
        verify_private_paths(private, self.config['owner_sid'])
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            rows = db.execute('SELECT id,state,audio FROM jobs LIMIT 10001').fetchall()
            if len(rows) > 10000:
                raise ControlBlocked('job_inspection_limit')
            held = bool(db.execute("SELECT 1 FROM metadata WHERE key='execution_hold'").fetchone())
            completed = 0
            wav_paths = []
            if verify_audio:
                for job_id, state, _ in rows:
                    if state == 'completed':
                        if not isinstance(job_id, str) or not re.fullmatch('[a-f0-9]{32}', job_id):
                            raise ControlBlocked('stored_job_identity_invalid')
                        wav = _helpers().local_file(SPOOL / job_id / 'narration.wav')
                        wav_paths.extend((wav.parent, wav))
                for offset in range(0, len(wav_paths), 500):
                    if time.monotonic() >= deadline:
                        raise ControlBlocked('private_audio_inspection_deadline')
                    verify_private_paths(wav_paths[offset:offset + 500], self.config['owner_sid'])
            for job_id, state, audio in rows:
                if time.monotonic() >= deadline:
                    raise ControlBlocked('private_audio_inspection_deadline')
                if not isinstance(job_id, str) or not re.fullmatch('[a-f0-9]{32}', job_id):
                    raise ControlBlocked('stored_job_identity_invalid')
                if verify_audio and state == 'completed':
                    recorded = json.loads(audio)
                    wav = _helpers().local_file(SPOOL / job_id / 'narration.wav')
                    if (not isinstance(recorded, dict) or
                            any(type(recorded.get(key)) is not int for key in ('bytes', 'frames', 'sample_rate', 'channels', 'sample_width')) or
                            type(recorded.get('duration')) not in (int, float) or
                            wav.stat().st_size != recorded['bytes']):
                        raise ControlBlocked('stored_audio_integrity_failed')
                    measured = inspect_wav(wav)
                    if (measured['sha256'] != recorded.get('sha256') or
                            any(measured[key] != recorded[key] for key in ('frames', 'sample_rate', 'channels', 'sample_width')) or
                            measured['duration_seconds'] != recorded['duration']):
                        raise ControlBlocked('stored_audio_integrity_failed')
                    completed += 1
        return {'jobs': len(rows), 'completed_verified': completed, 'execution_hold': held,
            'pending': sum(state in ('running', 'queued') for _, state, _ in rows)}

    def _start(self):
        if self.server is not None:
            return {'ownership': 'this_broker', **self._health()}
        # Occupancy precheck only; the actual HTTPServer bind remains authoritative.
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', 39110))
            except OSError:
                raise ControlBlocked('listener_unowned_or_occupied') from None
        manifest = self._manifest(full=True)
        jobs = self._inspect_jobs()
        if jobs['pending'] or jobs['execution_hold']:
            raise ControlBlocked('host_jobs_require_reconciliation')
        secret = self._secret()
        store = NarratorStore(SPOOL, manifest)
        try:
            server = NarratorHTTPServer(('127.0.0.1', 39110), store, secret)
        except BaseException:
            store.close()
            raise
        self.store, self.server = store, server
        self.thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
        self.thread.start()
        store.start()
        return {'ownership': 'this_broker', **self._health()}

    def _stop(self):
        if self.server is None:
            raise ControlBlocked('listener_not_owned_by_broker')
        self.server.shutdown()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise ControlBlocked('host_shutdown_outcome_unknown')
        with self.store.lock:
            health = self.store.health()
            if self.store.active or health['queue_depth'] or health['execution_hold']:
                self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
                self.thread.start()
                raise ControlBlocked('host_jobs_require_reconciliation')
        self.server.server_close()
        self.store.close()
        self.server = self.store = self.thread = None
        return {'ownership': 'stopped_this_broker'}

    def _execute(self, operation):
        if operation == 'narrator-credential-ensure':
            return self._credential_ensure()
        if operation == 'narrator-start':
            return self._start()
        if operation == 'narrator-stop':
            return self._stop()
        if operation == 'narrator-validate':
            return {'provenance': self._manifest(full=True).provenance}
        if operation == 'narrator-health':
            return self._health()
        if operation == 'narrator-diagnostics':
            health = self._health()
            if self._request(None)[0] != 401 or self._request(self._secret() + '-invalid')[0] != 401:
                raise ControlBlocked('authentication_rejection_unverified')
            return {**health, 'missing_bearer': 401, 'wrong_bearer': 401, 'inference_submitted': False}
        if operation == 'narrator-verify':
            self._manifest()
            return self._inspect_jobs(verify_audio=True)
        unknown = self.db.execute("SELECT id,operation FROM requests WHERE state='started' ORDER BY rowid LIMIT 20").fetchall()
        # The current inspection itself is started, but is not a historical crash hold.
        unknown = [(job_id, op) for job_id, op in unknown if job_id != self._current_request_id]
        count = self.db.execute("SELECT count(*) FROM requests WHERE state='started' AND id<>?", (self._current_request_id,)).fetchone()[0]
        history = self.db.execute("SELECT id,operation,state,response FROM requests WHERE operation IN ('narrator-start','narrator-stop','narrator-credential-ensure') AND id<>? ORDER BY rowid DESC LIMIT 20", (self._current_request_id,)).fetchall()
        recent = []
        for job_id, op, state, response in history:
            outcome = json.loads(response).get('status') if state == 'finished' and response else None
            if outcome not in (None, 'PASS', 'BLOCKED'):
                raise ControlBlocked('control_ledger_response_invalid')
            recent.append({'request_id': job_id, 'operation': op, 'state': state, 'outcome': outcome})
        return {**self._inspect_jobs(), 'inspection_only': True, 'replayed': False,
            'control_execution_hold': bool(count), 'unknown_control_requests': count, 'recent_mutations': recent,
            'requests': [{'request_id': job_id, 'operation': op, 'state': 'outcome_unknown'} for job_id, op in unknown]}

    def handle(self, request):
        request_id = request.get('request_id') if isinstance(request, dict) else None
        operation = request.get('operation') if isinstance(request, dict) else None
        base = {'schema_version': 1, 'request_id': request_id, 'operation': operation}
        if (not isinstance(request, dict) or set(request) != {'schema_version', 'request_id', 'operation'} or
                type(request['schema_version']) is not int or request['schema_version'] != 1 or
                not isinstance(request_id, str) or not re.fullmatch('[a-f0-9]{32}', request_id) or
                not isinstance(operation, str) or operation not in OPERATIONS):
            return {**base, 'status': 'BLOCKED', 'error': 'invalid_control_request'}
        with self.lock:
            inserted = False
            try:
                self._identity()
                verify_spool_acl(SPOOL)
                self._paths()
                old = self.db.execute('SELECT operation,state,response FROM requests WHERE id=?', (request_id,)).fetchone()
                if old:
                    if old[0] != operation:
                        raise ControlBlocked('request_id_conflict')
                    if old[1] != 'finished':
                        raise ControlBlocked('control_outcome_unknown_do_not_replay')
                    return json.loads(old[2])
                if operation in ('narrator-start', 'narrator-stop', 'narrator-credential-ensure') and self.db.execute("SELECT 1 FROM requests WHERE state='started' LIMIT 1").fetchone():
                    raise ControlBlocked('control_previous_outcome_unknown')
                if self.db.execute('SELECT count(*) FROM requests').fetchone()[0] >= 10000:
                    raise ControlBlocked('control_ledger_full')
                with self.db:
                    self.db.execute('INSERT INTO requests VALUES(?,?,?,NULL)', (request_id, operation, 'started'))
                inserted = True
                started = time.monotonic()
                self._current_request_id = request_id
                result = self._execute(operation)
                if time.monotonic() - started > 120:
                    raise ControlBlocked('control_deadline_outcome_requires_inspection')
                response = {**base, 'status': 'PASS', 'result': result}
            except ControlBlocked as exc:
                response = {**base, 'status': 'BLOCKED', 'error': str(exc)}
            except Exception:
                response = {**base, 'status': 'BLOCKED', 'error': 'control_action_unverified'}
            uncertain = response.get('error') in ('control_action_unverified', 'control_deadline_outcome_requires_inspection', 'host_shutdown_outcome_unknown')
            if inserted and not uncertain and self.db.execute('SELECT state FROM requests WHERE id=?', (request_id,)).fetchone() == ('started',):
                with self.db:
                    self.db.execute('UPDATE requests SET state=?,response=? WHERE id=?',
                        ('finished', json.dumps(response, separators=(',', ':')), request_id))
                    self.db.execute('INSERT INTO audit VALUES(?,?,?,?,?,?)', (request_id, self.config['owner_sid'], operation, response['status'], max(0, int((time.monotonic() - started) * 1000)), digest(response)))
            return response


def main():
    helper = _helpers()
    config = helper.load_config()
    control = NarratorControl(config)
    cancel = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: cancel.set())
    helper.allow_bridge_inspection(config)
    try:
        helper.serve(config, control.handle, cancel)
    finally:
        if control.server is not None:
            try:
                control._stop()
            except ControlBlocked:
                # Never cancel active speech as a side effect of control shutdown.
                # Keep the broker alive until its owned queue can safely close.
                while control.server is not None:
                    time.sleep(1)
                    try:
                        control._stop()
                    except ControlBlocked:
                        pass
        control.db.close()


if __name__ == '__main__':
    main()
