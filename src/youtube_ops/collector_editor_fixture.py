"""Owned, unbranded native technical fixture; not a narrated acceptance demo."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from fractions import Fraction
import re
import struct
import uuid
import wave
import zlib

from .collector_editor import OpenShot, digest, write_json
from .collector_voice import inspect_wav, MAX_WAV


def narration_receipt(client, path):
    """Validate the remote provider's Forge-local artifact; never fetch a host path."""
    path = client.local_path(path, {'.json'})
    if path.name != 'narration.json':
        raise ValueError('Expected the remote provider narration.json receipt')
    with path.open('rb') as stream:
        raw = stream.read(128 * 1024 + 1)
    if len(raw) > 128 * 1024:
        raise ValueError('Narration receipt exceeds limit')
    receipt = json.loads(raw)
    if not isinstance(receipt, dict) or receipt.get('provider') != 'voicestudio_remote' or receipt.get('status') != 'generated_pending_review' \
            or receipt.get('review_only') is not True or receipt.get('publication_eligible') is not False:
        raise ValueError('A completed remote review-only narration receipt is required')
    for key in ('text_sha256', 'rights_sha256', 'host_model_evidence_sha256'):
        if not isinstance(receipt.get(key), str) or not re.fullmatch('[a-f0-9]{64}', receipt[key]):
            raise ValueError('Narration provenance evidence is missing')
    for key in ('engine_id', 'voice_id', 'model_id', 'model_revision'):
        if not isinstance(receipt.get(key), str) or not 1 <= len(receipt[key]) <= 256:
            raise ValueError('Narration model/profile identity is missing')
    audio_path = client.local_path(path.with_name('narration.wav'), {'.wav'})
    with audio_path.open('rb') as stream:
        audio_bytes = stream.read(MAX_WAV + 1)
    if len(audio_bytes) > MAX_WAV:
        raise ValueError('Narration audio exceeds limit')
    audio = inspect_wav(audio_bytes)
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
            or abs(duration - audio['duration_seconds']) > 1e-9 or not .1 <= duration <= 50:
        raise ValueError('Narration duration is invalid or exceeds the 50-second fixture')
    cues = receipt.get('cues', [])
    if not isinstance(cues, list) or len(cues) > 16:
        raise ValueError('Expected at most 16 actual measured speech cues')
    last_end = 0
    for cue in cues:
        if not isinstance(cue, dict) or not isinstance(cue.get('text'), str) \
                or not 1 <= len(cue['text']) <= 4096 or '\x00' in cue['text']:
            raise ValueError('Invalid measured cue text')
        first, end = cue.get('start_sample'), cue.get('end_sample')
        if type(first) is not int or type(end) is not int or not last_end <= first < end <= audio['frames']:
            raise ValueError('Cue samples are outside audio or overlap')
        for key, sample in (('start', first), ('end', end)):
            value = cue.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) \
                    or abs(value - sample / audio['sample_rate']) > 1e-9:
                raise ValueError('Cue seconds are not derived from actual PCM samples')
        last_end = end
    if sum(len(cue['text']) for cue in cues) > 4096:
        raise ValueError('Measured cue text exceeds the provider script limit')
    return path, audio_path, receipt, audio


def caption_fingerprint(client, clip_id):
    clip = client._invoke(['clip', 'get', clip_id])['data']
    style = client._invoke(['text', 'get', clip_id])['data']['style']
    # Saving relocates thumbnail caches; every other native clip/style field is protected.
    clip = {key: value for key, value in clip.items() if key != 'image'}
    return hashlib.sha256(json.dumps({'clip': clip, 'style': style}, sort_keys=True).encode()).hexdigest()


def replaced_caption_ids(client, speech_id, clips):
    matches = []
    for path in client.receipts.glob('*.json'):
        if not re.fullmatch('[0-9a-f]{32}', path.stem):
            continue
        record = json.loads(path.read_text())
        result = record.get('result', {})
        if record.get('kind') == 'narration.attach' and (
                result.get('speech_clip_id') or result.get('native', {}).get('refs', {}).get('speech', {}).get('id')) == speech_id:
            matches.append(result)
    if not matches:
        return []  # First attachment may explicitly replace the fixture's original accent.
    if len(matches) != 1 or matches[0].get('caption_ownership') != 'managed':
        raise ValueError('Narration caption ownership is ambiguous; reconcile before retake')
    captions = matches[0]['generated_captions']
    present = {clip['id'] for clip in clips}
    for caption in captions:
        if caption['clip_id'] not in present or caption_fingerprint(client, caption['clip_id']) != caption['sha256']:
            raise ValueError('Generated caption was changed or removed; preserve manual edits and reconcile retake')
    return [caption['clip_id'] for caption in captions]


