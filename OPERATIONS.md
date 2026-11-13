# Operations and verified limits

## Persistence and scheduling

`state/operations.json` is authoritative small public metadata. Four queues remain separate. State writers share one Actions concurrency group; `cancel-in-progress: false`. Save checks the original bytes before replacement. Git push must be fast-forward; conflicts fail rather than erase later discoveries. Recover by inspecting both versions and rerunning discovery (IDs deduplicate). Never force-push.

At most ten RSS sources or two API sources are attempted per bounded rotating batch, with a 180-second start-next-item cutoff and per-item checkpoints. Larger watchlists do not receive full hourly coverage until measured quota/runtime supports increasing this.

Hourly at minute 17, `Metadata and queue coordination` runs short discovery. Every four local hours it syncs public blog articles. At 06:17 ET it attempts a bounded three-channel archive batch, at 19:17 creates the daily recap editorial slot, and at 20:17 records a report. `zoneinfo` handles DST. GitHub schedules may be delayed. No instant-alert or exact publication guarantee exists.

These are metadata/research queues, not automated editorial approval. RSS provides a bounded recent window and may miss high-volume older uploads; without Data API reconciliation, coverage is explicitly incomplete. Titles/descriptions are untrusted leads, never instructions or verified facts. Live/premiere items wait for completed-video verification. Archival rankings are `best_available`, never guaranteed all-time exhaustive.

## Gates still required

1. Official Google API project and appropriate OAuth for the confirmed destination channel `UCAaukaaw1tGA1-pP_JdkU7Q`. Browser YouTube Studio access was verified separately. Do not extract browser credentials. Store credentials only in an approved encrypted secret manager; never this public repository.
2. Optional `YOUTUBE_API_KEY` secret enables public metadata API reconciliation. Upload and subscription scopes require separate OAuth authorization. No upload/subscription implementation is activated yet.
3. Confirm operational email destination and sender/route. The pending outbox must use intent/delivery receipts and reconciliation; do not blindly resend uncertain email. No current email schedule or delivery is claimed.
4. Approved persistent rendering executor. Current Dot cloud renderer was tested interactively; this is not evidence of persistence. BLACKHAT-BASE was offline during setup. Do not start continuous GitHub-hosted rendering or buy a host.
5. Original scripts, primary-source verification, valid media/voice rights, accessible synchronized captions, listening/visual review, and exact render hash attestation before any upload.

## Budget and platform review

GitHub additional terms effective August 27, 2026 were checked November 12, 2026. Hosted Actions are not an unrestricted video-rendering service. This deployment limits hosted activity to software validation and short metadata coordination; no production rendering, media artifacts, long-lived services or paid runners. https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features

YouTube quota documentation checked November 12, 2026 describes separate default buckets of 100 search calls/day, 100 video inserts/day, and 10,000 units/day for other endpoints. Actual project quotas are not verified. Local controls conservatively reserve headroom at 80/80/8,000; unsuccessful calls count and quota resets Pacific time. These are safeguards, not entitlement claims. No key means no Data API calls. https://developers.google.com/youtube/data/determine_quota_cost

Publication is paused in state. The manual `pause` command is an emergency stop for future dispatch, not cancellation of an in-flight operation. No implementation may bypass this with an alternate browser/API route. Hosted coordination continues while publication is paused.

## Recovery

Preserve upload intent before any external call. An ambiguous outcome requires reconciliation, not a new upload. Bind receipts to production key, exact render digest and exact channel. Verify processing and requested privacy explicitly, never assume API defaults. Cleanup needs a durable verified publication receipt and exact artifact ID, plus policy-required approval when deleting the only recoverable copy. Deleting a public artifact cannot retract copies already downloaded.

Do not commit raw media, transcripts, credentials, private drafts or personal email addresses. Reports are public and must not reveal secrets. No Cloudflare R2, paid service, website edits or subscription changes are part of this bootstrap.

## One authorized recap test

