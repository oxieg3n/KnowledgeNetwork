"""Offline, exact-audio removal of two known private-review footer labels.

No upload, approval promotion, narration generation or generic video editing.
"""
import hashlib
import json
import subprocess
from pathlib import Path

RECTANGLES = ((90, 1798, 900, 28), (100, 1738, 880, 36))
START = 1.42  # The approved bumper reveals the first content card at this point.

def run(args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,timeout=600).stdout

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stream_hash(path, *, pcm=False):
    args=['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(path),'-map','0:a:0','-vn']
    args += ['-c:a','pcm_s16le','-f','s16le','-'] if pcm else ['-c:a','copy','-f','adts','-']
    return hashlib.sha256(run(args)).hexdigest()

def frames(path):
    data=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
    return [f['best_effort_timestamp_time'] for f in data['frames']]

def finish(preview, output, expected_hash, *, segments, manifest_hash, manifest_path):
    preview=Path(preview);output=Path(output)
    if preview.is_symlink() or not preview.is_file() or digest(preview)!=expected_hash:
        raise ValueError('Exact regular owner-reviewed preview required')
    if output.exists(): raise FileExistsError('Preserve existing artifacts')
    info=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_streams','-of','json',str(preview)]))
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'],video['pix_fmt'])!=(1080,1920,'yuv420p'):
        raise ValueError('Only the reviewed portrait template is supported')
    original_frames=frames(preview)
    def probe_duration(path):
        return json.loads(run(['ffprobe','-v','error','-show_format','-of','json',str(path)]))['format']['duration']
    original_duration=probe_duration(preview)
    if not segments or len(segments)>10 or not manifest_hash or len(manifest_hash)!=64:
        raise ValueError('Bounded exact manifest/segment evidence required')
    manifest_path=Path(manifest_path)
    if manifest_path.is_symlink() or digest(manifest_path)!=manifest_hash: raise ValueError('Manifest hash mismatch')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('sha256')!=expected_hash or manifest.get('review_only') is not True:
        raise ValueError('Exact preview manifest required')
    elapsed=0.0; ranges=[]
    for segment in segments:
        path=Path(segment['path'])
        if path.is_symlink() or digest(path)!=segment['sha256']: raise ValueError('Segment hash mismatch')
        data=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-of','json',str(path)]))
        duration=float(data['format']['duration'])
        if not 0<duration<=60 or segment['kind'] not in ('intro','original','source'): raise ValueError('Segment bounds/type')
        ranges.append((elapsed,elapsed+duration,segment['kind']));elapsed+=duration
    if abs(elapsed-float(original_frames[-1]))>0.15: raise ValueError('Segment timeline mismatch')
    masks=[]
    for start,end,kind in ranges:
        if kind=='intro': start=max(start,START)
        rectangle=RECTANGLES[1 if kind=='source' else 0]
        masks.append((start,end,rectangle))
    filters=','.join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x0c1420:t=fill:enable='gte(t,{start})*lt(t,{end})'" for start,end,(x,y,w,h) in masks)
    output.parent.mkdir(parents=True,exist_ok=True)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    for start,end,kind in ranges:
        if kind=='intro': continue
        label='Original text card • AI narration' if kind=='original' else 'Licensed archival excerpt • commentary follows'
        y,px=(1800,22) if kind=='original' else (1740,26)
        filters+=f",drawtext=fontfile={font}:text='{label}':x=100:y={y}:fontsize={px}:fontcolor=0x9fb3c8:enable='gte(t,{start})*lt(t,{end})'"

    run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(preview),'-map','0:v:0','-map','0:a:0','-vf',filters,'-c:v','libx264','-preset','fast','-crf','0','-threads','2','-pix_fmt','yuv420p','-fps_mode','passthrough','-c:a','copy','-movflags','+faststart',str(output)])
    if output.stat().st_size>256*1024*1024: raise ValueError('Derivative exceeds recovery size limit')
    if probe_duration(output)!=original_duration: raise ValueError('Container duration changed')
    if frames(output)!=original_frames: raise ValueError('Frame timeline changed')
    audio=stream_hash(preview);pcm=stream_hash(preview,pcm=True)
    if stream_hash(output)!=audio or stream_hash(output,pcm=True)!=pcm:
        raise ValueError('Approved audio changed')
    verify_pixels(preview,output,original_frames,masks)
    return {'manifest_sha256':manifest_hash,'outside_footer_pixels_identical':True,'source_preview_sha256':expected_hash,'sha256':digest(output),'duration_seconds':original_duration,'frame_count':len(original_frames),'frame_timestamps_identical':True,'aac_bitstream_sha256':audio,'pcm_sha256':pcm,'audio_identical':True,'change':'Known review-footer rectangles only, after bumper reveal','rectangles':RECTANGLES,'start_seconds':START,'publication_eligible':False,'manual_visual_review':'pending'}


def verify_pixels(before,after,timestamps,masks):
    """Lossless encode must preserve every decoded YUV sample outside footer masks."""
    def decoder(path):
        return subprocess.Popen(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(path),'-map','0:v:0','-f','rawvideo','-pix_fmt','yuv420p','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    a,b=decoder(before),decoder(after);size=1080*1920*3//2
    from threading import Timer
    def stop():
        for process in (a,b):
            if process.poll() is None: process.kill()
    watchdog=Timer(600,stop);watchdog.start()
    def read(stream):
        chunks=[];n=0
        while n<size:
            c=stream.read(size-n)
            if not c: break
            chunks.append(c);n+=len(c)
        return bytearray(b''.join(chunks))
    try:
        for t in timestamps:
            aa,bb=read(a.stdout),read(b.stdout)
            if len(aa)!=size or len(bb)!=size: raise ValueError('Decoded frame missing')
            active=[rect for start,end,rect in masks if start<=float(t)<end]
            if active:
                offset=0
                for width,height,scale in [(1080,1920,1),(540,960,2),(540,960,2)]:
                    for x,y,w,h in active:
                        for row in range(y//scale,(y+h)//scale):
                            lo=offset+row*width+x//scale;hi=lo+w//scale
                            aa[lo:hi]=bytes(hi-lo);bb[lo:hi]=bytes(hi-lo)
                    offset+=width*height
            if aa!=bb: raise ValueError('Pixels outside footer changed')
        if a.stdout.read(1) or b.stdout.read(1): raise ValueError('Additional decoded frames')
        if a.wait(timeout=30)!=0 or b.wait(timeout=30)!=0: raise ValueError('Decoder failed')
    finally:
        watchdog.cancel()
        for p in (a,b):
            if p.poll() is None:p.kill();p.wait(timeout=30)
            p.stdout.close()
