"""FORGE consumer of the fixed, private Oxiegen-Narrator service."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import sys
import time
import urllib.parse
import uuid
import wave

from .collector_credentials import credential_target, read_credential, write_credential
from .collector_narration_common import (VoiceError, MAX_JSON, MAX_WAV, checkpoint,
    digest, inspect_wav, local_spool, private_address, read_json, sha256_file,
    socket_deadline, voice_lease)

SERVICE = 'knowledge-network-voxcpm2'
NARRATOR = 'oxiegen-narrator'
PROVIDER = 'voxcpm2_remote'
NAMESPACE = 'VoxCPM2'
POLL_SECONDS = 600
REQUEST_SECONDS = 30
STATES = ('queued', 'running', 'completed', 'failed', 'cancelled')
HASH = re.compile('[a-f0-9]{64}')
ID = re.compile('[a-f0-9]{32}')


def provenance(value):
    if not isinstance(value, dict) or set(value) != {'script_sha256', 'config_sha256', 'model_revision', 'license_evidence_sha256'}:
        raise VoiceError('BLOCKED_NARRATOR_PROVENANCE')
    for key in ('script_sha256', 'config_sha256', 'license_evidence_sha256'):
        if not isinstance(value[key], str) or not HASH.fullmatch(value[key]):
            raise VoiceError('BLOCKED_NARRATOR_PROVENANCE')
    revision = value['model_revision']
    if not isinstance(revision, str) or not revision.strip() or len(revision) > 256 or any(ord(c) < 32 for c in revision):
        raise VoiceError('BLOCKED_NARRATOR_PROVENANCE')
    return dict(value)


def request_identity(job_id, text, segments):
    if not isinstance(job_id, str) or not ID.fullmatch(job_id):
        raise VoiceError('INVALID_NARRATION_JOB_ID')
    if not isinstance(text, str) or not text.strip() or len(text) > 12000:
        raise VoiceError('INVALID_NARRATION_TEXT')
    parts = [text] if segments is None else segments
    if (not isinstance(parts, list) or not 1 <= len(parts) <= 16 or
            any(not isinstance(part, str) or not part.strip() for part in parts) or
            sum(len(part) for part in parts) > 12000 or
            any(ord(c) < 32 and c not in '\n\t' for part in [text, *parts] for c in part) or
            ' '.join(text.split()) != ' '.join(' '.join(parts).split())):
        raise VoiceError('INVALID_NARRATION_SEGMENTS')
    return parts


def retain_partial(path, reason):
    """Keep this attempt's closed artifact; reconciliation decides its later fate."""
    try:
        before = path.lstat()
    except FileNotFoundError:
        return
    if not re.fullmatch(r'(download|joined)-[a-f0-9]{32}\.partial', path.name):
        raise VoiceError('NARRATION_PARTIAL_RETENTION_UNVERIFIED')
    artifact_hash, evidence = None, 'not_measured'
    if (not path.is_symlink() and not getattr(before, 'st_file_attributes', 0) & 0x400
            and path.is_file() and before.st_nlink == 1 and before.st_size <= MAX_WAV):
        measured, total, deadline = hashlib.sha256(), 0, time.monotonic() + 5
        try:
            with path.open('rb') as stream:
                while total <= MAX_WAV and time.monotonic() < deadline:
                    block = stream.read(min(1024 * 1024, MAX_WAV - total + 1))
                    if not block:
                        after = path.lstat()
                        if total == before.st_size and all(getattr(before, key) == getattr(after, key)
                                for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')):
                            artifact_hash, evidence = measured.hexdigest(), 'measured_stable'
                        break
                    total += len(block); measured.update(block)
        except OSError:
            evidence = 'unavailable'
    record = {'status': 'retained_for_reconciliation', 'artifact': path.name,
              'sha256': artifact_hash, 'bytes': before.st_size, 'hash_evidence': evidence, 'hold_reason': reason,
              'review_only': True, 'publication_eligible': False}
    with path.with_suffix('.retained.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, sort_keys=True)
        stream.flush(); os.fsync(stream.fileno())


class RemoteVoxCPM2Provider:
    def __init__(self, base_url, route, spool):
        if not isinstance(base_url, str) or not isinstance(route, dict):
            raise VoiceError('INVALID_NARRATOR_ENDPOINT')
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or
                parsed.path or parsed.query or parsed.fragment or '\\' in base_url or any(ord(c) < 33 for c in base_url)):
            raise VoiceError('INVALID_NARRATOR_ENDPOINT')
        try:
            self.port = parsed.port if parsed.port is not None else 443
            addresses = route.get('pinned_addresses')
            if not 1 <= self.port <= 65535 or not isinstance(addresses, list) or not addresses or not all(private_address(address) for address in addresses):
                raise VoiceError('BLOCKED_NARRATOR_DESTINATION')
            self.addresses = {str(ipaddress.ip_address(address)) for address in addresses}
        except (ValueError, TypeError) as exc:
            raise VoiceError('INVALID_NARRATOR_ENDPOINT') from exc
        if (route.get('schema_version') != 1 or route.get('base_url') != base_url or
                route.get('host_identity') != 'BLACKHAT-BASE' or route.get('transport') != 'https' or
                route.get('auth_mode') != 'scoped_bearer' or
                any(not isinstance(route.get(key), str) or not route[key].strip() for key in ('verified_by', 'verified_at')) or
                not HASH.fullmatch(str(route.get('transport_evidence_sha256', '')))):
            raise VoiceError('BLOCKED_NARRATOR_ROUTE')
        self.base_url, self.host, self.route, self.spool = base_url, parsed.hostname, route, local_spool(spool)

    @classmethod
    def from_environment(cls):
        if os.environ.get('COLLECTOR_NARRATOR_PROVIDER') != PROVIDER:
            raise VoiceError('BLOCKED_NARRATOR_CONFIG')
        try:
            return cls(os.environ['COLLECTOR_NARRATOR_BASE_URL'],
                read_json(os.environ['COLLECTOR_NARRATOR_ROUTE_FILE']), os.environ['COLLECTOR_NARRATOR_SPOOL'])
        except KeyError as exc:
            raise VoiceError('BLOCKED_NARRATOR_CONFIG') from exc

    def _connect(self, timeout, register):
        address = sorted(self.addresses)[0]
        connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        raw = socket.socket(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM)
        try:
            raw.settimeout(timeout)
            register(raw)
            raw.connect((address, self.port))
            raw = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host, do_handshake_on_connect=False)
            register(raw)
            raw.do_handshake()
            connection.sock = raw
        except BaseException:
            raw.close()
            raise
        return connection

    def _request(self, method, path, payload=None, *, destination=None, cancel=None):
        read = method == 'GET' and (path == '/health' or re.fullmatch(r'/v1/narrations/[a-f0-9]{32}(/audio)?', path))
        post = method == 'POST' and (path == '/v1/narrations' or re.fullmatch(r'/v1/narrations/[a-f0-9]{32}/cancel', path))
        if not (read or post) or (payload is not None) != bool(post) or (destination is not None and not path.endswith('/audio')):
            raise VoiceError('UNSUPPORTED_NARRATOR_ENDPOINT')
        secret, _ = read_credential(self.base_url, 'scoped_bearer', namespace=NAMESPACE)
        headers = {'Authorization': 'Bearer ' + secret, 'Connection': 'close',
                   'Accept': 'audio/wav' if destination is not None else 'application/json'}
        body = json.dumps(payload, ensure_ascii=False).encode() if post else None
        if body is not None:
            if len(body) > 65536:
                raise VoiceError('NARRATOR_INPUT_TOO_LARGE')
            headers['Content-Type'] = 'application/json'
        deadline = time.monotonic() + REQUEST_SECONDS
        with socket_deadline(deadline, cancel, bool(post)) as (register, check):
            for attempt in range(1 if post else 3):
                connection = response = None
                try:
                    check()
                    connection = self._connect(min(10, max(.1, deadline-time.monotonic())), register)
                    connection.request(method, path, body, headers)
                    response = connection.getresponse(); check()
                    status = response.status
                    if 300 <= status < 400:
                        raise VoiceError('BLOCKED_NARRATOR_REDIRECT')
                    if not post and status in (429, 503) and attempt < 2:
                        retry = response.getheader('Retry-After', '')
                        if retry.isdigit() and int(retry) > 2:
                            raise VoiceError('NARRATOR_BACKPRESSURE')
                        delay = min(2, max(.25, float(retry) if retry.isdigit() else .25 * 2 ** attempt))
                        if cancel: cancel.wait(delay)
                        else: time.sleep(delay)
                        continue
                    if status not in ((200, 201, 202) if post else (200,)):
                        error = VoiceError({401: 'NARRATOR_AUTH_FAILED', 403: 'NARRATOR_AUTH_FAILED',
                            404: 'NARRATION_NOT_FOUND', 409: 'NARRATION_IDEMPOTENCY_CONFLICT',
                            429: 'NARRATOR_BACKPRESSURE', 503: 'NARRATOR_BACKPRESSURE'}.get(status, 'NARRATOR_HTTP_' + str(status)))
                        error.http_status = status
                        raise error
                    mime = response.getheader('Content-Type', '').split(';')[0].lower()
                    if mime not in (('audio/wav', 'audio/x-wav', 'audio/wave') if destination is not None else ('application/json',)):
                        raise VoiceError('INVALID_NARRATOR_CONTENT_TYPE')
                    limit, result, received = (MAX_WAV if destination is not None else MAX_JSON), bytearray(), 0
                    stream = Path(destination).open('xb') if destination is not None else None
                    try:
                        while True:
                            check(); block = response.read1(65536); check()
                            if not block: break
                            received += len(block)
                            if received > limit: raise VoiceError('NARRATOR_RESPONSE_TOO_LARGE')
                            if stream: stream.write(block)
                            else: result.extend(block)
                        if stream: stream.flush(); os.fsync(stream.fileno())
                    finally:
                        if stream: stream.close()
                    return bytes(result)
                except ssl.SSLCertVerificationError as exc:
                    check(); raise VoiceError('BLOCKED_NARRATOR_TLS') from exc
                except (OSError, TimeoutError, http.client.HTTPException) as exc:
                    check(); raise VoiceError('NARRATION_TRANSPORT_OUTCOME_UNKNOWN' if post else 'NARRATOR_DISCONNECTED') from exc
                finally:
                    if response: response.close()
                    if connection: connection.close()

    def _json(self, method, path, payload=None, cancel=None):
        try:
            result = json.loads(self._request(method, path, payload, cancel=cancel))
        except (ValueError, UnicodeError) as exc:
            raise VoiceError('INVALID_NARRATOR_RESPONSE') from exc
        if not isinstance(result, dict): raise VoiceError('INVALID_NARRATOR_RESPONSE')
        return result

    def _health(self, cancel=None):
        health = self._json('GET', '/health', cancel=cancel)
        if (type(health.get('schema_version')) is not int or health['schema_version'] != 1 or
                health.get('service') != SERVICE or health.get('narrator_id') != NARRATOR or
                health.get('status') not in ('ready', 'blocked') or type(health.get('execution_hold')) is not bool):
            raise VoiceError('BLOCKED_NARRATOR_SERVICE_IDENTITY')
        return health

    def status(self):
        health = self._health()
        try:
            expected = provenance(self.route.get('expected_provenance'))
            matched = provenance(health.get('provenance')) == expected
        except VoiceError:
            matched = False
        ready = health['status'] == 'ready' and not health['execution_hold'] and matched
        return {'provider': PROVIDER, 'narrator_id': NARRATOR, 'status': 'PASS' if ready else 'BLOCKED',
                'service_identity_verified': True, 'provenance_matches': matched,
                'execution_hold': health['execution_hold'], 'publication_eligible': False}

    @staticmethod
    def _job(value, key, text_hash, expected):
        if (value.get('id') != key or value.get('state') not in STATES or
                value.get('text_sha256') != text_hash or provenance(value.get('provenance')) != expected):
            raise VoiceError('NARRATION_HOST_RECEIPT_MISMATCH')
        return value

    def _complete(self, key, text_hash, expected, initial, cancel):
        job = self._job(initial, key, text_hash, expected)
        deadline = time.monotonic() + POLL_SECONDS
        while job['state'] in ('queued', 'running'):
            if cancel and cancel.is_set(): raise VoiceError('NARRATION_CANCELLED_HOST_STATUS_UNVERIFIED')
            if time.monotonic() >= deadline: raise VoiceError('NARRATION_POLL_DEADLINE')
            if cancel: cancel.wait(.25)
            else: time.sleep(.25)
            job = self._job(self._json('GET', '/v1/narrations/' + key, cancel=cancel), key, text_hash, expected)
        if job['state'] != 'completed':
            raise VoiceError('NARRATION_' + job['state'].upper())
        return job

    def _audio(self, directory, index, job, cancel):
        path = directory / f'segment-{index:02d}.wav'
        temporary = directory / ('download-' + uuid.uuid4().hex + '.partial')
        try:
            if not path.exists():
                self._request('GET', '/v1/narrations/' + job['id'] + '/audio', destination=temporary, cancel=cancel)
                source = temporary
            else: source = path
            if source.stat().st_size > MAX_WAV: raise VoiceError('NARRATION_AUDIO_TOO_LARGE')
            audio = inspect_wav(source)
            expected = job.get('audio')
            if not isinstance(expected, dict): raise VoiceError('INVALID_NARRATION_AUDIO_RECEIPT')
            for key in ('frames', 'sample_rate', 'channels', 'sample_width'):
                if type(expected.get(key)) is not int or expected[key] != audio[key]:
                    raise VoiceError('NARRATION_AUDIO_MISMATCH')
            if (expected.get('sha256') != audio['sha256'] or type(expected.get('bytes')) is not int or
                    expected['bytes'] != source.stat().st_size or type(expected.get('duration')) not in (int, float) or
                    not math.isfinite(expected['duration']) or abs(expected['duration'] - audio['duration_seconds']) > 1e-9):
                raise VoiceError('NARRATION_AUDIO_MISMATCH')
            if source != path: os.replace(source, path)
            return path, audio
        finally:
            retain_partial(temporary, 'download_outcome_requires_reconciliation')

    def generate(self, job_id, text, *, segments=None, cancel=None):
        parts = request_identity(job_id, text, segments)
        expected = provenance(self.route.get('expected_provenance'))
        identity = digest({'job_id': job_id, 'text': text, 'segments': parts,
                           'endpoint': digest(self.base_url), 'provenance': expected})
        with voice_lease(self.spool):
            directory = self.spool / job_id
            directory.mkdir(exist_ok=True); local_spool(directory)
            receipt = directory / 'narration.json'
            if receipt.exists():
                intent = read_json(receipt)
                if intent.get('request_sha256') != identity: raise VoiceError('NARRATION_IDEMPOTENCY_CONFLICT')
                header = {'schema_version': 3, 'provider': PROVIDER, 'narrator_id': NARRATOR,
                    'collector_job_id': job_id, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'provenance': expected, 'review_only': True, 'publication_eligible': False}
                if any(intent.get(key) != value for key, value in header.items()): raise VoiceError('NARRATION_LOCAL_RECEIPT_CHANGED')
                if intent.get('status') == 'generated_pending_review':
                    audio = inspect_wav(directory / 'narration.wav')
                    if audio != intent.get('audio'): raise VoiceError('NARRATION_LOCAL_AUDIO_CHANGED')
                    cues, last = intent.get('cues'), 0
                    if not isinstance(cues, list) or len(cues) != len(parts): raise VoiceError('NARRATION_LOCAL_RECEIPT_CHANGED')
                    for cue, part in zip(cues, parts):
                        if (not isinstance(cue, dict) or cue.get('text') != part or type(cue.get('start_sample')) is not int or
                                type(cue.get('end_sample')) is not int or cue['start_sample'] != last or
                                not last < cue['end_sample'] <= audio['frames'] or
                                any(type(cue.get(key)) not in (int, float) or not math.isfinite(cue[key]) or
                                    abs(cue[key]-sample/audio['sample_rate']) > 1e-9 for key, sample in
                                    (('start', last), ('end', cue['end_sample'])))):
                            raise VoiceError('NARRATION_LOCAL_RECEIPT_CHANGED')
                        last = cue['end_sample']
                    if last != audio['frames']: raise VoiceError('NARRATION_LOCAL_RECEIPT_CHANGED')
                    return intent
            else:
                intent = {'schema_version': 3, 'provider': PROVIDER, 'narrator_id': NARRATOR,
                    'collector_job_id': job_id, 'request_sha256': identity, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'provenance': expected, 'host_jobs': [], 'cues': [], 'review_only': True,
                    'publication_eligible': False, 'listening': 'NOT_TESTED', 'status': 'prepared'}
                checkpoint(directory / 'request.json', {'text': text, 'segments': parts, 'request_sha256': identity})
                checkpoint(receipt, intent)
            try:
                health = self._health(cancel)
                if provenance(health.get('provenance')) != expected: raise VoiceError('BLOCKED_NARRATOR_PROVENANCE_CHANGED')
                audio_parts, cues, offset, format_key = [], [], 0, None
                for index, part in enumerate(parts):
                    if shutil.disk_usage(self.spool).free < MAX_WAV * 3: raise VoiceError('NARRATOR_DISK_RESERVE')
                    key = job_id if len(parts) == 1 else hashlib.sha256((job_id + '/' + str(index)).encode()).hexdigest()[:32]
                    text_hash = hashlib.sha256(part.encode()).hexdigest()
                    if index >= len(intent['host_jobs']):
                        if health['execution_hold'] or health['status'] != 'ready': raise VoiceError('BLOCKED_NARRATOR_EXECUTION_HOLD')
                        intent['host_jobs'].append({'id': key, 'text_sha256': text_hash, 'state': 'submission_intent'})
                        intent.update(status='submission_intent'); checkpoint(receipt, intent)
                        initial = self._json('POST', '/v1/narrations', {'idempotency_key': key, 'text': part, 'narrator_id': NARRATOR}, cancel)
                    else:
                        # A recorded intent is never POSTed again, including a lost response.
                        initial = self._json('GET', '/v1/narrations/' + key, cancel=cancel)
                    job = self._complete(key, text_hash, expected, initial, cancel)
                    intent['host_jobs'][index] = {name: job[name] for name in ('id', 'state', 'text_sha256')}
                    checkpoint(receipt, intent)
                    path, audio = self._audio(directory, index, job, cancel)
                    current_format = (audio['channels'], audio['sample_width'], audio['sample_rate'])
                    if format_key is not None and format_key != current_format: raise VoiceError('NARRATION_SEGMENT_FORMAT_CHANGED')
                    format_key = current_format
                    end = offset + audio['frames']
                    if end > audio['sample_rate'] * 600 or end * audio['channels'] * audio['sample_width'] > MAX_WAV - 44:
                        raise VoiceError('NARRATION_AUDIO_TOO_LARGE')
                    cues.append({'text': part, 'start_sample': offset, 'end_sample': end,
                                 'start': offset / audio['sample_rate'], 'end': end / audio['sample_rate']})
                    offset = end; audio_parts.append(path)
                output = directory / ('joined-' + uuid.uuid4().hex + '.partial')
                try:
                    with wave.open(str(output), 'wb') as joined:
                        joined.setnchannels(format_key[0]); joined.setsampwidth(format_key[1]); joined.setframerate(format_key[2])
                        for path in audio_parts:
                            with wave.open(str(path), 'rb') as source:
                                for block in iter(lambda: source.readframes(16384), b''): joined.writeframesraw(block)
                    with output.open('r+b') as stream: stream.flush(); os.fsync(stream.fileno())
                    final = directory / 'narration.wav'
                    try:
                        info = final.lstat()
                    except FileNotFoundError:
                        info = None
                    if info is not None:
                        if (final.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400
                                or not final.is_file() or info.st_nlink != 1 or info.st_size > MAX_WAV
                                or inspect_wav(final) != inspect_wav(output)):
                            raise VoiceError('NARRATION_LOCAL_OUTPUT_REQUIRES_RECONCILIATION')
                    else:
                        os.replace(output, final)
                finally:
                    retain_partial(output, 'join_outcome_requires_reconciliation')
                intent.update(status='generated_pending_review', cues=cues, audio=inspect_wav(directory / 'narration.wav'))
                intent.pop('error', None); checkpoint(receipt, intent)
                return intent
            except (VoiceError, OSError, ValueError, wave.Error) as exc:
                code = str(exc) if isinstance(exc, VoiceError) else 'NARRATION_LOCAL_EVIDENCE_INVALID'
                intent.update(status='blocked_remote_narrator', error=code); checkpoint(receipt, intent)
                raise VoiceError(code) from exc

    def cancel(self, job_id):
        if not isinstance(job_id, str) or not ID.fullmatch(job_id): raise VoiceError('INVALID_NARRATION_JOB_ID')
        directory = local_spool(self.spool / job_id)
        receipt = read_json(directory / 'narration.json')
        if receipt.get('provider') != PROVIDER or receipt.get('collector_job_id') != job_id: raise VoiceError('INVALID_NARRATION_RECEIPT')
        expected = provenance(self.route.get('expected_provenance'))
        if provenance(self._health().get('provenance')) != expected:
            raise VoiceError('BLOCKED_NARRATOR_PROVENANCE_CHANGED')
        results = []
        for job in receipt.get('host_jobs', []):
            if job.get('state') in ('submission_intent', 'queued', 'running'):
                key = job.get('id')
                if not isinstance(key, str) or not ID.fullmatch(key): raise VoiceError('INVALID_NARRATION_RECEIPT')
                result = self._job(self._json('POST', '/v1/narrations/' + key + '/cancel', {}), key, job.get('text_sha256'), expected)
                results.append({'id': key, 'state': result['state']})
        return {'provider': PROVIDER, 'collector_job_id': job_id, 'host_jobs': results,
                'status': 'HOST_STATUS_OBSERVED' if results else 'NO_ACTIVE_HOST_JOB', 'publication_eligible': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='The Knowledge Network Collector direct VoxCPM2 narrator')
    parser.add_argument('command', choices=('status', 'credential-save', 'generate', 'cancel'))
    parser.add_argument('--job-id'); parser.add_argument('--text-file', type=Path); parser.add_argument('--segments-file', type=Path)
    args = parser.parse_args(argv)
    try:
        provider = RemoteVoxCPM2Provider.from_environment()
        if args.command == 'credential-save':
            if not sys.stdin.isatty(): raise VoiceError('INTERACTIVE_NARRATOR_CREDENTIAL_ENTRY_REQUIRED')
            secret = getpass.getpass('Private direct narrator credential: ')
            write_credential(provider.base_url, secret, 'scoped_bearer', namespace=NAMESPACE)
            result = {'status': 'SAVED', 'credential_target': credential_target(provider.base_url, NAMESPACE)}
        elif args.command == 'status': result = provider.status()
        elif args.command == 'cancel': result = provider.cancel(args.job_id)
        else:
            if not args.text_file or not args.job_id: parser.error('generate requires --job-id and --text-file')
            if args.text_file.stat().st_size > 48000 or (args.segments_file and args.segments_file.stat().st_size > 50000):
                raise VoiceError('NARRATOR_INPUT_TOO_LARGE')
            segments = json.loads(args.segments_file.read_text(encoding='utf-8-sig')) if args.segments_file else None
            result = provider.generate(args.job_id, args.text_file.read_text(encoding='utf-8-sig'), segments=segments)
            result = {key: value for key, value in result.items() if key not in ('cues',)}
        print(json.dumps(result, indent=2)); return 1 if result.get('status') == 'BLOCKED' else 0
    except (VoiceError, OSError, ValueError, TypeError, KeyError) as exc:
        code = str(exc) if isinstance(exc, VoiceError) or (isinstance(exc, ValueError) and re.fullmatch('[A-Z_]+', str(exc))) else 'INVALID_NARRATOR_CONFIG'
        print(json.dumps({'status': 'blocked_remote_narrator', 'error': code, 'publication_eligible': False})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
