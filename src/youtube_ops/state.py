"""Small public metadata store. Single writer + optimistic revision checks."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

QUEUES = ('FRESH_UPLOAD', 'DAILY_TECH_RECAP', 'BLOG_VIDEO', 'EVERGREEN_TOP10')

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def key(*parts: str) -> str:
    return hashlib.sha256('\0'.join(parts).encode()).hexdigest()

class State:
    def __init__(self, directory: str | Path):
        self.path = Path(directory) / 'operations.json'
        self.original = self.path.read_bytes() if self.path.exists() else None
        self.data = json.loads(self.original) if self.original else {
            'schema_version': 1, 'revision': 0, 'queues': {q: {} for q in QUEUES},
            'channels': {}, 'publications': {}, 'alerts': {}, 'blog_versions': {},
            'archive_progress': {}, 'rights_ledger': {}, 'runs': [], 'quota': {},
            'control': {'publication_paused': True, 'production_host_verified': False}}
        if self.data['schema_version'] != 1:
            raise ValueError('Unsupported state schema')

    def enqueue(self, queue: str, item_id: str, item: dict) -> bool:
        if queue not in QUEUES:
            raise ValueError('Unknown queue')
        if item_id in self.data['queues'][queue]:
            return False
        self.data['queues'][queue][item_id] = {
            **item, 'id': item_id, 'status': item.get('status', 'needs_editorial_review'),
            'attempts': 0, 'discovered_at': now()}
        return True

    def alert(self, alert_id: str, payload: dict) -> bool:
        if alert_id in self.data['alerts']:
            return False
        self.data['alerts'][alert_id] = {**payload, 'status': 'pending', 'created_at': now()}
        return True

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self.original:
            raise RuntimeError('State changed; reload/reconcile, never overwrite')
        self.data['revision'] += 1
        raw = (json.dumps(self.data, indent=2, sort_keys=True) + '\n').encode()
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, self.path)
        self.original = raw
