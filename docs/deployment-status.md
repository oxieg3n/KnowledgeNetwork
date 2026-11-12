# Deployment verification — November 12, 2026

This is a partial operational bootstrap, not a claim of autonomous publishing.

## PASS with evidence

- Existing **public** `oxieg3n/KnowledgeNetwork` retained; no website repository modifications.
- PR #2 merged as `2b4762b71319f9641bc658e737fb73b30582ccd2` after exact-head software validation: https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43315554846
- 35 unit/reconciliation/recovery tests passed. Tests cover conflict rejection, durable intents, ambiguous-send blocking, exact destination/render identity, cleanup protection, timezone/DST, RSS identity, API reconciliation and per-attempt quota.
- First hosted metadata checkpoint: https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43315644697 ; durable state commit `01244a8` independently read back.
- Separate trusted dispatches also persisted state: monitor https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43315945986 at `ef4129815e9527cd0ee31a5e3f9804665d44d3cd`, then archive https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43316065348 at `209941e`. Monitor found zero duplicates/new leads; archive recorded the missing-key blocker. Successful Actions status is not a successful archive ranking.
- Four durable work queues initialized. Initial live public blog check queued **29** published article versions. **66** official RSS video leads preserved without duplicate additions on hosted recheck. These are research leads, not fact-checked/publishable scripts.
- 150 watchlist entries imported, representing 121 unique names. **10 distinct channels** verified through official-site links, canonical YouTube identities and matching uploads-playlist ownership. Remaining sources pending.
- Initial local technical render: 34.319 seconds, 1080×1920, H.264/AAC/30fps. This synthetic test is explicitly NOT FOR PUBLICATION; see rendering.md for measured hash and limitations.
- Confirmed target channel: https://www.youtube.com/@PoweredByOxieg3n (`UCAaukaaw1tGA1-pP_JdkU7Q`). Interactive Studio access verified separately; not equivalent to API OAuth.

## BLOCKED / PENDING, not inferred success

- Official YouTube upload/subscription OAuth not configured. No subscriptions or uploads performed.
- `YOUTUBE_API_KEY` missing: RSS monitoring works, but full uploads-playlist API reconciliation and top-ten archival rankings have not run. Feed coverage is bounded and can be incomplete.
- No verified operational email route/destination. Pending alert outbox only; no email sent or claimed delivered.
- Persistent production execution not yet verified. Interactive Dot cloud rendering works; hosted Actions are not used as a continuous video service. No paid compute/storage or R2 enabled.
- Human-quality editorial/audio/caption review and primary-source-backed scripts remain required. No synthetic narration is presented as an owner's or creator's real voice.
- Cleanup integration and exact YouTube processing/visibility receipts remain untested on a real publication. Unit simulations are not real upload proof.

Publication stays paused. The remaining daily recap/blog adaptation/source Short workflows are editorial work queues, not automatic source-summary republication. No article quota or content should be filled with unverified filler.

## Caption follow-up

A second local technical render measured 34.986 seconds with 19 burned-in phrase captions timed from actual synthesized PCM. Four mobile-scale frames inspected with no clipping or overlap; 38 total tests pass locally. This remains NOT FOR PUBLICATION until listening/prosody and editorial review. Exact hash: `ead66581c634caac022bc9167072a208c913858afa17e105b27fa89796113d8c`.

## API and production integration follow-up

The owner subsequently configured a restricted metadata API key. It was tested functionally without displaying the credential:

- https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43317989328 : `api_enabled=true`, two channels API-reconciled and four new leads. Rotating-batch coverage remains partial.
- https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43318113760 : archival ranking PASS, 30 `best_available` candidates saved. Durable state `c90d199` read back.

The earlier missing-API-key blocker is resolved. **OAuth upload/subscription authorization is still separate and unverified.** The official upload adapter remains disabled pending OAuth, exact reviewed package/render checks and a trusted durable checkpoint integration. Bounded render reservations and recurrence instructions are implemented, but schedule creation and actual scheduled rendering must be verified separately by the root coordinator. No publication, email or subscription is claimed.
