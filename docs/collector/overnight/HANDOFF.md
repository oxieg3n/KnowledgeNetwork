# Paused checkpoint — November 14, 2026

The owner requested a pause at 07:36 America/New_York to change direction.
Development and helper work stopped. This is a recoverable partial build,
not morning acceptance or a completed installation. Wait for further instructions.

## Source and backup

Branch: `feature/collector-v7-overnight`, based on `e388ad8`.
Integrated helper commits through `90f0bea`; the following checkpoint commits
preserve root integration changes and this handoff. No PR was created, no branch
was pushed, and nothing was merged. The owner's originally untracked `AGENTS.md`
is preserved unmodified and excluded from implementation commits.

Local backup destination: `C:/admin/collector-backups/20261114-073652`.
The backup contains an all-refs Git bundle, source archive, original AGENTS.md,
private evidence/media, existing release output, and SHA-256 manifest. Consult
the backup's receipt for the exact checkpoint commit and digests. It is local
to this VM; no off-VM backup is claimed.

Separate helper worktrees/branches remain intact at KnowledgeNetwork-worker,
KnowledgeNetwork-editor and KnowledgeNetwork-voice beside the main worktree.
Their source commits were integrated. Voice worktree bin/obj build artifacts
are untracked, not source changes.

## Implemented and checked

- Windows .NET 10 LTS worker/CLI: restricted local Windows pipe, client/server
  authentication, durable SQLite WAL/FULL commits, job deduplication, result
  hashes, append-only events, cancellation and replay-safe diagnostic recovery.
  Worker source builds with zero warnings/errors; 26 self-checks passed.
- Only diagnostic.echo and immutable research.snapshot jobs are enabled.
  No production scheduler or publication operation is enabled. Editor and
  narration adapters are separate developer clients, not yet service jobs.
- Native WPF operations dashboard compiles with zero warnings/errors. It calls
  the real CLI. Source includes own-app UIA/rendered-window smoke instrumentation
  and explicit tab order, but that instrumentation has NOT been run.
- Native admin-only install-service/remove-service source compiles. Noncanonical
  worktree executable paths are denied. Actual installed-path installation,
  LocalService health, pipe-squatting test, service restart/reboot, installer
  execution and upgrade/uninstall remain NOT TESTED. No Collector service is
  installed at this checkpoint.
- Integrated Python suite passed 133 tests with 5 skips before later editor
  hardening. A subsequent FFmpeg-enabled run ran 135 tests with 2 failures in
  existing Linux-font finishing code. The targeted Windows font-path fix then
  passed all 3 finishing tests, preserving audio and outside-footer pixels.
  Editor helper's latest focused run passed 17 tests. The full suite must be
  rerun after all latest changes; do not combine these counts into a new total.
- Python 3.13.17 and .NET SDK10.0.404/runtime10.0.15 installed. Development venv
  includes tzdata2026.2, NumPy2.3.5 and now Pillow13.0.0. Earlier tests initially
  used Pillow12; a full latest-environment regression is pending.

Evidence logs: `C:/admin/collector-v7`, with initial baseline logs additionally
at `C:/admin/collector-baseline-tests.log`, `collector-baseline-configured.log`
and `collector-integrated-python.log`.

## Native media proof and important failure

OpenShot4.1.1 was downloaded from its official release, matched installer SHA-256
`6c18abf951a798b536b07aa88f78d62eb55345903699b429b08322323c049690`, and installed.
Its native Windows console introduction returned real output. The installed
console digest is recorded in dependencies.lock.json. No fallback editor selected.

Private project:
`C:/admin/collector-v7/editor-vault/technical-002/technical-v2.osp`.
Private export:
`C:/admin/collector-v7/editor-vault/technical-002/native-final.mp4`.
The source project survived actual native save/edit/save/reopen. Export job
`cde34dc4acd84df190dd91831eafa5e4` completed from revision54. It is50.000 seconds,
360x640,30fps, H264/yuv420p, AAC48k stereo,1500frames, full decode exit0.
Configured black/silence scans found no qualifying spans. Original low-volume
tones are technical audio, not narration. No listening occurred.

**FAILED visual text acceptance:** actual exported frames at5,25,40 seconds
show backgrounds/animated graphic/lower-third backing but no title/text glyphs.
Contact sheet: `C:/admin/collector-v7/editor-contact-sheet.png`, actually viewed.
Do not call native text or the production demo passed. The editor helper found
a candidate cause: OpenShot export_worker forces Qt offscreen on Windows,
whose basic font database may not see system fonts. A per-session documented
QT_QPA_FONTDIR configuration is a candidate, NOT tested/applied. The next run
must first verify official support and render a new native session/fixture;
do not silently replace native text with a different compositor.

