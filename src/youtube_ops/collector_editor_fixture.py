"""Owned, unbranded native technical fixture; not a narrated acceptance demo."""
import argparse
import json
import math
from pathlib import Path
import struct
import wave
import zlib

from .collector_editor import OpenShot


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


def build(client, directory, width=360, height=640, reuse_session=False):
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
    first = client.save(directory / 'technical-v1.osp')
    edit = [{'method': 'text.set', 'params': {'id': applied['refs']['title2']['clip']['id'],
             'text': 'Local review only\nRevision 2'}}]
    changed = client.apply(edit, client.inspect()['revision'])
    second = client.save(directory / 'technical-v2.osp')
    reopened = client.reopen(second['path'], second['sha256'])
    return {'session_id': started['session_id'], 'first_project': first, 'project': second,
            'reopened': reopened, 'changed': changed, 'directory': str(directory),
            'end_frame': 1500, 'expected_duration_seconds': 50,
            'voice': 'BLOCKED: no licensed VoiceStudio narration supplied',
            'branding': 'BLOCKED: unbranded technical fixture; approved bookends not supplied',
            'caption_alignment': 'NOT TESTED: timed technical text is not speech alignment',
            'manual_edit': 'NOT TESTED', 'review_only': True, 'publication_eligible': False}


def main():
    parser = argparse.ArgumentParser(description='Create an owned OpenShot local technical fixture, without rendering')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--session', help='Reuse an already enrolled, reconciled native session')
    parser.add_argument('--width', type=int, choices=[360, 1080], default=360)
    args = parser.parse_args()
    client = OpenShot(args.executable, args.executable_sha256, args.vault, args.session)
    result = build(client, args.directory, args.width, args.width * 16 // 9, bool(args.session))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
