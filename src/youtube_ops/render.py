"""Local original-graphics renderer. A render is evidence, never publication approval."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import wave
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], *, timeout: int = 600, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)


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
        graphic = scene.get('graphic')
        if graphic is not None:
            validate_graphic(graphic)
    if not isinstance(spec.get('sources', []), list):
        raise ValueError('sources must be a list')


def validate_graphic(graphic: dict) -> None:
    if not isinstance(graphic, dict) or graphic.get('kind') not in ('flow', 'comparison', 'timeline'):
        raise ValueError('graphic kind must be flow, comparison, or timeline')
    items = graphic.get('items', [])
    if not isinstance(items, list) or not 2 <= len(items) <= 4:
        raise ValueError('graphic requires two to four items')
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('graphic item must be an object')
        for key, limit in [('label', 45), ('detail', 100)]:
            value = item.get(key, '')
            if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
                raise ValueError('invalid graphic item text')
    emphasis = graphic.get('emphasis')
    if emphasis is not None and (type(emphasis) is not int or not 0 <= emphasis < len(items)):
        raise ValueError('graphic emphasis must name an existing item')


def draw_graphic(draw: Any, graphic: dict, size: tuple[int, int], font_path: str) -> None:
    """Draw subject-specific qualitative relationships, never invented chart values."""
    from PIL import ImageFont
    validate_graphic(graphic)
    w, h = size
    if w <= h:
        raise ValueError('subject graphics currently require landscape format')
    items = graphic['items']
    gap, left, top, bottom = 34, 120, 365, 645
    box_width = (w - 2 * left - gap * (len(items)-1)) // len(items)
    label_font = ImageFont.truetype(font_path, 34)
    detail_font = ImageFont.truetype(font_path, 28)
    for index, item in enumerate(items):
        x = left + index * (box_width+gap)
        selected = graphic.get('emphasis') == index
        outline = '#fbbf24' if selected else '#7dd3fc'
        draw.rounded_rectangle((x, top, x+box_width, bottom), radius=18,
                               fill='#173047' if selected else '#112535', outline=outline, width=4)
        y = top + 24
        for text, font, step, maximum in [(item['label'],label_font,44,2),(item['detail'],detail_font,36,4)]:
            lines = wrap(draw,text,font,box_width-36)
            if len(lines)>maximum:
                raise ValueError('graphic text overflow: shorten label or detail')
            for line in lines:
                draw.text((x+18,y),line,font=font,fill='#f8fafc' if font == label_font else '#bed1e1')
                y += step
            y += 12
        if y > bottom-6:
            raise ValueError('graphic text overflow: combined label/detail too tall')
        if index < len(items)-1 and graphic['kind'] == 'flow':
            mid = (top+bottom)//2
            draw.line((x+box_width+4,mid,x+box_width+gap-6,mid),fill='#7dd3fc',width=4)
            draw.polygon([(x+box_width+gap-6,mid),(x+box_width+gap-15,mid-7),(x+box_width+gap-15,mid+7)],fill='#7dd3fc')
    if graphic['kind'] == 'timeline':
        draw.line((left,top-25,w-left,top-25),fill='#7dd3fc',width=3)
        for index in range(len(items)):
            x=left+index*(box_width+gap)+box_width//2
            draw.ellipse((x-7,top-32,x+7,top-18),fill='#fbbf24')


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


def caption_phrases(text: str, *, font_path: str, width: int, px: int,
                    max_words: int = 10) -> list[str]:
    """Split spoken text into readable clauses; timing comes from actual PCM below."""
    from PIL import Image, ImageDraw, ImageFont
    draw = ImageDraw.Draw(Image.new('RGB', (width, 100)))
    font = ImageFont.truetype(font_path, px)
    # ASS syntax is never accepted as narration markup.
    if any(c in text for c in ('{', '}', '\\')):
        raise ValueError('caption text must be plain speech without ASS control syntax')
    phrases, current = [], []
    for word in text.split():
        candidate = ' '.join(current + [word])
        if current and (len(current) >= max_words or len(wrap(draw, candidate, font, width)) > 2):
            phrases.append(' '.join(current))
            current = []
        current.append(word)
        if len(wrap(draw, ' '.join(current), font, width)) > 2:
            raise ValueError('caption phrase exceeds two lines')
        if re.search(r'[.!?;:,]$', word):
            phrases.append(' '.join(current))
            current = []
    if current:
        phrases.append(' '.join(current))
    return phrases


def synthesize_phrases(voice: Any, phrases: list[str], wav: Path) -> list[dict]:
    """Synthesize each phrase, join PCM, and retain exact sample-based boundaries."""
    import io
    pcm, captions, sample_count, params = [], [], 0, None
    for text in phrases:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as stream:
            voice.synthesize_wav(text, stream)
        with wave.open(io.BytesIO(buf.getvalue()), 'rb') as stream:
            actual = (stream.getnchannels(), stream.getsampwidth(), stream.getframerate())
            if params is not None and params != actual:
                raise ValueError('inconsistent synthesis PCM format')
            params = actual
            frames = stream.getnframes()
            start = sample_count / actual[2]
            pcm.append(stream.readframes(frames))
            sample_count += frames
            captions.append({'start': start, 'end': sample_count / actual[2], 'text': text})
    if not params or not sample_count:
        raise ValueError('empty synthesized audio')
    with wave.open(str(wav), 'wb') as stream:
        stream.setnchannels(params[0]); stream.setsampwidth(params[1]); stream.setframerate(params[2])
        stream.writeframes(b''.join(pcm))
    return captions


def ass_time(seconds: float) -> str:
    ticks = round(seconds * 100)
    return f'{ticks // 360000}:{ticks // 6000 % 60:02}:{ticks // 100 % 60:02}.{ticks % 100:02}'


def write_captions(path: Path, captions: list[dict], size: tuple[int, int], font_path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    px = 48 if w < h else 44
    width = w - (220 if w < h else 300)
    font = ImageFont.truetype(font_path, px)
    draw = ImageDraw.Draw(Image.new('RGB', size))
    y = h - (365 if w < h else 205)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{px},&H00FFFFFF,&H00FFFFFF,&H00121C2A,&H00121C2A,0,0,0,0,100,100,0,0,3,12,0,5,110,110,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for cue in captions:
        if any(c in cue['text'] for c in ('{', '}', '\\', '\n', '\r')):
            raise ValueError('caption text must be plain single-line speech')
        lines = wrap(draw, cue['text'], font, width)
        if len(lines) > 2:
            raise ValueError('caption has more than two lines')
        text = r'\N'.join(lines)
        position = '{' + rf'\an5\pos({w//2},{y})' + '}'
        rows.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Default,,0,0,0,,{position}{text}")
    path.write_text(header + '\n'.join(rows) + '\n')


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
    textblock(scene['title'], 215 if w < h else 185, 56 if scene.get('graphic') else (66 if w < h else 70), '#f8fafc', 350 if scene.get('graphic') else h // 2 - 30)
    # Original schematic, never presented as product evidence or measurements.
    cy = h // 2
    if scene.get('graphic') is not None:
        draw_graphic(d, scene['graphic'], size, font_path)
    else:
        radius = 52 if w < h else 65
        centers = [margin + radius, w//2, w-margin-radius]
        for a, b in zip(centers, centers[1:]):
            d.line((a+radius, cy, b-radius, cy), fill='#4ea8d5', width=6)
        for j, cx in enumerate(centers):
            d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill='#172e42', outline='#7dd3fc', width=4)
            d.text((cx-12, cy-20), str(j+1), font=ImageFont.truetype(font_path, 32), fill='#ffffff')
    textblock(scene['caption'], cy + 140, 44 if w < h else 42, '#d9e5ef', h-(520 if w < h else 280))
    label = 'TECHNICAL TEST • NOT FOR PUBLICATION' if technical_test else 'Original explanatory graphic • AI narration'
    d.text((margin, h-120), label, font=ImageFont.truetype(font_path, 22), fill='#9fb3c8')
    d.rectangle((margin, h-65, margin + int((w-2*margin)*(index+1)/total), h-57), fill='#7dd3fc')
    im.save(path)


def scene_video_filter(duration: float, size: tuple[int, int], ass_name: str) -> str:
    """Small visual entrance and elapsed-time cue; subtitles are never faded/cropped."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('positive finite narration duration required')
    if not re.fullmatch(r'scene-[0-9]+\.ass', ass_name):
        raise ValueError('only generated caption basenames are allowed')
    w, h = size
    left = 100 if w < h else 120
    width = w - 2 * left
    # Discrete one-sixtieth increments avoid version-dependent dynamic drawbox widths.
    # This bar expresses elapsed narration time only, not source measurements.
    filters = [f'fade=t=in:st=0:d={min(.18,duration/4):.6f}',
               f'drawbox=x={left}:y={h-92}:w={width}:h=6:color=0x36506a:t=fill']
    for index in range(60):
        x0 = left + width * index // 60
        x1 = left + width * (index+1) // 60
        filters.append(f"drawbox=x={x0}:y={h-92}:w={x1-x0}:h=6:color=0x7dd3fc:t=fill:enable='gte(t,{duration*(index+1)/60:.6f})'")
    # Subtitles come last, keeping them fully opaque and safely positioned throughout.
    filters.append(f'ass={ass_name}')
    return ','.join(filters)


