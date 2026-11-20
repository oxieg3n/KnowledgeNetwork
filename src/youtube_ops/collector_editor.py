"""Restricted OpenShot 4.1.1 client for trusted, local review-only projects.

Native OpenShot state stays authoritative. This is not a renderer or a second
timeline. The worker must serialize calls and keep the vault/session registry
private; this client is not a sandbox for an unrestricted desktop connection.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid


MAX_JSON = 2 * 1024 * 1024
MEDIA = {'.mp4', '.mov', '.mkv', '.png', '.jpg', '.jpeg', '.wav', '.mp3', '.flac'}
CLIP_VALUES = {'position', 'start', 'end', 'layer', 'volume', 'alpha', 'scale_x',
               'scale_y', 'location_x', 'location_y', 'rotation', 'has_audio', 'has_video'}
TEXT_STYLE = {'text', 'font_family', 'font_size', 'font_bold', 'font_italic',
              'alignment', 'width', 'color', 'background', 'background_padding',
              'background_corner', 'stroke', 'stroke_width', 'line_spacing', 'place'}
METHODS = {
    'file.import': {'path'},
    'clip.add': {'file_id', 'layer', 'position', 'start', 'end', 'volume', 'audio_only'},
    'clip.set': {'id', 'values'}, 'clip.remove': {'id'},
    'clip.split': {'id', 'at'},
    'clip.fade': {'id', 'fade_in', 'fade_out', 'property', 'value'},
    'clip.keyframe.set': {'id', 'property', 'space', 'unit', 'at', 'value', 'interpolation'},
    'text.add': TEXT_STYLE | {'layer', 'position', 'duration'},
    'text.set': TEXT_STYLE | {'id', 'this_clip_only'},
    'effects.add': {'clip_id', 'type'},
    'effects.set': {'id', 'values'},
    'project.profile.set': {'values'},
}


class EditorError(RuntimeError):
    """A safe status code, without native logs or session credentials."""
    def __init__(self, code, native_session_id=None):
        super().__init__(code)
        self.native_session_id = native_session_id


def _receipt_metadata(path):
    before = path.lstat()
    if (path.is_symlink() or getattr(before, 'st_file_attributes', 0) & 0x400
            or not path.is_file() or before.st_nlink != 1 or before.st_size > MAX_JSON):
        raise EditorError('pending_retention_source_unverified')
    security = None
    if os.name == 'nt':
        api = ctypes.WinDLL('advapi32', use_last_error=True).GetFileSecurityW
        api.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p,
                        ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
        api.restype = ctypes.c_int
        size = ctypes.c_uint32()
        api(str(path), 7, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise EditorError('pending_retention_security_unverified')
        data = ctypes.create_string_buffer(size.value)
        if not api(str(path), 7, data, len(data), ctypes.byref(size)):
            raise EditorError('pending_retention_security_unverified')
        security = hashlib.sha256(data.raw[:size.value]).hexdigest()
    with path.open('rb') as stream:
        raw = stream.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        raise EditorError('pending_retention_source_unverified')
    value = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': before.st_size,
             'file_identity': [before.st_dev, before.st_ino], 'mode': before.st_mode,
             'owner_group_dacl_sha256': security}
    after = path.lstat()
    if any(getattr(before, key) != getattr(after, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')):
        raise EditorError('pending_retention_source_changed')
    return value


def _move_receipt(source, target):
    # Both paths are in the same private receipt directory; no replace/copy fallback.
    if os.name == 'nt':
        move = ctypes.WinDLL('kernel32', use_last_error=True).MoveFileExW
        move.argtypes, move.restype = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32], ctypes.c_int
        succeeded = move(str(source), str(target), 0)
    elif sys.platform.startswith('linux'):
        move = getattr(ctypes.CDLL(None, use_errno=True), 'renameat2', None)
        if move is None:
            raise EditorError('pending_retention_move_unavailable')
        move.argtypes, move.restype = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint], ctypes.c_int
        succeeded = move(-100, os.fsencode(source), -100, os.fsencode(target), 1) == 0
    else:
        raise EditorError('pending_retention_move_unavailable')
    if not succeeded:
        raise EditorError('pending_retention_move_unverified')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    temporary = path.with_suffix('.tmp')
    with temporary.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def bounded(value, depth=0):
    if depth > 8:
        raise ValueError('Nested input exceeds limit')
    if isinstance(value, dict):
        if len(value) > 32:
            raise ValueError('Object exceeds limit')
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError('Object keys must be strings')
            bounded(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 256:
            raise ValueError('Array exceeds limit')
        for item in value:
            bounded(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > 4096 or '\x00' in value:
            raise ValueError('Text exceeds limit or contains NUL')
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value) or abs(value) > 100_000_000:
            raise ValueError('Number exceeds limit')
    elif value is not None and not isinstance(value, bool):
        raise ValueError('Unsupported JSON value')


class OpenShot:
    def __init__(self, executable, executable_sha256, vault, session=None):
        self.executable = Path(executable).resolve(strict=True)
        if self.executable.name.lower() != 'openshot-qt-cmd.exe':
            raise ValueError('Use the verified Windows console executable')
        if not re.fullmatch('[0-9a-f]{64}', executable_sha256):
            raise ValueError('Executable SHA-256 required')
        if digest(self.executable) != executable_sha256:
            raise EditorError('executable_hash_mismatch')
        self.executable_sha256 = executable_sha256
        self.vault = Path(vault).resolve(strict=True)
        if not self.vault.is_dir() or str(self.vault).startswith('\\\\'):
            raise ValueError('A local private vault directory is required')
        if session is not None and not re.fullmatch('[a-zA-Z0-9_-]{1,80}', session):
            raise ValueError('Invalid native session ID')
        self.session = session
        self.receipts = self.vault / '.collector-editor'
        self.receipts.mkdir(exist_ok=True)
        if self.receipts.resolve() != self.receipts:
            raise ValueError('Editor receipts cannot be redirected through a link')
        self.font_directory = None
        if os.name == 'nt':
            self.font_directory = (Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Fonts').resolve(strict=True)
            if not self.font_directory.is_dir() or not any(self.font_directory.glob('*.ttf')):
                raise EditorError('system_fonts_unavailable')

    def _managed_session(self):
        if not self.session or not (self.receipts / ('session-' + self.session + '.json')).is_file():
            raise EditorError('unmanaged_native_session')
        marker = self.receipts / ('session-' + self.session + '.json')
        if marker.stat().st_size > 1024:
            raise EditorError('unmanaged_native_session')
        record = json.loads(marker.read_text())
        expected = {'session_id': self.session, 'executable_sha256': self.executable_sha256}
        font_directory = record.pop('font_directory', None)
        if record != expected or font_directory not in (None, str(self.font_directory)):
            raise EditorError('unmanaged_native_session')

    def local_path(self, path, suffixes, exists=True):
        candidate = Path(path)
        if not candidate.is_absolute() or '..' in candidate.parts:
            raise ValueError('Absolute vault path required')
        candidate = candidate.resolve(strict=exists)
        if not candidate.is_relative_to(self.vault) or candidate.suffix.lower() not in suffixes:
            raise ValueError('Path outside vault or unsupported media type')
        if exists and not candidate.is_file():
            raise ValueError('Local file required')
        if not exists and (candidate.exists() or not candidate.parent.is_dir()):
            raise ValueError('Output must be new with an existing parent')
        return candidate

    def _invoke(self, arguments, session=True):
        if self.vault.resolve() != self.vault or self.receipts.resolve() != self.receipts:
            raise EditorError('vault_path_changed')
        if digest(self.executable) != self.executable_sha256:
            raise EditorError('executable_hash_mismatch')
        args = [str(self.executable), '--cli', '--timeout', '25']
        if session:
            self._managed_session()
            args += ['--session', self.session]
        args += arguments
        env = dict(os.environ)
        env.pop('OPENSHOT_SESSION', None)
        env['KN_COLLECTOR_RETAIN_ARTIFACTS'] = '1'
        if self.font_directory is not None:
            # Qt's Windows offscreen export uses FreeType, not the Windows font database.
            env['QT_QPA_FONTDIR'] = str(self.font_directory)
        # Retain the installed user's registry; never return its authentication record.
        # Native failures can contain useful private evidence; retain exact owned
        # output files instead of deleting them when the subprocess closes.
        invocation = self.receipts / ('invoke-' + uuid.uuid4().hex)
        invocation.mkdir()
        with (invocation / 'stdout.private.log').open('x+b') as stdout, \
                (invocation / 'stderr.private.log').open('x+b') as stderr:
            process = subprocess.Popen(args, cwd=self.vault, env=env, shell=False,
                                       stdout=stdout, stderr=stderr,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            # Cold frozen imports precede the native start command's own 30s
            # readiness window. Preserve its structured timeout/session identity.
            deadline = time.monotonic() + (90 if not session else 40)
            while process.poll() is None:
                if max(os.fstat(stdout.fileno()).st_size, os.fstat(stderr.fileno()).st_size) > MAX_JSON:
                    process.kill(); process.wait()
                    raise EditorError('native_output_limit_reconcile_required')
                if time.monotonic() > deadline:
                    process.kill(); process.wait()
                    raise EditorError('native_timeout_reconcile_required')
                time.sleep(0.05)
            stream = stdout if process.returncode == 0 else stderr
            stream.seek(0)
            raw = stream.read(MAX_JSON + 1)
            if len(raw) > MAX_JSON:
                raise EditorError('native_output_limit_reconcile_required')
            try:
                reply = json.loads(raw)
            except (ValueError, UnicodeError):
                raise EditorError('invalid_native_response') from None
            if not isinstance(reply, dict):
                raise EditorError('invalid_native_response')
            if process.returncode or not reply.get('ok'):
                error = reply.get('error')
                code = error.get('code', 'native_failed') if isinstance(error, dict) else 'native_failed'
                if not isinstance(code, str) or not re.fullmatch('[a-z_]{1,80}', code):
                    code = 'native_failed'
                owned = None
                if code == 'startup_timeout' and isinstance(error, dict):
                    message = error.get('message', '')
                    match = re.search(r'([0-9a-f]{32})\.log\s*$', message) if isinstance(message, str) else None
                    owned = match.group(1) if match else None
                raise EditorError(code, native_session_id=owned)
            if 'result' not in reply:
                raise EditorError('invalid_native_response')
            return reply['result']

    def start(self, show=False):
        if type(show) is not bool:
            raise ValueError('Explicit native GUI selection required')
        self._retention_ready()
        pending = self.receipts / 'start-pending.json'
        intent = {'id': uuid.uuid4().hex, 'kind': 'session.start', 'session_id': None}
        try:
            with pending.open('x') as stream:
                json.dump(intent, stream)
                stream.flush(); os.fsync(stream.fileno())
        except FileExistsError:
            raise EditorError('startup_reconciliation_required') from None
        try:
            result = self._invoke(['session', 'start'] + (['--show'] if show else []), session=False)
        except EditorError as exc:
            if exc.native_session_id:
                intent['session_id'] = exc.native_session_id
                write_json(pending, intent)
                self._enroll(exc.native_session_id)
            raise
        self._enroll(result['session_id'])
        write_json(self.receipts / (intent['id'] + '.json'), {**intent, 'result': result})
        self._retain_completed_pending(pending, intent)
        return {'session_id': self.session, 'review_only': True, 'publication_eligible': False}

    def _enroll(self, session_id):
        if not isinstance(session_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', session_id):
            raise EditorError('invalid_native_session')
        self.session = session_id
        write_json(self.receipts / ('session-' + self.session + '.json'),
                   {'session_id': self.session, 'executable_sha256': self.executable_sha256,
                    'font_directory': str(self.font_directory)})

    def recover_start(self):
        pending = self.receipts / 'start-pending.json'
        if not pending.is_file() or pending.stat().st_size > 1024:
            raise EditorError('startup_reconciliation_required')
        intent = json.loads(pending.read_text())
        if not re.fullmatch('[0-9a-f]{32}', intent.get('id', '')) or intent.get('kind') != 'session.start':
            raise EditorError('startup_reconciliation_required')
        session_id = intent.get('session_id')
        if not isinstance(session_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', session_id):
            raise EditorError('startup_identity_unknown_inspect_native_process')
        self.session = session_id
        status = self._invoke(['session', 'status'])
        if status.get('data', {}).get('session_id') != session_id:
            raise EditorError('startup_identity_mismatch')
        write_json(self.receipts / (intent['id'] + '.json'), {**intent, 'result': status})
        self._retain_completed_pending(pending, intent)
        return {'session_id': session_id, 'native': status, 'review_only': True, 'publication_eligible': False}

    def inspect(self):
        return self._invoke(['project', 'get'])

    def _pending(self):
        self._managed_session()
        return self.receipts / (self.session + '-pending.json')

    def audit_sources(self, *, pending_intent=None):
        """Check actual native readers, including changes made outside this adapter."""
        pending = self._pending()
        if pending.exists() or pending_intent is not None:
            if (not isinstance(pending_intent, dict) or pending_intent.get('kind') != 'timeline.thumbnail'
                    or not pending.is_file()):
                raise EditorError('unresolved_native_operation')
            metadata = _receipt_metadata(pending)
            with pending.open('rb') as stream:
                raw = stream.read(MAX_JSON + 1)
            if (len(raw) > MAX_JSON or hashlib.sha256(raw).hexdigest() != metadata['sha256']
                    or json.loads(raw) != pending_intent or _receipt_metadata(pending) != metadata):
                raise EditorError('unresolved_native_operation')
        approved = {}
        for path in self.receipts.glob('*.json'):
            if re.fullmatch('[0-9a-f]{32}', path.stem):
                receipt = json.loads(path.read_text())
                for asset in receipt.get('details', {}).get('imported_assets', []):
                    approved.setdefault(asset['path'], set()).add(asset['sha256'])
        checked = {}
        def inspect_paths(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == 'reader' and isinstance(child, dict) and child.get('type') not in {
                            'FFmpegReader', 'QtImageReader', 'QtTextReader'}:
                        raise EditorError('unsupported_native_reader')
                    if key in {'path', 'resource', 'mask', 'url', 'font_path'} and child:
                        path = str(self.local_path(child, MEDIA))
                        if path not in checked:
                            checked[path] = digest(path)
                        if checked[path] not in approved.get(path, set()):
                            raise EditorError('unregistered_or_changed_native_asset')
                    inspect_paths(child)
            elif isinstance(value, list):
                for child in value:
                    inspect_paths(child)
        for kind in ('file', 'clip'):
            rows = self._invoke([kind, 'list'])['data']
            if not isinstance(rows, list) or len(rows) > 256:
                raise EditorError('native_object_limit')
            for row in rows:
                object_id = row.get('id')
                if not isinstance(object_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', object_id):
                    raise EditorError('invalid_native_object_id')
                inspect_paths(self._invoke([kind, 'get', object_id])['data'])
        return checked

    def _intent(self, kind, details):
        self._retention_ready()
        path = self._pending()
        intent = {'id': uuid.uuid4().hex, 'kind': kind, 'session': self.session,
                  'details': details, 'review_only': True, 'publication_eligible': False}
        try:
            with path.open('xb') as stream:
                stream.write(json.dumps(intent, sort_keys=True).encode())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            raise EditorError('unresolved_native_operation') from None
        return intent

    def _complete(self, intent, result):
        write_json(self.receipts / (intent['id'] + '.json'), {**intent, 'result': result})
        self._retain_completed_pending(self._pending(), intent)
        return result

    def _retention_state(self):
        marker = self.receipts / 'pending-retention.json'
        try:
            marker.with_suffix('.tmp').lstat()
        except FileNotFoundError:
            pass
        else:
            return {'status': 'unverified_write'}
        try:
            info = marker.lstat()
        except FileNotFoundError:
            return None
        if (marker.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400
                or not marker.is_file() or info.st_nlink != 1 or info.st_size > 4096):
            return {'status': 'unverified_file'}
        try:
            state = json.loads(marker.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            return {'status': 'unverified_json'}
        return state if isinstance(state, dict) else {'status': 'unverified_json'}

    def _retention_ready(self):
        state = self._retention_state()
        if state is None:
            return
        if (not isinstance(state, dict) or state.get('status') != 'completed'
                or not re.fullmatch('[a-f0-9]{32}', str(state.get('intent_id', '')))
                or not re.fullmatch('[a-f0-9]{64}', str(state.get('sha256', '')))
                or type(state.get('bytes')) is not int or not 0 < state['bytes'] <= MAX_JSON
                or state.get('retained') != 'terminal-' + state['intent_id'] + '.json'):
            raise EditorError('pending_retention_requires_reconciliation')

    def _retain_completed_pending(self, pending, intent):
        from .collector_narration_common import VoiceError, voice_lease
        try:
            # Reuse the retained cross-process lease; one whole retirement at a time.
            with voice_lease(self.receipts):
                self._retain_completed_pending_locked(pending, intent)
        except VoiceError as error:
            raise EditorError('pending_retention_busy') from error

    def _retain_completed_pending_locked(self, pending, intent):
        self._retention_ready()
        if pending.parent != self.receipts or not re.fullmatch('[a-f0-9]{32}', intent.get('id', '')):
            raise EditorError('pending_retention_source_unverified')
        before = _receipt_metadata(pending)
        with pending.open('rb') as stream:
            raw = stream.read(MAX_JSON + 1)
        if json.loads(raw) != intent or hashlib.sha256(raw).hexdigest() != before['sha256']:
            raise EditorError('pending_retention_source_changed')
        target = self.receipts / ('terminal-' + intent['id'] + '.json')
        record = target.with_suffix('.retained.json')
        if target.exists() or record.exists():
            raise EditorError('pending_retention_collision')
        marker = self.receipts / 'pending-retention.json'
        state = {'status': 'pending', 'intent_id': intent['id'], 'source': pending.name,
                 'retained': target.name, 'sha256': before['sha256'], 'bytes': before['bytes']}
        write_json(marker, state)
        _move_receipt(pending, target)
        if _receipt_metadata(target) != before:
            raise EditorError('pending_retention_requires_reconciliation')
        # Terminal intents remain referenced operational evidence, not obsolete archives.
        evidence = {**state, **before, 'status': 'retained_terminal_evidence',
                    'reason': 'definite native completion', 'retained_at_ns': time.time_ns()}
        with record.open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, sort_keys=True)
            stream.flush(); os.fsync(stream.fileno())
        write_json(marker, {**state, 'status': 'completed'})

    def reconcile(self):
        """Inspect only; uncertain mutations are never automatically replayed/cleared."""
        pending = json.loads(self._pending().read_text()) if self._pending().exists() else None
        return {'pending': pending, 'project': self.inspect(),
                'pending_retention': self._retention_state(),
                'exports': self._invoke(['export', 'list']),
                'operations': self._invoke(['operation', 'list'])}

    def validate_edits(self, commands):
        bounded(commands)
        if not isinstance(commands, list) or not 1 <= len(commands) <= 128:
            raise ValueError('Expected 1..128 bounded edits')
        for command in commands:
            if not isinstance(command, dict) or set(command) - {'method', 'params', 'as'}:
                raise ValueError('Invalid edit envelope')
            method = command.get('method')
            params = command.get('params')
            if method not in METHODS or not isinstance(params, dict) or set(params) - METHODS[method]:
                raise ValueError('Unsupported edit or parameter')
            if method == 'file.import':
                self.local_path(params.get('path', ''), MEDIA)
            if method == 'clip.set' and (not isinstance(params.get('values'), dict)
                                        or set(params['values']) - CLIP_VALUES
                                        or any(type(v) not in (int, float) for v in params['values'].values())):
                raise ValueError('Unsupported clip property')
            if method == 'clip.keyframe.set' and params.get('property') not in CLIP_VALUES - {'layer', 'has_audio', 'has_video'}:
                raise ValueError('Unsupported keyframe property')
            if method == 'effects.add' and params.get('type') not in {'Saturation', 'Brightness', 'Blur', 'Crop'}:
                raise ValueError('Unsupported effect')
            if method == 'effects.set' and (not isinstance(params.get('values'), dict)
                    or set(params['values']) - {'saturation', 'brightness', 'contrast', 'horizontal_radius',
                                                'vertical_radius', 'left', 'right', 'top', 'bottom'}
                    or any(type(v) not in (int, float) for v in params['values'].values())):
                raise ValueError('Unsupported effect property')
            if method == 'project.profile.set':
                values = params.get('values')
                if not isinstance(values, dict) or set(values) - {'width', 'height', 'fps', 'display_ratio', 'pixel_ratio', 'description'}:
                    raise ValueError('Unsupported profile property')
        if len(json.dumps(commands).encode()) > 128 * 1024:
            raise ValueError('Edit payload exceeds limit')

    def apply(self, commands, base_revision):
        if type(base_revision) is not int or base_revision < 0:
            raise ValueError('Expected revision required')
        self.validate_edits(commands)
        intent = self._intent('edit.apply', {'base_revision': base_revision,
                              'commands_sha256': hashlib.sha256(json.dumps(commands, sort_keys=True).encode()).hexdigest(),
                              'imported_assets': [{'path': item['params']['path'],
                                                   'sha256': digest(item['params']['path'])}
                                                  for item in commands if item['method'] == 'file.import']})
        # JSON comes via a private file to avoid Windows command-line length limits.
        batch = self.receipts / (intent['id'] + '-batch.json')
        write_json(batch, commands)
        result = self._invoke(['edit', 'apply', '--json', '@' + str(batch),
                               '--expect-revision', str(base_revision)])
        return self._complete(intent, result)

    def save(self, path):
        path = self.local_path(path, {'.osp'}, exists=False)
        revision = self.inspect()['revision']
        sources = self.audit_sources()
        intent = self._intent('project.save', {'path': str(path)})
        result = self._invoke(['project', 'save', str(path)])
        operation_id = result.get('operation_id')
        if not isinstance(operation_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', operation_id):
            raise EditorError('save_operation_missing_reconcile_required')
        operation = self._invoke(['operation', 'get', operation_id])['data']
        # Saving relocates native project assets and can legitimately advance revision.
        if operation.get('method') != 'project.save' or operation.get('state') != 'completed' \
                or operation.get('revision_before') != revision:
            raise EditorError('revision_changed_during_save_reconcile_required')
        result = {'native': result, 'path': str(path), 'sha256': digest(path),
                  'assets': sources, 'review_only': True, 'publication_eligible': False}
        return self._complete(intent, result)

    def reopen(self, path, sha256):
        path = self.local_path(path, {'.osp'})
        receipts = [json.loads(p.read_text()) for p in self.receipts.glob('*.json')
                    if re.fullmatch('[0-9a-f]{32}', p.stem)]
        saved = next((r['result'] for r in receipts if r.get('kind') == 'project.save'
                      and r.get('result', {}).get('path') == str(path)
                      and r.get('result', {}).get('sha256') == sha256), None)
        if digest(path) != sha256 or saved is None:
            raise EditorError('untrusted_or_changed_project')
        for asset, expected in saved.get('assets', {}).items():
            if digest(self.local_path(asset, MEDIA)) != expected:
                raise EditorError('unregistered_or_changed_native_asset')
        intent = self._intent('project.open', {'path': str(path), 'sha256': sha256})
        return self._complete(intent, self._invoke(['project', 'open', str(path)]))

    def export(self, path, end_frame):
        self._managed_session()
        marker = json.loads((self.receipts / ('session-' + self.session + '.json')).read_text())
        if self.font_directory is not None and marker.get('font_directory') != str(self.font_directory):
            raise EditorError('new_font_configured_session_required')
        path = self.local_path(path, {'.mp4'}, exists=False)
        if type(end_frame) is not int or not 1 <= end_frame <= 108_000:
            raise ValueError('Export range must be 1..108000 inclusive frames')
        before = self.inspect()
        sources = self.audit_sources()
        intent = self._intent('export.start', {'path': str(path), 'snapshot_context': before,
                                              'assets': sources, 'end_frame': end_frame})
        # Never wait/retry start: preserve native job ID and inspect that same job.
        result = self._invoke(['export', 'start', str(path),
                              '--start-frame', '1', '--end-frame', str(end_frame)])
        if result.get('data', {}).get('revision') != before['revision']:
            job_id = result.get('data', {}).get('job_id')
            if isinstance(job_id, str) and re.fullmatch('[a-zA-Z0-9_-]{1,80}', job_id):
                self._invoke(['export', 'cancel', job_id])
            raise EditorError('revision_changed_during_export_reconcile_required')
        return self._complete(intent, result)

    def export_status(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', job_id):
            raise ValueError('Invalid native export ID')
        return self._invoke(['export', 'status', job_id])

    def thumbnail(self, path, frame=1, width=None, height=None):
        """Capture the actual composed native frame for intro reveal and local QC."""
        from PIL import Image
        path = self.local_path(path, {'.png'}, exists=False)
        if type(frame) is not int or not 1 <= frame <= 108000:
            raise ValueError('Timeline frame must be 1..108000')
        before = self.inspect()
        if type(before.get('revision')) is not int or before['revision'] < 0:
            raise EditorError('thumbnail_context_unverified_reconcile_required')
        profile = before['data']
        width = profile['width'] if width is None else width
        height = profile['height'] if height is None else height
        if (any(type(value) is not int or not 1 <= value <= 4096 for value in (width, height))
                or width * height > 8 * 1024 * 1024):
            raise ValueError('Thumbnail dimensions exceed the native inspection limit')
        ratio = profile.get('fps')
        if not isinstance(ratio, dict) or any(type(ratio.get(key)) is not int or not 1 <= ratio[key] <= 1000000
                                              for key in ('num', 'den')):
            raise ValueError('Native project FPS is invalid')
        fps = ratio['num'] / ratio['den']
        sources = self.audit_sources()
        intent = self._intent('timeline.thumbnail', {'path': str(path), 'frame': frame,
            'width': width, 'height': height, 'revision': before['revision'], 'assets': sources})
        result = self._invoke(['timeline', 'thumbnail', '--frame', str(frame),
            '--width', str(width), '--height', str(height), '--output', str(path)])
        data = result.get('data', {})
        if not isinstance(data, dict):
            raise EditorError('thumbnail_context_unverified_reconcile_required')
        tiles = data.get('tiles')
        if (result.get('revision') != before['revision'] or data.get('timebase') != 'timeline'
                or self.local_path(data.get('path', ''), {'.png'}) != path
                or any(type(data.get(key)) is not int or data[key] != value
                       for key, value in (('width', width), ('height', height)))
                or type(data.get('fps')) not in (int, float) or not math.isfinite(data['fps']) or abs(data['fps'] - fps) > 1e-9
                or not isinstance(tiles, list) or len(tiles) != 1 or not isinstance(tiles[0], dict)
                or type(tiles[0].get('frame')) is not int or tiles[0]['frame'] != frame
                or type(tiles[0].get('seconds')) not in (int, float)
                or not math.isfinite(tiles[0]['seconds']) or abs(tiles[0]['seconds'] - (frame - 1) / fps) > 1e-9):
            raise EditorError('thumbnail_context_unverified_reconcile_required')
        info = path.lstat()
        if (path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400
                or info.st_nlink != 1 or info.st_size > 64 * 1024 * 1024 or data.get('image_bytes') != info.st_size):
            raise EditorError('thumbnail_artifact_unverified_reconcile_required')
        try:
            with Image.open(path) as picture:
                if picture.format != 'PNG' or picture.size != (width, height):
                    raise EditorError('thumbnail_artifact_unverified_reconcile_required')
                picture.verify()
        except (OSError, ValueError, Image.DecompressionBombError):
            raise EditorError('thumbnail_artifact_unverified_reconcile_required') from None
        if self.inspect()['revision'] != before['revision'] or self.audit_sources(pending_intent=intent) != sources:
            raise EditorError('thumbnail_revision_changed_reconcile_required')
        artifact_hash = digest(path)
        after = path.lstat()
        if any(getattr(info, key) != getattr(after, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')):
            raise EditorError('thumbnail_artifact_changed_reconcile_required')
        result['artifact'] = {'sha256': artifact_hash, 'bytes': info.st_size, 'frame': frame,
                              'revision': before['revision'], 'review_only': True,
                              'publication_eligible': False}
        return self._complete(intent, result)


def main():
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector: local OpenShot adapter')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--session')
    parser.add_argument('operation', choices=['start', 'recover-start', 'inspect', 'apply', 'save', 'reopen', 'export', 'export-status', 'thumbnail', 'reconcile'])
    parser.add_argument('--request', help='Local JSON request file, at most 128 KiB')
    args = parser.parse_args()
    try:
        client = OpenShot(args.executable, args.executable_sha256, args.vault, args.session)
        request = {}
        if args.request:
            with Path(args.request).open('rb') as stream:
                raw = stream.read(128 * 1024 + 1)
                if len(raw) > 128 * 1024:
                    raise ValueError('Request exceeds limit')
            request = json.loads(raw)
        methods = {'start': client.start, 'recover-start': client.recover_start, 'inspect': client.inspect, 'apply': client.apply,
                   'save': client.save, 'reopen': client.reopen, 'export': client.export,
                   'export-status': client.export_status, 'thumbnail': client.thumbnail, 'reconcile': client.reconcile}
        result = methods[args.operation](**request)
        print(json.dumps({'status': 'PASS', 'result': result, 'review_only': True, 'publication_eligible': False}))
        return 0
    except (ValueError, OSError, EditorError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc) if isinstance(exc, EditorError) else type(exc).__name__,
                          'review_only': True, 'publication_eligible': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
