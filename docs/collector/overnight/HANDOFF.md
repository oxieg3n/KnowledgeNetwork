# V8 handoff — verified staging build, incomplete production acceptance

Updated November 14, 2026, America/New_York. Resumed checkpoint `8c0e7f0` on
`feature/collector-v7-overnight`. Original backup
`C:/admin/collector-backups/20261114-073652` is preserved. Its Git bundle still
hashes `c09bd03678201fe4576e746246c7709ba32dbdc2b6b2c7992872f4c9367659cd`.
The prior paused handoff remains in that backup and Git history.

Implementation/evidence checkpoint: `36b88c9`. A noninteractive push of the
feature branch failed because Git credentials were unavailable; no remote branch
or review PR was created. Local history and all completed work remain intact.

Non-destructive fetch found origin/main `47e7aeb`. Only its updated AGENTS.md
and three V8 instructions were integrated; no live production state was merged
or reset. Original untracked instructions were also preserved at
`C:/admin/collector-v8/pre-v8-AGENTS.md`. All helper worktrees remain.

## Outcome

PASS: installed Windows staging worker/dashboard, real LocalService health,
durable jobs, restart/upgrade/uninstall/reinstall retention, native 1080p editable
project/export with visible text, and authenticated private host API discovery.

BLOCKED: actual remote narration and complete branded Short. Last successful
host catalog reported only noncommercial OmniVoice TTS weights installed, no
loaded speech engine/actual execution device, and no cleared voice profile.
The supplied consumption PIN subsequently began failing 401/403. Approved badge
and outro MP4 bytes remain outside GitHub and were not materialized.

After the owner reconfirmed the Tailscale HTTPS route and reported that sharing
could not be enabled following an update, one further provider status check
returned `BLOCKED_VOICE_AUTH`. The route is reachable; authenticated speech
access is not restored. Evidence: private `voice-user-route-recheck.json`.
No host settings, networking or GUI were changed and no speech POST was sent.

INCOMPLETE engineering: editor/narration dispatch through the service identity
and user-session companion; source-level Collector/Qt editing workspace. The
WPF operations window is not an integrated video timeline. Developer adapters
and the stock Qt editor do not complete that requirement.

Publication remains PAUSED. No demonstration or other video was uploaded.

## Installer, launch and repair

Unsigned installer, actually installed, upgraded and reinstalled:
`C:/admin/projects/KnowledgeNetwork/output/installer-v8-round3/The-Knowledge-Network-Collector-0.1.0-setup.exe`

SHA-256: `145c61039e183e6bfd38fa74099c8a261ff881beac097d760d108961b82e0725`.
All successful install/upgrade/reinstall runs exited 0. Actual uninstall exited
0 and retained the private database. Manifests, .NET notices, Apache license
and NuGet license/copyright metadata are packaged. Python development clients,
OpenShot, VoiceStudio and models are not bundled in this installer.

Installed CLI: `C:/Program Files/The Knowledge Network Collector/kn-collector.exe`
SHA-256: `4d9cf8f0ec0aa9b9f5c55ab076b87a608a98af36296bc1e28cc8875535d67515`.
Worker DLL SHA-256: `e34e8278da1ca7d1de400dd3ab4ffdb30f3f50c746924bcfb0b7732919db3f5a`.

Dashboard: `C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe`
SHA-256: `d61b35b5d3c39b0d4ff4b7b9adb9d389320c12613c218bdc1c2f0b0c8fa28d04`.
Dashboard DLL SHA-256: `bc3c4483bdd09a3efe4b85b7882e8c3ceb751e26ff8277f39e09b84bf44017b1`.
Worker build identifies source `9b1b669`; corrected dashboard was built from
`719ea5b`. Later Python/docs commits do not change those binaries.