def probe(path: Path) -> dict:
    return json.loads(run(['ffprobe', '-protocol_whitelist', 'file,pipe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]).stdout)


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


def assemble_segments(concat: Path, final: Path, *, branded: bool) -> None:
    """Uniform generated scene sizes, stable filter state across color metadata changes."""
    encoding = (['-vf','fps=30,setpts=PTS-STARTPTS','-af','asetpts=PTS-STARTPTS',
                 '-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                 '-r','30','-fps_mode','cfr','-c:a','aac','-ar','48000','-ac','2','-b:a','160k']
                if branded else ['-c','copy'])
    run(['ffmpeg','-hide_banner','-loglevel','error','-reinit_filter','0','-f','concat','-safe','1','-i',str(concat),
         *encoding,'-movflags','+faststart',str(final)])


def render(spec: dict, output: Path, model: Path, voice_metadata: dict,
           font_path: str = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', *, local_assets: dict | None = None) -> dict:
    validate_spec(spec)
    if spec.get('licensed_assets') or any('licensed_excerpt' in s for s in spec.get('scenes', [])):
        from .licensed import verify_local_assets
        excerpt_assets = ({k:v for k,v in local_assets.items() if k != 'poweredby_logo'}
                          if spec.get('brand_intro') is not None and local_assets else local_assets)
        verify_local_assets(spec, excerpt_assets)
    intro_config = spec.get('brand_intro')
    if intro_config is not None:
        from .intro import verify_intro
        if not local_assets or 'poweredby_logo' not in local_assets:
            raise ValueError('brand_intro requires local approved poweredby_logo')
        verify_intro(intro_config, Path(local_assets['poweredby_logo']))
    verify_voice(model, voice_metadata)
    # Official native ONNX builds can initialize telemetry during import.
    # Refuse to import Piper/ONNX unless process startup explicitly opted out.
    if os.environ.get("ORT_DISABLE_TELEMETRY") != "1":
        raise ValueError("Start Python with ORT_DISABLE_TELEMETRY=1 before loading Piper/ONNX")
    from piper import PiperVoice
    from PIL import __version__ as pillow_version
    if output.exists():
        raise FileExistsError('choose a new output directory; never overwrite recovery media')
    output.mkdir(parents=True)
    output = output.resolve()
    size = (1080, 1920) if spec['format']=='short' else (1920,1080)
    voice = PiperVoice.load(str(model))
    segments, durations, captions = [], [], []
    elapsed = 0.0
    for i, scene in enumerate(spec['scenes']):
        if 'licensed_excerpt' in scene:
            clip=scene['licensed_excerpt']; duration=clip['end']-clip['start']
            source=Path(local_assets[clip['asset_id']]).resolve()
            source_probe=probe(source)
            if clip['end']>float(source_probe['format']['duration']) or not any(s['codec_type']=='audio' for s in source_probe['streams']):
                raise ValueError('Source cut exceeds media or audio missing')
            cues=clip['captions']; ass=output/f'scene-{i:02}.ass'
            write_captions(ass,cues,size,font_path)
            # Preserve full source frame: never crop a speaker or contextual slide.
            # Text is drawn with Pillow, not interpolated into an FFmpeg expression.
            from PIL import Image, ImageDraw, ImageFont
            bg=Image.new('RGB',size,'#0c1420'); draw=ImageDraw.Draw(bg)
            font=ImageFont.truetype(font_path,42)
            asset=spec['licensed_assets'][clip['asset_id']]
            for text,y in [(scene['title'],180),(asset['attribution'],1250)]:
                lines=wrap(draw,text,font,860)
                if len(lines)>4: raise ValueError('Licensed attribution/title overflow')
                for j,line in enumerate(lines): draw.text((110,y+j*58),line,font=font,fill='#f8fafc')
            draw.text((110,1740),'Licensed archival excerpt • commentary follows',font=ImageFont.truetype(font_path,26),fill='#7dd3fc')
            png=output/f'scene-{i:02}.png'; bg.save(png)
            mp4=output/f'scene-{i:02}.mp4'
            run(['ffmpeg','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe','-ss',str(clip['start']),'-t',str(duration),'-i',str(source),
                 '-loop','1','-i',str(png),'-filter_complex',
                 f'[0:v]scale=1080:700:force_original_aspect_ratio=decrease,setsar=1[v];[1:v][v]overlay=(W-w)/2:520,ass={ass.name}[out]',
                 '-map','[out]','-map','0:a:0','-t',str(duration),'-r','30','-c:v','libx264','-preset','ultrafast','-crf','22',
                 '-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11',
                 '-threads','2',str(mp4)],cwd=output)
        else:
            wav = output / f'scene-{i:02}.wav'
            phrases = caption_phrases(scene['narration'], font_path=font_path,
                                      width=size[0]-(220 if size[0]<size[1] else 300),
                                      px=48 if size[0]<size[1] else 44)
            cues = synthesize_phrases(voice, phrases, wav)
            duration = cues[-1]['end']
            ass = output / f'scene-{i:02}.ass'
            write_captions(ass, cues, size, font_path)
            png = output / f'scene-{i:02}.png'
            card(scene, png, size, i, len(spec['scenes']), technical_test=spec.get('technical_test',False), font_path=font_path)
            mp4 = output / f'scene-{i:02}.mp4'
            run(['ffmpeg','-hide_banner','-loglevel','error','-loop','1','-i',str(png),'-i',str(wav),
                 '-t',str(duration),'-r','30','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',
                 '-vf',scene_video_filter(duration,size,ass.name), '-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-threads','2',str(mp4)], cwd=output)
        segments.append(mp4)
        durations.append(duration)
        for cue in cues:
            captions.append({'start':round(elapsed+cue['start'],3), 'end':round(elapsed+cue['end'],3), 'text':cue['text'], 'scene':i})
        # Muxed scene duration includes codec/frame padding; use it for later scene offsets.
        elapsed += float(probe(mp4)['format']['duration'])
    intro_evidence = None
    if intro_config is not None:
        from PIL import Image
        from .intro import render_intro, offset_captions, TEMPLATE, LOGO_SHA256
        first = output/'first-content-frame.png'
        run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(segments[0]),'-frames:v','1',str(first)])
        bumper = render_intro(intro_config, Path(local_assets['poweredby_logo']),
                              Image.open(first).convert('RGB'), output, font_path)
        intro_duration = float(probe(bumper)['format']['duration'])
        if abs(intro_duration-1.6) > 1/30:
            raise ValueError('intro timing outside reviewed template bounds')
        segments.insert(0, bumper)
        captions = offset_captions(captions, intro_duration)
        intro_evidence = {'template':TEMPLATE,'title':intro_config['title'],
                          'logo_sha256':LOGO_SHA256,'intro_sha256':sha256(bumper),
                          'content_offset_seconds':intro_duration,
                          'origin':'owner-selected logo; original procedural plasma and synchronized sound',
                          'listening_review':'pending exact-final-render review',
                          'source_endorsement':False}
    concat = output / 'segments.txt'
    # Generated safe basenames only; no untrusted strings in concat input.
    concat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    final = output / 'final.mp4'
    assemble_segments(concat, final, branded=bool(intro_evidence))
    qc = assess_probe(probe(final), size, spec['format']=='short')
    scan = run(['ffmpeg','-hide_banner','-i',str(final),'-vf',(f"trim=start={intro_evidence['content_offset_seconds']},blackdetect=d=0.5:pix_th=0.05" if intro_evidence else 'blackdetect=d=0.5:pix_th=0.05'),
                '-af','silencedetect=n=-45dB:d=2,ebur128=peak=true','-f','null','-'])
    qc['branded_black_background_exemption_seconds'] = intro_evidence['content_offset_seconds'] if intro_evidence else 0
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
        'brand_intro':intro_evidence,
        'licensed_assets':spec.get('licensed_assets',{}),
        'voice':voice_metadata,'graphics':{'origin':'original programmatic schematic; licensed source frames where explicitly registered' if spec.get('licensed_assets') else 'original programmatic schematic','font':'DejaVu Sans (Bitstream Vera / DejaVu license)'},
        'captions':'burned-in captions and JSON sidecar; original narration uses synthesized PCM phrase timing; licensed excerpts use reviewed source-relative cues; muxed scene offsets; manual listening/sync review required',
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
    ap.add_argument('--local-assets',type=Path,help='private JSON asset-id to local-path mapping; never committed')
    args=ap.parse_args()
    manifest=render(json.loads(args.spec.read_text()),args.output,args.voice,json.loads(args.voice_metadata.read_text()),local_assets=json.loads(args.local_assets.read_text()) if args.local_assets else None)
    print(json.dumps({'status':manifest['status'],'qc_passed':manifest['qc']['passed'],'publication_eligible':False}))

if __name__=='__main__':
    main()
