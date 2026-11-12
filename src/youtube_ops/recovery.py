"""Fail-closed recovery protocol; no network or deletion operations.

Callers MUST commit/push and read back each returned checkpoint before performing
an external side effect. ``State.save`` alone is not durable on an Actions runner.
Persist the in-flight intent before sending; after a crash it is deliberately
ambiguous, even if the process may have stopped before the request went out.
Reconciliation evidence must come from an authenticated platform read, not from a
successful local request or an assumed timeout. This module validates attestations;
it does not obtain evidence, grant publishing permission, or perform API calls.
"""
from __future__ import annotations

import re
from copy import deepcopy
from .state import State, now

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_COMMIT = re.compile(r"[a-f0-9]{40}\Z")
_VIDEO = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_CHANNEL = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")


def _sha(value: str) -> None:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError('Expected SHA-256 digest')


def _identity(record: dict, channel_id: str, production_key: str, digest: str):
    if (record['channel_id'], record['production_key'], record['render_sha256']) != (channel_id, production_key, digest):
        raise ValueError('Channel, production key or render digest mismatch')


def _persist(state: State, record: dict) -> dict:
    record['updated_at'] = now()
    state.save()
    return {'revision': state.data['revision'], 'record': deepcopy(record)}


def upload_intent(state: State, production_key: str, channel_id: str,
                  render_sha256: str, visibility: str, *, artifact_id: int | None = None) -> dict:
    """Reserve exactly one send attempt; an existing intent cannot be retried.

    After save, commit/push/read back this state revision, then send only in that
    original invocation. All reruns must reconcile first, including a crash before
    any bytes were sent. This is an idempotency reservation, not publishing approval.
    """
    _sha(render_sha256)
    if not production_key or not _CHANNEL.fullmatch(channel_id):
        raise ValueError('Production key and immutable channel ID required')
    if visibility not in ('private', 'unlisted', 'public'):
        raise ValueError('Explicit visibility required')
    if artifact_id is not None and (type(artifact_id) is not int or artifact_id <= 0):
        raise ValueError('Exact numeric artifact ID required')
    publications = state.data['publications']
    if production_key in publications:
        _identity(publications[production_key], channel_id, production_key, render_sha256)
        raise RuntimeError('Existing intent requires reconciliation; do not resend')
    record = {'production_key': production_key, 'channel_id': channel_id,
              'render_sha256': render_sha256, 'requested_visibility': visibility,
              'artifact_id': artifact_id, 'status': 'in_flight', 'attempt': 1,
              'created_at': now(), 'cleanup': 'not_eligible'}
    publications[production_key] = record
    return _persist(state, record)


def validate_durable_checkpoint(state: State, revision: int, commit_sha: str,
                                readback_revision: int) -> None:
    """Validate the caller's successful remote commit/readback attestation.

    No external write is authorized by this check alone. Callers supply a commit
    only after verifying remote contents, not merely after making a local commit.
    """
    if not _COMMIT.fullmatch(commit_sha or '') or revision != readback_revision or revision != state.data['revision']:
        raise ValueError('Confirmed remote checkpoint does not match current state')
    if not state.path.exists() or state.path.read_bytes() != state.original:
        raise ValueError('Local checkpoint changed')


def upload_ambiguous(state: State, production_key: str) -> dict:
    record = state.data['publications'][production_key]
    if record['status'] == 'verified':
        raise RuntimeError('Verified publication must not return to ambiguous')
    record['status'] = 'reconciliation_required'
    return _persist(state, record)


def reconcile_upload(state: State, production_key: str, *, channel_id: str,
                     render_sha256: str, video_id: str, processing_status: str,
                     actual_visibility: str, evidence: str,
                     exact_match_verified: bool) -> dict:
    """Record authenticated platform evidence, retaining unprocessed uploads.

    ``exact_match_verified`` means the upload belongs to this production identity,
    not just a title match. Confirm using an upload receipt/resumable response plus
    owner/channel metadata or a trusted unique production marker. Read processing
    and visibility from videos.list. Evidence must not contain credentials.
    """
    record = state.data['publications'][production_key]
    _identity(record, channel_id, production_key, render_sha256)
    if not _VIDEO.fullmatch(video_id or '') or not evidence or not exact_match_verified:
        raise ValueError('Exact platform reconciliation evidence required')
    if record.get('video_id') and record['video_id'] != video_id:
        raise ValueError('Video ID changed; manual reconciliation required')
    if actual_visibility not in ('private', 'unlisted', 'public'):
        raise ValueError('Observed visibility required')
    if record['status'] == 'verified' and (processing_status != 'succeeded' or actual_visibility != record['requested_visibility']):
        raise RuntimeError('Verified receipt changed; record a separate platform-change review')
    record.update(video_id=video_id, url=f'https://www.youtube.com/watch?v={video_id}',
                  processing_status=processing_status, actual_visibility=actual_visibility,
                  verification_evidence=evidence, verified_at=now())
    record['status'] = ('verified' if processing_status == 'succeeded' and
                        actual_visibility == record['requested_visibility'] else 'verification_pending')
    return _persist(state, record)


