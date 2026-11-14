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

## Actual local results for this repair

- Windows Python 3.13 project venv: 302 tests in 57.983s, OK with five explicit
  FFmpeg-unavailable skips. Private log: C:/admin/collector-v9/ci-review-python.log.
- Worker locked restore and Release build with win-x64: PASS, zero warnings/errors.
  Initial restore without the runtime identifier failed NU1004; CI was corrected
  to use the already-required identifier from Build-Release.ps1 rather than
  regenerating the lock or weakening locked restore.
- Existing worker self-test: PASS, 163 checks. Isolated temporary evidence:
  C:/Users/oxieg3n/AppData/Local/Temp/kn-collector-self-test-7695b92601d74f9a9357bdcde0b321ae.
- WPF dashboard Release compilation: PASS, zero warnings/errors; no UI acceptance
  or installed-app rebuild/upgrade is implied.
- git diff --check: PASS. Ponytail FULL review skill read/applied; no findings in
  fixed workflow commands, source-only job isolation, permissions or pinned action
  use. actionlint/YAML parser is not installed; hosted syntax/execution remains
  NOT TESTED until the coordinator pushes the integrated commit.
- Exact main blob bytes adopted for the three V8 notices in source commit
  2e295ea. Non-mutating merge-tree against origin/main c41ec1 returned exit0 and
  tree 5f44e29003189a3f61d4a214d22744e083104966 with no conflicts. This proves
  those notice updates remove the observed add/add conflicts; no merge occurred.

No Linux runner was available locally. Windows CI uses Python3.12, so the local
Python3.13 result is supporting evidence rather than exact hosted parity. Root
should inspect the first actual hosted runs and any explicit skips before
reporting CI success.

## First hosted run and Windows fixture correction

After integration, hosted Linux passed. The first Windows Python job
[132608484897](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43647509991/job/132608484897)
failed: 302 tests,18 failures/16 errors/5 skips. Dependency installation passed.
The actual runner TEMP used C:/Users/RUNNER~1 while resolve() yielded
C:/Users/runneradmin. Synthetic inspector fixtures mixed those lexical and
canonical roots, causing snapshot_escape before their intended containment
assertions. The editor fixture similarly wrote noncanonical fake receipt paths
and expected noncanonical native arguments. This is fixture setup, not evidence
that the already-passed BLACKHAT-BASE inventory failed.

Correction canonicalizes existing temporary roots before building synthetic
files, links, receipts and expected paths. All containment, link-change,
file-identity, redaction and exact-hash assertions remain intact. No test was
skipped or weakened; production inspector/kit and editor source are unchanged.

Focused local verification:24 inspector tests PASS and31 editor tests PASS.
A separate fresh directory was given a distinct real Windows 8.3 alias using
GetShortPathNameW; both suites were rerun with TMP/TEMP set to that alias,
all55 PASS. Private evidence: C:/admin/collector-v9/ci-short-alias-fixed.log.
This exercises the observed path mismatch without a host model inspection,
new model inference, host settings, or network changes. Hosted Python3.12 rerun
remains necessary after integration; local verification used Python3.13.

Full local regression under a fresh distinct real 8.3 TMP/TEMP alias also
passed:302 tests in41.151s, five FFmpeg-unavailable skips, no failures/errors.
Private log: C:/admin/collector-v9/ci-full-short-alias-fixed.log.
Ponytail diff review found no production changes, relaxed assertions or new
framework; changes only establish canonical fixture roots and retain the actual
hosted failure and correction evidence.