def attach_narration_to_fixture(client, receipt_path, base_revision, replace_clip_id=None):
    """Import verified remote audio into this fixture's dedicated third track."""
    path, audio_path, receipt, audio = narration_receipt(client, receipt_path)
    current = client.inspect()
    if current['revision'] != base_revision:
        raise ValueError('Fixture changed; inspect the new revision')
    data = current['data']
    layers = sorted(layer['number'] for layer in data['layers'])
    if len(layers) < 5:
        raise ValueError('The owned fixture requires five native layers')
    clips = client._invoke(['clip', 'list'])['data']
    speech_clips = [clip for clip in clips if clip['layer'] == layers[2]]
    if speech_clips and (len(speech_clips) != 1 or speech_clips[0]['id'] != replace_clip_id):
        raise ValueError('Speech track occupied; explicitly identify the owned accent clip to replace')
    if replace_clip_id is not None and not speech_clips:
        raise ValueError('The requested accent clip is not on the speech track')
    commands = [{'method': 'clip.remove', 'params': {'id': replace_clip_id}}] if speech_clips else []
    if speech_clips:
        commands += [{'method': 'clip.remove', 'params': {'id': clip_id}}
                     for clip_id in replaced_caption_ids(client, replace_clip_id, clips)]
    commands += [
        {'method': 'file.import', 'as': 'narration', 'params': {'path': str(audio_path)}},
        {'method': 'clip.add', 'as': 'speech', 'params': {'file_id': {'$ref': 'narration.id'},
            'layer': layers[2], 'position': 0, 'end': audio['duration_seconds'], 'audio_only': True, 'volume': 1}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'speech.id'}, 'property': 'volume',
            'fade_in': .02, 'fade_out': .02, 'value': 1}},
    ]
    for clip in clips:
        if clip['layer'] == layers[1]:
            for at, value in [(0, .05), (audio['duration_seconds'], .05)]:
                commands.append({'method': 'clip.keyframe.set', 'params': {'id': clip['id'],
                    'property': 'volume', 'space': 'timeline', 'unit': 'seconds', 'at': at, 'value': value}})
            if audio['duration_seconds'] < 49:
                commands.append({'method': 'clip.keyframe.set', 'params': {'id': clip['id'],
                    'property': 'volume', 'space': 'timeline', 'unit': 'seconds',
                    'at': audio['duration_seconds'] + .5, 'value': .25}})
    cues = receipt.get('cues', [])
    alignment = 'BLOCKED: actual measured speech cues were not supplied'
    if cues and all(len(cue['text']) <= 96 and cue['text'].count('\n') <= 1 for cue in cues):
        fps = Fraction(data['fps']['num'], data['fps']['den'])
        for index, cue in enumerate(cues):
            first = round(Fraction(cue['start_sample'], audio['sample_rate']) * fps)
            end = round(Fraction(cue['end_sample'], audio['sample_rate']) * fps)
            if end <= first:
                raise ValueError('Measured speech cue is shorter than one project frame')
            commands += [
                {'method': 'text.add', 'as': 'caption' + str(index), 'params': {
                    'text': cue['text'], 'layer': layers[4], 'position': float(first / fps),
                    'duration': float((end-first) / fps), 'font_family': 'Segoe UI',
                    'font_size': max(8, data['width'] // 24), 'width': int(data['width'] * .85),
                    'color': '#ffffff', 'background': '#c0202933', 'background_padding': 10, 'place': 'center'}},
                {'method': 'clip.set', 'params': {'id': {'$ref': 'caption' + str(index) + '.clip.id'},
                    'values': {'location_y': .20}}},
            ]
        alignment = 'MEASURED_SEGMENT_CUES_PENDING_REVIEW: sample boundaries quantized to native project frames'
    elif cues:
        alignment = 'BLOCKED: measured cue text too long; request shorter measured speech segments'
    applied = client.apply(commands, base_revision)
    result = {'provider': receipt['provider'], 'audio': audio, 'receipt_sha256': digest(path),
        'text_sha256': receipt['text_sha256'],
        'rights_sha256': receipt['rights_sha256'], 'host_model_evidence_sha256': receipt['host_model_evidence_sha256'],
        'engine_id': receipt['engine_id'], 'voice_id': receipt['voice_id'], 'model_id': receipt['model_id'],
        'model_revision': receipt['model_revision'], 'caption_alignment': alignment, 'native': applied,
        'speech_clip_id': applied['refs']['speech']['id'], 'generated_captions': [],
        'caption_ownership': 'pending',
        'review_only': True, 'publication_eligible': False, 'listening': 'NOT_TESTED'}
    ownership_path = client.receipts / (uuid.uuid4().hex + '.json')
    write_json(ownership_path, {'kind': 'narration.attach', 'result': result})
    if alignment.startswith('MEASURED_SEGMENT'):
        for index in range(len(cues)):
            clip_id = applied['refs']['caption' + str(index)]['clip']['id']
            result['generated_captions'].append({'clip_id': clip_id, 'sha256': caption_fingerprint(client, clip_id)})
    if client.inspect()['revision'] != applied['revision']:
        raise ValueError('Fixture changed while recording caption ownership; reconcile before retake')
    result['caption_ownership'] = 'managed'
    write_json(ownership_path, {'kind': 'narration.attach', 'result': result})
    return result


def png(path, width, height, color, transparent=False):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            inside = 10 <= x < width - 10 and 10 <= y < height - 10
            rows.extend((*color, 230 if inside else 0) if transparent else (*color, 255))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 6, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(bytes(rows))) + chunk(b'IEND', b''))


