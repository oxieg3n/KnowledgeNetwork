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

Exports start once, asynchronously. Receipts preserve the pre-start context and
native export job result. The native result's snapshot revision is authoritative;
the pre-start inspection alone is not proof of the captured revision when the
owner edits concurrently. Poll `export-status` for the same job ID. Timeouts do
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
