# The Knowledge Network Collector: V7 unattended overnight handoff

Repository: https://github.com/oxieg3n/KnowledgeNetwork
Prepared November 13, 2026. Target: existing designated Windows VM.

## Start Codex here

Paste all text from [START_HERE_CODEX_OVERNIGHT.txt](START_HERE_CODEX_OVERNIGHT.txt) into Codex CLI opened in this repository on the VM. Codex is expected to read and execute:
1. [OVERNIGHT_BUILD_DIRECTIVE.md](OVERNIGHT_BUILD_DIRECTIVE.md), the new V7 unattended autonomy/recovery/morning-handoff policy.
2. [V6 master directive](../v6/CODEX_THE_KNOWLEDGE_NETWORK_COLLECTOR_V6.md), the full detailed product requirements.
3. [Open-source reuse study](../v6/COLLECTOR_OPEN_SOURCE_RESEARCH.md), refreshed against installed tools.
4. [ASSISTANT_END_TO_END_TEST.md](ASSISTANT_END_TO_END_TEST.md), the exact safe local demo to prepare for owner testing.
5. Live repository source, operations/publishing policies, rights controls, branding documents and tests.

## Owner setup assumptions

- Windows VM is running, network-accessible, with sufficient space for development/media/model caches.
- Codex CLI and Git are ready in the VM and Codex is explicitly running with owner-selected YOLO/full-access mode.
- **VoiceStudio for Windows is ALREADY INSTALLED and must be reused, never reinstalled by default.** The owner may start it before sleep; Codex should check/start existing local backend if needed, without resetting profiles/models.
- ChatGPT desktop may be signed in on the VM; Codex must test whether the existing Dot 'Assistant' actually has computer access. A signed-in desktop app alone does not prove this.
- The host machine and VM must stay awake; a suspended host also suspends VM development.

## Scope and protections

V7 overrides V6 startup assumptions and allows broad unattended local setup/testing/install work in the designated VM. It does NOT lift rights, OAuth, publication pauses, approval, security, or licensing gates. Codex must not publish demo media. It should attempt extensive independent work and deliver honest partial results if externally blocked. Work must happen on an isolated feature branch, without overwriting running project state or modifying the separate poweredby website.

Use specialized agents in parallel for independent source work, but serialize shared VM/Windows installs, database migrations, graphics/voice model loads, installer tests and heavy renders. Preserve Git history, active unrelated sessions, existing approved renders, and brand assets.

## Morning handoff

Codex writes docs/collector/overnight/HANDOFF.md on its implementation feature branch and provides installer paths, hashes, actual tests/results, remaining blockers and a specific tested Collector command interface, plus an exact message you can give Dot to create a 45-55 second 9:16 Short using new editing capabilities, VoiceStudio narration, subtitles, graphics, effects, audio mixing and approved plasma intro/outro.

The template for the owner-facing request is [ASSISTANT_END_TO_END_TEST.md](ASSISTANT_END_TO_END_TEST.md). It explicitly forbids public uploads during the test.

This documentation was committed to the public repository to direct Codex. It does not represent a completed installation, actual scheduled Assistant connection or finished editing workflow.
