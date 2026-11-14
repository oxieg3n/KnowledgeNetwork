# Collector V9: Focused integration-blocker recovery after local checkpoint e904f15

Reported 2026-11-14, FORGE Windows VM. This is a recovery directive for the existing Collector, NOT a restart or new project. The exact local handoff and current feature branch have not been uploaded to GitHub, so all details below are reported by the owner and MUST be verified directly on FORGE before implementation.

## Fixed baseline, do not discard

- Working branch: `feature/collector-v7-overnight`; local checkpoint `e904f15`.
- Original owner backup preserved. New backup: `C:\admin\collector-backups\v9-final-20261114-1410`.
- Owner-reported passing checks: **284 tests, 163 worker checks, 17 dashboard checks**.
- Worker was healthy after a restart, real editor jobs and 50-second synthetic render passed.
- Owner's ChatGPT Dot **Assistant** read both FORGE handoffs and correctly returned BLOCKED. No production or local approved-narrator Short was produced. Public publishing remains PAUSED.
- Existing local documents:
  - `C:\Admin\Projects\KnowledgeNetwork\docs\collector\overnight\HANDOFF.md`
  - `C:\Admin\Projects\KnowledgeNetwork\docs\collector\ASSISTANT-OPERATIONS.md`
- Host inspector was staged but **not run** on BLACKHAT-BASE. Do not misreport as verified.
- Installer is unsigned; no review PR; host narration parity/rights, approved bookend assets, VM reboot and end-to-end Dot tests not verified.
- Read `AGENTS.md`, `docs/collector/v9/DIRECT_VOXCPM2_ARCHITECTURE.md`, and `docs/collector/v9/START_HERE_DIRECT_VOXCPM2_CODEX.txt`; protect Gateway and unrelated host services.

## Workstream 1: Fix untrusted_pipe_server, not the trust policy

Assistant's Collector health call reports `untrusted_pipe_server`. Investigate the actual named-pipe/worker client trust handshake, ACLs, server identity, executable/process path, service account, persisted signing/binding data, stale pipe instances, and whether the host/VM tests are referring to the same installed build. Compare the Dot/Assistant execution identity against the CLI identity that passed earlier tests. Determine the **specific cause** before changing it. Fail closed. Do not bypass the check, disable ACL validation, relax to Everyone, skip identity verification, or replace secure IPC with unauthenticated localhost HTTP. Repair the actual mismatch with small changes and add regression tests for trusted client success, spoofed server failure, stale installation, process restart, and Dot identity. Only declare fixed after Assistant itself can safely retrieve real Collector health.

## Workstream 2: Activate canonical narrator safely

The default approved narrator is a successful owner-run script ON BLACKHAT-BASE:

```powershell
& "D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1" `
  -Text "This is the voice of the Knowledge Network." `
  -Output "D:\tools\audio\voices\Oxiegen-Narrator\test.wav"
```

Installed VoxCPM2 Python/CLI root: `D:\tools\audio\voicestudio\data\engines\voxcpm2\${b}; do NOT depend on VoiceStudio app/API/network, and do not reinstall or move its model.

First open local FORGE handoff, locate `BLOCKED_NARRATOR_CONFIG` exact origin and staged host inspector, examine the inspector's contents and scope, identify missing host-only facts and the exact owner-approved one-time command needed to inspect the host, and request only the minimum authorization/action if required. Do NOT execute a staged host inspector automatically through unrelated restricted SSH/Gateway access, or make host networking/service/firewall edits without permission. On BLACKHAT-BASE, inspect canonical script, narrator configuration, voice conditioning/prompt/reference, interpreter, checkpoint/revision, postprocessing, license/consent evidence. Keep original assets intact. Generate a new disposable WAV without overwriting the owner's existing test.wav. Prove it runs without VoiceStudio's app/backend. A host-only test is not Forge remote proof.

Follow V9 architecture: a small fixed-purpose authenticated host service for the canonical narrator, private via a dedicated owner-approved tailnet route, serial GPU jobs, fixed narrator identity, no arbitrary command or file path, verified WAV bytes. Avoid existing Serve :8443 Universal Gateway and old root VoiceStudio route unless owner specifically approves the narrow replacement after checking actual bindings. From FORGE verify a real authenticated request, WAV transfer, decoding/hash/duration and import. No fabricated voice identity or automatic fallback to other TTS.

## Workstream 3: Recover exact approved brand assets

Do not regenerate approximate replacements. Read `docs/brand-intro.md` and `docs/brand-outro.md` and inspect historical private asset manifests, existing collector render output, authorized backups, approved Library deliverables and known media storage locations through existing allowed access. Ask for owner-only local asset copy if unavailable. Copy to FORGE's private, approved media root and record source, SHA-256 and ffprobe metadata. Do not commit binaries.

Approved:
- Intro template `poweredby-plasma-v1` (~1.6s). It is a component that uses the pinned, exact `Neon Cosmic Oxieg3n Emblem.png`, SHA256 `5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54`, and dynamic title.
- Outro template `poweredby-plasma-outro-v1`, exact owner-approved 7.8s 30fps files, with ORIGINAL narration/CTA unchanged.
- Portrait `Powered-By-Outro-Portrait.mp4`, SHA256 `62496803360e377d81ab54b6970d94fcce3eee125f5d22c2fe08377dcf1b5c9b`, 1080x1920.
- Landscape `Powered-By-Outro-Landscape.mp4`, SHA256 `3720a160cd8acb46c828d448cca740252fb8c6a80eba892f1573dc5b56479ee3`, 1920x1080.
- No matching hash: BLOCKED_ASSET, not "approved". Existing asset hash checks remain mandatory.

## Focused workflow and acceptance

1. Preserve/verify current local branch, dirty tree, `e904f15`, backup directories, current service/editor results. Do not rerun all expensive tests unnecessarily.
2. Delegate distinct file ownership to IPC/security, narrator/provider, private asset recovery, and integration/editor QA agents. Start independent investigations concurrently; serialize host changes and actual GPU/editor work.
3. Repair the named-pipe trust issue and validate it using **Assistant's actual client context**, not merely Codex under the developer account.
4. Verify host script/rights; implement and validate narrow transport only after host-specific permission; receive actual original narrator WAV from FORGE.
5. Recover and hash BOTH orientation-specific approved outro assets and original intro badge; do not confuse a synthetic replacement with a production-approved file.
6. When all prerequisites are genuinely available, re-run EXACT requested Assistant E2E exercise: 45–55s LOCAL REVIEW-ONLY editable Short, canonical direct VoxCPM2 narration, measured captions, text, graphics, animated effect, multiple video layers, ducked music, exact plasma intro+outro. Save/reopen, export exact revision, decode/QC. Record real paths, SHA256, duration, asset provenance, failure statuses.
7. Keep PUBLIC PUBLISHING PAUSED. No uploads.
8. Update local `docs/collector/overnight/HANDOFF.md` and `docs/collector/ASSISTANT-OPERATIONS.md` only with verified results and accurate commands. Save a fresh checkpoint/backup after fixes, preserve old snapshots. Report exactly what remains blocked, not simulated successes.

If you cannot directly inspect the two FORGE documents, stop before proposing concrete modifications that depend on their content and give a minimal evidence collection command. Do not claim this GitHub note contains or replaces that private local handoff.
