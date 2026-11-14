# Collector V8: Forge production worker + BLACKHAT-BASE VoiceStudio API

Owner architecture update: November 14, 2026. Source repository: https://github.com/oxieg3n/KnowledgeNetwork.

## Authority and scope

This V8 document supersedes **only the placement, connectivity, and acceptance expectations for VoiceStudio** in `AGENTS.md`, `docs/collector/v7/*`, and V6 master handoff. All other product requirements, Ponytail FULL mode, Taste/UI/UX Pro Max requirements, existing work, rights checks, approval requirements, production pause, exact render verification, and branch boundaries remain intact.

**FORGE** is the Windows VM where Codex builds and runs **The Knowledge Network Collector** and where Assistant (Dot) interacts with the worker. **BLACKHAT-BASE** is the separate Windows physical host containing the **already installed VoiceStudio Windows app and GPU**. The host VoiceStudio installation is the only production speech endpoint. Do **not** install, migrate or duplicate VoiceStudio on Forge as a prerequisite. Do not remote-control the host desktop, keyboard, mouse, clipboard or logged-in interactive session for narration tasks.

## Desired runtime flow

```
Assistant Dot
  -> Collector worker/API on FORGE
  -> editor project and speech job stored durably on FORGE
  -> authenticated, private, encrypted request to BLACKHAT-BASE VoiceStudio
  -> selected legally usable voice/model synthesizes WAV on host GPU if supported
  -> audio response streamed/downloaded to FORGE media spool
  -> validate exact audio bytes/hash, sample rate, duration, and provenance
  -> editable timeline + captions + mix + graphics + approved plasma intro/outro
  -> local render + QC + review; public publishing remains paused
```

The body narration uses VoiceStudio. The preapproved plasma outro keeps its original approved audio. Audio transfer should happen via a normal HTTP response, not host file paths or mouse-driven Save dialogs. Handle large audio as streamed bytes/files, never inline model context. Keep host model files and voice profiles on BLACKHAT-BASE; host paths are not Forge paths.

## Remote VoiceStudio capabilities to use, with sources

Current upstream documentation:
- https://github.com/debpalash/VoiceStudio/blob/main/docs/sharing.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/api-auth.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/mcp.md
- https://github.com/debpalash/VoiceStudio/blob/main/skills/voicestudio/SKILL.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/production-private-api.md

VoiceStudio's installed Windows app normally serves its local backend on `127.0.0.1:3900` on **BLACKHAT-BASE**, not Forge. Probe on the host or through approved private routing: `GET /health`, `GET /openapi.json`, `GET /v1/audio/voices`, `POST /v1/audio/speech`. Discover real installed model/voice/profile IDs through the live instance; do not invent names or confuse the compatibility aliases `tts-1`/`alloy` with actual provider voices. `/mcp/` is optional; ordinary REST suffices for the Collector's bounded TTS function.

Do not confuse VoiceStudio's separately marketed **remote compute/worker** product features with ordinary documented remote calls to its existing speech REST API. The requested architecture uses a standard consumer request to the host's installed VoiceStudio backend. Do not purchase a Pro feature or build an extra remote GPU controller.

## Choose exactly one secure connectivity route after checking the actual VM and host

**Preferred when already possible:** use VoiceStudio's built-in **Settings > Sharing & Remote Access > Tailscale** on BLACKHAT-BASE, routing through the existing private tailnet. This proxies the host's local service while preserving the loaded model. Verify FORGE is actually joined to and can access the same tailnet; a VM does not automatically inherit the host's Tailscale identity. Ensure VoiceStudio's Tailscale Serve handler does not conflict with existing Gateway/Tailscale Serve; preserve all existing handlers. Never run `tailscale serve reset`, use Funnel, enable a publicly reachable share, or casually reconfigure the owner's host networking. Tailnet access control must limit callers to FORGE. Use the URL displayed by the app; do not assume `https`, port, or host name. The underlying tailnet can encrypt HTTP transport using WireGuard. Prefer a route-aware, authenticated proxy limited to required consumption paths if feasible and necessary; avoid making broad admin capabilities available to the Collector. Do not put a VoiceStudio root key into Forge if a narrower protected route will work.

**Alternative when the VM and host have an actually verified isolated/trusted Hyper-V connection:** VoiceStudio **Settings > Sharing & Remote Access > Network/Local network** can expose a PIN-protected API on the host's selected reachable address and share port. Find the actual address in VoiceStudio; do not infer it from host name or presume the VM's `localhost` refers to the host. Test reachability from FORGE. Supply `X-OmniVoice-Pin` in a request header (not URL), with the PIN in a local protected secret. It rotates each time sharing restarts and is **not durable**; report that limitation. VoiceStudio's LAN sharing is plain HTTP, so use it only over a trusted isolated link, with a narrowly scoped host firewall rule and no router port forwarding. Prefer the encrypted Tailscale approach for unattended durability. Do not weaken firewall protections simply to get a green check.

