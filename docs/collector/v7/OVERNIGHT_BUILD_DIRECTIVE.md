# The Knowledge Network Collector: V7 overnight autonomous build directive

Updated November 13, 2026. Owner timezone: America/New_York. Repository: https://github.com/oxieg3n/KnowledgeNetwork.

## Relationship to V6

This V7 directive OVERRIDES the execution, setup, and handoff procedures of the V6 specification for an unattended Codex CLI run. The technical requirements remain governed by:
- docs/collector/v6/CODEX_THE_KNOWLEDGE_NETWORK_COLLECTOR_V6.md
- docs/collector/v6/COLLECTOR_OPEN_SOURCE_RESEARCH.md
- docs/brand-intro.md and docs/brand-outro.md
- README.md, OPERATIONS.md, SECURITY.md, docs/recurring-production.md, docs/rendering.md, current application source, tests, receipts, policy, and any applicable AGENTS.md instructions.

Read the source files completely; the V7 text is not a replacement for technical specifications. Inspect current repository state and actual VM before making changes. Respect newer verified approvals and existing compatible development. Do not ask the owner to repeat information found in repository files.

## Owner's exact overnight setup and authorization

The owner will start the designated Windows VM, install/sign in to ChatGPT desktop, prepare Git and Codex CLI, and leave Codex CLI running in YOLO/full-access mode while sleeping. **VoiceStudio for Windows will already be installed before this prompt is started.** The installed software is an existing dependency to REUSE, not an application to reinstall. The owner authorizes autonomous, local-machine software development actions required for this project: cloning/pulling the designated repository, branching, adding/editing source and tests, installing supported free development prerequisites, configuring the project-specific Windows service and local development environment, opening local applications, running tests and performance probes, building a signed-if-available or otherwise explicitly unsigned installer, and generating owned/synthetic demonstration videos. Work independently through routine installation prompts, configuration decisions, repair steps, retries, refactoring, testing, and documentation.

Do not interpret YOLO as unlimited product authorization. No payments, new subscriptions, license purchases, irreversible VM/host modifications, credentials exposure, changes to Windows host rather than project VM, firewall exposure to the internet, browser credential extraction, weakening security controls, production-website changes, or bypassing usage rights. Do not accept new paid/license terms on behalf of the owner. If a relevant model download requires user acceptance or consent, use another already licensed/installed option for the offline test, document the exact missing approval and continue independent work.

**Public production publishing remains paused.** Only local synthetic/owned QA output and private preview generation are authorized overnight. Do not upload or publish to YouTube, Facebook or a public site during the unsupervised run, and do not change OAuth or publishing gates to force success. Never reuse unlicensed footage or clone a person's voice without consent. Do not register the VM as a general self-hosted runner for the public repo.

## Work allocation: parallelize independent work, serialize shared resources

Use available helper agents by default, assign each a bounded role, specific files/branch/worktree, acceptance criteria, and final report. A suggested split:
A. Windows supervisor/service/CLI + durable SQLite job states, cancellation and restart recovery.
B. Editor integration: test preferred OpenShot native CLI, timeline, layered editing, project revision conflict and preview parity; only test Shotcut/MLT as a documented fallback.
C. VoiceStudio adapter and legally usable local narration, health/model discovery, file output verification and graceful recovery.
D. Frontend UX and installer: accessible minimal dark dashboard, service status, editor preview, jobs/reviews, installer/uninstaller and diagnostics.
E. QA/security/integration: synthetic fixtures, production locks, exact hash checks, process isolation and acceptance tests.
Root coordinator owns contracts/interfaces, integration, Git coordination, and final verification; do not delegate the only integration decisions or claim helper reports as proven runtime observations.

Use distinct worktrees or nonoverlapping files. Establish a minimal shared API contract and fixture before parallelizing. Avoid simultaneous git mutations, package installations, shared DB migrations, service restarts, OpenShot GUI sessions, VoiceStudio model loads, heavy FFmpeg renders, or Windows installer tests. All VM-native acceptance runs must be serialized. If helper subagents are unavailable, run tasks sequentially with the same partitions.

