# The Knowledge Network Collector: open-source reuse decision

Reviewed November 13, 2026. This is a source/documentation review and an implementation recommendation. No listed editor, voice model, or integration was installed or benchmarked on the owner's VM during this review. Upstream claims and test counts are not local acceptance evidence. Codex must pin versions and confirm actual supported behavior before adoption.

## Recommended combination

Use a narrowly maintained **OpenShot-based editing workspace with its first-party agent CLI**, the existing **KnowledgeNetwork Python pipeline**, the proposed **Windows background service**, and **VoiceStudio through its local API**. The Collector should own the job/research/rights/publication workflow; established projects should supply editing, rendering, speech and media processing.

The final source review changed the provisional Shotcut preference: OpenShot 4.1 added native agent editing, and 4.1.1 was the latest release observed. Its CLI is explicitly experimental, so real Windows acceptance is required. Shotcut/MLT remains the first fallback.

The exact app name is **The Knowledge Network Collector**. Retain the current public `oxieg3n/KnowledgeNetwork` repository. Do not create a second project just to rename it.

## What to reuse and what not to rely on

| Project | Evidence inspected | Decision |
|---|---|---|
| OpenShot 4.1.x + libopenshot | Official release notes and agent CLI guide: native editing commands, JSON, shared GUI/headless sessions, revisions and native export. Latest observed release 4.1.1. | Preferred first proof. Reuse the actual editor and its first-party interface; experimental CLI requires tests, version pinning and recovery handling. |
| Shotcut + MLT | Official feature list, source/build notes, native project format and rendering documentation. Multitrack GUI, filters, keyframes, subtitles, mixing, proxies, undo/redo and MLT export already exist. | First fallback if the OpenShot integration fails a concrete acceptance requirement. Reuse the GUI/engine and prove the Windows bridge. |
| HKUDS/CLI-Anything, Shotcut harness | MLT operations and renderer implementation; Apache-2.0 license. The inspected render lookup assumes `melt` on PATH and includes a separate FFmpeg fallback. | Evaluate only if selecting Shotcut. Audit operations, Windows binary/plugin discovery and native render parity; not an already-validated complete backend. |
| NoBanks/shotcut-mcp | README current limits: one video track, GUI edits overwritten by subsequent tool calls, only dissolve rendered, Windows rendering not covered by CI. MIT. | Reference only, not the production editor adapter. These limitations conflict with a shared human/agent multitrack editor. |
| VoiceStudio | Windows installation, local HTTP/OpenAPI/MCP documentation, engine docs, licensing notice. | Integrate its supported local API while initially retaining a separate installed app. No need to recreate its speech interface or automate ordinary narration with mouse clicks. |
| Existing `youtube_ops` | Current repo, approved intro/outro modules and brand instructions. | Preserve the existing operational protections and reuse proven media pieces. Add adapters rather than replacing the pipeline. |
| Kdenlive | Official introduction and editing documentation; Qt/MLT foundation and Windows distribution. | Capable alternative, but no demonstrated reason to add a third production editor. |
| OpenCut | Upstream README describes a rewrite; API, MCP and headless functionality are listed as upcoming. | Do not base production acceptance on roadmap features. Reassess a shipping release later. |
| OpenTimelineIO | Official documentation describes editorial interchange and external media references. | Optional interchange, not a renderer or replacement timeline UI. Report unsupported effects on interchange. |
| Glaxnimate | Shotcut's own feature list documents its vector-animation integration. | Reuse for a specific motion-graphics need; not a mandatory second workflow for every video. |
| Remotion | Official pricing/license conditions distinguish eligible free use from paid arrangements. | Optional future choice, not the default dependency for an unrestricted open-source stack. Do not describe all usage as free. |
| FFmpeg/FFprobe | Official filters and licensing documentation. | Continue controlled media preparation, probing, captions/QC and compatible existing rendering. Audit the actual shipped build's licenses. |

