"""Reusable owner-selected plasma bumper. Never authorizes publication."""
from pathlib import Path
import math
import random
import subprocess
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .render import sha256, run, wrap

TEMPLATE = "poweredby-plasma-v1"
DURATION = 1.6
LOGO_SHA256 = "5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54"

def offset_captions(captions, seconds):
    if not math.isfinite(seconds) or abs(seconds-DURATION)>1/30:
        raise ValueError("intro timing outside reviewed template bounds")
    return [dict(c, start=round(c['start']+seconds,3), end=round(c['end']+seconds,3))
            for c in captions]

def verify_intro(config, logo):
    if not isinstance(config, dict) or config.get("template") != TEMPLATE:
        raise ValueError("unknown intro template")
    title = config.get("title", "")
    if not isinstance(title, str) or not title.strip() or len(title) > 100 or any(ord(c)<32 for c in title):
        raise ValueError("intro title must be 1-100 plain printable characters")
    if sha256(logo) != LOGO_SHA256:
        raise ValueError("approved circular badge hash mismatch")
    return title.strip()

def render_intro(config, logo_path, scene, output, font_path):
    """Render exactly 48 frames; final 0.18s reveals actual first content frame."""
    title = verify_intro(config, logo_path)
    W,H = scene.size
    if (W,H) not in ((1080,1920),(1920,1080)):
        raise ValueError("unsupported intro dimensions")
    FPS=30
    cy=720 if W<H else 400
    diameter=620 if W<H else 480
    radius=diameter*296/620
    title_y=1110 if W<H else 720
    title_font=ImageFont.truetype(font_path,52)
    line_height=70
    lines=wrap(ImageDraw.Draw(scene),title,title_font,W*.68)
    if len(lines)>2:
        raise ValueError("intro title exceeds two lines; shorten display title")
    logo=Image.open(logo_path).convert('RGB')
    out=output/'intro-silent.mp4'
    p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(out)],stdin=subprocess.PIPE)
    try:
        rng=random.Random(319)
        # Intentionally irregular: clustered roots, open sectors, varied path weights.
        angles=[.03,.18,.61,.94,1.01,1.63,1.96,2.07,2.53,2.91,3.03,3.72,4.03,4.19,4.66,5.24,5.39,5.92]
        traits=[(rng.uniform(.6,1.6),rng.uniform(-1,1),rng.uniform(.3,1.1),rng.uniform(0,6.28),rng.randint(2,5)) for _ in angles]
        for n in range(48):
         t=n/FPS
         if t>=1.6: im=scene.copy()
         else:
          im=Image.new('RGB',(W,H),'black')
          # 0.1s arrival; readable hold; fast zoom through camera.
          z=max(0,(t-1.13)/.47); scale=(.96+.04*min(t/.16,1))*(1+9*z*z*z)
          size=int(diameter*scale); art=logo.resize((size,size),Image.Resampling.LANCZOS)
          im.paste(art,((W-size)//2,int(cy-size/2)))
          # Continuous, organic plasma: many softly twisting filaments, fine bright
          # cores, diffuse multi-scale bloom, uneven lengths and branching tips.
          from PIL import ImageChops
          colored=Image.new('RGB',(W,H),'black'); cores=Image.new('RGB',(W,H),'black')
          cd=ImageDraw.Draw(colored); hd=ImageDraw.Draw(cores)
          strength=max(0,min(t/.18,1))*(1-min(z*1.5,1))
          for j,rootangle in enumerate(angles):
           width,bow,power,phase,branches=traits[j]
           angle=rootangle+.045*math.sin(t*1.6+phase)
           # The arc is not a radial ray: its endpoint drifts independently of its root.
           aim=angle+bow*.20+.05*math.sin(t*2+phase)
           vx,vy=math.cos(aim),math.sin(aim)
           tx=(W-3-W/2)/vx if vx>0 else (2-W/2)/vx if vx<0 else 1e9
           ty=(H-3-cy)/vy if vy>0 else (2-cy)/vy if vy<0 else 1e9
           distance=min(tx,ty)
           ex=W/2+vx*distance; ey=cy+vy*distance
           vertical=tx<ty
           side=(1 if vx>0 else -1) if vertical else (1 if vy>0 else -1)
           sx=W/2+radius*math.cos(angle); sy=cy+radius*math.sin(angle)
           length=math.hypot(ex-sx,ey-sy)
           # Curved cubic control points: initial outward flare, then buoyant sweep.
           c1x=sx+math.cos(angle)*length*.32-math.sin(angle)*bow*length*.23
           c1y=sy+math.sin(angle)*length*.32+math.cos(angle)*bow*length*.23-65
           c2x=ex-(ex-sx)*.3+math.sin(angle)*bow*length*.25
           c2y=ey-(ey-sy)*.3-math.cos(angle)*bow*length*.25-75*math.sin(t*1.4+phase)
           pts=[]
           for k in range(141):
            u=k/140; v=1-u
            x=v**3*sx+3*v*v*u*c1x+3*v*u*u*c2x+u**3*ex
            y=v**3*sy+3*v*v*u*c1y+3*v*u*u*c2y+u**3*ey
            wobble=(11*math.sin(u*11-t*3+phase)+5*math.sin(u*25+t*4+j))*math.sin(math.pi*u)
            pts.append((x+math.sin(angle)*wobble,y-math.cos(angle)*wobble))
           purple=(.5+.5*math.sin(angle*2+.9))**2
           base=(int(30+145*purple),int(180-120*purple),255)
           activity=power*(.20+.80*(.5+.5*math.sin(t*(1.7+j%3)+phase))**1.4)*strength
           for k in range(140):
            u=k/140; fade=(.85+.15*math.cos(u*math.tau))*activity
            cd.line(pts[k:k+2],fill=tuple(int(v*fade) for v in base),width=max(1,int(width*(5 if u<.8 else 3))))
            hd.line(pts[k:k+2],fill=tuple(int(v*fade) for v in (175+60*purple,210-35*purple,255)),width=1)
           # Smooth branching surface filaments splay vertically at the contact point.
           # The small inward bow keeps the fan visible rather than clipping it away.
           for f in range(-branches//2,branches//2+1):
            if f==0: continue
            span=(30+abs(f)*24)*(0.65+power)*(1+.15*math.sin(t*2+j+f*2))
            branch=[]
            for q in range(65):
             u=q/64
             inward=(11+abs(f)*9)*math.sin(math.pi*u*.93)
             ripple=3.2*math.sin(u*15+t*5+j+f)*math.sin(math.pi*u)
             branch.append((ex-side*(inward+ripple),ey+(1 if f>0 else -1)*span*u) if vertical else (ex+(1 if f>0 else -1)*span*u,ey-side*(inward+ripple)))
            for q in range(64):
             u=q/64; fade=(1-u)**.65*activity*.72
             cd.line(branch[q:q+2],fill=tuple(int(v*fade) for v in base),width=3)
             hd.line(branch[q:q+2],fill=tuple(int(v*fade) for v in (175+60*purple,210-35*purple,255)),width=1)
           # Diffuse attachment points at the logo and the imagined glass boundary.
           for x,y,r in [(sx,sy,6),(ex,ey,9)]:
            cd.ellipse((x-r,y-r,x+r,y+r),fill=tuple(int(v*activity*.65) for v in base))
          bloom=ImageChops.add(colored.filter(ImageFilter.GaussianBlur(14)),colored.filter(ImageFilter.GaussianBlur(4)))
          im=ImageChops.add(im,bloom)
          im=ImageChops.add(im,colored.filter(ImageFilter.GaussianBlur(1.2)))
          im=ImageChops.add(im,cores)
          if z<.25:
           shade=ImageDraw.Draw(im)
           shade.rounded_rectangle((W*.14,title_y-18,W*.86,title_y+len(lines)*line_height+15),radius=20,fill='black')
           for index,line in enumerate(lines):
            box=shade.textbbox((0,0),line,font=title_font)
            shade.text(((W-(box[2]-box[0]))/2,title_y+index*line_height),line,font=title_font,fill='#f5f8ff')
          if t>1.42: im=Image.blend(im,scene,min(1,(t-1.42)/.18))
         if n in [12,25,38,45]: im.save(output/f'intro-frame-{n}.jpg')
         p.stdin.write(im.tobytes())
        p.stdin.close()
        if p.wait()!=0:
            raise RuntimeError("intro encoding failed")
    except BaseException:
        if p.stdin and not p.stdin.closed:
            p.stdin.close()
        if p.poll() is None:
            p.terminate()
        p.wait(timeout=10)
        raise
    sound(output)
    target=output/'intro.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(out),'-i',str(output/'intro.wav'),
         '-t','1.6','-c:v','copy','-c:a','aac','-ar','48000','-ac','2','-b:a','160k',str(target)])
    return target

def sound(output):
    import numpy as np
    import wave
    sr=48000; t=np.arange(sr*4)/sr
    rng=np.random.default_rng(114); audio=np.zeros((len(t),2))
    z=np.maximum(0,(t-1.13)/.47)
    strength=np.clip(t/.18,0,1)*(1-np.minimum(z*1.5,1));strength[t>=1.6]=0
    angles=[.03,.18,.61,.94,1.01,1.63,1.96,2.07,2.53,2.91,3.03,3.72,4.03,4.19,4.66,5.24,5.39,5.92]
    r=random.Random(319)
    traits=[(r.uniform(.6,1.6),r.uniform(-1,1),r.uniform(.3,1.1),r.uniform(0,6.28),r.randint(2,5)) for _ in angles]
    energy=np.zeros_like(t); events=[]
    for j,(angle,(_,_,power,phase,_)) in enumerate(zip(angles,traits)):
     activity=power*(.20+.80*(.5+.5*np.sin(t*(1.7+j%3)+phase))**1.4)*strength
     energy+=activity
     # Local maxima of visible filament strength trigger tiny crackle clusters.
     peaks=np.where((activity[1:-1]>activity[:-2])&(activity[1:-1]>=activity[2:])&(activity[1:-1]>.25))[0]+1
     pan=.5+.35*math.cos(angle); gain=np.array([math.sqrt(1-pan),math.sqrt(pan)])
     for idx in peaks:
      when=idx/sr
      if when>1.42: continue
      events.append({'time_seconds':round(when,4),'filament':j,'type':'crackle','visual_strength':round(float(activity[idx]),3)})
      for delay,amp in [(0,1),(.013,.42),(.031,.2)]:
       n=1800;start=idx+int(delay*sr);u=np.arange(n)/sr
       noise=rng.normal(0,1,n);noise=np.convolve(noise,[.25,.5,.25],mode='same')
       env=(1-np.exp(-u/.0007))*np.exp(-u/.009)
       pulse=noise*env*.12*activity[idx]*amp
       audio[start:start+n]+=pulse[:,None]*gain
    energy/=len(angles)
    # Quiet continuous electrical bed; smoothed noise avoids a harsh white-noise blast.
    noise=rng.normal(0,1,len(t));noise=np.convolve(noise,np.ones(7)/7,mode='same')
    bed=(noise*.075 + .017*np.sin(2*np.pi*120*t)+.008*np.sin(2*np.pi*240*t))*(.25+energy)*strength
    for c in range(2):audio[:,c]+=bed
    # Accelerating zoom gets a short rising discharge, ending with the visual reveal.
    u=np.clip((t-1.13)/.47,0,1); env=np.sin(np.pi*u)**1.6;env[(t<1.13)|(t>=1.6)]=0
    sw=rng.normal(0,1,len(t)); sw=np.convolve(sw,np.ones(9)/9,mode='same')
    surge=(.075*sw+.009*np.sin(2*np.pi*(180*t+220*(t-1.13)**2)))*env
    for c in range(2):audio[:,c]+=surge
    # Conservative fixed peak ceiling; final AAC true peak is measured separately.
    peak=np.max(np.abs(audio));audio*=min(1,.28/peak)
    with wave.open(str(output/'intro.wav'),'wb') as f:
     f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((audio[:int(sr*DURATION)]*32767).astype('<i2').tobytes())
    (output/'intro-sound-provenance.json').write_text(json.dumps({'origin':'Original procedural synthesis; no third-party samples','sample_rate':sr,'events':events,'visual_timing':{'zoom_start':1.13,'reveal_end':1.6},'review':'Technical checks only; owner listening review pending'},indent=2))