## Priority work plan: deliver a working morning build

**Stage 0: inventory, safety and checkpoint.** Inspect running VM, OS/build, CPU, RAM, disk, GPU actually exposed, installed Python/.NET/Git/Codex/OpenShot/FFmpeg/VoiceStudio and optional packages. Read git status, branches, history, active worktrees and existing state before writing. Preserve uncommitted work; use a feature branch (e.g. feature/collector-windows-overnight) or reuse an active compatible Collector feature branch. If repository is not cloned, clone the designated public repository. Preserve all production ledgers and published receipts. Create a scoped work plan and run initial test suite.

**Stage 1: connection and durable worker.** Implement local Windows worker service and a restricted CLI with JSON results. Use an ACL-protected named-pipe/local connection to the service, not arbitrary shell or exposed HTTP. Build an idempotent job test (submit, get status, get result, cancel where allowed). Persist job records and exact hashes through service restart, VM reboot if safe, and duplicate submissions. If ChatGPT's computer connection allows real Assistant interaction, prove it; otherwise prepare a copy/paste Assistant instruction and clearly mark scheduled Dot-to-VM connectivity UNVERIFIED. A local Codex CLI test is NOT equivalent to Dot reaching the VM.

**Stage 2: install/integrate editor.** Check compatible installed OpenShot before installing a pinned, official stable version. Validate its native CLI/agent operations on Windows using a full multitrack test: two visual tracks, title/graphic layer, narrated audio and music, timed captions, transition, keyframes/effect, protected intro/outro, export, save/reopen, manual UI edit, then agent edit without losing the manual change. Produce a durable native project and actual render. If OpenShot fails a required feature after a bounded fix, record the evidence and test Shotcut/MLT against the same fixture. Do not settle for a launcher-only 'editor' or an inert control. A focused functional integration takes precedence over appearance polishing.

**Stage 3: integrate PREINSTALLED VoiceStudio.** Discover the actual Windows installed version, process/app location, models, existing profiles and persisted data. Do NOT reinstall, reset, overwrite profiles, reinitialize the database, create a competing backend, or blindly update VoiceStudio. Launch existing desktop app only if needed. Probe local http://127.0.0.1:3900/health, /openapi.json, /v1/audio/voices (or discover configured port). Prefer supported local REST speech endpoint; optional MCP endpoint http://127.0.0.1:3900/mcp/ for agent use; do not guess model or voice IDs. Confirm selected voice model and reference rights permit commercial YouTube content; do not use the noncommercial default OmniVoice weights without separate clearance. Use existing authorized model/profile, if available; otherwise produce an explicitly labelled synthetic test with a legally permitted fallback and leave real VoiceStudio production voice marked blocked. Never auto-download a gated voice model or accept its license without owner approval. Generate real sample WAV, validate decoded output, listen or provide inspectable audio, capture actual duration, and import into editor. Treat voice unavailable, auth error, engine busy, and unsupported feature as distinct statuses.

**Stage 4: branding and production proof.** Use the already approved plasma intro poweredby-plasma-v1 and plasma outro poweredby-plasma-outro-v1, their exact pinned asset digests and orientation-specific approved files; never approximate or overwrite shared brand assets. They are included once each. If actual approved local assets are absent, do not fabricate equivalent approved files: create a clear missing-asset message and render a separate unbranded technical fixture while continuing integration. Full Short must be <=60 seconds including ~1.6-second intro and ~7.8-second outro. Caption offsets and graphics must be correct. VoiceStudio narrates NEW body material only; preserve approved outro voice. Verify full decode, orientation, FPS, actual video/audio durations, transitions, caption placement, audio levels, black/silent spans, project save/reopen, exact final hash, rights and local review status. Never silently convert a preview to approved/public.