## Why the final recommendation is OpenShot first

OpenShot's official 4.1 release documents agent editing as experimental, and the 4.1.1 release adds maintenance and packaging fixes. The agent guide describes a native shared editor session rather than a separate project generator. This directly addresses the Collector's need for both human and agent editing without depending on a third-party MCP adapter's incomplete reconstruction.

The Windows console entry point is `openshot-qt-cmd.exe --cli`. Probe actual installed command help instead of assuming an `openshot-cli.exe` exists. Pin the tested distribution and reject unsupported capabilities. The native interface is a foundation, not proof that the Collector already works.

Keep the existing Windows supervisor and Python operational pipeline. Build the editor workspace through a small maintained integration with OpenShot's Qt/Python UI. Do not invent a WPF timeline. A separate stock OpenShot window is acceptable during the proof, but it does not meet the final built-in-editor requirement. Avoid foreign-window embedding hacks.

Native `.osp` project state should remain authoritative. The operational manifest binds versions, assets, rights and review to that native composition. Use revisions, save checkpoints and structured commands, preserving manual changes. OpenShot's guide warns that runtime failures can leave partial edits and export timeouts need not stop jobs. The Collector must reconcile real state before replaying operations. A project file does not contain all its referenced media.

If this proof fails, use the same fixtures to evaluate Shotcut/MLT and its native `.mlt` format. Do not make both editors mandatory, flatten rich projects into an incomplete JSON summary, or silently substitute an export that omits unsupported effects.

## VoiceStudio integration and model selection

The documented local backend exposes health/schema discovery, voice listing, speech generation and MCP. The Collector can send approved text through a provider adapter, validate the audio response and register the resulting file directly into the project. An Open VoiceStudio button is still useful for profiles, model setup and troubleshooting. The endpoint should remain local to the VM; Dot's cloud localhost is not the VM's localhost.

VoiceStudio's application license and its model licenses are separate. Its license notice permits commercial application use under AGPL terms, but identifies the default OmniVoice pretrained weights as CC-BY-NC. A license for VoiceStudio code does not grant rights to every model, voice sample or tokenizer. Do not automatically use that default for this business channel.

PocketTTS is one CPU-oriented candidate documented by VoiceStudio. Its documentation lists MIT code, CC-BY-4.0 weights and a gated access agreement. That is a starting point for exact-version review and an audition, not blanket clearance or a claim it is the best-sounding engine. Check the selected voice, consent, model/output terms and any required attribution. Do not bypass notice/access checks or silently fall back to a paid provider.

Measure an actual 30-60-second audition using the channel's technical vocabulary. Assess pronunciation, pacing, consistency, audible artifacts, elapsed time and peak memory. Verify whether the installed backend can run after closing the desktop app, locking the screen, signing out and rebooting. A Windows service cannot assume it owns the logged-in user's app state or model directory.

## Plasma intro and outro: reuse the approved work

Repository instructions now include both `docs/brand-intro.md` and `docs/brand-outro.md`, plus `src/youtube_ops/outro.py`. The inspected main tree was `b1ec4c38c4abc5c3d7bd7cf6dced2abc95a6354f`. Refresh before coding.

The intro is `poweredby-plasma-v1`, nominally 1.6 seconds. The approved outro is `poweredby-plasma-outro-v1`, 7.8 seconds, with distinct portrait and landscape assets and pinned hashes. The outro includes the approved spoken call to action and hold/fade. Preserve its existing sound even when new body narration moves to VoiceStudio.

Nominal bookend duration is 9.4 seconds. For a 60-second finished Short that leaves about 50.6 seconds for its body, before accounting for actual assembly timing and transitions. Inspect measured muxed durations. Do not silently shorten approved branding to fit a script.

Place exactly one intro and one outro on each newly authored final timeline. Derived Shorts should take the clean content range from a long-form project and apply their own matching bookends, not inherit and duplicate the parent's. Do not change older reviewed requests or the already-approved DEF CON renders.