Launch normally from the Start Menu or:

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
$nonce = [guid]::NewGuid().ToString('N')
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health $nonce
```

Repair: rerun the installer, or run the installed CLI's `install-service`
elevated as the configured owner. `remove-service` is native and preserves
data. No PowerShell execution policy was changed or bypassed. Observed installer
signature status is NotSigned; no signing certificate is claimed.

## Worker and persistence

Service `KnowledgeNetworkCollector` is Running, startup Auto, LocalService.
Private data: `C:/ProgramData/KnowledgeNetworkCollector`.
Persistent worker ID: `cb6ce3cd482148e7b8b0c8661ec8c6e9`.
Job `131f54611e5a41c8b9e0d178b1a11dde` succeeded and survived service restart,
upgrade, full uninstall and reinstall with the same result hash and worker ID.
Result SHA-256: `f082e2ce38e84625e303c17d16948a0e824e84e49fd5686b5ab14bb145593b65`.
Consistent pre-uninstall backup:
`C:/admin/collector-v8/worker-before-uninstall.sqlite`.

PASS: duplicate returns same job, changed payload rejects, exact nonce matches,
terminal cancellation retains success. Fake-pipe test received zero bytes and
returned `untrusted_pipe_server`. Tampered package failed before service mutation.
Noncanonical install path failed with exit 7 and retained the running service PID.
Actual service/private-spool ACLs reviewed.

Only `diagnostic.echo` and `research.snapshot` jobs are enabled. Editor/narration
jobs explicitly report disabled; no arbitrary shell/remote-HTTP job exists.
Immutable research snapshot contains 143 fresh leads, 2 recap slots, 33 blog
versions and 42 evergreen entries. This is not a production cutover.

VM reboot, signed-out/locked operation, scheduled Assistant access and off-VM
recovery remain NOT TESTED/UNVERIFIED. Local Codex calls are not Dot proof.

## Remote VoiceStudio

BLACKHAT-BASE is the speech host; FORGE is the Collector/editor VM. The existing
VM VoiceStudio installation was preserved and unused by V8. No host desktop,
input, clipboard, model install, license acceptance, firewall, Gateway, service
or Tailscale configuration changes occurred.

PASS earlier: supplied HTTPS endpoint matched the private tailnet peer; TLS
certificate/hostname verification; health/OpenAPI 0.5.6 and voice catalog.
Wrong PIN returned 401, correct PIN 200. Credential went only into Forge's
Windows Credential Manager via stdin, not process arguments, environment secrets,
repository or URL. Private route and nonsecret user configuration stay outside
Git. Remote Workers or an administrative key was not needed for this API path.

Latest check at 13:35 UTC: stored credential rejected. Independent standard HTTPS
client returned 403; provider reported blocked authentication. Cause was not
proven and retries stopped. Refresh using interactive local `credential-save`,
then perform one `verify-auth`. No bypass was attempted.

Speech capabilities and model catalog reads passed; `/model/loaded` was denied.
Client retains partial evidence without requesting administrative credentials.
Only `k2-fsa/OmniVoice` was installed for TTS; its publisher labels pretrained
weights noncommercial. No commercial model/voice clearance was invented. RTX3060
visibility is not actual GPU speech execution proof.

**No host speech POST, real WAV, GPU synthesis or listening occurred.**
Original 97-word/9-segment request `1610ea5e060d431980e52af9f273ed85` is prepared
as `blocked_remote_voice` / rights-not-verified. Private spool:
`C:/admin/collector-v8/editor-vault/remote-voice`. Original text/segments:
`C:/admin/collector-v8/demo-script.private.txt` and `demo-segments.private.json`.

Source supports streamed WAV checks, exact observed model identity, measured
PCM cues, cross-process serialization, deadlines and cancellation. Local socket
fixtures test slow headers/body and TLS interruption. Unknown POST outcomes
retain a global durable hold across new job IDs/process restarts; no automatic
retry, expiry or unsafe override. These tests are not actual host synthesis.
See [voice acceptance](../VOICE-PROVIDER-ACCEPTANCE.md) for scope and prerequisites.

## Native editor and media

OpenShot 4.1.1/libopenshot 1.1.1, pinned Windows native console. Child-only
`QT_QPA_FONTDIR` fixed the V7 missing-glyph export without binary patches or
global/host changes.

Project: `C:/admin/collector-v8/editor-vault/technical-1080-001/technical-v3.osp`
SHA-256: `fcbdaef5d8b3a4c8a67ddce33ef6df4ea89c88ca024972f5af9ab5b362e2b4a0`.
Video: same directory, `native-final-1080.mp4`.
SHA-256: `b11728e5b2504871db1ad255ba92e3ed8015a9aca3cfc73015ee7b3c2a5d950a`.

PASS: exactly 50.000s, 1080x1920, 30fps, H264/yuv420p, AAC48k stereo, 1500 frames,
full decode, configured black/silence scans and unchanged six source hashes.
Job `8c8555feddb54d16b1e0be6e6a6277d4` exported revision 104. Three actual scenes
show native titles, lower thirds and review labels. Native trim/split/reorder,
grouped undo, 30000/1001 split timing and save/reopen passed.

Music reset/duck/readback/two-undo proof restored exact original clip JSON.
Managed first attachments/longer retakes remove stale gain points. Manual caption
or music edits and ambiguous ownership block a retake before mutation.

This is an unbranded fixture with original low-volume tones, not speech.
Artifact wall interval was 130.643s; one worker sample measured about 923MiB,
not a continuous peak. Real speech mix, listening, manual Qt GUI edit, preview/
export parity, landscape and approved bookends remain unverified. V7 artifacts
are intact. Exact saved project/video hashes stayed unchanged after native tests.

The owner reconfirmed that approved MP4 bytes are maintained separately. Existing
intro/outro code and hashes were reread/preserved. Actual badge/MP4 locations
remain needed; no substitute or re-created approved media was used.

## Tests and visual review

Final Python/FFmpeg regression: **173 passed, zero failures/skips**, 50.359s.
Installed worker self-test: **37 checks passed**. Dashboard: **17 real in-process
UIA/CLI/service/focus/error/recovery/render checks passed**, exit 0. An actual
invalid-job-ID crash was fixed and retested through installer upgrade.

Rendered WPF captures at 1040x780 and 800x600 were inspected: readable charcoal
layout, visible focus, wrapped actions and no clipped main controls. Actual
Windows desktop capture succeeded too. OS input/accessibility-tree testing was
blocked by the dashboard's higher Windows integrity than the computer-use helper;
no security settings/barriers were changed. OS DPI/high contrast and an ordinary
non-elevated desktop client remain NOT TESTED.

Evidence: `C:/admin/collector-v8`. Reports include `final-regression.log`,
`installed-self-test.json`, `native-worker-acceptance.json`, `pipe-squatting.json`,
`package-integrity-negative.json`, `installer-path-negative.json`,
`uninstall-retention.json`, `dashboard-smoke-002/smoke-results.json`,
`native-desktop-review.json`, `editor-native-qc-1080.json`,
`editor-native-music-proof.json`, `host-probe-result.json`, and
`voice-latest-auth-check.json`. Raw API/route/catalog files and media stay private.

Ponytail 5.3.3 FULL resolver verified; actual review skill and independent review
applied. No lifecycle-hook trust/execution was asserted. UI/UX Pro Max 2.15.0
actual skill and targeted WPF/focus/status searches reused current tokens.
Taste 2.5.1 native visual judgment applied; web gates are not applicable.
Remaining native UI/host/lifecycle checks are listed above.

## Assistant test and production controls

Use the copyable request in [Assistant operations](../ASSISTANT-OPERATIONS.md).
It begins with the real installed health CLI and private remote provider.
A tested one-command full narrated/branded Short does not exist yet; the
acceptance request must report invalid auth, missing eligible model/voice or
unmaterialized bookends rather than invent success.

Production receipts, rights/review gates and workflows are unchanged.
operations.json remains
`d61551c51fc46bc65b6e3c11b0e6d12e38b13efdef44121a07c8570ee22b799d`.
Publication is paused. No public media upload or automatic publication occurred.