def tone(path, frequency, seconds=50):
    rate = 16000
    samples = bytearray()
    for i in range(seconds * rate):
        envelope = min(1, i / rate, (seconds * rate - i - 1) / rate)
        samples.extend(struct.pack('<h', int(1000 * envelope * math.sin(2 * math.pi * frequency * i / rate))))
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(samples)


def build(client, directory, width=360, height=640, reuse_session=False, narration_path=None):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(client.vault) or directory.exists():
        raise ValueError('Fixture requires a new directory inside the private vault')
    directory.mkdir()
    backgrounds = []
    for index, color in enumerate([(25, 32, 41), (29, 38, 48), (22, 34, 43)]):
        path = directory / ('scene-' + str(index) + '.png')
        png(path, width, height, color)
        backgrounds.append(path)
    graphic = directory / 'original-graphic.png'
    png(graphic, width, height, (51, 124, 151), transparent=True)
    bed = directory / 'original-ambient.wav'
    accent = directory / 'original-accent.wav'
    tone(bed, 165)
    tone(accent, 220)
    started = {'session_id': client.session} if reuse_session else client.start()
    current = client.inspect()
    layers = sorted(layer['number'] for layer in current['data']['layers'])
    if len(layers) < 5:
        raise RuntimeError('Fixture requires five native OpenShot layers')
    commands = [{'method': 'project.profile.set', 'params': {'values': {
        'width': width, 'height': height, 'fps': {'num': 30, 'den': 1},
        'display_ratio': {'num': 9, 'den': 16}, 'pixel_ratio': {'num': 1, 'den': 1}}}}]
    scenes = [(0, 16, 'Research', 'Original technical fixture'),
              (16, 17, 'Editable timeline', 'Research > edit > voice > review'),
              (33, 17, 'Local review only', 'Shorts / recap / blog adaptations')]
    for index, (position, duration, title, caption) in enumerate(scenes):
        commands.extend([
            {'method': 'file.import', 'as': 'scene' + str(index), 'params': {'path': str(backgrounds[index])}},
            {'method': 'clip.add', 'as': 'background' + str(index), 'params': {
                'file_id': {'$ref': 'scene' + str(index) + '.id'}, 'layer': layers[0],
                'position': position, 'start': 0, 'end': duration}},
            {'method': 'text.add', 'as': 'title' + str(index), 'params': {
                'text': title, 'layer': layers[4], 'position': position, 'duration': duration,
                'font_family': 'Segoe UI', 'font_size': int(width / 11), 'font_bold': True,
                'color': '#eef4f8', 'width': int(width * .85), 'place': 'top'}},
            {'method': 'text.add', 'params': {
                'text': caption, 'layer': layers[4], 'position': position, 'duration': duration,
                'font_family': 'Segoe UI', 'font_size': int(width / 19), 'color': '#d5e4ed',
                'width': int(width * .84), 'place': 'lower-third', 'background': '#b0202933',
                'background_padding': 10}},
        ])
    commands.extend([
        {'method': 'text.add', 'as': 'review_label', 'params': {
            'text': 'LOCAL REVIEW ONLY\nUnbranded technical test', 'layer': layers[4],
            'position': 0, 'duration': 50, 'font_family': 'Segoe UI',
            'font_size': int(width / 28), 'color': '#b5c4cf',
            'width': int(width * .85), 'place': 'bottom'}},
        {'method': 'file.import', 'as': 'graphic', 'params': {'path': str(graphic)}},
        {'method': 'clip.add', 'as': 'overlay', 'params': {'file_id': {'$ref': 'graphic.id'},
            'layer': layers[3], 'position': 0, 'end': 50}},
        {'method': 'clip.set', 'params': {'id': {'$ref': 'overlay.id'},
            'values': {'scale_x': .55, 'scale_y': .18, 'rotation': -5}}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'overlay.id'}, 'fade_in': 1, 'fade_out': 1}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'overlay.id'}, 'property': 'location_x',
            'space': 'clip', 'unit': 'seconds', 'at': 0, 'value': -.15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'overlay.id'}, 'property': 'location_x',
            'space': 'clip', 'unit': 'seconds', 'at': 49, 'value': .15}},
        {'method': 'effects.add', 'params': {'clip_id': {'$ref': 'overlay.id'}, 'type': 'Saturation'}},
        {'method': 'file.import', 'as': 'bed', 'params': {'path': str(bed)}},
        {'method': 'clip.add', 'as': 'bedclip', 'params': {'file_id': {'$ref': 'bed.id'},
            'layer': layers[1], 'position': 0, 'end': 50, 'audio_only': True, 'volume': .25}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'bedclip.id'}, 'property': 'volume',
            'fade_in': 1, 'fade_out': 2, 'value': .25}},
        {'method': 'file.import', 'as': 'accent', 'params': {'path': str(accent)}},
        {'method': 'clip.add', 'as': 'accentclip', 'params': {'file_id': {'$ref': 'accent.id'},
            'layer': layers[2], 'position': 0, 'end': 50, 'audio_only': True, 'volume': .15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': 1, 'value': .15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': 16, 'value': .03}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': 33, 'value': .15}},
    ])
    applied = client.apply(commands, current['revision'])
    narration = None
    if narration_path is not None:
        narration = attach_narration_to_fixture(client, narration_path, applied['revision'],
                                                applied['refs']['accentclip']['id'])
    first = client.save(directory / 'technical-v1.osp')
    edit = [{'method': 'text.set', 'params': {'id': applied['refs']['title2']['clip']['id'],
             'text': 'Local review only\nRevision 2'}}]
    changed = client.apply(edit, client.inspect()['revision'])
    second = client.save(directory / 'technical-v2.osp')
    reopened = client.reopen(second['path'], second['sha256'])
    return {'session_id': started['session_id'], 'first_project': first, 'project': second,
            'reopened': reopened, 'changed': changed, 'directory': str(directory),
            'end_frame': 1500, 'expected_duration_seconds': 50,
            'voice': narration or 'BLOCKED: no licensed remote VoiceStudio narration supplied',
            'branding': 'BLOCKED: unbranded technical fixture; approved bookends not supplied',
            'caption_alignment': narration['caption_alignment'] if narration else 'NOT TESTED: timed technical text is not speech alignment',
            'manual_edit': 'NOT TESTED', 'review_only': True, 'publication_eligible': False}


def main():
    parser = argparse.ArgumentParser(description='Create an owned OpenShot local technical fixture, without rendering')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--session', help='Reuse an already enrolled, reconciled native session')
    parser.add_argument('--width', type=int, choices=[360, 1080], default=360)
    parser.add_argument('--narration-receipt', help='Verified remote narration.json inside the private editor vault')
    args = parser.parse_args()
    client = OpenShot(args.executable, args.executable_sha256, args.vault, args.session)
    result = build(client, args.directory, args.width, args.width * 16 // 9,
                   bool(args.session), args.narration_receipt)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