**If neither path works safely:** keep the local Collector and other pipelines working, save the speech request as `blocked_remote_voice`, and give the owner one minimal host-side, one-time setup instruction. Do not install a second VoiceStudio on Forge and do not switch to an unapproved narrator. Do not attempt host GUI takeover as a workaround.

Host VoiceStudio may need to remain running as an installed desktop app after owner sign-in. That does **not** require controlling the host screen for each narration task. Only claim reliable sign-out/reboot recurrence after testing the real host session lifecycle; do not create competing host backends or run privileged services without a reviewed design.

## Forge service design and API security

Provide a single pluggable `RemoteVoiceStudioProvider` replacing the V7 assumption of `LocalVoiceStudioProvider`, not two independent schedulers. Configure it using nonsecret `COLLECTOR_VOICE_PROVIDER=voicestudio_remote` and `COLLECTOR_VOICESTUDIO_BASE_URL` (exact verified endpoint), and a secure Windows credential store for the transient PIN or an approved narrow API credential. Never commit the PIN, bearer key, host private IP, user-specific local path, narrator reference, downloaded media, or private audio in the public repository or CI logs.

Restrict Collector's remote calls to `/health`, `/openapi.json`, `/v1/audio/voices`, and `/v1/audio/speech`, plus discovered necessary safe read-only voice capability endpoints. Do not grant Assistant a general remote HTTP tool, VoiceStudio admin routes, remote process execution, voice cloning, recording, mic/dictation control, arbitrary file reads, or host settings modification. If a root key is technically required it carries broader VoiceStudio administration privileges, so introduce a restricted proxy or document the risk for owner review; never treat a root credential as a read-only TTS key.

Implement strict input validation, request size limits, idempotent speech-job IDs, one bounded active TTS request, deadlines and cancellation semantics, exponential backoff with backpressure/Retry-After, and safe recovery for uncertain results. Host GPU workloads share physical compute resources with Forge's VM, so benchmark and cap concurrency; never promise a fixed speed multiplier. Verify actual chosen model/device (CUDA vs CPU) and warm/cold timing. Transport encryption and reachable `/health` do not alone prove authorized speech generation.

For each successful TTS job persist: Collector job ID, source script hash, chosen permitted model/profile reference, host capability fingerprint/version, actual resolution of compute device, generated WAV/codec/length, SHA-256, source rights record, timing, endpoint health, and retry/queue state. Never persist host credentials in metadata or output reports. On error, distinguish disconnected host, session not running, incorrect PIN/authorization, missing model, model busy, GPU unavailable, unsupported profile, and audio validation failure.

## Tests and required proof

1. On BLACKHAT-BASE, existing VoiceStudio answers loopback health requests and shows an installed/selected model genuinely accelerated by a GPU if supported. Do not assume a device is active from a GPU's presence.
2. On FORGE, the selected private endpoint is reachable by a **separate** network request and correctly enforces authorization (invalid credentials fail on protected endpoints).
3. FROM FORGE, a test original script is sent via API without foreground windows, GUI injection, clipboard, RDP, or user input on BLACKHAT-BASE.
4. FROM FORGE, a real WAV is received, decoded, probed, hashed, and imported into a multitrack project. Generate two different body narrations to verify no stale cached response. Never claim that an HTTP 200 containing error text is valid audio.
5. Forge merges body speech with captions, graphics, mixed audio, the EXACT approved intro/outro assets (if available), renders a review-only Short, then reopens project and validates the final file.
6. Reboot/restart test: observe which components automatically come online after Windows login/reboot; if host VoiceStudio needs login, record an explicit dependency. A local simulated test is insufficient evidence.
7. Assistant-to-FORGE connection and scheduled task access are a separate proof; do not confuse a Forge-to-host health request with Dot access to the worker.
8. Keep production publishing paused, with a durable render and morning handoff stating actual blockers and exact steps.

## Final handoff and overnight instruction changes

Codex must produce `docs/collector/overnight/HANDOFF.md` on the feature branch detailing verified host/Forge reachability, actual endpoint/path (redact private addresses in public report), proof of VoiceStudio API synthesis, measured runtime, model commercial suitability and exact project/video paths. The Assistant end-to-end local test under `docs/collector/v7/ASSISTANT_END_TO_END_TEST.md` remains the acceptance target but must call this remote-provider path. Preserve all existing V7 work except the now obsolete requirement to install/run VoiceStudio inside Forge.

The Codex worker is authorized to modify its own FORGE VM and Collector feature branch. It is **not** authorized to reset or broadly modify BLACKHAT-BASE, Gateway, Tailscale Serve or firewall; any narrowly scoped host-side config required must be described and approved separately by the owner.