def confirm_not_created(state: State, production_key: str, *, evidence: str,
                        definitive_no_creation: bool) -> dict:
    """Only a definitive non-creation result permits a new attempt.

    An empty recent-upload search, network timeout or absent response is NOT
    definitive. Prefer an API rejection known to occur before creation. Unknown
    cases stay blocked for human reconciliation rather than risk duplication.
    """
    record = state.data['publications'][production_key]
    if record.get('video_id') or record['status'] == 'verified':
        raise RuntimeError('Existing remote video cannot be retried')
    if not definitive_no_creation or not evidence:
        raise ValueError('Definitive non-creation evidence required')
    record.update(status='retry_allowed', non_creation_evidence=evidence)
    return _persist(state, record)


def retry_upload_intent(state: State, production_key: str) -> dict:
    record = state.data['publications'][production_key]
    if record['status'] != 'retry_allowed':
        raise RuntimeError('Retry has not been reconciled')
    record['status'] = 'in_flight'
    record['attempt'] += 1
    return _persist(state, record)


def cleanup_intent(state: State, production_key: str, *, artifact_id: int,
                   publication_commit: str, publication_readback_verified: bool,
                   equivalent_copy: dict) -> dict:
    """Reserve deletion only after receipt is remotely durable and recoverable.

    A second retained, verified equivalent copy is required because this module
    does not obtain per-action approval for irreversible deletion. A YouTube URL
    alone is not proof that the original MP4 can be recovered. Do not store private
    download URLs or credentials in the public equivalent-copy reference.
    """
    record = state.data['publications'][production_key]
    if type(artifact_id) is not int or artifact_id != record.get('artifact_id'):
        raise ValueError('Artifact ID does not match publication')
    if record['status'] != 'verified' or not publication_readback_verified or not _COMMIT.fullmatch(publication_commit or ''):
        raise RuntimeError('Verified durable publication receipt required')
    if (equivalent_copy.get('sha256') != record['render_sha256'] or
            equivalent_copy.get('verified') is not True or
            not equivalent_copy.get('reference')):
        raise RuntimeError('Recoverable equivalent copy has not been verified')
    if record['cleanup'] not in ('not_eligible', 'failed'):
        raise RuntimeError('Cleanup is already pending/completed; reconcile first')
    record.update(cleanup='in_flight', publication_commit=publication_commit,
                  equivalent_copy=deepcopy(equivalent_copy))
    return _persist(state, record)


def reconcile_cleanup(state: State, production_key: str, *, artifact_id: int,
                      http_status: int, exact_artifact_absent_verified: bool = False) -> dict:
    record = state.data['publications'][production_key]
    if type(artifact_id) is not int or artifact_id != record.get('artifact_id'):
        raise ValueError('Artifact ID mismatch')
    if record['cleanup'] not in ('in_flight', 'failed'):
        raise RuntimeError('No recorded cleanup intent')
    if http_status == 204 or (http_status == 404 and exact_artifact_absent_verified):
        record['cleanup'] = 'deleted'
    else:
        record['cleanup'] = 'failed'
    return _persist(state, record)


def email_intent(state: State, alert_id: str, *, destination_sha256: str,
                 message_sha256: str) -> dict:
    """Reserve one email without persisting a private address in public state."""
    _sha(destination_sha256); _sha(message_sha256)
    record = state.data['alerts'][alert_id]
    if record['status'] != 'pending':
        raise RuntimeError('Email already attempted; reconcile before any resend')
    record.update(status='in_flight', destination_sha256=destination_sha256,
                  message_sha256=message_sha256, attempted_at=now())
    return _persist(state, record)


def reconcile_email(state: State, alert_id: str, *, destination_sha256: str,
                    message_sha256: str, provider_message_id: str,
                    outcome: str, evidence: str) -> dict:
    """Accepted is not delivered. Unknown sends remain blocked, never auto-retried."""
    record = state.data['alerts'][alert_id]
    if (destination_sha256, message_sha256) != (record.get('destination_sha256'), record.get('message_sha256')):
        raise ValueError('Email destination/content mismatch')
    if record['status'] not in ('in_flight', 'unknown', 'accepted'):
        raise RuntimeError('No reconcilable email attempt')
    if outcome not in ('unknown', 'accepted', 'delivered', 'bounced') or not evidence:
        raise ValueError('Supported observed outcome/evidence required')
    if record['status'] == 'accepted' and outcome == 'unknown':
        raise RuntimeError('Do not downgrade a confirmed accepted message to unknown')
    if outcome != 'unknown' and not provider_message_id:
        raise ValueError('Provider message ID required')
    if record.get('provider_message_id') and record['provider_message_id'] != provider_message_id:
        raise ValueError('Email provider identity changed')
    record.update(status=outcome, provider_message_id=provider_message_id,
                  evidence=evidence)
    return _persist(state, record)
