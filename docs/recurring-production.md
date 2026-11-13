# Supported bounded recurring production

## Execution model

The selected fallback is a scheduled Dot task, not an always-running browser or daemon and not a GitHub-hosted video farm. Dot's cloud computer has completed a real 35-second narrated/captioned render. That proves a bounded interactive render, **not** scheduled recurrence or durable media retention.

The root coordinator can register a supported durable automation at **09:00, 12:00, 15:00, 18:00 and 19:00 America/New_York**. This cadence allows daytime fresh/blog preparation and the plan's 19:00 daily recap finalization before its 20:00 target. It does not guarantee a publication at that time; delayed runs, insufficient stories, missing OAuth or failed QC must be reported honestly. Initial three-Short daily cap remains separate from recap/blog formats. Hourly source discovery continues in the existing Actions control workflow and must not be duplicated.

**Activation status:** the coordinator confirmed the supported preproduction schedule was saved on November 12, 2026 at 09:00, 12:00, 15:00, 18:00 and 19:00 America/New_York, with the first upcoming run at 18:00 that day. This records schedule creation, not proof of scheduled rendering or publishing. Publication pause and all stage-specific gates remain intact. No new Actions rendering workflow is required or enabled.

## What a run may do without OAuth

1. Read current trusted main, repository instructions, publication pause, state and recent run outcomes. Verify permissions and current tool/host availability.
2. Select at most one useful candidate. Inspect actual primary sources, dates and existing coverage. Prepare an original script with genuine facts/sources/originality/usefulness review and exact script hash. Discovery rows and public descriptions are leads, not permission or proof.
3. Persist a reviewed JSON production request and its queue readiness through the authorized repository review process. Never expose private drafts, personal mailbox data or credentials.
4. Inspect current recovery/media-handoff capabilities. If no approved recoverable handoff or same-run authorized uploader exists, retain the script/request and record the blocker rather than repeatedly rendering disposable files.
5. Render at most one item after all pre-render prerequisites and a remotely durable reservation. No unlimited loops or background workers. Missing dependencies may be installed from their official sources within approved scope; no paid API, purchase or new storage.

No OAuth-dependent step is activated by this schedule. Do not publish, subscribe, email, change credentials or enable uploader flags from a generic background wake. Explicitly follow the owner's stage-specific authorization and actual verified account setup.

## Reservation and state protocol

`render_queue.validate_request` requires an existing ready queue item, supported reviewed media path, exact script review and source evidence. `reserve_render` rejects an existing reservation, saves the production/request identity and switches the queue to rendering. One active rendering job is allowed. The coordinator must then:

- Read the remote file SHA, commit the reservation with compare-and-swap, and read back the exact bytes/revision.
- On conflict, fetch the latest state and reapply only its scoped reservation to that state. Never force-push or replace newer Actions discoveries.
- Supply the actual remote commit and exact state-byte SHA-256 readback proof to `execute_reserved`; do not invent attestations. A trusted durable-checkpoint callback must persist/read back its execution-start intent before encoding. An `execution_started` record cannot be re-executed without explicit outcome reconciliation, including after an encoder crash.
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

## Narrow licensed excerpt preparation

The `licensed_cc_by_excerpt` rights path permits one locally supplied CC BY 3.0 or
4.0 excerpt of at most 20 seconds in a Short, with at least two original commentary
scenes and a documented distinct-value rationale. It is not a blanket channel
license or a downloading service. The operator must verify the original license,
commercial adaptation scope, underlying third-party rights, exact source bytes,
visual content, context and accurate timed transcript. Supply source files through
`execute_reserved(..., local_assets={asset_id: Path(...)})`; private local paths
are not part of the public request. The reviewed script's `licensed_assets` map
binds the SHA-256, creator, title, source/license evidence URLs, attribution and
modification notice. Its excerpt scene includes exact start/end and caption times
relative to that cut. See `tests/test_licensed.py` for the data schema (fixtures are
not clearance or usable production requests).

The source frame is fitted rather than cropped, source audio remains source audio,
and attribution is visible. Original scenes use licensed synthetic narration and
remain explicitly labeled. Both segment types use common 48 kHz stereo AAC so
concatenation does not switch audio formats. Final listening, context, caption sync,
visual, rights, synthetic-disclosure and reused-content review are still required.
No render grants publication eligibility. Existing remote reservation/readback,
execution-start intent, recovery, channel/OAuth and publication-pause requirements
remain unchanged. This adapter neither fetches media nor enables an uploader.

## Owner-selected video branding (November 13, 2026)

Future owner-channel productions use `poweredby-plasma-v1` and a subject-specific
display title as described in [brand-intro.md](brand-intro.md). The 1.6-second
bumper counts toward the total runtime. Preserve source attribution and verify
the exact combined render, including listening, before release. This production
default does not modify older renders, receipts, upload permissions or pause state.

## Owner-private review previews

An explicit owner request to make source-based review videos may use
`rights_path=licensed_cc_by_review_preview`, with request `purpose` and script
`review_purpose` both `owner_private_review`. This is not production readiness.
The queue status is `preview_requested`; normal exact-script editorial review,
remote reservation and execution-start checkpoints still apply. Licensing,
commercial adaptation scope, exact source hashes, visual/context inspection and
attribution remain mandatory. No known rights conflict is allowed. Audio inspection
may remain explicitly `pending`; underlying-rights and no-third-party-music flags
retain their actual values and are never invented to obtain a render.

Preview manifests and durable render jobs retain `review_only=true` and
`publication_eligible=false`; completion is `preview_rendered_pending_review`.
The uploader rejects explicit preview packages and retained preview jobs matching
the production key or media hash even if submitted flags are changed. Private
Library delivery to the owner is review, not YouTube upload or public release.
There is no automatic promotion mechanism. A future fully reviewed release must
be handled separately; do not relabel or erase the preview receipt. Publication
pause, daily cap, credentials and all normal production defaults remain unchanged.

## Future-video branding
All newly authored video scripts must include the approved `brand_outro` template before review and digest calculation. See [brand-outro.md](brand-outro.md) for portrait/landscape assets and exact validation. Existing approved requests and renders are immutable; do not retrofit the ten DEF CON previews.
