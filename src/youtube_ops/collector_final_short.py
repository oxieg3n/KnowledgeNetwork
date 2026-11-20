"""One original, editable local-review Short using the existing native editor.

This is bounded acceptance orchestration, not another timeline or narrator.
Native receipts remain authoritative and uncertain operations are never retried.
"""
from fractions import Fraction
import json
import os
from pathlib import Path
import struct
import wave

from PIL import Image, ImageDraw

from .collector_editor import digest, write_json
from .collector_editor_fixture import attach_narration_to_fixture, capture_music_baseline
from .intro import render_intro, verify_intro
from .outro import verify_outro
from .collector_narration_receipt import read_voxcpm2_receipt


TITLE = 'Verify the bytes'
SEGMENTS = (
    'Your files can be copied perfectly, but how can you tell?',
    "A checksum turns a file's bytes into a short fingerprint.",
    'Change one byte, and a cryptographic hash will usually change dramatically.',
    'When you copy an important video, compare the SHA two fifty six hashes before and after.',
    'Matching hashes give strong evidence that the bytes arrived unchanged.',
    'But a checksum does not prove who created a file, or whether it is safe.',
    'Get the expected hash through a trusted source.',
    'Verify the bytes, then verify the source.',
)
SOURCE = 'https://csrc.nist.gov/projects/hash-functions'
BODY_FRAMES, INTRO_FRAMES, OUTRO_FRAMES, FPS = 1218, 48, 234, 30


def caption_frames(cues, sample_rate):
    """Keep measured samples authoritative; quantize once, then offset bookends."""
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError('Measured positive sample rate required')
    result = []
    last = 0
    for cue in cues:
        start, end = cue['start_sample'], cue['end_sample']
        if (type(start) is not int or type(end) is not int or not last <= start < end
                or not isinstance(cue['text'], str) or not 1 <= len(cue['text']) <= 96):
            raise ValueError('Ordered measured caption segments required')
        first = round(Fraction(start * FPS, sample_rate))
        final = round(Fraction(end * FPS, sample_rate))
        if not 0 <= first < final <= BODY_FRAMES:
            raise ValueError('Measured speech exceeds final body interval')
        result.append({'text': cue['text'], 'start_sample': start, 'end_sample': end,
                       'first_frame': first + INTRO_FRAMES, 'end_frame': final + INTRO_FRAMES})
        last = end
    if not result:
        raise ValueError('Actual measured narration cues required')
    return result


def _music(path):
    """Original quiet chord bed; no third-party recordings or samples."""
    import math
    rate = 16000
    count = BODY_FRAMES * rate // FPS
    chords = ((130.8128, 164.8138, 195.9977), (110, 130.8128, 164.8138),
              (87.3071, 110, 130.8128), (97.9989, 123.4708, 146.8324))
    samples = bytearray()
    for frame in range(count):
        t = frame / rate
        chord = chords[min(3, int(t / 10.15))]
        local = t % 10.15
        envelope = min(1, t / 1.5, local / .3, (10.15 - local) / .3,
                       (count - frame - 1) / (rate * 2))
        value = sum(math.sin(2 * math.pi * frequency * t) for frequency in chord) / 3
        value += .12 * math.sin(2 * math.pi * chord[0] * 2 * t)
        samples.extend(struct.pack('<h', round(8000 * envelope * value)))
    with wave.open(str(path), 'wb') as output:
        output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        output.writeframes(samples)


def _assets(directory):
    backgrounds, diagrams = [], []
    colors = ('#111c2a', '#142333', '#192332')
    for index, color in enumerate(colors):
        background = directory / f'scene-{index + 1}.png'
        picture = Image.new('RGB', (1080, 1920), color)
        draw = ImageDraw.Draw(picture)
        draw.rectangle((0, 0, 1080, 18), fill='#67c6d9')
        draw.line((84, 1560, 996, 1560), fill='#34475a', width=2)
        picture.save(background)
        backgrounds.append(background)
        art = Image.new('RGBA', (1080, 1920))
        d = ImageDraw.Draw(art)
        if index == 0:
            d.rounded_rectangle((220, 610, 860, 1110), 28, fill='#233a50', outline='#87d8e4', width=4)
            for row in range(4):
                for column in range(8):
                    x, y = 270 + column * 65, 670 + row * 80
                    d.rounded_rectangle((x, y, x + 36, y + 36), 6,
                                        fill='#6fc7d8' if (row + column) % 3 else '#e9bd77')
            d.line((300, 1050, 780, 1050), fill='#a6e2e9', width=8)
        elif index == 1:
            for x in (130, 620):
                d.rounded_rectangle((x, 680, x + 330, 1060), 24, fill='#244459', outline='#87d8e4', width=4)
                for row in range(4):
                    d.line((x + 55, 750 + row * 68, x + 270, 750 + row * 68), fill='#87d8e4', width=8)
            d.line((475, 860, 600, 860), fill='#e9bd77', width=10)
            d.polygon(((600, 860), (565, 835), (565, 885)), fill='#e9bd77')
        else:
            d.polygon(((540, 590), (820, 700), (790, 1040), (540, 1230), (290, 1040), (260, 700)),
                      fill='#244459', outline='#87d8e4', width=4)
            d.line((390, 900, 500, 1010, 700, 790), fill='#e9bd77', width=22)
        diagram = directory / f'diagram-{index + 1}.png'
        art.save(diagram)
        diagrams.append(diagram)
    bed = directory / 'original-chord-bed.wav'
    _music(bed)
    return backgrounds, diagrams, bed


