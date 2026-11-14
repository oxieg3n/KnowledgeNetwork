# Collector V9: Direct VoxCPM2 + Oxiegen-Narrator (authoritative)

Owner-approved architecture change: 2026-11-14. This document supersedes V8's VoiceStudio narration requirement only; it does not invalidate V6/V7 functionality, checkpoint protection, branding, editor, security, or publication policy.

## Machine roles and canonical narrator

- FORGE VM: Collector Windows worker, editor, jobs, research, narration client, captions, rendering, and installer.
- BLACKHAT-BASE physical Windows host with RTX 3060: all VoxCPM2 GPU inference and private narrator assets.
- DO NOT use VoiceStudio's desktop UI, REST endpoints, MCP endpoints, networking/sharing setup, backend service, or runtime state for the Collector. It proved unreliable.
- Existing installed **VoxCPM2 Python/CLI** is located at `D:\tools\audio\voicestudio\data\engines\voxcpm2\${b}. This directory name is a historical install location, NOT a requirement to run VoiceStudio.
- The **approved/default narrator** used for all new video *body* speech is the working PowerShell entry point `D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1`. It is the voice-identity reference. Do not replace it with a new text-designed voice or a generic default.

The owner confirmed this working BLACKHAT-BASE command:

```powershell
& "D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1" `
  -Text "This is the voice of the Knowledge Network." `
  -Output "D:\tools\audio\voices\Oxiegen-Narrator\test.wav"
```

Before producing a host worker, inspect the actual script, installed Python/interpreter, model checkpoint and revision, narrator reference audio or voice design configuration, possible reference transcript, deterministic seed, cfg/timesteps, audio filters, output format, and permissions. Keep original script and voice files immutable. For Codex tests, allocate a NEW unique temp output file instead of overwriting test.wav. Never commit narration content, voice samples, checkpoint files, or secrets.

## Direct Python support

Official upstream https://github.com/OpenBMB/VoxCPM documents `from voxcpm import VoxCPM`, `VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)`, `model.generate(...)`, and WAV export via soundfile. Upstream labels code and weights Apache-2.0: https://github.com/OpenBMB/VoxCPM/blob/main/LICENSE and https://huggingface.co/openbmb/VoxCPM2. Retain exact revision and verify supporting weight/component licenses and narrator consent provenance for commercial YouTube production.

**The Python library has NO automatically available remote HTTP endpoint.** Build a small dedicated host-side narration service. First make it call the owner's approved `narrate.ps1` (safe argument passing, never a free-form shell command), which already works. Prefer direct persistent Python model invocation later ONLY after proving it preserves the script's configured narrator voice, text conditioning and output behavior. Do not make up model or voice IDs, blindly reuse upstream sample seed, change the voice prompt, or move the installed environment unnecessarily. Do not require VoiceStudio to be running.

## Secure Forge-to-host service contract

Implement the smallest justified authenticated API, with schema shared by FORGE and host before concurrent agent work. Suggested endpoints, **not existing routes until actually implemented**:
- `GET /health`: process/model worker status only; no local paths or secrets.
- `POST /v1/narrations`: idempotent owned text, fixed `narrator_id=oxiegen-narrator`, bounded request size/length and WAV output.
- `GET /v1/narrations/{id}`: queued/running/completed/failed status.
- `GET /v1/narrations/{id}/audio`: authenticated, bounded, verified WAV streaming.

No arbitrary command, filesystem path, model name, voice reference, URL, or output destination can come from an API caller. Use internally allocated job directories, safe ACLs, predictable cleanup, reliable cancellation and retry behavior, and one GPU job at a time. A persistent Python process should load weights once if possible, but may only replace the canonical script once narrator parity is tested. Limit GPU memory contention with other host workloads. Log status/IDs but redact auth tokens, scripts, raw private paths and narration text.

Authenticate using a limited app-specific credential in addition to tailnet access. Bind the service locally and publish only an **approved private Tailscale Serve route**; protect endpoint with tailnet ACLs and app auth. Credentials stored in Windows protected local stores or an appropriate host-only secret store, never public code/CLI history/logs. Do not start a generic remote shell/server.

## Existing Tailscale Serve (read before touching)

Owner-observed host status:
- default HTTPS root: proxies `127.0.0.1:8085`, which is the **old VoiceStudio** API; it is NOT a direct VoxCPM2 endpoint.
- HTTPS `:8443`: proxies `127.0.0.1:43130`, the **Universal Gateway**.
- Never overwrite Gateway, reset Serve, enable Funnel, or assume a loopback proxy enforces API auth. Keep other routes untouched. Inspect current status read-only. If the owner hasn't authorized the specific host-service/Serve change, produce exact one-time owner-run PowerShell steps and label integration BLOCKED; develop mock and client independently. Do not reuse an unrelated restricted Android SSH/emulation worker as general remote execution.

Forge must confirm real communication from FORGE, never merely host-only loopback. Audio received as HTTP bytes must pass header/format/size/decoded duration/sample-rate and SHA-256 checks before local import. Distinguish simulated tests and real network transfer.

## Resuming without damaging the Collector

Existing work is on local FORGE branch `feature/collector-v7-overnight`, checkpoint `8c0e7f0`; verified backup `C:\admin\collector-backups\20261114-073652` (500 files, zero hash mismatches); local handoff `docs/collector/overnight/HANDOFF.md`. This branch and handoff may not be pushed. Don't reset, reclone, overwrite backups, discard changes, force-push, blindly merge/rebase, or invent completed steps. Fetch origin/main non-destructively, read new V9 docs using git show, and integrate only needed changes in the existing branch/worktree.

Replace or adapt the current `RemoteVoiceStudioProvider` with a minimal `RemoteVoxCPM2Provider`, preserving existing Collector job/media contracts. Remove active VoiceStudio health/auth/model/voice selection dependencies. Keep FORGE's editor, jobs, four production queues, Windows service, installer, Dot interface, UI/UX, Python render/QC and FFmpeg code. Continue Ponytail FULL, UI/UX Pro Max and Taste; specialize helper agents without overlapping files; serialize GPU and heavy media testing.

Approved plasma intro `poweredby-plasma-v1` (~1.6s) and approved exact portrait/landscape outro `poweredby-plasma-outro-v1` (~7.8s) remain unchanged and appear once in new videos. VoxCPM2 replaces ONLY body narration, NEVER the approved outro spoken CTA. Shorts target 45–55 seconds including bookends; precise captions, playback/QC and native editability mandatory. Preserve licensing/consent/right-to-use checks and publishing PAUSED. `oxieg3n/poweredby` stays read-only.

## Acceptance and handoff

1. Verify the owner's script and narrator identity on BLACKHAT-BASE, and prove it works with VoiceStudio GUI/backend stopped.
2. Inspect and test installed VoxCPM2 Python API, without changing narrator behavior.
3. Test secure API auth, injection/file-path denial, error handling, idempotency, concurrency, cancellation/restart, WAV validation.
4. Initiate a REAL request from FORGE over approved network, receive new narrator WAV bytes, record duration/sample rate/hash, integrate an editable multitrack project and render LOCAL review-only Short.
5. If host changes or approvals are blocked, finish independent Collector work, deliver a verified narrow setup instruction, and report "remote narration BLOCKED", not success.
6. Update local handoff with exact commands, inspected narrator configuration (without exposing private assets), installation/revision/license evidence, working Forge API URL in PRIVATE config (not public GitHub), tests, UI/editor/installer status and one tested Assistant end-to-end test invocation.
7. Never upload to public YouTube/blog/social without separate explicit review and authorization.