## Implementation proof before committing to the architecture

Use the installed native CLI with owned or synthetic media and a permitted voice to prove one real multitrack project: footage, a graphic overlay, text, a keyframed change, music ducking under narration, captions, and both approved bookends. Produce portrait and landscape versions. Make a manual GUI edit and a subsequent agent edit, close/reopen the project and verify both survive. Compare preview and export. A test that skipped the renderer is not a passed rendering test.

Separately prove Assistant can send a bounded job to the VM, retrieve a durable result and do so on a genuine scheduled run. Preserve current publication pauses throughout development. The project is not complete because a local developer can run a command or a third-party README says it supports agents.

## License and maintenance boundaries

Maintain a dependency inventory with pinned revision, binary provenance, license, source/notice obligations and update path. OpenShot/Shotcut GUI GPL licenses and VoiceStudio's AGPL are not public-domain licenses. The OpenShot library has separate licensing; it does not relicense the whole desktop application. Rebranding or putting the repository on GitHub does not remove attribution or distribution obligations. Audit Qt, MLT, codecs, plugins, fonts and model weights separately. Prefer documented interfaces and a small upstream patch set to reduce maintenance.

## Primary references

- Existing application repository: https://github.com/oxieg3n/KnowledgeNetwork
- Approved intro: https://github.com/oxieg3n/KnowledgeNetwork/blob/main/docs/brand-intro.md
- Approved outro: https://github.com/oxieg3n/KnowledgeNetwork/blob/main/docs/brand-outro.md
- Outro validation: https://github.com/oxieg3n/KnowledgeNetwork/blob/main/src/youtube_ops/outro.py
- OpenShot native agent CLI: https://www.openshot.org/static/files/user-guide/agent_cli.html
- OpenShot 4.1 announcement: https://www.openshot.org/blog/2026/10/25/openshot-41-direct-text-editing-auto-optimize-command-line-editing/
- OpenShot current releases: https://github.com/OpenShot/openshot-qt/releases
- OpenShot editor source: https://github.com/OpenShot/openshot-qt
- Shotcut features: https://www.shotcut.org/features/
- Shotcut source/build/license: https://github.com/mltframework/shotcut
- MLT documentation: https://www.mltframework.org/docs/
- Shotcut command-line export: https://forum.shotcut.org/t/export-at-the-command-line/44067
- CLI-Anything Shotcut harness: https://github.com/HKUDS/CLI-Anything/tree/main/shotcut/agent-harness
- CLI-Anything rendering implementation: https://github.com/HKUDS/CLI-Anything/blob/main/shotcut/agent-harness/cli_anything/shotcut/utils/melt_backend.py
- shotcut-mcp limitations: https://github.com/NoBanks/shotcut-mcp
- VoiceStudio: https://github.com/debpalash/VoiceStudio
- VoiceStudio Windows installation: https://github.com/debpalash/VoiceStudio/blob/main/docs/install/windows.md
- VoiceStudio agent skill: https://github.com/debpalash/VoiceStudio/blob/main/skills/voicestudio/SKILL.md
- VoiceStudio platform API: https://github.com/debpalash/VoiceStudio/blob/main/docs/speech-platform.md
- VoiceStudio license notice: https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md
- OmniVoice model card: https://huggingface.co/k2-fsa/OmniVoice
- PocketTTS integration: https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/pockettts.md
- PocketTTS model card: https://huggingface.co/kyutai/pocket-tts
- OpenShot library: https://www.openshot.org/libopenshot/
- Kdenlive introduction: https://docs.kdenlive.org/en/getting_started/introduction.html
- OpenCut project status: https://github.com/OpenCut-app/OpenCut
- OpenTimelineIO: https://opentimelineio.readthedocs.io/en/latest/
- Remotion license/pricing: https://www.remotion.dev/docs/license/pricing
- FFmpeg licensing: https://ffmpeg.org/legal.html