def prepare_body(client, directory):
    """Create actual native editable content; explicitly incomplete without voice."""
    directory = client.local_path(Path(directory) / 'body-state.json', {'.json'}, exists=False).parent
    if any(directory.iterdir()):
        raise ValueError('Body requires a fresh empty private directory')
    current = client.inspect()
    if client._invoke(['clip', 'list'])['data']:
        raise ValueError('Acceptance requires a fresh empty native project')
    layers = sorted(item['number'] for item in current['data']['layers'])
    if len(layers) < 5:
        raise ValueError('Five independent native layers required')
    backgrounds, diagrams, bed = _assets(directory)
    commands = [{'method': 'project.profile.set', 'params': {'values': {
        'width': 1080, 'height': 1920, 'fps': {'num': FPS, 'den': 1},
        'display_ratio': {'num': 9, 'den': 16}, 'pixel_ratio': {'num': 1, 'den': 1}}}}]
    titles = ('A file has a fingerprint', 'Copy. Then compare.', 'Integrity needs a source')
    subtitles = ('01  /  SHA-256', '02  /  VERIFY THE TRANSFER', '03  /  TRUSTED EXPECTATION')
    for index in range(3):
        position, duration = index * 406 / FPS, 406 / FPS
        commands += [
            {'method': 'file.import', 'as': f'bgfile{index}', 'params': {'path': str(backgrounds[index])}},
            {'method': 'clip.add', 'as': f'bg{index}', 'params': {'file_id': {'$ref': f'bgfile{index}.id'},
                'layer': layers[0], 'position': position, 'end': duration}},
            {'method': 'file.import', 'as': f'artfile{index}', 'params': {'path': str(diagrams[index])}},
            {'method': 'clip.add', 'as': f'art{index}', 'params': {'file_id': {'$ref': f'artfile{index}.id'},
                'layer': layers[3], 'position': position, 'end': duration}},
            {'method': 'effects.add', 'as': f'color{index}', 'params': {
                'clip_id': {'$ref': f'art{index}.id'}, 'type': 'Saturation'}},
            {'method': 'effects.set', 'params': {'id': {'$ref': f'color{index}.id'},
                'values': {'saturation': .82}}},
            {'method': 'clip.fade', 'params': {'id': {'$ref': f'art{index}.id'}, 'fade_in': .3, 'fade_out': .3}},
            {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': f'art{index}.id'},
                'property': 'scale_x', 'space': 'clip', 'unit': 'seconds', 'at': 0, 'value': .92}},
            {'method': 'clip.keyframe.set', 'params': {'id': {'$ref': f'art{index}.id'},
                'property': 'scale_x', 'space': 'clip', 'unit': 'seconds', 'at': duration - 1/FPS, 'value': 1.02}},
            {'method': 'text.add', 'as': f'title{index}', 'params': {'text': titles[index],
                'font_family': 'Segoe UI', 'font_size': 72, 'font_bold': True, 'width': 900,
                'color': '#f0f5fa', 'layer': layers[4], 'position': position, 'duration': duration, 'place': 'top'}},
            {'method': 'text.add', 'params': {'text': subtitles[index],
                'font_family': 'Segoe UI', 'font_size': 36, 'width': 900, 'color': '#91cedc',
                'layer': layers[4], 'position': position, 'duration': duration, 'place': 'lower-third'}},
        ]
    commands += [
        {'method': 'file.import', 'as': 'musicfile', 'params': {'path': str(bed)}},
        {'method': 'clip.add', 'as': 'music', 'params': {'file_id': {'$ref': 'musicfile.id'},
            'layer': layers[1], 'position': 0, 'end': BODY_FRAMES/FPS, 'audio_only': True, 'volume': .15}},
    ]
    applied = client.apply(commands, current['revision'])
    capture_music_baseline(client, applied['refs']['music']['id'], applied['revision'])
    state = {'status': 'INCOMPLETE_BODY_ONLY', 'session_id': client.session,
             'revision': applied['revision'], 'refs': applied['refs'], 'directory': str(directory),
             'sources': [SOURCE], 'script': list(SEGMENTS), 'body_frames': BODY_FRAMES,
             'real_narration': False, 'bookends_assembled': False, 'publication_eligible': False}
    write_json(directory/'body-state.json', state)
    return state


