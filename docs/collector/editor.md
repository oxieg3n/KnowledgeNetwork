# Native editor integration

The Knowledge Network Collector uses OpenShot's native project and editing CLI.
This adapter does not generate a competing timeline or translate effects into a
different renderer. Its output is always local review only; it has no uploader.

## Verified upstream interface

Source inspected: OpenShot `v4.1.1`, release commit `eead0c7`, the latest official
release returned on November 14, 2026. This establishes API syntax, not a local
acceptance pass. Native runtime observations belong in the overnight handoff.

- [Official release](https://github.com/OpenShot/openshot-qt/releases/tag/v4.1.1)
- [Pinned CLI implementation](https://github.com/OpenShot/openshot-qt/blob/v4.1.1/src/cli.py)
- [Pinned editing service](https://github.com/OpenShot/openshot-qt/blob/v4.1.1/src/classes/agent/service.py)
- [Pinned CLI guide](https://github.com/OpenShot/openshot-qt/blob/v4.1.1/doc/agent_cli.rst)

Windows entry point: `openshot-qt-cmd.exe --cli`. Global `--session ID` precedes
the command. Native responses wrap results in `{"ok":true,"result":...}`.
`edit apply --json @file --expect-revision N` retains native IDs and undo groups.
Project inspection returns the current revision and `data.layers`.

## Restricted adapter

`python -m youtube_ops.collector_editor --help` shows the actual local client.
An explicitly configured console executable and SHA-256 are mandatory. No PATH
lookup, shell, Python evaluator, arbitrary plugin, media URL, imported project,
or unrestricted native command is accepted. Imported media and new outputs must
be inside the configured private vault. The worker must own serialization and
the vault/session-registry ACLs. This Python client is not an OS sandbox.
Only sessions started and enrolled by this adapter can be controlled. The
executable digest is rechecked for every invocation. Receipt-directory links and
changed vault paths are rejected. An adversarial process under the same Windows
identity can still race file changes between validation and native reads; private
ACLs, a protected editor installation, and final source/hash rechecks remain
required. Do not treat path validation as protection from that identity.

Upstream session startup has a fixed 30-second discovery window. Cold startup
can outlast it while the native server continues running. A startup intent blocks
duplicate starts; the session ID from the pinned native timeout log reference is
preserved without exposing registry credentials. Use `recover-start` to check
that same session after it becomes reachable. If no identity was returned,
inspect the native process/registry under coordinator control rather than start
another editor. The fixture's `--session` can reuse an enrolled recovered session.

Supported edits are native media import; clip placement, trimming, reorder via
position/layer, split, removal, gain/transform, alpha/audio fades and keyframes;
native text/lower thirds; a curated effect set; and custom project profiles.
Parameters remain subject to the installed upstream validator. Unsupported
operations fail instead of disappearing from export. Captions can use timed
native text only after real speech timing is supplied; this adapter does not
claim automatic speech alignment.

Every mutation first commits a private intent with the requested revision and
asset hashes. A native error or timeout retains that intent and blocks replay.
`reconcile` reads native project, export and recent-operation state. It does not
automatically decide an uncertain edit succeeded or clear a pending operation.
Preserve the private evidence and resolve it under the coordinator's control;
never delete a pending file merely to retry the original mutation.

Saves use new filenames and native serialization. Reopening requires a matching
managed-save receipt and exact current project hash, so changed external files
are rejected rather than overwriting a human edit. Manual GUI editing within
the shared live session still needs a fresh inspected revision before edits.
The GUI/service user-session boundary remains an acceptance test.
Before saves/exports, the adapter inspects the native file and clip readers and
requires local sources matching exact prior-import hashes. Changed/unregistered
GUI-added sources, unsupported readers and path escapes block those operations.
Reopen also rechecks the source hashes in its managed-save receipt.
Native save can advance revision while moving project assets. The adapter checks
the tracked save operation's `revision_before` against the audited context,
rather than rejecting that legitimate save revision change.

Exports start once, asynchronously. Receipts preserve the pre-start context and
native export job result. The native result's snapshot revision is authoritative;
the adapter cancels the returned native job if its snapshot revision differs
from the inspected/audited context and retains the pending intent. Native export
start lacks an expected-revision option, so this detection is after start;
the editor and source vault must remain under the trusted user's control.
Poll `export-status` for the same job ID. Timeouts do
not cancel native work. This adapter never promotes a render to approved status.

## Owned technical fixture

`python -m youtube_ops.collector_editor_fixture --help` builds a new private
50-second portrait project using original PNGs and two original low-volume tone
WAVs. It uses three scenes, overlapping visual layers, native text, keyframed
graphic motion, a Saturation effect, fades, and two independently mixed audio
tracks. It saves revision 1, changes native text, saves revision 2 and reopens
the exact revision-2 bytes. Rendering is a separate serialized operation.

Default resolution is 360x640 for a bounded technical test; `--width 1080`
creates 1080x1920. It is deliberately labelled unbranded and not narrated when
the actual approved bookends/licensed VoiceStudio narration are unavailable.
Timed technical labels are not claimed as speech-aligned captions. This fixture
does not establish manual GUI edit preservation, audible narration, listening,
bookend acceptance, or a complete V7 production demonstration.

Unit tests use mocked native replies and never count as a real editor pass.

## Observed Windows proof, November 14, 2026

OpenShot 4.1.1/libopenshot 1.1.1 executed the actual layered technical batch,
native text correction, save/reopen and native export on the VM. The final native
session inspection reported revision 54, 12 clips, 12 file entries, one effect,
five layers, a clean saved project and available undo. This is a 360x640 technical
proof, not the requested 1080x1920 narrated/branded acceptance demo.

The native export completed 1500 frames: exactly 50.000 seconds of H.264/yuv420p
at 30 fps, with 50.000 seconds of AAC stereo audio at 48 kHz. Full FFmpeg decode
returned zero. Configured black detection (at least 0.5 seconds, pixel threshold
0.10) and silence detection (at least 2 seconds below -50 dB) returned no spans.
Original tones were intentionally quiet: mean -44.7 dB and maximum -38.4 dB.
All six original source hashes still matched after export.

- Native `technical-v2.osp` SHA-256: `02104e6651757a1c5132615bc11c43fbeb6f4738c8af402aec7eb113c2272a9e`.
- Native `native-final.mp4` SHA-256: `66ef21dc5413abf087f28a3e9f1ab69ac9e66b77f6f3cd987cf83c702ed76f9d`.

Approximate native job artifact interval was 22.329 seconds, measured from job
spec creation to worker-log last write. This is not a benchmark or a measured
peak-resource claim. No human listening, manual GUI edit, speech alignment,
VoiceStudio narration, approved branding, integrated GUI, or service-to-editor
companion acceptance is established by this proof. Publication remains paused.

The subsequent actual visual review of that 360x640 export FAILED: native text
glyphs were absent despite a successful codec/decode pass. Preserve that artifact
as failed visual evidence; the technical checks above do not qualify its text.

## V8 Windows offscreen font repair and 1080p proof

The pinned OpenShot export worker forces the Qt offscreen platform. Qt 5.15's
[Windows offscreen implementation](https://github.com/qt/qtbase/blob/5.15/src/plugins/platforms/offscreen/qoffscreenintegration.cpp)
uses FreeType, whose
[font database](https://github.com/qt/qtbase/blob/5.15/src/platformsupport/fontdatabases/freetype/qfreetypefontdatabase.cpp)
loads its configured font directory. Qt's
[fontDir implementation](https://github.com/qt/qtbase/blob/5.15/src/gui/text/qplatformfontdatabase.cpp)
honors `QT_QPA_FONTDIR`; its fallback is the Qt library's fonts directory rather
than the Windows system font directory. The installed editor lacked that fallback
font directory. Correct native text/font/color records alone therefore did not
prove glyph rendering.

The adapter now sets `QT_QPA_FONTDIR` to the existing Windows system Fonts folder
only in the native child environment, before session startup. Export workers
inherit it. No font is downloaded/copied, no upstream binary is patched, and no
global environment or host setting is changed. New managed session markers retain
that configuration; older unconfigured sessions cannot export while falsely
claiming the new font setup. Saved projects and old evidence remain untouched.

A new 1080x1920 native project and 50.000-second native export completed. Actual
exported frames at 5, 25 and 40 seconds were viewed at mobile size: native titles,
lower-third words and a persistent local-review/unbranded label are visible and
legible in all three scenes. This establishes the missing-glyph repair for that
fixture, not general GUI or publication acceptance.

The project also passed actual native trim, split, reorder and grouped undo.
A separate profile change to 30000/1001 fps and split at exactly 1.001 seconds
used the expected native frame boundary; grouped undo restored 30 fps and all
original clip summaries. Final save/reopen retained the composition and history.
Native undo was called by the controlled test coordinator; it is not advertised
as a newly implemented service job or unrestricted job command.

- `technical-v3.osp` SHA-256: `fcbdaef5d8b3a4c8a67ddce33ef6df4ea89c88ca024972f5af9ab5b362e2b4a0`.
- `native-final-1080.mp4` SHA-256: `b11728e5b2504871db1ad255ba92e3ed8015a9aca3cfc73015ee7b3c2a5d950a`.
- Native export snapshot revision 104; 1500 frames, 30 fps, H.264/yuv420p,
  AAC 48 kHz stereo, audio/video each 50.000 seconds, full decode exit zero.
- No configured black/silence spans; all six source hashes unchanged after export.
- Approximate job artifact wall interval 130.643 seconds. One live worker sample
  showed 967,540,736 bytes peak working set at that moment; a final continuously
  sampled resource peak was not measured.

This remains an unbranded technical fixture with original quiet tones. Host
VoiceStudio narration, real speech captions, approved plasma assets, listening,
manual GUI edits, GUI/service companion and preview/export parity remain separate
acceptance rows. Public publishing remains paused.

## Minimal worker integration boundary

Keep scheduling and durable job identity in the .NET worker. Register individual
typed editor job types rather than exposing an arbitrary Python command, native
CLI argument list, session ID, executable path or vault path to job input.
Configure the pinned Python/editor locations and private vault once under the
worker identity. Map project IDs to enrolled native sessions on the worker side.
The same durable idempotency key owns the intent/result; pending native intent
means reconciliation, not a second subprocess replay after restart.

For visible/native desktop work, use an ACL-protected logged-in-user companion
that calls this adapter. Do not run the desktop editor in Windows service session
zero or claim a developer console proves that boundary. A service job finishes
only when its native result/receipt is preserved. An export submission preserves
the returned native job ID and exact `result.data.revision`; poll that job through
completion and bind final QC/hash to it. Until this route is implemented and
tested, advertise the editor as a separate local developer client, not as an
already supported service job or integrated Collector editing UI.
