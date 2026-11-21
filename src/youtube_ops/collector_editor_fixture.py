"""Owned, unbranded native technical fixture; not a narrated acceptance demo."""
import argparse
import hashlib
import json
import math
from itertools import product
from pathlib import Path
from fractions import Fraction
import re
import struct
import uuid
import wave
import zlib

from .collector_editor import OpenShot, digest, write_json
from .collector_narration_receipt import read_voxcpm2_receipt


def body_timing(body_frames=1500):
    if type(body_frames) is not int or not (body_frames == 1500 or 1068 <= body_frames <= 1368):
        raise ValueError('Body requires the legacy 1500 frames or a 45–55 second Short bookend budget')
    edges = [0, 480, 990, 1500] if body_frames == 1500 else [0, body_frames // 3, 2 * body_frames // 3, body_frames]
    return edges, Fraction(body_frames, 30)


def narration_receipt(client, path, body_frames=1500):
    _, duration = body_timing(body_frames)
    path = client.local_path(path, {'.json'})
    client.local_path(path.with_name('narration.wav'), {'.wav'})
    return read_voxcpm2_receipt(path, max_duration=float(duration))


def caption_fingerprint(client, clip_id):
    clip = client._invoke(['clip', 'get', clip_id])['data']
    style = client._invoke(['text', 'get', clip_id])['data']['style']
    # Saving relocates thumbnail caches; every other native clip/style field is protected.
    clip = {key: value for key, value in clip.items() if key != 'image'}
    return hashlib.sha256(json.dumps({'clip': clip, 'style': style}, sort_keys=True).encode()).hexdigest()


def music_fingerprint(clip):
    values = {key: clip.get(key) for key in ('id', 'position', 'start', 'end', 'volume')}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def music_matches_fingerprint(clip, expected):
    # Native save/reopen can encode the same integral time as 0 or 0.0.
    if music_fingerprint(clip) == expected:
        return True
    keys = ('position', 'start', 'end')
    choices = []
    for key in keys:
        value = clip.get(key)
        choices.append((int(value), float(int(value))) if type(value) in (int, float)
                       and abs(value) <= 2**53 and value == int(value) else (value,))
    return any(music_fingerprint(dict(clip, **dict(zip(keys, values)))) == expected
               for values in product(*choices))


def capture_music_baseline(client, clip_id, revision):
    path = client.receipts / (uuid.uuid4().hex + '.json')
    result = {'ownership': 'pending', 'managed_music': [{'clip_id': clip_id}]}
    write_json(path, {'kind': 'fixture.music', 'result': result})
    result['managed_music'][0]['sha256'] = music_fingerprint(client._invoke(['clip', 'get', clip_id])['data'])
    if client.inspect()['revision'] != revision:
        raise ValueError('Fixture changed while recording music baseline; reconcile before narration')
    result['ownership'] = 'managed'
    write_json(path, {'kind': 'fixture.music', 'result': result})


def replaced_narration(client, speech_id, clips):
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
        return None  # First attachment may explicitly replace the fixture's original accent.
    if len(matches) != 1 or matches[0].get('caption_ownership') != 'managed':
        raise ValueError('Narration caption ownership is ambiguous; reconcile before retake')
    captions = matches[0]['generated_captions']
    present = {clip['id'] for clip in clips}
    for caption in captions:
        if caption['clip_id'] not in present or caption_fingerprint(client, caption['clip_id']) != caption['sha256']:
            raise ValueError('Generated caption was changed or removed; preserve manual edits and reconcile retake')
    return matches[0]


def checked_music(client, clips, layer, previous):
    music_ids = {clip['id'] for clip in clips if clip['layer'] == layer}
    if previous is None:
        baselines = []
        for path in client.receipts.glob('*.json'):
            if re.fullmatch('[0-9a-f]{32}', path.stem):
                record = json.loads(path.read_text())
                result = record.get('result', {})
                if record.get('kind') == 'fixture.music' and {
                        item['clip_id'] for item in result.get('managed_music', [])} == music_ids:
                    baselines.append(result)
        if len(baselines) != 1 or baselines[0].get('ownership') != 'managed':
            raise ValueError('Managed fixture music baseline missing or ambiguous; reconcile before narration')
        owned = baselines[0]['managed_music']
    else:
        owned = previous.get('managed_music', [])
    if not owned or {item['clip_id'] for item in owned} != music_ids:
        raise ValueError('Music ownership changed; preserve manual music and reconcile narration')
    result = []
    for item in owned:
        clip = client._invoke(['clip', 'get', item['clip_id']])['data']
        if not music_matches_fingerprint(clip, item.get('sha256')):
            raise ValueError('Music gain or timing was changed; preserve manual edits and reconcile narration')
        result.append(clip)
    return result


def attach_narration_to_fixture(client, receipt_path, base_revision, replace_clip_id=None, body_frames=1500):
    """Import verified remote audio into this fixture's dedicated third track."""
    _, duration = body_timing(body_frames)
    path, audio_path, receipt, audio, receipt_hash = narration_receipt(client, receipt_path, body_frames)
    if Fraction(audio['frames'], audio['sample_rate']) > duration:
        raise ValueError('Measured narration exceeds the available body; preserve speech and revise timing')
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
    previous = replaced_narration(client, replace_clip_id, clips) if speech_clips else None
    music = checked_music(client, clips, layers[1], previous)
    commands = [{'method': 'clip.remove', 'params': {'id': replace_clip_id}}] if speech_clips else []
    if previous:
        commands += [{'method': 'clip.remove', 'params': {'id': caption['clip_id']}}
                     for caption in previous['generated_captions']]
    commands += [
        {'method': 'file.import', 'as': 'narration', 'params': {'path': str(audio_path)}},
        {'method': 'clip.add', 'as': 'speech', 'params': {'file_id': {'$ref': 'narration.id'},
            'layer': layers[2], 'position': 0, 'end': audio['duration_seconds'], 'audio_only': True, 'volume': 1}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'speech.id'}, 'property': 'volume',
            'fade_in': .02, 'fade_out': .02, 'value': 1}},
    ]
    fps = Fraction(data['fps']['num'], data['fps']['den'])
    speech_end = Fraction(audio['frames'], audio['sample_rate'])
    for clip in music:
        length = Fraction(str(clip['end'])) - Fraction(str(clip['start']))
        last = Fraction(round(length * fps) - 1, 1) / fps
        if last <= 0:
            raise ValueError('Managed music clip is too short for narration mixing')
        fade_start = max(Fraction(0), last - 2)
        points = {Fraction(0): 0, min(Fraction(1), speech_end, last): .05, fade_start: .05, last: 0}
        if speech_end < fade_start:
            points.update({speech_end: .05, min(speech_end + Fraction(1, 2), fade_start): .25, fade_start: .25})
        # Native scalar set replaces the entire Points curve, clearing owned prior restores.
        commands.append({'method': 'clip.set', 'params': {'id': clip['id'], 'values': {'volume': .05}}})
        commands += [{'method': 'clip.keyframe.set', 'params': {'id': clip['id'],
            'property': 'volume', 'space': 'clip', 'unit': 'seconds', 'at': float(at), 'value': value}}
            for at, value in sorted(points.items())]
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
    if digest(path) != receipt_hash or digest(audio_path) != audio['sha256']:
        raise ValueError('Narration artifacts changed after validation; reconcile before editing')
    applied = client.apply(commands, base_revision)
    result = {'provider': receipt['provider'], 'audio': audio, 'receipt_sha256': receipt_hash,
        'text_sha256': receipt['text_sha256'],
        'narrator_id': receipt['narrator_id'], 'provenance': {key: receipt['provenance'][key] for key in (
            'script_sha256', 'config_sha256', 'model_revision', 'license_evidence_sha256')},
        'caption_alignment': alignment, 'native': applied,
        'speech_clip_id': applied['refs']['speech']['id'], 'generated_captions': [],
        'managed_music': [],
        'caption_ownership': 'pending',
        'review_only': True, 'publication_eligible': False, 'listening': 'NOT_TESTED'}
    ownership_path = client.receipts / (uuid.uuid4().hex + '.json')
    write_json(ownership_path, {'kind': 'narration.attach', 'result': result})
    if alignment.startswith('MEASURED_SEGMENT'):
        for index in range(len(cues)):
            clip_id = applied['refs']['caption' + str(index)]['clip']['id']
            result['generated_captions'].append({'clip_id': clip_id, 'sha256': caption_fingerprint(client, clip_id)})
    result['managed_music'] = [{'clip_id': clip['id'], 'sha256': music_fingerprint(
        client._invoke(['clip', 'get', clip['id']])['data'])} for clip in music]
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
    frames = round(seconds * rate)
    samples = bytearray()
    for i in range(frames):
        envelope = min(1, i / rate, (frames - i - 1) / rate)
        samples.extend(struct.pack('<h', int(1000 * envelope * math.sin(2 * math.pi * frequency * i / rate))))
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(samples)