**Stage 5: connect existing four operational queues without rewriting them.** Integrate fresh-upload research, daily recap, published blog-to-video (read-only poweredby repo), and evergreen ranking into the local service, with distinct durable queue IDs, priority and time-zone semantics. No duplicate running scheduler during cutover. If full migration or OAuth is not verifiable, keep current production queues untouched and deliver safe adapters and staging tests. Avoid racing existing Dot/GitHub schedulers or changing their production flags.

**Stage 6: package, document and present.** Create reproducible Windows release build and installer in local output; include start-menu shortcut, service setup or clear service installation process, diagnostics, explicit runtime dependencies, log paths, repair/uninstall and upgrade behavior. Run existing and new automated tests, clean-install or upgrade smoke tests where safe, synthetic render tests, UI keyboard/focus checks, and VM reboot/persistence test if safely reversible. Do not report a passing feature without the real fixture/observed output.

## Operating during unattended period

- Continue through available work rather than pausing for optional preferences. Choose maintainable defaults and document decisions.
- Use token-efficient context: inspect targeted files; summarize stable discoveries for helper agents; avoid endlessly re-reading large logs.
- On failure: inspect error/log, make bounded repair, rerun scoped test, then one integrated regression. On recurrent failure isolate component, mark BLOCKED with exact reason, and continue independent tasks.
- Limit active heavy media jobs to ONE. Detect free space and stop safely before filling the VM disk; do not assume hardware GPU passthrough. Preserve the existing Windows VM networking, host access/security settings and unrelated running projects.
- Do not disable antivirus, firewall, UAC, safety checks, publishing safeguards or browser protections just to silence an error.
- Prefer pinned, official upstream sources and verify download hashes/signatures where provided. Do not run unreviewed repository setup scripts or user-generated extensions with privileged permissions.
- When working in a public repository: never commit credentials, raw captured media, private drafts, model weights, owner-only brand assets, machine addresses, paths exposing sensitive usernames, or private emails.
- Checkpoint code and test evidence to the feature branch with clear commits. Do not merge or push changes to main without owner review. Never force push or overwrite state.
- Do not claim scheduled Assistant reachability without a real scheduled Dot job; leave a ready-to-run instruction and status if unavailable.
- Do not promise uninterrupted execution if the VM, Codex run, or network becomes unavailable; make progress recoverable from local project state and Git branch.

## Morning handoff requirements (mandatory)

Write docs/collector/overnight/HANDOFF.md on the feature branch (do not commit machine secrets). Also produce a human-readable summary in Codex's final message containing:
1. Repository URL, feature branch, commits, PR link if actually opened (do not invent).
2. Installer/exe exact verified Windows path, file SHA-256 and how to launch/repair. State if unavailable.
3. Run results: tests passed/failed/skipped with counts and actual file/log locations.
4. Actual Assistant-to-VM and scheduled Dot connectivity status, independently labelled.
5. VoiceStudio installed version, backend health, selected legally usable model/profile (without sensitive data), test audio file and measured sample duration.
6. Editing tests: native project path, approved intro/outro availability, preview/final MP4 paths, duration, orientation, audio/caption/effects evidence and hash.
7. Service restart/recovery and deduplication outcomes.
8. Precise outstanding blockers and manual owner actions, prioritized; no repeated generic setup advice.
9. Current publishing state must remain paused, with proof.
10. The EXACT FINAL COMMAND for Assistant to run a legally safe, end-to-end, owner-review-only Short test using all implemented editor capabilities. Use actual installed CLI/API commands, not invented flags. Include the plain-English Assistant message from ASSISTANT_END_TO_END_TEST.md, updated for discovered runtime paths and commands.

## Acceptance bar for morning readiness

'Ready to review' means: executable installation and launch are verified, worker reports health, at least one real synthetic multitrack project survives save/reopen and agent edit, one locally playable produced video is inspectable, and missing features are clearly labeled. 'Full end-to-end READY' additionally requires verified VoiceStudio licensed narration, exact approved intro+outro, accessible preview, quality tests, durable job, and actual Assistant computer connection on a real run. Never conflate these grades. If a step cannot be finished, deliver honest partial completion with exact follow-up, not a fabricated pass.