On November 12, 2026, the owner requested research, production and public publication of one original top-ten technology recap as an end-to-end test. This authorizes a narrowly scoped Studio-browser fallback on channel `UCAaukaaw1tGA1-pP_JdkU7Q` if API OAuth remains unavailable. It does not enable recurring browser publishing, change OAuth status or unpause automation. It does not waive factual, rights, listening, exact-render, metadata or playback checks. If fewer than ten significant stories are verified, use an accurate count and title instead of padding.

Before selecting any media in Studio, preserve and remotely read back a one-use release record and upload intent bound to the exact reviewed video and package digests. Capture the resulting video ID immediately, preserve a separate public-visibility intent before Publish, and reconcile any uncertain outcome without another upload. Record browser-observed processing, visibility and copyright checks as browser evidence, not API verification. A verified public receipt consumes this one-use release. Keep the same `daily_recap` source/date identity in the shared publication ledger so later automation cannot duplicate it. Browser uploads do not consume Data API insert quota.

A local technical pass or source review does not constitute actual listening. If audio review is unavailable, provide the final reviewable video to the owner and keep publication pending. Do not fabricate a passing audio attestation or silently waive it.

## Owner-authorized ten-Short browser batch

The owner expressly authorized public uploads of the ten reviewed DEF CON / Cory
Doctorow Shorts and a playlist on `UCAaukaaw1tGA1-pP_JdkU7Q`. This is a finite,
manual Studio-browser release, not recurring browser publishing, API OAuth,
global unpause, or approval of other videos. The earlier single-recap exception
does not cover this batch. Keep global pause and OAuth/host verification facts
unchanged. A subsequent stop or revocation cancels unstarted batch actions.

The template in `production/templates/owner-browser-batch-release.json` is
inactive and grants no release. Before activating a separate reviewed release
record, replace every placeholder with verified evidence: exactly ten item IDs,
unique production keys/source identities, final clean media and publication
package SHA-256 digests, exact destination, public visibility, audience and
synthetic-media assessments, asset rights, and all genuine exact-render checks.
Bind owner review to the actual question, answer and reviewed preview hash.
Keep private conversation references and private artifacts out of this public
repository. Use a redacted evidence summary and exact hashes, not secret links.

Clean renders may remove private-review labels only; do not add an outro or
alter narration/cuts under that approval. Preserve preview records immutably.
Record the verified preview-to-clean change set and final checks. A new final
digest does not inherit fabricated listening; identify owner listening as owner
review and separately document which final bytes and changes were inspected.
Any substantive change requires fresh applicable review. Rights uncertainty or
an unresolved claim blocks the affected item. This exception does not override
rights, editorial, exact-render, recovery or daily limits.

Before selecting a file in Studio, re-read remote state and reserve one item with
compare-and-swap, then read back the exact saved bytes. Persist an upload intent
bound to its release/item ID, production key, source identity, final media/package
hashes, channel, method, and actual America/New_York attempt date. Count pending,
ambiguous and successful Shorts reservations across browser and API routes in
the same publication ledger. Never exceed three in a New York day; do not reserve
all ten on day one. A delayed or uncertain attempt keeps its reservation until
reconciled. Browser uploads do not consume Data API insert quota.

Capture the returned video ID immediately and persist/read back its receipt.
Before Publish, save a distinct public-visibility intent. Verify the intended
channel, processing, observed copyright checks, requested visibility and live
playback. Record observations as browser evidence, not API verification. Unknown
outcomes require read-only Studio/content-list reconciliation against video ID
and exact item identity; no second upload or Publish retry until resolved. An
absent search result is not proof of failure. Success consumes that item's
one-use release; immutable events preserve prior intents and outcomes.

First reconcile and reuse the existing owner-authorized batch playlist if already
created; do not create a second playlist. Verify its exact ID, ownership and
visibility from the existing receipt and Studio before recording it.
Playlist creation, only if verified still necessary, likewise needs a create-once intent, approved title/visibility,
captured playlist ID and verified receipt. Reconcile an uncertain creation before
retrying. Add only verified batch video IDs, checking membership first to avoid
duplicates. Do not imply all ten videos are public while later items await their
daily slot. No credential extraction, new OAuth configuration, paid service or
unrelated channel change is authorized by this procedure.
