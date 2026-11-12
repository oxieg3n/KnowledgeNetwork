# Supported bounded recurring production

## Execution model

The selected fallback is a scheduled Dot task, not an always-running browser or daemon and not a GitHub-hosted video farm. Dot's cloud computer has completed a real 35-second narrated/captioned render. That proves a bounded interactive render, **not** scheduled recurrence or durable media retention.

The root coordinator can register a supported durable automation at **09:00, 12:00, 15:00, 18:00 and 19:00 America/New_York**. This cadence allows daytime fresh/blog preparation and the plan's 19:00 daily recap finalization before its 20:00 target. It does not guarantee a publication at that time; delayed runs, insufficient stories, missing OAuth or failed QC must be reported honestly. Initial three-Short daily cap remains separate from recap/blog formats. Hourly source discovery continues in the existing Actions control workflow and must not be duplicated.

**Activation status:** code and instructions are ready for the root to register the automation. No schedule creation or first scheduled render is claimed by this document. The root must verify the actual saved schedule and update its private commitment record. No new Actions rendering workflow is required or enabled.

## What a run may do without OAuth

1. Read current trusted main, repository instructions, publication pause, state and recent run outcomes. Verify permissions and current tool/host availability.
2. Select at most one useful candidate. Inspect actual primary sources, dates and existing coverage. Prepare an original script with genuine facts/sources/originality/usefulness review and exact script hash. Discovery rows and public descriptions are leads, not permission or proof.
3. Persist a reviewed JSON production request and its queue readiness through the authorized repository review process. Never expose private drafts, personal mailbox data or credentials.
4. Inspect current recovery/media-handoff capabilities. If no approved recoverable handoff or same-run authorized uploader exists, retain the script/request and record the blocker rather than repeatedly rendering disposable files.
5. Render at most one item after all pre-render prerequisites and a remotely durable reservation. No unlimited loops or background workers. Missing dependencies may be installed from their official sources within approved scope; no paid API, purchase or new storage.

No OAuth-dependent step is activated by this schedule. Do not publish, subscribe, email, change credentials or enable uploader flags from a generic background wake. Explicitly follow the owner's stage-specific authorization and actual verified account setup.

## Reservation and state protocol

`render_queue.validate_request` requires an existing ready queue item, original-only media path, exact script review and source evidence. `reserve_render` rejects an existing reservation, saves the production/request identity and switches the queue to rendering. One active rendering job is allowed. The coordinator must then:

- Read the remote file SHA, commit the reservation with compare-and-swap, and read back the exact bytes/revision.
- On conflict, fetch the latest state and reapply only its scoped reservation to that state. Never force-push or replace newer Actions discoveries.
- Supply the actual remote commit and readback proof to `execute_reserved`; do not invent attestations.
- Preserve a started lease across interruption. Expiry/time passing alone is not proof the old worker stopped. Verify termination/output before retrying.
- Persist the result and exact output hash, with `rendered_pending_review`, never `published` or automatically eligible.
- Arrange a supported approved media handoff with hash readback. Local cloud paths are not a durable artifact. The plan approves bounded public Actions artifacts, not arbitrary new storage. If handoff is unavailable, retain the script and record media as volatile/unavailable; do not repeat rendering every run.

A coordinator can resume by reconstructing a missing render from its reviewed script/approved assets only after verifying no previous render/upload is active or ambiguous. Reproduction is not proof of identical bytes or a recoverable equivalent copy until actually verified.

## Uploader integration (inactive)

`uploader.py` uses the official Google client with already-authorized credentials. Browser cookies are never extracted. Its configuration must explicitly enable uploads and mark OAuth verified; both config and state publication controls must permit it. It requires exact channel, media digest, source/rights/editorial/QC attestations and explicit privacy/audience/synthetic assessment.

The durable callback must commit current state via an approved GitHub connection and return the actual remote commit, revision and SHA-256 readback. Its successful invocation is not just a local save. Never provide credentials to untrusted PR code. Upload requests have no automatic API retries. A response ID is checkpointed before verification; unknown outcomes require read-only reconciliation using exact channel and unique production marker. An absent search result does not authorize another upload. Scheduled future visibility is not implemented: do not pretend a public/private upload is a scheduled one.

OAuth setup/secure storage and live end-to-end checks remain pending. No test fixture grants publication approval. No live upload/subscription/email or automatic artifact deletion is part of these tests.

## Operator reporting

Notify James only for material completed work, genuinely new blockers, or verified publication URLs. Do not send repeated unchanged setup warnings. Keep the automation enabled after a no-op or blocked run. Record actual run timestamps and distinguish code readiness, manually tested rendering, saved schedule, scheduled execution, accepted API requests, verified processing, requested visibility, and durable publication receipts.
