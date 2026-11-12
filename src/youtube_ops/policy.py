"""Fail closed on missing rights, editorial evidence, and publication prerequisites."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REQUIRED_CHECKS = ('facts', 'rights', 'originality', 'audio', 'captions', 'visuals', 'metadata')

def local_date(instant: datetime) -> str:
    if instant.tzinfo is None:
        raise ValueError('Timezone required')
    return instant.astimezone(ZoneInfo('America/New_York')).date().isoformat()

def publication_blockers(item: dict, control: dict) -> list[str]:
    result = []
    if control.get('publication_paused', True): result.append('publication_paused')
    if not control.get('production_host_verified'): result.append('approved_host_missing')
    if item.get('rights_path') not in ('original', 'licensed'): result.append('rights_not_cleared')
    assets = item.get('assets', [])
    if not assets: result.append('asset_provenance_missing')
    for asset in assets:
        if not all(asset.get(x) for x in ('sha256', 'rights_holder', 'license', 'evidence')):
            result.append('incomplete_asset_rights')
        if asset.get('third_party') and not all(asset.get(x) for x in ('download_permitted', 'edit_permitted', 'youtube_permitted', 'commercial_permitted')):
            result.append('asset_scope_missing')
        if asset.get('expires_at') and datetime.fromisoformat(asset['expires_at']) <= datetime.now(timezone.utc):
            result.append('asset_rights_expired')
    if not item.get('primary_sources'): result.append('primary_sources_missing')
    digest = item.get('render_sha256')
    if not digest or item.get('reviewed_render_sha256') != digest: result.append('exact_render_review_missing')
    for check in REQUIRED_CHECKS:
        evidence = item.get('checks', {}).get(check, {})
        if evidence.get('status') != 'pass' or not evidence.get('evidence'):
            result.append('check_' + check)
    if not item.get('distinct_value'): result.append('distinct_value_missing')
    if item.get('visibility') not in ('private', 'unlisted', 'public'): result.append('visibility_missing')
    if not isinstance(item.get('made_for_kids'), bool): result.append('audience_missing')
    return sorted(set(result))

def next_ready(state: dict, instant: datetime) -> dict | None:
    """Deadline-aware selection. No fabricated readiness and no interrupted render."""
    queues = state['queues']
    if any(x.get('status') == 'rendering' for q in queues.values() for x in q.values()):
        return None
    ready = [(q, x) for q, items in queues.items() for x in items.values() if x.get('status') == 'ready']
    def rank(pair):
        q, x = pair
        due = datetime.fromisoformat(x['deadline']) if x.get('deadline') else None
        priority = 0 if x.get('verified_breaking') else 1 if q == 'DAILY_TECH_RECAP' and due and (due-instant).total_seconds() < 7200 else {'FRESH_UPLOAD':2,'BLOG_VIDEO':3,'DAILY_TECH_RECAP':4,'EVERGREEN_TOP10':5}[q]
        return priority, -(x.get('editorial_score', 0)), x.get('discovered_at', '')
    return min(ready, key=rank)[1] if ready else None
