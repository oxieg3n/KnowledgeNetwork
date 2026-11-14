"""Bounded VoiceStudio client. Speech output is always local review evidence."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import shutil
import urllib.error
import urllib.parse
import urllib.request
import wave

MAX_JSON = 8 * 1024 * 1024
MAX_WAV = 64 * 1024 * 1024


class VoiceError(RuntimeError):
    """Safe status; never include response bodies, tokens or request text."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VoiceError('BLOCKED_REDIRECT')


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_wav(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                             audio.getframerate(), audio.getnframes())
            if channels not in (1, 2) or width not in (2, 3, 4) or not 8000 <= rate <= 192000:
                raise VoiceError('INVALID_AUDIO_FORMAT')
            if not 0 < frames / rate <= 600:
                raise VoiceError('INVALID_AUDIO_DURATION')
            if len(audio.readframes(frames)) != frames * channels * width:
                raise VoiceError('TRUNCATED_AUDIO')
    except (wave.Error, EOFError) as exc:
        raise VoiceError('INVALID_WAV') from exc
    return {'duration_seconds': frames / rate, 'sample_rate': rate, 'channels': channels,
            'sample_width': width, 'frames': frames, 'sha256': hashlib.sha256(data).hexdigest()}


def verify_rights(evidence, engine_id, voice_id):
    """Verify reviewed local evidence; a boolean never establishes rights by itself."""
    if not isinstance(evidence, dict) or evidence.get('schema_version') != 1:
        raise VoiceError('BLOCKED_VOICE_RIGHTS')
    if evidence.get('engine_id') != engine_id or evidence.get('voice_id') != voice_id:
        raise VoiceError('BLOCKED_VOICE_IDENTITY')
    if any(not isinstance(value, str) or not value.strip() for value in (engine_id, voice_id)):
        raise VoiceError('BLOCKED_VOICE_IDENTITY')
    for key in ('rights_reviewed', 'commercial_use', 'youtube_use', 'voice_consent'):
        if evidence.get(key) is not True:
            raise VoiceError('BLOCKED_VOICE_RIGHTS')
    for key in ('model_id', 'model_revision', 'license', 'reviewed_by', 'reviewed_at', 'voice_basis'):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            raise VoiceError('BLOCKED_VOICE_RIGHTS')
    urls = evidence.get('evidence_urls')
    if not isinstance(urls, list) or not urls or any(
            not isinstance(url, str) or not url.startswith('https://') for url in urls):
        raise VoiceError('BLOCKED_VOICE_RIGHTS')
    artifacts = evidence.get('model_artifacts')
    if not isinstance(artifacts, list) or not artifacts:
        raise VoiceError('BLOCKED_MODEL_EVIDENCE')
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str):
            raise VoiceError('BLOCKED_MODEL_EVIDENCE')
        try:
            if sha256_file(artifact['path']) != artifact.get('sha256'):
                raise VoiceError('BLOCKED_MODEL_CHANGED')
        except OSError as exc:
            raise VoiceError('BLOCKED_MODEL_MISSING') from exc


