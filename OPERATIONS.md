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
