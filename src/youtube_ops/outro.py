"""Exact owner-approved end card; local assets only, no publication permission."""
from pathlib import Path
import shutil
from .render import sha256, probe

TEMPLATE = 'poweredby-plasma-outro-v1'
DURATION = 7.8
ASSETS = {
    'short': {'sha256': '62496803360e377d81ab54b6970d94fcce3eee125f5d22c2fe08377dcf1b5c9b',
              'size': (1080, 1920)},
    'landscape': {'sha256': '3720a160cd8acb46c828d448cca740252fb8c6a80eba892f1573dc5b56479ee3',
                  'size': (1920, 1080)},
}


def validate_config(config):
    if config != {'template': TEMPLATE}:
        raise ValueError('unknown or modified approved outro configuration')


def verify_outro(config, path, format):
    validate_config(config)
    expected = ASSETS[format]
    if sha256(Path(path)) != expected['sha256']:
        raise ValueError('approved outro hash mismatch')
    info = probe(Path(path))
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    if (video['width'], video['height']) != expected['size'] or any(
        abs(float(s['duration']) - DURATION) > 1/30 for s in (video, audio)):
        raise ValueError('approved outro dimensions or timeline mismatch')
    return dict(template=TEMPLATE, sha256=expected['sha256'], duration_seconds=DURATION,
                owner_approved=True, text='Like, Follow, Subscribe!',
                origin='approved circular logo; original procedural plasma and crackle; Piper LJ Speech voice',
                voice_license='MIT model; public-domain LJ Speech recordings',
                voice_license_url='https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD',
                final_combined_listening_review='pending')


def append_outro(config, path, format, output, segments):
    evidence = verify_outro(config, path, format)
    evidence['start_seconds'] = sum(float(probe(p)['format']['duration']) for p in segments)
    target = output / 'approved-outro.mp4'
    shutil.copyfile(path, target)
    if sha256(target) != evidence['sha256']:
        raise ValueError('outro copy verification failed')
    segments.append(target)
    return evidence


def verify_assembled_timeline(info, expected_duration):
    streams = {s['codec_type']: s for s in info['streams'] if s['codec_type'] in ('video', 'audio')}
    return set(streams) == {'video', 'audio'} and all(
        abs(float(s.get('duration', 0)) - expected_duration) <= 0.15
        for s in streams.values())