class VoiceStudio:
    def __init__(self, base_url='http://127.0.0.1:3900', *, token=None, timeout=10):
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', '::1')
                or parsed.username or parsed.password or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment):
            raise VoiceError('BLOCKED_NON_LOOPBACK_ENDPOINT')
        try:
            port = parsed.port
        except ValueError as exc:
            raise VoiceError('INVALID_ENDPOINT') from exc
        if port is None or not 1 <= port <= 65535:
            raise VoiceError('INVALID_ENDPOINT')
        if not 0 < timeout <= 300:
            raise VoiceError('INVALID_TIMEOUT')
        if token is not None and ('\n' in token or '\r' in token):
            raise VoiceError('INVALID_CREDENTIAL')
        self.base_url, self.token, self.timeout = base_url.rstrip('/'), token, timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _request(self, path, payload=None, *, limit=MAX_JSON, timeout=None):
        if path not in ('/health', '/openapi.json', '/v1/audio/voices', '/v1/audio/speech'):
            raise VoiceError('UNSUPPORTED_ENDPOINT')
        headers = {'Accept': 'application/json' if payload is None else 'audio/wav'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        body = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers)
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise VoiceError('RESPONSE_TOO_LARGE')
                return data, response.headers.get_content_type()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise VoiceError('BLOCKED_VOICE_AUTH') from exc
            if exc.code in (409, 429, 503):
                raise VoiceError('BLOCKED_VOICE_BUSY_OR_UNAVAILABLE') from exc
            raise VoiceError('VOICE_HTTP_' + str(exc.code)) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise VoiceError('VOICE_TIMEOUT_RESULT_UNKNOWN' if payload else 'VOICE_TIMEOUT') from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise VoiceError('VOICE_TIMEOUT_RESULT_UNKNOWN' if payload else 'VOICE_TIMEOUT') from exc
            raise VoiceError('BLOCKED_VOICE_SESSION') from exc

    def _json(self, path):
        data, mime = self._request(path)
        if mime != 'application/json':
            raise VoiceError('INVALID_VOICE_RESPONSE')
        try:
            result = json.loads(data)
        except (ValueError, UnicodeError) as exc:
            raise VoiceError('INVALID_VOICE_RESPONSE') from exc
        if not isinstance(result, dict):
            raise VoiceError('INVALID_VOICE_RESPONSE')
        return result

    def discover(self):
        self._json('/health')
        schema = self._json('/openapi.json')
        paths = schema.get('paths', {})
        if not isinstance(paths, dict) or 'post' not in paths.get('/v1/audio/speech', {}):
            raise VoiceError('UNSUPPORTED_SPEECH_SCHEMA')
        catalog = self._json('/v1/audio/voices')
        if not isinstance(catalog.get('voices'), list) or not isinstance(catalog.get('engines'), list):
            raise VoiceError('INVALID_VOICE_CATALOG')
        if any(not isinstance(row, dict) for row in catalog['voices'] + catalog['engines']):
            raise VoiceError('INVALID_VOICE_CATALOG')
        return schema, catalog

    def status(self):
        schema, catalog = self.discover()
        return {'schema_version': 1, 'status': 'PASS', 'backend_version': schema.get('info', {}).get('version'),
                'profile_count': sum(v.get('type') == 'profile' for v in catalog['voices']),
                'engine_count': len(catalog['engines']), 'rights_status': 'NOT_VERIFIED',
                'publication_eligible': False}

    def generate(self, text, evidence, output):
        if not isinstance(text, str) or not text.strip() or len(text) > 4096 or any(
                ord(c) < 32 and c not in '\n\t' for c in text):
            raise VoiceError('INVALID_NARRATION_TEXT')
        if not isinstance(evidence, dict):
            raise VoiceError('BLOCKED_VOICE_RIGHTS')
        engine, voice = evidence.get('engine_id'), evidence.get('voice_id')
        verify_rights(evidence, engine, voice)
        schema, catalog = self.discover()
        selected = next((e for e in catalog['engines'] if e.get('id') == engine), None)
        if not selected or selected.get('available') is not True:
            raise VoiceError('BLOCKED_VOICE_ENGINE')
        # Available means dependencies exist, not that weights are local. Avoid
        # triggering an engine's implicit first-use download from this client.
        if selected.get('execution_evidence', {}).get('evidence_state') != 'loaded':
            raise VoiceError('BLOCKED_VOICE_MODEL_NOT_LOADED')
        if selected.get('active_model_id') not in (None, evidence['model_id']):
            raise VoiceError('BLOCKED_MODEL_CHANGED')
        # Compatibility aliases can silently select a different voice or engine.
        profiles = [v.get('voice_id') for v in catalog['voices'] if v.get('type') == 'profile']
        if voice not in profiles and voice not in (selected.get('preset_voices') or []):
            raise VoiceError('BLOCKED_VOICE_PROFILE')
        output = Path(output)
        parent = output.parent
        while not parent.exists():
            parent = parent.parent
        if shutil.disk_usage(parent).free < MAX_WAV * 2:
            raise VoiceError('BLOCKED_DISK_SPACE')
        output.mkdir(parents=True, exist_ok=False)
        intent = {'schema_version': 1, 'status': 'generation_intent', 'engine_id': engine,
                  'voice_id': voice, 'model_id': evidence['model_id'],
                  'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                  'evidence_sha256': hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest(),
                  'backend_version': schema.get('info', {}).get('version'),
                  'review_only': True, 'publication_eligible': False, 'listening': 'NOT_TESTED'}
        receipt = output / 'narration.json'
        def checkpoint():
            temporary = receipt.with_suffix('.tmp')
            with temporary.open('w', encoding='utf-8') as stream:
                json.dump(intent, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, receipt)
        checkpoint()
        try:
            data, mime = self._request('/v1/audio/speech', {'model': engine, 'voice': voice,
                     'input': text, 'response_format': 'wav'}, limit=MAX_WAV, timeout=300)
            if mime not in ('audio/wav', 'audio/x-wav', 'audio/wave'):
                raise VoiceError('INVALID_AUDIO_CONTENT_TYPE')
            audio = inspect_wav(data)
            with (output / 'narration.wav').open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            intent.update(status='generated_pending_review', audio=audio)
        except VoiceError as exc:
            intent.update(status=str(exc), retry_automatically=False)
            checkpoint()
            raise
        checkpoint()
        return intent


def main(argv=None):
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector VoiceStudio adapter')
    parser.add_argument('command', choices=('status', 'generate'))
    parser.add_argument('--url', default='http://127.0.0.1:3900')
    parser.add_argument('--text-file', type=Path)
    parser.add_argument('--rights-file', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        client = VoiceStudio(args.url, token=os.environ.get('OMNIVOICE_API_KEY'))
        if args.command == 'status':
            result = client.status()
        else:
            if not all((args.text_file, args.rights_file, args.output)):
                parser.error('generate requires --text-file, --rights-file and --output')
            if args.text_file.stat().st_size > 16384 or args.rights_file.stat().st_size > MAX_JSON:
                raise VoiceError('INPUT_TOO_LARGE')
            result = client.generate(args.text_file.read_text(encoding='utf-8'),
                        json.loads(args.rights_file.read_text(encoding='utf-8')), args.output)
        print(json.dumps(result, indent=2))
        return 0
    except (VoiceError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({'status': str(exc) if isinstance(exc, VoiceError) else 'INVALID_LOCAL_INPUT',
                          'publication_eligible': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
