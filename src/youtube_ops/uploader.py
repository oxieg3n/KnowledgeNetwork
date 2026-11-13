"""Inactive-by-default official YouTube resumable-upload adapter.

This module supplies mechanisms, not publication authorization. A trusted caller
must provide reviewed exact-render metadata, verified OAuth, an explicitly enabled
configuration, and a durable callback that commits state remotely and reads the
exact bytes back. Browser cookies are never accepted or extracted. No CLI, token
store or scheduled publishing is enabled here. Never expose resumable session URLs
in public state/logs: they can carry upload authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from typing import Callable

from .policy import publication_blockers
from .recovery import (upload_intent, upload_ambiguous, reconcile_upload,
                       validate_durable_checkpoint)
from .state import State, now

CHANNEL = re.compile(r'UC[A-Za-z0-9_-]{22}\Z')
VIDEO = re.compile(r'[A-Za-z0-9_-]{11}\Z')
MAX_BYTES = 512 * 1024 * 1024


class UploadBlocked(RuntimeError):
    """A redacted, safe-to-report failure; no retry permission is implied."""


def official_client(credentials):
    """Use already-authorized credentials from approved secret storage only.

    OAuth onboarding/refresh-token storage is deliberately outside this adapter.
    The 30-second HTTP timeout bounds each API/chunk request. Imports remain lazy
    so core tests and read-only metadata workflows need no OAuth packages.
    """
    import httplib2
    import google_auth_httplib2
    from googleapiclient.discovery import build
    http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
    return build('youtube', 'v3', http=http, cache_discovery=False)


def official_media(stream):
    from googleapiclient.http import MediaIoBaseUpload
    return MediaIoBaseUpload(stream, mimetype='video/mp4', chunksize=8*1024*1024,
                             resumable=True)


def production_marker(production_key: str, digest: str) -> str:
    return 'kn-' + hashlib.sha256((production_key + '\0' + digest).encode()).hexdigest()


def reviewed_package_digest(item: dict) -> str:
    """Canonical review identity for the entire publication package.

    Reviewers must record this digest AFTER final metadata/rights/editorial review.
    Computing it alone grants no approval. All fields (including checks, source
    evidence, render, channel, cadence identity and API metadata) are bound except
    the digest itself. Any edit requires a fresh genuine review and attestation.
    """
    package = {k: v for k, v in item.items() if k != 'reviewed_package_sha256'}
    try:
        encoded = json.dumps(package, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        raise UploadBlocked('Publication package is not canonical JSON') from None
    return hashlib.sha256(encoded).hexdigest()


class Uploader:
    def __init__(self, client, config: dict, durable_checkpoint: Callable[[State], dict],
                 *, media_factory=official_media, monotonic=time.monotonic,
                 utcnow=lambda: datetime.now(timezone.utc)):
        self.client = client
        self.config = config
        self.checkpoint = durable_checkpoint
        self.media_factory = media_factory
        self.clock = monotonic
        self.utcnow = utcnow
        channel = config.get('destination_channel_id', '')
        if not CHANNEL.fullmatch(channel):
            raise ValueError('Exact immutable destination channel is required')
        self.channel_id = channel

    def _durable(self, state: State):
        """Callback must attest to exact remote bytes, not just a revision number."""
        proof = self.checkpoint(state)
        validate_durable_checkpoint(state, state.data['revision'],
                                    proof.get('commit_sha', ''),
                                    proof.get('readback_revision', -1))
        expected = hashlib.sha256(state.original).hexdigest()
        if proof.get('readback_sha256') != expected:
            raise UploadBlocked('Remote checkpoint bytes do not match')

    def _account(self):
        try:
            data = self.client.channels().list(part='id,contentDetails', mine=True,
                                               maxResults=50).execute(num_retries=0)
        except Exception:
            raise UploadBlocked('Unable to verify authorized destination channel') from None
        ids = [x.get('id') for x in data.get('items', [])]
        # Multiple or truncated account identities are not safe to guess from.
        if ids != [self.channel_id] or data.get('nextPageToken'):
            raise UploadBlocked('Authorized account is not the exact intended channel')
        return data['items'][0]

    def _validate(self, state: State, item: dict):
        # Inspect durable provenance, not just caller-supplied flags. A separate
        # future reviewed-release mechanism is outside this private-preview path.
        preview_jobs = [j for j in state.data.get('render_jobs',{}).values() if j.get('review_only')]
        if item.get('review_only') or item.get('purpose')=='owner_private_review' or item.get('review_purpose')=='owner_private_review' or any(
            j.get('production_key')==item.get('production_key') or
            (j.get('render_sha256') and j.get('render_sha256')==item.get('render_sha256')) for j in preview_jobs):
            raise UploadBlocked('Owner-review preview has no production release')
        if self.config.get('upload_enabled') is not True or self.config.get('oauth_verified') is not True:
            raise UploadBlocked('Uploader/OAuth not explicitly enabled and verified')
        if self.config.get('publication_paused', True):
            raise UploadBlocked('Publication is paused in configuration')
        if item.get('technical_test') or item.get('publication_eligible') is not True:
            raise UploadBlocked('Technical tests/unqualified renders cannot be uploaded')
        blockers = publication_blockers(item, state.data['control'])
        if blockers:
            raise UploadBlocked('Publication gates failed: ' + ', '.join(blockers))
        if item.get('destination_channel_id') != self.channel_id:
            raise UploadBlocked('Reviewed package has a different destination')
        if not isinstance(item.get('contains_synthetic_media'), bool):
            raise UploadBlocked('Explicit synthetic-media assessment required')
        if not isinstance(item.get('production_key'), str) or not item['production_key']:
            raise UploadBlocked('Production key required')
        title, description = item.get('title'), item.get('description')
        if not isinstance(title, str) or not title.strip() or len(title) > 100:
            raise UploadBlocked('Title is missing or exceeds YouTube limits')
        if not isinstance(description, str) or len(description.encode('utf-8')) > 5000:
            raise UploadBlocked('Description is missing or exceeds YouTube limits')
        if any(c in title for c in '<>\x00\r\n') or '\x00' in description:
            raise UploadBlocked('Unsupported metadata characters')
        if item.get('reviewed_package_sha256') != reviewed_package_digest(item):
            raise UploadBlocked('Exact publication package review missing or changed')
        if item.get('publish_at'):
            raise UploadBlocked('Scheduled publication is not implemented by this adapter')

    def _budget_days(self):
        instant = self.utcnow()
        if instant.tzinfo is None:
            raise UploadBlocked('Timezone-aware budget clock required')
        return (instant.astimezone(ZoneInfo('America/New_York')).date().isoformat(),
                instant.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat())

    def _check_limits(self, state: State, item: dict) -> tuple[str, str]:
        """Conservative reservations count unknown/in-flight attempts, not successes.

        publication_format is short, daily_recap or blog_video. source_identity
        identifies the reviewed story/article version, not a fresh random job ID.
        Legacy unclassified reservations require explicit review before new sends.
        """
        fmt = item.get('publication_format')
        source = item.get('source_identity')
        if fmt not in ('short', 'daily_recap', 'blog_video'):
            raise UploadBlocked('Explicit supported publication format required')
        if not isinstance(source, str) or not source.strip() or len(source)>1024 or any(ord(c)<32 for c in source):
            raise UploadBlocked('Stable reviewed source identity required')
        ny_day, pt_day = self._budget_days()
        reservations = [r for r in state.data['publications'].values()
                        if r.get('channel_id') == self.channel_id]
        if any(not all(r.get(f) for f in ('publication_format','source_identity','attempt_ny_date','insert_quota_pt_date'))
               for r in reservations):
            raise UploadBlocked('Legacy publication reservations need cadence reconciliation')
        if any(r['publication_format']==fmt and r['source_identity']==source for r in reservations):
            raise UploadBlocked('Source identity already has a reserved output in this format')
        if fmt == 'short' and sum(r['publication_format']=='short' and r['attempt_ny_date']==ny_day
                                  for r in reservations) >= 3:
            raise UploadBlocked('Three Shorts already reserved for this New York day')
        if fmt == 'daily_recap':
            try:
                recap_day = date.fromisoformat(item.get('recap_date', ''))
            except (ValueError, TypeError):
                raise UploadBlocked('Explicit valid recap date required') from None
            if recap_day.isoformat()!=item['recap_date'] or recap_day>date.fromisoformat(ny_day):
                raise UploadBlocked('Recap date is invalid or in the future')
            if any(r['publication_format']=='daily_recap' and r.get('recap_date')==item['recap_date']
                   for r in reservations):
                raise UploadBlocked('This New York recap date already has a reserved upload')
        limit = self.config.get('upload_daily_limit', 80)
        if type(limit) is not int or not 1 <= limit <= 80:
            raise UploadBlocked('Upload budget must be between one and eighty inserts per Pacific day')
        consumed = state.data['quota'].get(pt_day, {}).get('upload', 0)
        if type(consumed) is not int or consumed<0:
            raise UploadBlocked('Corrupt upload quota ledger')
        if consumed >= limit:
            raise UploadBlocked('Conservative Pacific-day insert quota exhausted')
        return ny_day, pt_day

    def upload(self, state: State, item: dict, video_path: Path, *,
               max_chunks: int = 128, max_seconds: int = 900) -> dict:
        """One attempt only. A rerun always reconciles instead of inserting again."""
        self._validate(state, item)
        reviewed_digest = item['reviewed_package_sha256']
        if not 1 <= max_chunks <= 128 or not 1 <= max_seconds <= 1800:
            raise ValueError('Bounded chunk/time limits required')
        production_key, digest = item['production_key'], item['render_sha256']
        self._check_limits(state, item)
        if production_key in state.data['publications']:
            raise UploadBlocked('Existing intent requires read-only reconciliation')
        path = Path(video_path)
        if path.suffix.lower() != '.mp4' or path.is_symlink() or not path.is_file():
            raise UploadBlocked('Regular MP4 file required')
        if not 0 < path.stat().st_size <= MAX_BYTES:
            raise UploadBlocked('MP4 size exceeds local limit')
        # Snapshot into a private spool so the hashed bytes cannot be swapped by
        # editing the input pathname while the resumable request is underway.
        with tempfile.SpooledTemporaryFile(max_size=8*1024*1024, mode='w+b') as stream:
            h = hashlib.sha256()
            size = 0
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024*1024), b''):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise UploadBlocked('MP4 grew beyond local limit')
                    stream.write(chunk); h.update(chunk)
            if h.hexdigest() != digest:
                raise UploadBlocked('Actual MP4 does not match reviewed render digest')
            stream.seek(0)
            self._account()
            marker = production_marker(production_key, digest)
            body = {'snippet': {'title': item['title'], 'description': item['description'],
                                'tags': [marker], 'categoryId': str(item.get('category_id', '28'))},
                    'status': {'privacyStatus': item['visibility'],
                               'selfDeclaredMadeForKids': item['made_for_kids'],
                               'containsSyntheticMedia': item['contains_synthetic_media']}}
            ny_day, pt_day = self._check_limits(state, item)
            quota = state.data['quota'].setdefault(pt_day, {'general':0, 'search':0, 'upload':0})
            quota['upload'] = quota.get('upload', 0) + 1
            upload_intent(state, production_key, self.channel_id, digest, item['visibility'],
                          artifact_id=item.get('artifact_id'))
            record = state.data['publications'][production_key]
            record.update(marker=marker, publication_format=item['publication_format'],
                          source_identity=item['source_identity'], attempt_ny_date=ny_day,
                          insert_quota_pt_date=pt_day)
            if item['publication_format']=='daily_recap': record['recap_date']=item['recap_date']
            record['reviewed_package_sha256'] = reviewed_digest
            record['metadata_sha256'] = hashlib.sha256(
                __import__('json').dumps(body, sort_keys=True).encode()).hexdigest()
            state.save()
            self._durable(state)  # Must precede videos.insert or any next_chunk.
            self._validate(state, item)  # Honor a stop observed during remote checkpoint.
            if item['reviewed_package_sha256'] != reviewed_digest:
                raise UploadBlocked('Publication package changed during upload preparation')
            if self._budget_days() != (ny_day, pt_day):
                raise UploadBlocked('Date boundary crossed after reservation; reconcile before sending')
            response = None
            started = self.clock()
            try:
                request = self.client.videos().insert(part='snippet,status', body=body,
                            media_body=self.media_factory(stream), notifySubscribers=False)
                for _ in range(max_chunks):
                    if self.clock()-started >= max_seconds:
                        raise TimeoutError('Bounded upload deadline')
                    _, response = request.next_chunk(num_retries=0)
                    if response is not None:
                        break
                if not isinstance(response, dict) or not VIDEO.fullmatch(response.get('id', '')):
                    raise RuntimeError('Upload response not confirmed')
            except Exception:
                upload_ambiguous(state, production_key)
                self._durable(state)
                raise UploadBlocked('Upload outcome uncertain; reconcile before any retry') from None
            # Preserve receipt before any further remote call. If this checkpoint
            # fails, the earlier durable marker still makes reconciliation possible.
            record.update(video_id=response['id'], status='verification_pending',
                          response_received_at=now())
            state.save()
            self._durable(state)
        return self.reconcile(state, production_key)

    def reconcile(self, state: State, production_key: str, *, max_pages: int = 3) -> dict:
        """Read-only platform checks; an empty search never permits another upload."""
        if not 1 <= max_pages <= 3:
            raise ValueError('Bounded reconciliation required')
        record = state.data['publications'][production_key]
        if record['channel_id'] != self.channel_id:
            raise UploadBlocked('Stored intent belongs to another channel')
        channel = self._account()
        marker = production_marker(production_key, record['render_sha256'])
        if record.get('marker') != marker:
            raise UploadBlocked('Stored production marker mismatch')
        ids = [record['video_id']] if record.get('video_id') else []
        try:
            if not ids:
                uploads = channel.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
                if not uploads:
                    raise UploadBlocked('Authorized uploads playlist unavailable')
                token = None
                for _ in range(max_pages):
                    params = {'part':'contentDetails', 'playlistId':uploads, 'maxResults':50}
                    if token: params['pageToken'] = token
                    page = self.client.playlistItems().list(**params).execute(num_retries=0)
                    ids.extend(x['contentDetails']['videoId'] for x in page.get('items', []))
                    token = page.get('nextPageToken')
                    if not token: break
            matches = []
            for offset in range(0, len(ids), 50):
                data = self.client.videos().list(part='snippet,status,processingDetails',
                          id=','.join(ids[offset:offset+50])).execute(num_retries=0)
                for video in data.get('items', []):
                    snippet = video.get('snippet', {})
                    if snippet.get('channelId') == self.channel_id and marker in snippet.get('tags', []):
                        matches.append(video)
        except Exception:
            raise UploadBlocked('Platform verification unavailable; intent remains reserved') from None
        if len(matches) != 1:
            raise UploadBlocked('No unique exact production match; do not retry upload')
        video = matches[0]
        result = reconcile_upload(state, production_key, channel_id=self.channel_id,
                    render_sha256=record['render_sha256'], video_id=video['id'],
                    processing_status=video.get('processingDetails', {}).get('processingStatus', 'unknown'),
                    actual_visibility=video.get('status', {}).get('privacyStatus', 'unknown'),
                    evidence='Authenticated videos.list matched channel and unique production marker',
                    exact_match_verified=True)
        self._durable(state)
        return result['record']
