"""Bounded Dot-cloud rendering with durable leases; never publishes a video.

The coordinator must commit/push and read back the reservation through its
approved GitHub connection. This module does not extract browser credentials or
assume its local filesystem is persistent. Completed media needs approved durable
handoff before the coordinator ends; do not mark publication-ready here.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .state import State, now
from .recovery import validate_durable_checkpoint

_EDITORIAL = ('facts','sources','originality','usefulness')

def request_digest(request: dict) -> str:
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_request(request: dict, state: State) -> None:
    if request.get('schema_version')!=1: raise ValueError('Unsupported production request')
    queue=request.get('queue');item_id=request.get('item_id')
    if queue not in state.data['queues'] or item_id not in state.data['queues'][queue]:
        raise ValueError('Existing durable queue item required')
    if not re.fullmatch(r'[a-f0-9]{64}',request.get('production_key','')):
        raise ValueError('Stable SHA-256 production key required')
    if request.get('rights_path') not in ('original','licensed_cc_by_excerpt','licensed_cc_by_review_preview'):
        raise ValueError('Unsupported rights path')
    preview=request['rights_path']=='licensed_cc_by_review_preview'
    if preview and (request.get('purpose')!='owner_private_review' or request.get('script',{}).get('review_purpose')!='owner_private_review'):
        raise ValueError('Explicit private review purpose required')
    if not preview and (request.get('purpose') or request.get('script',{}).get('review_purpose')):
        raise ValueError('Preview requests cannot be promoted by changing rights path')
    if request['rights_path'] in ('licensed_cc_by_excerpt','licensed_cc_by_review_preview'):
        from .licensed import validate_licensed
        validate_licensed(request['script'],review_only=preview)
    elif request.get('script',{}).get('licensed_assets') or any('licensed_excerpt' in s for s in request.get('script',{}).get('scenes',[])):
        raise ValueError('Licensed footage cannot use original rights path')
    if request.get('script',{}).get('technical_test',False):
        raise ValueError('Technical tests must not enter production queues')
    if not request.get('primary_sources') or not request.get('distinct_value'):
        raise ValueError('Primary evidence and distinct editorial value required')
    for check in _EDITORIAL:
        review=request.get('editorial',{}).get(check,{})
        if review.get('status')!='pass' or not review.get('evidence'):
            raise ValueError('Editorial check missing: '+check)
    if request.get('script',{}).get('sources')!=request['primary_sources']:
        raise ValueError('Render sources must match reviewed evidence')
    # Bind review to the exact script, not a mutable path or an old draft.
    digest=hashlib.sha256(json.dumps(request['script'],sort_keys=True).encode()).hexdigest()
    if request.get('reviewed_script_sha256')!=digest:
        raise ValueError('Exact script review missing')
    if state.data['queues'][queue][item_id].get('status') not in (('preview_requested','rendering') if preview else ('ready','rendering')):
        raise ValueError('Queue item not editorially ready')
    from .render import validate_spec
    validate_spec(request['script'])

def reserve_render(state: State, request: dict, *, executor: str) -> dict:
    validate_request(request,state)
    if executor!='dot-cloud-bounded': raise ValueError('Unsupported/unverified executor')
    jobs=state.data.setdefault('render_jobs',{})
    key=request['production_key']
    if key in jobs: raise RuntimeError('Existing render needs reconciliation; do not start another')
    if any(j['status'] in ('rendering','execution_started') for j in jobs.values()):
        raise RuntimeError('A render is already reserved; reconcile before starting')
    record={'production_key':key,'request_sha256':request_digest(request),
            'queue':request['queue'],'item_id':request['item_id'],'executor':executor,
            'status':'rendering','started_at':now(),'media_handoff':'pending',
            'review_only':request.get('purpose')=='owner_private_review'}
    jobs[key]=record
    state.data['queues'][request['queue']][request['item_id']]['status']='rendering'
    state.save()
    return {'revision':state.data['revision'],'request_sha256':record['request_sha256']}

def execute_reserved(state: State, request: dict, *, output: Path, voice: Path,
                     voice_metadata: dict, commit_sha: str, readback_revision: int,
                     expected_request_sha256: str, readback_sha256: str, durable_checkpoint, renderer=None, local_assets=None) -> dict:
    """One bounded render after a real remote reservation readback.

    commit_sha/readback_revision are supplied by the trusted coordinator after
    actual GitHub reads, not invented by the renderer. No network calls here.
    """
    key=request['production_key'];record=state.data.get('render_jobs',{}).get(key)
    if not record or record['status']!='rendering':raise RuntimeError('No active reservation')
    validate_request(request,state)
    if record['request_sha256']!=request_digest(request) or expected_request_sha256!=record['request_sha256']:
        raise ValueError('Request changed after reservation')
    validate_durable_checkpoint(state,state.data['revision'],commit_sha,readback_revision)
    if readback_sha256!=hashlib.sha256(state.original).hexdigest():
        raise ValueError('Exact remote state bytes do not match')
    if not callable(durable_checkpoint):raise ValueError('Durable execution checkpoint callback required')
    # A failed/aborted encode cannot reuse a reserved invocation. Persist an
    # execution-start intent before running it, then require outcome reconciliation.
    record.update(status='execution_started',execution_started_at=now())
    state.save()
    def persist_remote():
        proof=durable_checkpoint(state)
        validate_durable_checkpoint(state,state.data['revision'],proof.get('commit_sha',''),proof.get('readback_revision',-1))
        if proof.get('readback_sha256')!=hashlib.sha256(state.original).hexdigest():
            raise ValueError('Execution checkpoint bytes do not match')
    persist_remote()
    if renderer is None:
        from .render import render
        renderer=render
    if request['rights_path'] in ('licensed_cc_by_excerpt','licensed_cc_by_review_preview'):
        result=renderer(request['script'],output,voice,voice_metadata,local_assets=local_assets)
    else:
        result=renderer(request['script'],output,voice,voice_metadata)
    digest=result.get('sha256')
    if not re.fullmatch(r'[a-f0-9]{64}',digest or '') or result.get('publication_eligible') is not False:
        raise ValueError('Invalid or improperly approved render result')
    status='preview_rendered_pending_review' if record.get('review_only') else 'rendered_pending_review'
    if record.get('review_only') and result.get('review_only') is not True:
        raise ValueError('Preview renderer failed to retain review-only provenance')
    record.update(status=status,render_sha256=digest,
                  completed_at=now(),media_handoff='pending',publication_eligible=False)
    state.data['queues'][request['queue']][request['item_id']]['status']=status
    state.save()
    persist_remote()
    return result

def record_handoff(state: State, production_key: str, *, public_reference: str,
                   verified_sha256: str, rights_cleared: bool) -> None:
    """Record a supported handoff; private paths/tokens must not be put here."""
    record=state.data['render_jobs'][production_key]
    if record['status']!='rendered_pending_review' or record['render_sha256']!=verified_sha256:
        raise ValueError('Exact completed render required')
    if not rights_cleared or not re.fullmatch(r'https://github\.com/oxieg3n/KnowledgeNetwork/actions/runs/[0-9]+/artifacts/[0-9]+',public_reference):
        raise ValueError('Approved public recovery reference required')
    record.update(media_handoff='verified',media_reference=public_reference)
    state.save()
