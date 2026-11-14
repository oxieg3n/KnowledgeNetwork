# PR #20 integration and software CI

Observed November 14, 2026. PR #20 remains draft and unmerged. Publication remains PAUSED.

## Exact cause of absent checks

GitHub reported head `6a76f4495f56f4a101b818ed715feec75da1f75a`, base
`c41ec1e8cf05ef1dfc8388d5965f1888aaff492f`, mergeable `CONFLICTING`, merge state
`DIRTY`, and empty statusCheckRollup. The Actions API returned zero runs for
that head. Actions is enabled; main's Software validation run
[43641560374](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43641560374)
succeeded. This is not an Actions outage or disabled repository.

The existing push trigger covered only main and feat/video-operations, excluding
feature/collector-v7-overnight. GitHub suppresses pull_request workflows while a
PR conflicts, as documented in its
[event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request).
Draft state alone does not explain this absence. No elevated pull_request_target
trigger is needed or permitted.

## Exact conflicts and safe integration

Non-mutating command run from the feature checkpoint:

```powershell
git merge-tree --write-tree 6a76f44 origin/main
```

It returned three add/add conflicts and no source-code conflicts:

- docs/collector/v8/REMOTE_VOICESTUDIO_ARCHITECTURE.md
- docs/collector/v8/RESUME_FROM_FORGE_CHECKPOINT.md
- docs/collector/v8/START_HERE_RESUME_CODEX.txt

Each main version differs from the feature version only by a two-line prefix
marking VoiceStudio narration superseded by V9. Preserve main's prefixes and the
identical historical body. This retains checkpoint rules and avoids reviving the
retired narration architecture.

Root coordinator integration strategy: first inspect current origin/main and
recheck these diffs, because the base can advance. On a separate reviewable
feature worktree, adopt those exact main document versions and commit normally.
Re-run merge-tree before considering any merge. Source checks on the feature
head do not prove the eventual merge result. If an integration merge is later
needed, use a normal reviewed merge commit with explicit conflict inspection;
never rebase shared history, force-push, auto-merge, or replace main. This
investigation performed no merge and changed no branch protection/settings.

## Minimal CI repair

Software validation now also triggers on pushes to the existing implementation
branch. That permits read-only source checks even while conflict resolution is
under review. The existing Python tests run on Windows and Linux with the
existing pinned Pillow/numpy dependencies and package-defined Windows tzdata.
A Windows job uses global.json's exact .NET SDK, locked worker restore, worker
build and its protocol/persistence/denied-operation self-tests, plus WPF dashboard
compilation. setup-dotnet v5 is pinned to official upstream commit
26b0ec14cb23fa6904739307f278c14f94c95bf1, resolved via GitHub's tags API.

Permissions remain contents:read; checkout credentials are not persisted.
control.yml, production settings, scheduled coordination, service installations,
Gateway, host routes and publication controls are unchanged. No secrets, media
artifacts, real narration, editor GUI, host model load or sustained render job is
added. Existing tiny synthetic FFmpeg test fixtures run only when tools exist;
missing tools/platform cases remain explicit unittest skips. Hosted software
checks are not native editor, CUDA, licensing, listening or full Short acceptance.

## Validation boundary

Hosted workflow execution is pending root integration and push; no hosted PASS
is claimed here. Local validation results are recorded in the integration
handoff. Review checked immutable action pins, read-only permissions, fixed
commands, no caller-controlled shell arguments, no new service or scheduler,
and reuse of existing tests rather than a new test framework.
