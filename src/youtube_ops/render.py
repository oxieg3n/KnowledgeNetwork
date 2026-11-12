"""Local original-graphics renderer. A render is evidence, never publication approval."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout)


def validate_spec(spec: dict) -> None:
    if spec.get('format') not in ('short', 'landscape'):
        raise ValueError('format must be short or landscape')
    scenes = spec.get('scenes', [])
    if not 1 <= len(scenes) <= 30:
        raise ValueError('one to thirty scenes required')
    for scene in scenes:
        for field, limit in [('title', 80), ('narration', 600), ('caption', 200)]:
            text = scene.get(field, '')
            if not isinstance(text, str) or not text.strip() or len(text) > limit:
                raise ValueError(f'invalid {field}')
            if any(ord(c) < 32 and c != '\n' for c in text):
                raise ValueError('control characters forbidden')
    if not isinstance(spec.get('sources', []), list):
        raise ValueError('sources must be a list')


def verify_voice(model: Path, metadata: dict) -> None:
    """Require independently reviewed rights and bind them to exact model bytes."""
    if metadata.get('rights_reviewed') is not True:
        raise ValueError('voice rights review required')
    for key in ('license', 'proof_url', 'rights_holder', 'model_sha256'):
        if not metadata.get(key):
            raise ValueError(f'missing voice provenance: {key}')
    if metadata.get('commercial_use') is not True or metadata.get('youtube_use') is not True:
        raise ValueError('voice publication scope missing')
    if sha256(model) != metadata['model_sha256']:
        raise ValueError('voice model hash mismatch')


def wrap(draw: Any, text: str, font: Any, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines():
        line = ''
        for word in para.split():
            candidate = f'{line} {word}'.strip()
            if draw.textlength(word, font=font) > width:
                raise ValueError('unbreakable word exceeds text area')
            if line and draw.textlength(candidate, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def card(scene: dict, path: Path, size: tuple[int, int], index: int, total: int,
         *, technical_test: bool, font_path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    im = Image.new('RGB', size, '#0c1420')
    d = ImageDraw.Draw(im)
    margin = 100 if w < h else 120
    def textblock(text: str, y: int, px: int, color: str, max_y: int) -> int:
        font = ImageFont.truetype(font_path, px)
        lines = wrap(d, text, font, w - 2 * margin)
        line_height = round(px * 1.38)
        if y + line_height * len(lines) > max_y:
            raise ValueError('text overflow: shorten scene text')
        for line in lines:
            d.text((margin, y), line, font=font, fill=color)
            y += line_height
        return y
    small = ImageFont.truetype(font_path, 28)
    d.text((margin, 90), 'POWERED BY OXIEG3N', font=small, fill='#7dd3fc')
    d.line((margin, 145, w-margin, 145), fill='#36506a', width=3)
    textblock(scene['title'], 215 if w < h else 185, 66 if w < h else 70, '#f8fafc', h // 2 - 30)
    # Original schematic, never presented as product evidence or measurements.
    cy = h // 2
    radius = 52 if w < h else 65
    centers = [margin + radius, w//2, w-margin-radius]
    for a, b in zip(centers, centers[1:]):
        d.line((a+radius, cy, b-radius, cy), fill='#4ea8d5', width=6)
    for j, cx in enumerate(centers):
        d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill='#172e42', outline='#7dd3fc', width=4)
        d.text((cx-12, cy-20), str(j+1), font=ImageFont.truetype(font_path, 32), fill='#ffffff')
    textblock(scene['caption'], cy + 140, 44 if w < h else 42, '#d9e5ef', h-200)
    label = 'TECHNICAL TEST • NOT FOR PUBLICATION' if technical_test else 'Original explanatory graphic • AI narration'
    d.text((margin, h-120), label, font=ImageFont.truetype(font_path, 22), fill='#9fb3c8')
    d.rectangle((margin, h-65, margin + int((w-2*margin)*(index+1)/total), h-57), fill='#7dd3fc')
    im.save(path)


def probe(path: Path) -> dict:
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]).stdout)


def assess_probe(data: dict, size: tuple[int, int], short: bool) -> dict:
    video = next((s for s in data['streams'] if s['codec_type']=='video'), {})
    audio = next((s for s in data['streams'] if s['codec_type']=='audio'), {})
    duration = float(data['format']['duration'])
    rate = video.get('avg_frame_rate', '0/1').split('/')
    fps = float(rate[0]) / float(rate[1]) if float(rate[1]) else 0
    checks = {
        'h264': video.get('codec_name') == 'h264',
        'pixel_format': video.get('pix_fmt') == 'yuv420p',
        'dimensions': (video.get('width'),video.get('height')) == size,
        'fps_30': abs(fps - 30) < 0.01,
        'aac_audio': audio.get('codec_name') == 'aac',
        'duration': 30 <= duration <= 60 if short else duration > 0,
    }
    return {'checks': checks, 'passed': all(checks.values()), 'duration_seconds': duration}


def render(spec: dict, output: Path, model: Path, voice_metadata: dict,
           font_path: str = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') -> dict:
    validate_spec(spec)
    verify_voice(model, voice_metadata)
    from piper import PiperVoice
    from PIL import __version__ as pillow_version
    if output.exists():
        raise FileExistsError('choose a new output directory; never overwrite recovery media')
    output.mkdir(parents=True)
    size = (1080, 1920) if spec['format']=='short' else (1920,1080)
    voice = PiperVoice.load(str(model))
    segments, durations, captions = [], [], []
    elapsed = 0.0
    for i, scene in enumerate(spec['scenes']):
        wav = output / f'scene-{i:02}.wav'
        with wave.open(str(wav), 'wb') as file:
            voice.synthesize_wav(scene['narration'], file)
        with wave.open(str(wav), 'rb') as file:
            duration = file.getnframes() / file.getframerate()
        png = output / f'scene-{i:02}.png'
        card(scene, png, size, i, len(spec['scenes']), technical_test=spec.get('technical_test',False), font_path=font_path)
        mp4 = output / f'scene-{i:02}.mp4'
        run(['ffmpeg','-hide_banner','-loglevel','error','-loop','1','-i',str(png),'-i',str(wav),
             '-t',str(duration),'-r','30','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-threads','2',str(mp4)])
        segments.append(mp4)
        durations.append(duration)
        captions.append({'start':round(elapsed,3),'end':round(elapsed+duration,3),'text':scene['narration']})
        elapsed += duration
    concat = output / 'segments.txt'
    # Generated safe basenames only; no untrusted strings in concat input.
    concat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    final = output / 'final.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(concat),
         '-c','copy','-movflags','+faststart',str(final)])
    qc = assess_probe(probe(final), size, spec['format']=='short')
    scan = run(['ffmpeg','-hide_banner','-i',str(final),'-vf','blackdetect=d=0.5:pix_th=0.05',
                '-af','silencedetect=n=-45dB:d=2,ebur128=peak=true','-f','null','-'])
    qc['black_segments'] = len(re.findall(r'black_start:', scan.stderr))
    qc['long_silences'] = len(re.findall(r'silence_start:', scan.stderr))
    qc['passed'] = qc['passed'] and qc['black_segments']==0 and qc['long_silences']==0
    qc['manual_checks'] = {k:'pending' for k in ('facts','rights','pronunciation','mobile_readability','caption_sync','distinct_editorial_value')}
    (output/'qc-analysis.txt').write_text(scan.stderr)
    (output/'captions.json').write_text(json.dumps(captions,indent=2))
    manifest = {
        'schema_version':1, 'technical_test':spec.get('technical_test',False),
        'publication_eligible':False, 'status':'rendered_pending_editorial_review',
        'sha256':sha256(final),'format':spec['format'],'sources':spec.get('sources',[]),
        'script_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),
        'voice':voice_metadata,'graphics':{'origin':'original programmatic schematic','font':'DejaVu Sans (Bitstream Vera / DejaVu license)'},
        'captions':'segment-aligned transcript; requires manual timing/readability review before publication',
        'pillow_version':pillow_version,'qc':qc,
    }
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('spec',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--voice',type=Path,required=True)
    ap.add_argument('--voice-metadata',type=Path,required=True)
    args=ap.parse_args()
    manifest=render(json.loads(args.spec.read_text()),args.output,args.voice,json.loads(args.voice_metadata.read_text()))
    print(json.dumps({'status':manifest['status'],'qc_passed':manifest['qc']['passed'],'publication_eligible':False}))

if __name__=='__main__':
    main()