Project SHA-256:
`02104e6651757a1c5132615bc11c43fbeb6f4738c8af402aec7eb113c2272a9e`.
MP4 SHA-256:
`66ef21dc5413abf087f28a3e9f1ab69ac9e66b77f6f3cd987cf83c702ed76f9d`.
No1080p fixture, manual GUI edit, preview/export comparison, true speech captions,
approved branding or full editor/service integration acceptance is claimed.

## Voice, branding and connection

Preexisting VoiceStudio0.5.8.0 was detected and preserved. Its existing app was
launched; processes eventually appeared, but loopback3900 probes still returned
BLOCKED_VOICE_SESSION. No model/profile/license was verified, downloaded or
accepted; no test speech WAV exists. No fallback narrator was substituted.

Approved badge and portrait/landscape outro media were not found in inspected
project/Downloads/Documents locations. Their expected hashes remain protected;
no equivalent assets were forged. The technical export is unbranded.

Real Assistant/Dot-to-VM and scheduled connection remain UNVERIFIED. Local Codex
commands are not proof. Both native computer-use runtimes repeatedly timed out;
one app inventory succeeded after reset, but no Collector/OpenShot GUI keyboard
or screenshot acceptance was obtained. WPF visual-tree instrumentation is pending
and must be reported separately from OS screenshots/actual DPI/OS key injection.

## Packaging and resume cautions

Existing self-contained build files are under
`C:/admin/projects/KnowledgeNetwork/output/collector-windows/`.
These are intermediate builds: they predate the latest native maintenance and
dashboard smoke/tab-order source changes. They are NOT the final release.
No Collector installer exe has been compiled or installed yet.

Inno Setup6.7.3 and FFmpeg Gyan9.0.2 were installed/extracted from checksum-verified
official release locations; see dependencies.lock.json and notices. Inno source
and reproducible build scripts are present. Windows effective PowerShell policy
is Restricted; an actual -File probe was denied. No policy was changed or bypassed.
The installer source now calls native maintenance verbs instead of PowerShell.

Before packaging, review a known pending issue: ServiceInstall.VerifyPackage
currently parses File.ReadAllBytes(manifest), while Windows PowerShell
Set-Content -Encoding UTF8 creates a BOM. Verify/fix that compatibility before
running the installer. Regenerate the manifest after final worker/dashboard
publishes and include runtime/NuGet notices. Test canonical path checks,
authenticated stable service health, malicious pipe denial with zero request
bytes, deduplication/restart, snapshot readback, installer upgrade/uninstall
retaining data, real dashboard flows and actual rendered screens. Do not count
source compilation as any of those runtime passes.

At pause, only owned idle OpenShot headless session process5940 and the existing
VoiceStudio app processes remained from this work; no FFmpeg/render/build process
or Collector worker service was running. They were left intact to preserve state.
No VM reboot or unrelated process shutdown was performed.

## Skills and production controls

Ponytail5.3.3 FULL instructions and actual review skill loaded from the installed
plugin. Its mode resolver returned full with a session-scoped setting; lifecycle
hook trust/execution was not asserted. UI/UX Pro Max2.15.0 official checkout at
`C:/admin/tools/ui-ux-pro-max` and actual SKILL were read, with targeted desktop,
focus, error, timeline and WPF searches. Taste2.5.1 actual installed SKILL was
read/applied for native visual judgment. No web gate pass is claimed. See design
spec for searches; actual native screenshot/DPI/manual keyboard checks remain pending.
Independent review found pipe impersonation, dashboard/default-data-directory
collision, installer path execution and premature health claims; source fixes
were integrated, with runtime verification still pending.

Publication remains PAUSED. The demo has NOT been publicly uploaded. No production
state, existing approvals/receipts, workflows, OAuth permissions or poweredby
website was changed. The operations.json digest remains
`d61551c51fc46bc65b6e3c11b0e6d12e38b13efdef44121a07c8570ee22b799d`.
Do not issue a purported tested final Assistant45–55second command yet: the full
licensed-voice/branded/local-service path has not run. Use the V7 Assistant test
template only after these concrete blockers and tests are resolved and the owner
authorizes resumption.