def build(client, directory, width=360, height=640, reuse_session=False, narration_path=None, body_frames=1500):
    edges, exact_duration = body_timing(body_frames)
    body_seconds = float(exact_duration)
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
    tone(bed, 165, body_seconds)
    tone(accent, 220, body_seconds)
    started = {'session_id': client.session} if reuse_session else client.start()
    current = client.inspect()
    layers = sorted(layer['number'] for layer in current['data']['layers'])
    if len(layers) < 5:
        raise RuntimeError('Fixture requires five native OpenShot layers')
    commands = [{'method': 'project.profile.set', 'params': {'values': {
        'width': width, 'height': height, 'fps': {'num': 30, 'den': 1},
        'display_ratio': {'num': 9, 'den': 16}, 'pixel_ratio': {'num': 1, 'den': 1}}}}]
    labels = [('Research', 'Original technical fixture'),
              ('Editable timeline', 'Research > edit > voice > review'),
              ('Local review only', 'Shorts / recap / blog adaptations')]
    scenes = [(edges[index] / 30, (edges[index + 1] - edges[index]) / 30, *label)
              for index, label in enumerate(labels)]
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
            'position': 0, 'duration': body_seconds, 'font_family': 'Segoe UI',
            'font_size': int(width / 28), 'color': '#b5c4cf',
            'width': int(width * .85), 'place': 'bottom'}},
        {'method': 'file.import', 'as': 'graphic', 'params': {'path': str(graphic)}},
        {'method': 'clip.add', 'as': 'overlay', 'params': {'file_id': {'$ref': 'graphic.id'},
            'layer': layers[3], 'position': 0, 'end': body_seconds}},
        {'method': 'clip.set', 'params': {'id': {'$ref': 'overlay.id'},
            'values': {'scale_x': .55, 'scale_y': .18, 'rotation': -5}}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'overlay.id'}, 'fade_in': 1, 'fade_out': 1}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'overlay.id'}, 'property': 'location_x',
            'space': 'clip', 'unit': 'seconds', 'at': 0, 'value': -.15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'overlay.id'}, 'property': 'location_x',
            'space': 'clip', 'unit': 'seconds', 'at': body_seconds - 1, 'value': .15}},
        {'method': 'effects.add', 'params': {'clip_id': {'$ref': 'overlay.id'}, 'type': 'Saturation'}},
        {'method': 'file.import', 'as': 'bed', 'params': {'path': str(bed)}},
        {'method': 'clip.add', 'as': 'bedclip', 'params': {'file_id': {'$ref': 'bed.id'},
            'layer': layers[1], 'position': 0, 'end': body_seconds, 'audio_only': True, 'volume': .25}},
        {'method': 'clip.fade', 'params': {'id': {'$ref': 'bedclip.id'}, 'property': 'volume',
            'fade_in': 1, 'fade_out': 2, 'value': .25}},
        {'method': 'file.import', 'as': 'accent', 'params': {'path': str(accent)}},
        {'method': 'clip.add', 'as': 'accentclip', 'params': {'file_id': {'$ref': 'accent.id'},
            'layer': layers[2], 'position': 0, 'end': body_seconds, 'audio_only': True, 'volume': .15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': 1, 'value': .15}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': edges[1] / 30, 'value': .03}},
        {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': 'accentclip.id'}, 'property': 'volume',
            'space': 'clip', 'unit': 'seconds', 'at': edges[2] / 30, 'value': .15}},
    ])
    applied = client.apply(commands, current['revision'])
    capture_music_baseline(client, applied['refs']['bedclip']['id'], applied['revision'])
    narration = None
    if narration_path is not None:
        narration = attach_narration_to_fixture(client, narration_path, applied['revision'],
                                                applied['refs']['accentclip']['id'], body_frames)
    first = client.save(directory / 'technical-v1.osp')
    edit = [{'method': 'text.set', 'params': {'id': applied['refs']['title2']['clip']['id'],
             'text': 'Local review only\nRevision 2'}}]
    changed = client.apply(edit, client.inspect()['revision'])
    second = client.save(directory / 'technical-v2.osp')
    reopened = client.reopen(second['path'], second['sha256'])
    return {'session_id': started['session_id'], 'first_project': first, 'project': second,
            'reopened': reopened, 'changed': changed, 'directory': str(directory),
            'end_frame': body_frames, 'expected_duration_seconds': body_seconds,
            'scene_frame_edges': edges,
            'bookend_budget': {'intro_frames': 48, 'outro_frames': 234,
                              'assembled_frames': body_frames + 282, 'assembled': False},
            'voice': narration or 'BLOCKED: verified VoxCPM2 Oxiegen-Narrator body WAV not supplied',
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
    parser.add_argument('--narration-receipt', help='Verified VoxCPM2 Oxiegen-Narrator narration.json inside the private editor vault')
    parser.add_argument('--body-frames', type=int, default=1500,
                        help='1500 for the retained technical fixture; 1218 reserves bookends inside a 50s Short')
    args = parser.parse_args()
    client = OpenShot(args.executable, args.executable_sha256, args.vault, args.session)
    result = build(client, args.directory, args.width, args.width * 16 // 9,
                   bool(args.session), args.narration_receipt, args.body_frames)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
