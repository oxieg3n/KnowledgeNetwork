"""Narrow, offline CC BY excerpt validation. No retrieval, upload or approval bypass."""
import math
import re
from pathlib import Path
from .render import sha256

LICENSES = {'CC-BY-3.0': 'https://creativecommons.org/licenses/by/3.0/',
            'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/'}

def validate_licensed(spec, *, review_only=False):
    if review_only and spec.get("review_purpose") != "owner_private_review":
        raise ValueError("Explicit owner-private preview purpose required")
    if not review_only and spec.get("review_purpose"):
        raise ValueError("Preview spec cannot be treated as production")
    assets = spec.get('licensed_assets', {})
    clips = [s for s in spec.get('scenes', []) if 'licensed_excerpt' in s]
    if spec.get('format') != 'short' or len(clips) != 1 or len(spec['scenes']) < 3:
        raise ValueError('One excerpt and at least two original commentary scenes required')
    if 'licensed_excerpt' in spec['scenes'][0] or 'licensed_excerpt' in spec['scenes'][-1]:
        raise ValueError('Original introduction and subsequent commentary required')
    if len(assets) != 1: raise ValueError('Exactly one reviewed source asset required')
    for asset_id, a in assets.items():
        if not re.fullmatch(r'[a-z0-9-]{1,64}', asset_id): raise ValueError('Invalid asset ID')
        if not re.fullmatch(r'[a-f0-9]{64}', a.get('sha256','')): raise ValueError('Exact source hash required')
        if LICENSES.get(a.get('license')) != a.get('license_url'): raise ValueError('Unsupported license')
        for k in ('source_url','license_evidence_url'):
            if not a.get(k,'').startswith('https://'): raise ValueError('Public provenance URL required')
        for k in ('title','creator','attribution','modifications','rights_review_evidence'):
            if not isinstance(a.get(k),str) or not a[k].strip(): raise ValueError('Missing provenance: '+k)
        required = ('commercial_adaptation_verified','excerpt_visual_reviewed','no_endorsement') if review_only else ('commercial_adaptation_verified','underlying_rights_reviewed','excerpt_visual_reviewed','no_third_party_music','no_endorsement')
        if review_only:
            if a.get('known_rights_conflict') is not False or a.get('audio_review_status') not in ('pending','pass'):
                raise ValueError('Preview requires explicit conflict assessment and audio-review status')
            if any(type(a.get(k)) is not bool for k in ('underlying_rights_reviewed','no_third_party_music')):
                raise ValueError('Preview must retain actual incomplete rights flags')
        for k in required:
            if a.get(k) is not True: raise ValueError('Missing rights review: '+k)
    s=clips[0]; c=s['licensed_excerpt']
    if c.get('asset_id') not in assets: raise ValueError('Unknown licensed asset')
    for k in ('start','end'):
        if type(c.get(k)) not in (int,float) or not math.isfinite(c[k]): raise ValueError('Finite cut required')
    duration=c['end']-c['start']
    if c['start']<0 or not 0<duration<=20: raise ValueError('Excerpt must be positive and at most twenty seconds')
    cues=c.get('captions',[]); end=0
    if not cues: raise ValueError('Reviewed source captions required')
    for cue in cues:
        a,b=cue.get('start'),cue.get('end')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (a,b)) or not end<=a<b<=duration:
            raise ValueError('Caption timing out of range')
        if not isinstance(cue.get('text'),str) or not cue['text'].strip() or any(x in cue['text'] for x in ('{','}','\\','\n','\r')):
            raise ValueError('Plain reviewed captions required')
        end=b
    if ' '.join(c['text'] for c in cues) != s['narration']: raise ValueError('Captions must match reviewed transcript')
    if c.get('context_reviewed') is not True or not c.get('context_evidence'): raise ValueError('Source context review required')
    if not spec.get('original_commentary_rationale'): raise ValueError('Meaningful original analysis required')
    review=spec.get('original_commentary_review',{})
    if review.get('status')!='pass' or not review.get('evidence'):
        raise ValueError('Substantive original commentary review required; scene counts are not a rights safe harbor')

def verify_local_assets(spec, local_assets):
    validate_licensed(spec, review_only=spec.get('review_purpose')=='owner_private_review')
    if set(local_assets or {}) != set(spec['licensed_assets']): raise ValueError('Exact local asset mapping required')
    for key,path in local_assets.items():
        path=Path(path)
        if not path.is_file() or sha256(path)!=spec['licensed_assets'][key]['sha256']:
            raise ValueError('Local licensed source does not match reviewed bytes')
