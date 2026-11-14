"""Retired V8 provider, retained for historical fixtures; active CLI fails closed."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import time
import urllib.parse
import uuid
import wave

from .collector_credentials import credential_target, read_credential, write_credential

from .collector_narration_common import (
    VoiceError, MAX_JSON, MAX_WAV, socket_deadline, digest, sha256_file,
    checkpoint, read_json, inspect_wav, private_address, local_spool, voice_lease,
)
PATHS = ('/health', '/openapi.json', '/v1/audio/voices', '/v1/audio/speech')
CAPABILITY_READS = ('/.well-known/voicestudio-speech', '/model/loaded', '/models')
READ_DEADLINE_SECONDS = 30
POST_DEADLINE_SECONDS = 180


def verify_rights(evidence, engine_id, voice_id):
    if not isinstance(evidence, dict) or evidence.get('schema_version') != 2:
        raise VoiceError('BLOCKED_REMOTE_VOICE_RIGHTS')
    if evidence.get('engine_id') != engine_id or evidence.get('voice_id') != voice_id:
        raise VoiceError('BLOCKED_VOICE_IDENTITY')
    for key in ('engine_id', 'voice_id', 'model_id', 'model_revision', 'license',
                'reviewed_by', 'reviewed_at', 'voice_basis'):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            raise VoiceError('BLOCKED_REMOTE_VOICE_RIGHTS')
    for key in ('rights_reviewed', 'commercial_use', 'youtube_use', 'voice_consent'):
        if evidence.get(key) is not True:
            raise VoiceError('BLOCKED_REMOTE_VOICE_RIGHTS')
    for key in ('capability_fingerprint', 'host_model_evidence_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', str(evidence.get(key, ''))):
            raise VoiceError('BLOCKED_HOST_MODEL_EVIDENCE')
    urls = evidence.get('evidence_urls')
    if not isinstance(urls, list) or not urls or any(not isinstance(url, str) or not url.startswith('https://') for url in urls):
        raise VoiceError('BLOCKED_REMOTE_VOICE_RIGHTS')
    artifacts = evidence.get('model_artifacts')
    if not isinstance(artifacts, list) or not artifacts:
        raise VoiceError('BLOCKED_HOST_MODEL_EVIDENCE')
    for artifact in artifacts:
        if (not isinstance(artifact, dict) or 'path' in artifact or
                not isinstance(artifact.get('logical_name'), str) or not artifact['logical_name'].strip() or
                not re.fullmatch('[a-f0-9]{64}', str(artifact.get('sha256', '')))):
            raise VoiceError('BLOCKED_HOST_MODEL_EVIDENCE')


def request_identity(job_id, text, segments):
    if not isinstance(job_id, str) or not re.fullmatch('[a-f0-9]{32}', job_id):
        raise VoiceError('INVALID_VOICE_JOB_ID')
    if not isinstance(text, str) or not text.strip() or len(text) > 4096 or any(ord(c) < 32 and c not in '\n\t' for c in text):
        raise VoiceError('INVALID_NARRATION_TEXT')
    segments = [text] if segments is None else segments
    if (not isinstance(segments, list) or not 1 <= len(segments) <= 16 or
            any(not isinstance(segment, str) or not segment.strip() for segment in segments) or
            sum(len(segment) for segment in segments) > 4096 or
            any(ord(character) < 32 and character not in '\n\t' for segment in segments for character in segment) or
            ' '.join(text.split()) != ' '.join(' '.join(segments).split())):
        raise VoiceError('INVALID_NARRATION_SEGMENTS')
    return segments, digest({'job_id': job_id, 'text': text, 'segments': segments})


def prepare_request(spool, job_id, text, segments=None):
    """Persist an actual requested script even when remote configuration is absent."""
    segments, identity = request_identity(job_id, text, segments)
    spool = local_spool(spool)
    with voice_lease(spool):
        return _prepare_request(spool, job_id, text, segments, identity)


def _prepare_request(spool, job_id, text, segments, identity):
    directory = spool / job_id
    directory.mkdir(exist_ok=True)
    local_spool(directory)
    path = directory / 'request.json'
    if path.exists():
        saved = read_json(path)
        if saved.get('request_identity') != identity:
            raise VoiceError('VOICE_IDEMPOTENCY_CONFLICT')
        return {key: value for key, value in saved.items() if key not in ('text', 'segments')}
    if (directory / 'narration.json').exists():
        raise VoiceError('VOICE_RESULT_REQUIRES_RECONCILIATION')
    configured = all(os.environ.get(key) for key in ('COLLECTOR_VOICE_PROVIDER', 'COLLECTOR_VOICESTUDIO_BASE_URL',
                     'COLLECTOR_VOICESTUDIO_ROUTE_FILE', 'COLLECTOR_VOICESTUDIO_SPOOL'))
    result = {'schema_version': 2, 'collector_job_id': job_id, 'request_identity': identity,
              'text': text, 'segments': segments, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'status': 'blocked_remote_voice', 'error': 'BLOCKED_VOICE_RIGHTS_NOT_VERIFIED' if configured else 'BLOCKED_REMOTE_VOICE_CONFIG',
              'rights_status': 'NOT_VERIFIED', 'provider': 'voicestudio_remote',
              'submission_started': False, 'review_only': True, 'publication_eligible': False}
    checkpoint(path, result)
    return {key: value for key, value in result.items() if key not in ('text', 'segments')}


class RemoteVoiceStudioProvider:
    def __init__(self, base_url, route, spool):
        if not isinstance(base_url, str) or not isinstance(route, dict):
            raise VoiceError('INVALID_REMOTE_VOICE_ENDPOINT')
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or
                parsed.path or parsed.query or parsed.fragment or '\\' in base_url or any(ord(c) < 33 for c in base_url)):
            raise VoiceError('INVALID_REMOTE_VOICE_ENDPOINT')
        try:
            self.port = parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)
            if not 1 <= self.port <= 65535:
                raise VoiceError('INVALID_REMOTE_VOICE_ENDPOINT')
            addresses = route.get('pinned_addresses')
            if not isinstance(addresses, list) or not addresses or not all(private_address(value) for value in addresses):
                raise VoiceError('BLOCKED_NON_PRIVATE_VOICE_DESTINATION')
        except (ValueError, TypeError) as exc:
            raise VoiceError('INVALID_REMOTE_VOICE_ENDPOINT') from exc
        if route.get('schema_version') != 1 or route.get('base_url') != base_url or route.get('host_identity') != 'BLACKHAT-BASE':
            raise VoiceError('BLOCKED_REMOTE_VOICE_ROUTE')
        if any(not isinstance(route.get(key), str) or not route[key].strip() for key in ('verified_by', 'verified_at')):
            raise VoiceError('BLOCKED_REMOTE_VOICE_ROUTE')
        if not re.fullmatch('[a-f0-9]{64}', str(route.get('transport_evidence_sha256', ''))):
            raise VoiceError('BLOCKED_REMOTE_VOICE_TRANSPORT')
        if (parsed.scheme == 'https' and route.get('transport') != 'https') or (parsed.scheme == 'http' and route.get('transport') not in ('tailscale_http', 'isolated_link_http')):
            raise VoiceError('BLOCKED_REMOTE_VOICE_TRANSPORT')
        if route.get('auth_mode') not in ('share_pin', 'scoped_bearer'):
            raise VoiceError('BLOCKED_ROOT_OR_MISSING_VOICE_CREDENTIAL')
        if route['auth_mode'] == 'scoped_bearer' and route.get('route_scoped') is not True:
            raise VoiceError('BLOCKED_ROOT_VOICE_CREDENTIAL')
        if parsed.scheme == 'http' and route['auth_mode'] == 'scoped_bearer' and route['transport'] != 'tailscale_http':
            raise VoiceError('BLOCKED_PLAINTEXT_BEARER')
        self.base_url, self.route, self.spool = base_url, route, local_spool(spool)
        self.host, self.scheme = parsed.hostname, parsed.scheme
        self.addresses = {str(ipaddress.ip_address(value)) for value in addresses}

    @classmethod
    def from_environment(cls):
        raise VoiceError('VOICESTUDIO_PROVIDER_RETIRED')

    def _connect(self, timeout, on_socket=lambda transport: None):
        # The operator verified these exact private literals. Connect directly:
        # no unbounded DNS resolution or rebinding can move a credential.
        address = sorted(self.addresses)[0]
        connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        raw = socket.socket(socket.AF_INET6 if ipaddress.ip_address(address).version == 6 else socket.AF_INET, socket.SOCK_STREAM)
        try:
            raw.settimeout(timeout)
            on_socket(raw)
            raw.connect((address, self.port))
            if self.scheme == 'https':
                raw = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host, do_handshake_on_connect=False)
                on_socket(raw)
                raw.do_handshake()
            connection.sock = raw
        except BaseException:
            raw.close()
            raise
        return connection

    def _request(self, path, payload=None, *, destination=None, credential=None, cancel=None):
        if path not in (*PATHS, *CAPABILITY_READS) or (payload is not None) != (path == '/v1/audio/speech'):
            raise VoiceError('UNSUPPORTED_VOICE_ENDPOINT')
        secret, _ = read_credential(self.base_url, self.route['auth_mode'])
        if credential is not None:
            secret = credential
        header = 'X-OmniVoice-Pin' if self.route['auth_mode'] == 'share_pin' else 'Authorization'
        headers = {header: secret if header.startswith('X-') else 'Bearer ' + secret,
                   'Accept': 'application/json' if payload is None else 'audio/wav', 'Connection': 'close'}
        body = None if payload is None else json.dumps(payload).encode()
        if body is not None:
            if len(body) > 32768:
                raise VoiceError('VOICE_INPUT_TOO_LARGE')
            headers['Content-Type'] = 'application/json'
        is_post = payload is not None
        deadline = time.monotonic() + (POST_DEADLINE_SECONDS if is_post else READ_DEADLINE_SECONDS)
        with socket_deadline(deadline, cancel, is_post) as (register, check):
            for attempt in range(1 if is_post else 3):
                connection, response = None, None
                try:
                    check()
                    connection = self._connect(min(10, max(.1, deadline - time.monotonic())), on_socket=register)
                    register(getattr(connection, 'sock', None))
                    connection.request('POST' if is_post else 'GET', path, body, headers)
                    response = connection.getresponse()
                    check()
                    status = response.status
                    if 300 <= status < 400:
                        raise VoiceError('BLOCKED_VOICE_REDIRECT')
                    if not is_post and status in (429, 503) and attempt < 2:
                        retry = response.getheader('Retry-After', '')
                        if retry.isdigit() and int(retry) > 2:
                            raise VoiceError('BLOCKED_VOICE_BACKPRESSURE')
                        pause = min(2, max(.25, float(retry) if retry.isdigit() else .25 * 2 ** attempt))
                        if time.monotonic() + pause >= deadline:
                            raise VoiceError('VOICE_READ_DEADLINE')
                        if cancel:
                            cancel.wait(pause)
                        else:
                            time.sleep(pause)
                        continue
                    if status != 200:
                        error = VoiceError({401: 'BLOCKED_VOICE_AUTH', 403: 'BLOCKED_VOICE_AUTH',
                            404: 'UNSUPPORTED_VOICE_PROFILE_OR_ROUTE', 409: 'BLOCKED_VOICE_MODEL_BUSY',
                            429: 'BLOCKED_VOICE_BACKPRESSURE', 503: 'BLOCKED_VOICE_MODEL_UNAVAILABLE'}.get(status, 'VOICE_HTTP_' + str(status)))
                        error.http_status = status
                        raise error
                    mime = response.getheader('Content-Type', '').split(';')[0].lower()
                    if destination is not None and mime not in ('audio/wav', 'audio/x-wav', 'audio/wave'):
                        raise VoiceError('INVALID_AUDIO_CONTENT_TYPE')
                    limit = MAX_WAV if destination is not None else MAX_JSON
                    result, received = bytearray(), 0
                    stream = Path(destination).open('xb') if destination is not None else None
                    try:
                        while True:
                            check()
                            block = response.read1(65536)
                            check()
                            if not block:
                                break
                            received += len(block)
                            if received > limit:
                                raise VoiceError('VOICE_RESPONSE_TOO_LARGE')
                            if stream:
                                stream.write(block)
                            else:
                                result.extend(block)
                        if stream:
                            stream.flush(); os.fsync(stream.fileno())
                    finally:
                        if stream:
                            stream.close()
                    return bytes(result), mime, status
                except ssl.SSLCertVerificationError as exc:
                    check()
                    raise VoiceError('BLOCKED_VOICE_TLS_VERIFICATION') from exc
                except (TimeoutError, socket.timeout, http.client.HTTPException, OSError) as exc:
                    check()
                    raise VoiceError('VOICE_TRANSPORT_RESULT_UNKNOWN' if is_post else 'BLOCKED_REMOTE_VOICE_DISCONNECTED') from exc
                finally:
                    if response:
                        response.close()
                    if connection:
                        connection.close()

    def _json(self, path):
        data, mime, _ = self._request(path)
        try:
            value = json.loads(data) if mime == 'application/json' else None
        except (ValueError, UnicodeError) as exc:
            raise VoiceError('INVALID_VOICE_RESPONSE') from exc
        if not isinstance(value, dict):
            raise VoiceError('INVALID_VOICE_RESPONSE')
        return value

    def discover(self):
        self._json('/health')
        schema, catalog = self._json('/openapi.json'), self._json('/v1/audio/voices')
        if not isinstance(schema.get('info'), dict):
            raise VoiceError('UNSUPPORTED_SPEECH_SCHEMA')
        if not isinstance(schema.get('paths'), dict) or not isinstance(schema['paths'].get('/v1/audio/speech'), dict) or 'post' not in schema['paths']['/v1/audio/speech']:
            raise VoiceError('UNSUPPORTED_SPEECH_SCHEMA')
        if any(not isinstance(catalog.get(key), list) or any(not isinstance(row, dict) for row in catalog[key]) for key in ('voices', 'engines')):
            raise VoiceError('INVALID_VOICE_CATALOG')
        return schema, catalog

    @staticmethod
    def selected_capabilities(schema, catalog, engine_id, voice_id):
        engine = next((row for row in catalog['engines'] if row.get('id') == engine_id), None)
        if not engine or engine.get('available') is not True:
            raise VoiceError('BLOCKED_VOICE_ENGINE')
        profiles = [row.get('voice_id') for row in catalog['voices'] if row.get('type') == 'profile']
        if voice_id not in profiles and voice_id not in (engine.get('preset_voices') or []):
            raise VoiceError('BLOCKED_VOICE_PROFILE')
        execution = engine.get('execution_evidence')
        if not isinstance(execution, dict):
            execution = {}
        projection = {'backend_version': schema.get('info', {}).get('version'),
            'speech_schema': schema['paths']['/v1/audio/speech'], 'engine_id': engine_id,
            'voice_id': voice_id, 'active_model_id': engine.get('active_model_id'),
            'execution': {key: execution.get(key) for key in ('implementation_variant', 'evidence_state',
                'actual_execution_provider', 'actual_execution_device', 'precision_or_quantization', 'runtime_versions')}}
        return engine, projection, digest(projection)

    def status(self, engine_id=None, voice_id=None):
        schema, catalog = self.discover()
        result = {'schema_version': 2, 'status': 'PASS', 'provider': 'voicestudio_remote',
            'backend_version': schema.get('info', {}).get('version'),
            'profile_count': sum(row.get('type') == 'profile' for row in catalog['voices']),
            'engine_count': len(catalog['engines']), 'route_evidence': 'operator_declared',
            'rights_status': 'NOT_VERIFIED', 'publication_eligible': False}
        if engine_id and voice_id:
            _, projection, fingerprint = self.selected_capabilities(schema, catalog, engine_id, voice_id)
            result.update(selected=projection, capability_fingerprint=fingerprint)
        return result

    def inspect_capabilities(self):
        """Read only pinned, documented discovery routes; never follow returned URLs."""
        schema, _ = self.discover()
        results = {}
        for path in CAPABILITY_READS:
            operation = schema['paths'].get(path)
            if not isinstance(operation, dict) or 'get' not in operation:
                results[path] = {'status': 'UNSUPPORTED'}
            else:
                try:
                    results[path] = {'status': 'PASS', 'data': self._json(path)}
                except (VoiceError, OSError, ValueError) as exc:
                    code = str(exc) if isinstance(exc, VoiceError) else 'VOICE_CAPABILITY_READ_FAILED'
                    results[path] = {'status': 'BLOCKED', 'error': code,
                                     'http_status': getattr(exc, 'http_status', None)}
        checkpoint(self.spool / 'host-capabilities.private.json', results)
        complete = all(result['status'] == 'PASS' for result in results.values())
        return {'status': 'PASS' if complete else 'PARTIAL', 'complete': complete,
                'capability_document_sha256': digest(results),
                'routes': list(results), 'private_evidence_saved': True,
                'publication_eligible': False}

    def verify_auth(self):
        secret, version = read_credential(self.base_url, self.route['auth_mode'])
        invalid = ('111111' if secret == '000000' else '000000') if self.route['auth_mode'] == 'share_pin' else uuid.uuid4().hex
        invalid_status = None
        try:
            self._request('/v1/audio/voices', credential=invalid)
        except VoiceError as exc:
            invalid_status = getattr(exc, 'http_status', None)
            if invalid_status not in (401, 403):
                raise
        if invalid_status not in (401, 403):
            raise VoiceError('BLOCKED_VOICE_AUTH_NOT_ENFORCED')
        catalog = self._json('/v1/audio/voices')
        if not isinstance(catalog.get('voices'), list):
            raise VoiceError('INVALID_VOICE_CATALOG')
        receipt = {'schema_version': 1, 'endpoint_sha256': digest(self.base_url),
            'route_sha256': digest(self.route),
            'credential_version': version, 'auth_mode': self.route['auth_mode'],
            'invalid_status': invalid_status, 'valid_status': 200,
            'observed_at': datetime.now(timezone.utc).isoformat()}
        checkpoint(self.spool / 'remote-auth.json', receipt)
        return {'status': 'PASS', 'auth_evidence_sha256': digest(receipt), 'publication_eligible': False}

    def _lease(self):
        return voice_lease(self.spool)

    def generate(self, job_id, text, evidence, *, segments=None, cancel=None):
        segments, identity = request_identity(job_id, text, segments)
        if not isinstance(evidence, dict):
            raise VoiceError('BLOCKED_REMOTE_VOICE_RIGHTS')
        request_hash = digest({'job_id': job_id, 'text': text, 'segments': segments,
                               'rights': evidence, 'endpoint': digest(self.base_url)})
        with self._lease():
            directory = self.spool / job_id
            if directory.exists():
                local_spool(directory)
            receipt = directory / 'narration.json'
            if receipt.exists():
                existing = read_json(receipt)
                if existing.get('request_sha256') != request_hash:
                    raise VoiceError('VOICE_IDEMPOTENCY_CONFLICT')
                if existing.get('status') == 'generated_pending_review' and sha256_file(directory / 'narration.wav') == existing.get('audio', {}).get('sha256'):
                    return existing
                raise VoiceError('VOICE_RESULT_REQUIRES_RECONCILIATION')
            if (self.spool / 'remote-active.json').exists():
                raise VoiceError('BLOCKED_VOICE_REMOTE_OUTCOME_UNCERTAIN')
            if directory.exists() and read_json(directory / 'request.json').get('request_identity') != identity:
                raise VoiceError('VOICE_IDEMPOTENCY_CONFLICT')
            if shutil.disk_usage(self.spool).free < MAX_WAV * 3:
                raise VoiceError('BLOCKED_DISK_SPACE')
            directory.mkdir(exist_ok=True)
            intent = {'schema_version': 2, 'collector_job_id': job_id, 'request_sha256': request_hash,
                'status': 'queued', 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'provider': 'voicestudio_remote', 'review_only': True, 'publication_eligible': False,
                'listening': 'NOT_TESTED', 'retry_automatically': False, 'segments': [], 'cues': []}
            checkpoint(receipt, intent)
            started = time.monotonic()
            try:
                engine_id, voice_id = evidence.get('engine_id'), evidence.get('voice_id')
                verify_rights(evidence, engine_id, voice_id)
                _, version = read_credential(self.base_url, self.route['auth_mode'])
                auth = read_json(self.spool / 'remote-auth.json')
                if (auth.get('endpoint_sha256') != digest(self.base_url) or auth.get('route_sha256') != digest(self.route) or auth.get('credential_version') != version or
                        auth.get('invalid_status') not in (401, 403) or auth.get('valid_status') != 200 or
                        auth.get('auth_mode') != self.route['auth_mode']):
                    raise VoiceError('BLOCKED_VOICE_AUTH_NOT_VERIFIED')
                schema, catalog = self.discover()
                engine, projection, fingerprint = self.selected_capabilities(schema, catalog, engine_id, voice_id)
                observed_model = engine.get('active_model_id')
                if not isinstance(observed_model, str) or not observed_model.strip():
                    raise VoiceError('BLOCKED_HOST_MODEL_UNVERIFIED')
                if fingerprint != evidence['capability_fingerprint'] or observed_model != evidence['model_id']:
                    raise VoiceError('BLOCKED_HOST_MODEL_CHANGED')
                if projection['execution']['evidence_state'] != 'loaded':
                    raise VoiceError('BLOCKED_VOICE_MODEL_NOT_LOADED')
                intent.update(engine_id=engine_id, voice_id=voice_id, model_id=evidence['model_id'],
                    model_revision=evidence['model_revision'], capability_fingerprint=fingerprint,
                    host_execution=projection['execution'], rights_sha256=digest(evidence),
                    host_model_evidence_sha256=evidence['host_model_evidence_sha256'],
                    backend_version=projection['backend_version'], auth_evidence_sha256=digest(auth))
                self._synthesize_segments(directory, receipt, intent, segments, engine_id, voice_id, cancel)
                intent.update(status='generated_pending_review', audio=inspect_wav(directory / 'narration.wav'))
            except (VoiceError, OSError, ValueError, wave.Error) as exc:
                intent.update(status='blocked_remote_voice', error=str(exc) if isinstance(exc, VoiceError) else 'INVALID_VOICE_LOCAL_EVIDENCE',
                              elapsed_seconds=time.monotonic() - started)
                checkpoint(receipt, intent)
                raise VoiceError(intent['error']) from exc
            intent['elapsed_seconds'] = time.monotonic() - started
            checkpoint(receipt, intent)
            return intent

    def _synthesize_segments(self, directory, receipt, intent, segments, engine_id, voice_id, cancel):
        format_key, offset = None, 0
        output = directory / 'narration.partial'
        joined = None
        try:
            for index, text in enumerate(segments):
                if shutil.disk_usage(self.spool).free < MAX_WAV * 3:
                    raise VoiceError('BLOCKED_DISK_SPACE')
                intent.update(status='generation_intent', active_segment=index)
                checkpoint(receipt, intent)
                path = directory / f'segment-{index:02d}.wav'
                hold = self.spool / 'remote-active.json'
                if hold.exists():
                    raise VoiceError('BLOCKED_VOICE_REMOTE_OUTCOME_UNCERTAIN')
                checkpoint(hold, {'schema_version': 1, 'status': 'remote_outcome_pending',
                    'collector_job_id': intent['collector_job_id'], 'segment_index': index,
                    'request_sha256': intent['request_sha256'],
                    'segment_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'created_at': datetime.now(timezone.utc).isoformat()})
                self._request('/v1/audio/speech', {'model': engine_id, 'voice': voice_id,
                    'input': text, 'response_format': 'wav'}, destination=path, cancel=cancel)
                audio = inspect_wav(path)
                key = audio['channels'], audio['sample_width'], audio['sample_rate']
                if format_key is None:
                    format_key = key
                    joined = wave.open(str(output), 'wb')
                    joined.setnchannels(key[0]); joined.setsampwidth(key[1]); joined.setframerate(key[2])
                elif key != format_key:
                    raise VoiceError('VOICE_SEGMENT_FORMAT_CHANGED')
                if offset + audio['frames'] > key[2] * 600 or (offset + audio['frames']) * key[0] * key[1] > MAX_WAV:
                    raise VoiceError('VOICE_RESPONSE_TOO_LARGE')
                with wave.open(str(path), 'rb') as source:
                    for block in iter(lambda: source.readframes(16384), b''):
                        joined.writeframesraw(block)
                intent['segments'].append({'index': index, 'audio': audio})
                intent['cues'].append({'text': text, 'start_sample': offset, 'end_sample': offset + audio['frames'],
                    'start': offset / key[2], 'end': (offset + audio['frames']) / key[2]})
                offset += audio['frames']
                checkpoint(receipt, intent)
                # Only validated, durably recorded audio resolves this host call.
                hold.unlink()
        finally:
            if joined is not None:
                joined.close()
        with output.open('r+b') as stream:
            stream.flush(); os.fsync(stream.fileno())
        os.replace(output, directory / 'narration.wav')


def main(argv=None):
    print(json.dumps({'status': 'blocked_remote_voice', 'error': 'VOICESTUDIO_PROVIDER_RETIRED',
                      'replacement': 'youtube_ops.collector_voxcpm2', 'publication_eligible': False}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
