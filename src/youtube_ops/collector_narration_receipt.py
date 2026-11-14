"""Validate retained local VoxCPM2 narration evidence; no network or synthesis."""
import hashlib
import json
import math
from pathlib import Path
import re

from .collector_narration_common import inspect_wav, MAX_WAV


def _local_file(value, limit):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith('\\\\'):
        raise ValueError('Absolute local narration file required')
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Narration reparse points are not accepted')
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Narration file missing or exceeds limit')
    return path


def read_voxcpm2_receipt(value, *, expected_text=None, max_duration=600):
    path = _local_file(value, 128 * 1024)
    if path.name != 'narration.json':
        raise ValueError('Expected the remote provider narration.json receipt')
    with path.open('rb') as stream:
        raw = stream.read(128 * 1024 + 1)
    if len(raw) > 128 * 1024:
        raise ValueError('Narration receipt exceeds limit')
    receipt = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(receipt, dict) or receipt.get('provider') != 'voxcpm2_remote' \
            or receipt.get('narrator_id') != 'oxiegen-narrator' or receipt.get('status') != 'generated_pending_review' \
            or receipt.get('review_only') is not True or receipt.get('publication_eligible') is not False:
        raise ValueError('A completed review-only VoxCPM2 Oxiegen-Narrator receipt is required')
    if not isinstance(receipt.get('text_sha256'), str) or not re.fullmatch('[a-f0-9]{64}', receipt['text_sha256']):
        raise ValueError('Narration script digest is missing')
    if expected_text is not None and (not isinstance(expected_text, str)
            or hashlib.sha256(expected_text.encode()).hexdigest() != receipt['text_sha256']):
        raise ValueError('Narration receipt does not match the exact scene text')
    provenance = receipt.get('provenance')
    if not isinstance(provenance, dict) or set(provenance) != {
            'script_sha256', 'config_sha256', 'model_revision', 'license_evidence_sha256'}:
        raise ValueError('Narrator provenance evidence is missing')
    for key in ('script_sha256', 'config_sha256', 'license_evidence_sha256'):
        if not isinstance(provenance.get(key), str) or not re.fullmatch('[a-f0-9]{64}', provenance[key]):
            raise ValueError('Narrator provenance evidence is missing')
    revision = provenance.get('model_revision')
    if not isinstance(revision, str) or not revision.strip() or len(revision) > 256 or any(ord(c) < 32 for c in revision):
        raise ValueError('Narrator model revision is missing')
    audio_path = _local_file(path.with_name('narration.wav'), MAX_WAV)
    audio = inspect_wav(audio_path)
    expected = receipt.get('audio')
    if not isinstance(expected, dict):
        raise ValueError('Narration PCM envelope missing')
    for key in ('frames', 'sample_rate', 'channels', 'sample_width'):
        if type(expected.get(key)) is not int or expected[key] != audio[key]:
            raise ValueError('Narration PCM envelope does not match audio')
    if expected.get('sha256') != audio['sha256']:
        raise ValueError('Narration audio SHA-256 does not match receipt')
    duration = expected.get('duration_seconds')
    if type(duration) not in (int, float) or not math.isfinite(duration) \
            or abs(duration - audio['duration_seconds']) > 1e-9 or not .1 <= duration <= max_duration:
        raise ValueError('Narration duration is invalid or exceeds the permitted duration')
    cues = receipt.get('cues', [])
    if not isinstance(cues, list) or len(cues) > 16:
        raise ValueError('Expected at most 16 actual measured speech cues')
    last_end = 0
    for cue in cues:
        if not isinstance(cue, dict) or not isinstance(cue.get('text'), str) \
                or not 1 <= len(cue['text']) <= 4096 or '\x00' in cue['text']:
            raise ValueError('Invalid measured cue text')
        first, end = cue.get('start_sample'), cue.get('end_sample')
        if type(first) is not int or type(end) is not int or not last_end == first < end <= audio['frames']:
            raise ValueError('Cue samples are outside audio or do not cover contiguous speech segments')
        for key, sample in (('start', first), ('end', end)):
            seconds = cue.get(key)
            if type(seconds) not in (int, float) or not math.isfinite(seconds) \
                    or abs(seconds - sample / audio['sample_rate']) > 1e-9:
                raise ValueError('Cue seconds are not derived from actual PCM samples')
        last_end = end
    if cues and last_end != audio['frames']:
        raise ValueError('Measured speech cues do not cover the complete audio')
    if sum(len(cue['text']) for cue in cues) > 4096:
        raise ValueError('Measured cue text exceeds the renderer script limit')
    if cues and expected_text is not None and ' '.join(' '.join(cue['text'] for cue in cues).split()) != ' '.join(expected_text.split()):
        raise ValueError('Measured cue text does not match scene narration')
    return path, audio_path, receipt, audio, hashlib.sha256(raw).hexdigest()