def finish(client, state, receipt_path, badge_path, outro_path, font_path):
    """Finish a fresh owned body once, then save/reopen/revise the exact edit."""
    if (state.get('status') != 'INCOMPLETE_BODY_ONLY' or state.get('session_id') != client.session
            or client.inspect()['revision'] != state['revision']):
        raise ValueError('Body changed or completion uncertain; reconcile instead of replaying')
    directory = Path(state['directory'])
    if (directory/'finalization-intent.json').exists():
        raise ValueError('Finalization already attempted; reconcile existing state')
    directory = client.local_path(directory/'finalization-intent.json', {'.json'}, exists=False).parent
    badge = client.local_path(badge_path, {'.png'})
    outro = client.local_path(outro_path, {'.mp4'})
    verify_intro({'template': 'poweredby-plasma-v1', 'title': TITLE}, badge)
    outro_evidence = verify_outro({'template': 'poweredby-plasma-outro-v1'}, outro, 'short')
    # Validate all measured cues and body fit before any timeline mutation.
    from .collector_editor_fixture import narration_receipt
    _, _, receipt, audio, _ = narration_receipt(client, receipt_path, BODY_FRAMES)
    read_voxcpm2_receipt(receipt_path, expected_text=' '.join(state['script']),
                         max_duration=BODY_FRAMES/FPS)
    captions = caption_frames(receipt['cues'], audio['sample_rate'])
    with (directory/'finalization-intent.json').open('x', encoding='utf-8') as stream:
        json.dump({'revision': state['revision'], 'receipt_sha256': digest(receipt_path),
                   'outro_sha256': outro_evidence['sha256']}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    narration = attach_narration_to_fixture(client, receipt_path, state['revision'], body_frames=BODY_FRAMES)
    first_frame = directory/'native-body-first.png'
    client.thumbnail(first_frame, frame=1, width=1080, height=1920)
    intro_directory = directory/'intro'
    intro_directory.mkdir()
    with Image.open(first_frame) as picture:
        intro = render_intro({'template': 'poweredby-plasma-v1', 'title': TITLE}, badge,
                             picture.convert('RGB'), intro_directory, str(font_path))
    clips = client._invoke(['clip', 'list'])['data']
    commands = [{'method': 'clip.set', 'params': {'id': clip['id'],
                'values': {'position': clip['position'] + INTRO_FRAMES/FPS}}} for clip in clips]
    layers = sorted(item['number'] for item in client.inspect()['data']['layers'])
    for name, media, start, duration in (
            ('intro', intro, 0, INTRO_FRAMES/FPS),
            ('outro', outro, (INTRO_FRAMES + BODY_FRAMES)/FPS, OUTRO_FRAMES/FPS)):
        commands += [
            {'method': 'file.import', 'as': name+'file', 'params': {'path': str(media)}},
            {'method': 'clip.add', 'as': name, 'params': {'file_id': {'$ref': name+'file.id'},
                'layer': layers[0], 'position': start, 'end': duration, 'volume': 1}},
        ]
    assembled = client.apply(commands, client.inspect()['revision'])
    revision1 = client.save(directory/'knowledge-network-review-v1.osp')
    client.reopen(revision1['path'], revision1['sha256'])
    revised = client.apply([{'method': 'text.set', 'params': {
        'id': state['refs']['title2']['clip']['id'], 'text': 'Verify bytes. Verify sources.'}}], client.inspect()['revision'])
    revision2 = client.save(directory/'knowledge-network-review-v2.osp')
    reopened = client.reopen(revision2['path'], revision2['sha256'])
    result = {'status': 'NATIVE_PROJECT_READY_FOR_EXPORT', 'session_id': client.session,
              'project': revision2, 'first_project': revision1, 'reopened': reopened,
              'revised': revised, 'assembled': assembled, 'narration': narration,
              'captions': captions, 'intro_sha256': digest(intro), 'outro': outro_evidence,
              'end_frame': INTRO_FRAMES + BODY_FRAMES + OUTRO_FRAMES,
              'owner_final_mix_review': 'PENDING', 'publication_eligible': False}
    write_json(directory/'final-project-result.json', result)
    return result
