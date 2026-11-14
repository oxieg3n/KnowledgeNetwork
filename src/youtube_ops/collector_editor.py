"""Restricted OpenShot 4.1.1 client for trusted, local review-only projects.

Native OpenShot state stays authoritative. This is not a renderer or a second
timeline. The worker must serialize calls and keep the vault/session registry
private; this client is not a sandbox for an unrestricted desktop connection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
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
        self.vault = Path(vault).resolve(strict=True)
        if not self.vault.is_dir() or str(self.vault).startswith('\\\\'):
            raise ValueError('A local private vault directory is required')
        if session is not None and not re.fullmatch('[a-zA-Z0-9_-]{1,80}', session):
            raise ValueError('Invalid native session ID')
        self.session = session
        self.receipts = self.vault / '.collector-editor'
        self.receipts.mkdir(exist_ok=True)

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
        args = [str(self.executable), '--cli', '--timeout', '25']
        if session:
            if not self.session:
                raise ValueError('Native session required')
            args += ['--session', self.session]
        args += arguments
        env = dict(os.environ)
        env.pop('OPENSHOT_SESSION', None)
        # Retain the installed user's registry; never return its authentication record.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(args, cwd=self.vault, env=env, shell=False,
                                       stdout=stdout, stderr=stderr,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 40
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
                raise EditorError(code)
            if 'result' not in reply:
                raise EditorError('invalid_native_response')
            return reply['result']

    def start(self):
        result = self._invoke(['session', 'start'], session=False)
        self.session = result['session_id']
        return {'session_id': self.session, 'review_only': True, 'publication_eligible': False}

    def inspect(self):
        return self._invoke(['project', 'get'])

    def _pending(self):
        if not self.session:
            raise ValueError('Native session required')
        return self.receipts / (self.session + '-pending.json')

    def _intent(self, kind, details):
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
        self._pending().unlink()
        return result

    def reconcile(self):
        """Inspect only; uncertain mutations are never automatically replayed/cleared."""
        pending = json.loads(self._pending().read_text()) if self._pending().exists() else None
        return {'pending': pending, 'project': self.inspect(),
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
                                        or set(params['values']) - CLIP_VALUES):
                raise ValueError('Unsupported clip property')
            if method == 'clip.keyframe.set' and params.get('property') not in CLIP_VALUES - {'layer', 'has_audio', 'has_video'}:
                raise ValueError('Unsupported keyframe property')
            if method == 'effects.add' and params.get('type') not in {'Saturation', 'Brightness', 'Blur', 'Crop'}:
                raise ValueError('Unsupported effect')
            if method == 'effects.set' and (not isinstance(params.get('values'), dict)
                    or set(params['values']) - {'saturation', 'brightness', 'contrast', 'horizontal_radius',
                                                'vertical_radius', 'left', 'right', 'top', 'bottom'}):
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
        intent = self._intent('project.save', {'path': str(path)})
        result = self._invoke(['project', 'save', str(path)])
        result = {'native': result, 'path': str(path), 'sha256': digest(path),
                  'review_only': True, 'publication_eligible': False}
        return self._complete(intent, result)

    def reopen(self, path, sha256):
        path = self.local_path(path, {'.osp'})
        receipts = [json.loads(p.read_text()) for p in self.receipts.glob('*.json')
                    if re.fullmatch('[0-9a-f]{32}', p.stem)]
        if digest(path) != sha256 or not any(r['kind'] == 'project.save'
                and r.get('result', {}).get('path') == str(path)
                and r.get('result', {}).get('sha256') == sha256 for r in receipts):
            raise EditorError('untrusted_or_changed_project')
        intent = self._intent('project.open', {'path': str(path), 'sha256': sha256})
        return self._complete(intent, self._invoke(['project', 'open', str(path)]))

    def export(self, path, end_frame):
        path = self.local_path(path, {'.mp4'}, exists=False)
        if type(end_frame) is not int or not 1 <= end_frame <= 108_000:
            raise ValueError('Export range must be 1..108000 inclusive frames')
        before = self.inspect()
        intent = self._intent('export.start', {'path': str(path), 'snapshot_context': before,
                                              'end_frame': end_frame})
        # Never wait/retry start: preserve native job ID and inspect that same job.
        return self._complete(intent, self._invoke(['export', 'start', str(path),
                              '--start-frame', '1', '--end-frame', str(end_frame)]))

    def export_status(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}', job_id):
            raise ValueError('Invalid native export ID')
        return self._invoke(['export', 'status', job_id])


def main():
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector: local OpenShot adapter')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--session')
    parser.add_argument('operation', choices=['start', 'inspect', 'apply', 'save', 'reopen', 'export', 'export-status', 'reconcile'])
    parser.add_argument('--request', help='Local JSON request file, at most 128 KiB')
    args = parser.parse_args()
    try:
        client = OpenShot(args.executable, args.executable_sha256, args.vault, args.session)
        request = {}
        if args.request:
            raw = Path(args.request).read_bytes()
            if len(raw) > 128 * 1024:
                raise ValueError('Request exceeds limit')
            request = json.loads(raw)
        methods = {'start': client.start, 'inspect': client.inspect, 'apply': client.apply,
                   'save': client.save, 'reopen': client.reopen, 'export': client.export,
                   'export-status': client.export_status, 'reconcile': client.reconcile}
        result = methods[args.operation](**request)
        print(json.dumps({'status': 'PASS', 'result': result, 'review_only': True, 'publication_eligible': False}))
        return 0
    except (ValueError, OSError, EditorError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc) if isinstance(exc, EditorError) else type(exc).__name__,
                          'review_only': True, 'publication_eligible': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
