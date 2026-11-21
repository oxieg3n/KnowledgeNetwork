# V9 client and native video preparation

November15,2026. Source reviewed at `18006d9df188a486ee334f484fe4d9daf6d75ffc`.
This is preparation, not an executed narration/render receipt. No GPU job,
credential entry, service/route change, editor launch or media export ran here.
Publication remains PAUSED; PR20 stays draft/unmerged.

## Actual gates before the first remote request

The dedicated SSH endpoint passed real FORGE acceptance for health, fixed
PowerShell self-test and native-port diagnostics. Its four-operation scope does
not supply narrator-owner Credential Manager access, an
authenticated narrator handler, file transfer or unrestricted PowerShell.
HTTPS9443 remains blocked by the reviewed broad all-peer tailnet permission.
A free native port does not satisfy that separate access-control prerequisite.

The approved no-denoiser host smoke and owner-reported listening approval are
reused, tied to WAV `1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7`.
The [active-runtime review](V9-ACTIVE-RUNTIME-REVIEW.md) separates fixed private
execution, generated commercial audio and redistribution. The existing selected
model/reference/script/declaration evidence and inactive-denoiser trace remain
applicable at that scope. Narrator dependency redistribution is not cleared;
publishing is not authorized. Do not invent a new rights failure merely because
remote deployment is unfinished, or bypass a real unresolved integrity check.

Read-only FORGE user-setting inspection found provider and spool configured,
but no base URL or route-file setting. Thus no real remote request was attempted.
Before speech, configure the existing client with the actual independently
reviewed HTTPS origin/private address pins, restrictive policy evidence and
exact validated host provenance. Enter the dedicated bearer through the existing
hidden FORGE credential prompt under the intended owner's user account. Do not
copy it from another user's CredMan via the diagnostic SSH identity or print it.

`collector_voxcpm2.py` verifies private address pins, normal TLS hostname and
certificate validation, fixed service/narrator identity, expected provenance,
host outcome, returned audio metadata/digest and fully decoded PCM. POST has
one transport attempt; saved submission intent subsequently recovers by GET.
There is no VoiceStudio or synthetic-audio fallback.

## Prepared first one-job acceptance command

The following uses actual existing CLI syntax. It is gated and NOT EXECUTED.
Run only after route/credential review. It records one job ID and exact text
before submission; do not rerun the directory-creation block to retry a job.

```powershell
Set-Location C:/Admin/Projects/KnowledgeNetwork
$env:PYTHONPATH = 'src'
foreach ($name in @('COLLECTOR_NARRATOR_PROVIDER','COLLECTOR_NARRATOR_BASE_URL','COLLECTOR_NARRATOR_ROUTE_FILE','COLLECTOR_NARRATOR_SPOOL')) {
    $value = [Environment]::GetEnvironmentVariable($name,'User')
    if (-not $value) { throw 'Reviewed narrator configuration is incomplete.' }
    Set-Item ('Env:'+$name) $value
}
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 status
if ($LASTEXITCODE -ne 0) { throw 'Stop: actual host health/provenance is not PASS.' }
$acceptance = 'C:/admin/collector-v9/remote-acceptance-001'
if (Test-Path -LiteralPath $acceptance) { throw 'Preserve existing acceptance evidence; recover its original ID.' }
New-Item -ItemType Directory -Path $acceptance -ErrorAction Stop | Out-Null
Set-Acl -LiteralPath $acceptance -AclObject (Get-Acl -LiteralPath C:/admin/collector-v9/inspector-provenance)
$job = [guid]::NewGuid().ToString('N')
$textFile = Join-Path $acceptance 'request.private.txt'
[IO.File]::WriteAllText($textFile,'This is a private Knowledge Network remote narration test.',[Text.UTF8Encoding]::new($false))
[ordered]@{job_id=$job;text_file=$textFile;text_sha256=(Get-FileHash -LiteralPath $textFile -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $acceptance 'submission.private.json') -Encoding UTF8
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 generate --job-id $job --text-file $textFile
if ($LASTEXITCODE -ne 0) { throw 'Preserve the original request/ID and reconcile; do not create a new ID.' }
```

Omitting `--segments-file` creates one host job. Its host ID equals the recorded
collector ID. The prepared full98-word/13-segment demo is a later acceptance run:
13 segments mean 13 sequential canonical script/model loads, not one warm GPU
call. The first short test is not the full video narration.

After an uncertain submission, load the saved record and use the same exact
text, ID, route and provenance with the same `generate` command. Do not regenerate
the ID or edit the text. The client validates `request_sha256`; a recorded host
intent is recovered by GET and is never blindly POSTed again. `NARRATION_NOT_FOUND`
after uncertainty requires host reconciliation, not a new request. Completed
local evidence is verified and returned without another model run. Terminal
failure, cancellation, execution hold or provenance mismatch must not be bypassed.
For deliberate cancellation only, the real syntax is
`python -m youtube_ops.collector_voxcpm2 cancel --job-id <recorded-id>`.

Keep the client spool's `request.json`, `narration.json`, `segment-00.wav` and
`narration.wav`. Save the actual completed host job receipt through the existing
authenticated GET `/v1/narrations/<recorded-id>` when available; the public CLI
does not invent a separate `get` subcommand. The provider already verifies that
GET result and downloaded segment. `segment-00.wav` must match the host's exact
audio SHA-256/bytes/PCM envelope. The final `narration.wav` is joined through
Python's WAV writer; its container hash may differ while its PCM matches. Record
both hashes rather than assuming container identity. For a segmented demo,
preserve every host ID/segment digest plus the joined receipt/cues.

Only record REMOTE_NARRATION_PASS after actual host completion, real HTTPS WAV
download, matching host/local segment hashes, decoded frames/duration and exact
provenance. File copying the old host smoke is not this evidence. The new output
and final mix need their own owner listening review.

## Exact branding inputs already available

Reuse retained recovery/QC receipts; no repeat download or full source rehash was
needed in this preparation. Source files remain outside Git on this branch.

| Input | Local retained original | Existing approved SHA-256 |
| --- | --- | --- |
| Badge | `C:/admin/collector-v9/approved-badge-main-74224b5cc1b1/Neon Cosmic Oxieg3n Emblem.png` | `5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54` |
| Portrait outro | `C:/admin/collector-v9/approved-brand-main-0ec0c05cb2fa/Powered-By-Outro-Portrait.mp4` | `62496803360e377d81ab54b6970d94fcce3eee125f5d22c2fe08377dcf1b5c9b` |
| Landscape outro | same directory, `Powered-By-Outro-Landscape.mp4` | `3720a160cd8acb46c828d448cca740252fb8c6a80eba892f1573dc5b56479ee3` |
| Intro reference | same directory, `Powered-By-Plasma-With-Sound-Preview.mp4` | `1eeec90cda8dec320e078e77d5a6c4b6034be6e9dd07e00220ccc601f688e781` |

Both outros are7.8s/30fps/H.264/AAC48kHz stereo in the correct1080x1920 and
1920x1080 orientations, with full decode and existing outro validation already
passed. Preview is4s portrait. Badge is1254x1254 RGB and passed PNG/intro checks.
The preview is reference-only. Generate the approved48-frame production intro
with the exact badge, dynamic title and actual first native body frame through
`intro.render_intro`; never substitute the4-second clip. Import the unchanged
portrait outro with original CTA/audio, rather than resynthesizing it.

## Editable native plan after real receipt acceptance

The installed console executable was independently rehashed in this preparation:
`C:/Program Files/OpenShot Video Editor/openshot-qt-cmd.exe`, SHA-256
`3637d631e5b01f263c87e7bbc0c9d3dd5b75274f7489bd2f56da8940ce292ca7`.
It matches the retained managed-session pin. No new native session was started.
Create a new private vault/project directory; do not reuse or overwrite
`service-v9-reviewed-edit.osp` / `service-v9-local-review.mp4`.

The existing fixture accepts `--narration-receipt`, supports measured cues,
ducking, text/effects/layers, save/edit/save/reopen, and remains a fixed50-second
**unbranded** body. It can provide the first intermediate narrated local review
project from a real receipt. It cannot be labeled the complete branded Short.
Receipt and WAV must be materialized as new hash-verified files inside the
private editor vault, since `OpenShot.local_path` rejects outside-vault paths.

For the50-second final target at30fps:

| Interval, half-open frames | Seconds | Native content |
| --- | --- | --- |
| `[0,48)` |0–1.6 | One exact-template dynamic intro |
| `[48,1266)` |1.6–42.2 |40.6s/1218-frame editable three-scene body |
| `[1266,1500)` |42.2–50 | One234-frame approved portrait outro |

Measured narration must fit the available body interval. Do not cut speech,
alter rate/voice or silently exceed the target. A longer measured narration
requires a reviewed retiming/revision or a different permitted45–55s target.
Scene boundaries should align with measured semantic cue boundaries, keeping all
three scenes meaningful; estimated speech duration is not alignment evidence.

Attach narration/cues at body-zero first. The attachment helper places speech
and captions at zero and protects music/caption fingerprints; calling it after
offsetting the complete timeline would undo correct placement or reject ownership.
Then shift every body visual/text/speech/music/caption clip by48 frames, using
the exact revision and owned clip references. Caption sample boundaries are
rounded to the nearest native frame, then add48; store sample-to-frame evidence.
Keep captions out of the bookends. Long cues over96characters or more than one
newline are explicitly blocked by the existing attachment helper; segment them
during actual speech generation, not by inventing word timestamps afterward.

Retiming must also rebuild the existing50s fixture's position16/33 scene edges,
end50 clips, overlay keyframe49 and music fade/restore points. Trim only owned
visual/music ranges, preserve manual edits and clear/rebuild only owned volume
curves. Separate background music starts at1.6s, stays ducked through measured
speech, restores only after its real end where space permits, and fades to zero
before42.2s. No background bed overlays intro/outro audio. Preserve source speech
and approved CTA and inspect the final combined mix separately.

Use existing native `file.import`, `clip.add`, `clip.set`, `text.add/set`,
`clip.keyframe.set`, `clip.fade` and effects operations. Body remains multitrack;
the rendered intro component is not a flattened replacement for the editable
body. Save revision1, reopen through its retained save/hash receipt, revise one
caption or graphic, save/reopen revision2, then export that exact snapshot with
`end_frame=1500`. The actual adapter CLI is `collector_editor ... <operation>
--request <private-json>`; `apply` takes `{commands,base_revision}`, `save` takes
`{path}`, `reopen` takes `{path,sha256}`, `export` takes `{path,end_frame}` and
`export-status` takes `{job_id}`. Record the native export ID before polling;
never restart an uncertain export under a fresh ID.

Fresh acceptance must decode all exported audio/video, measure1080x1920/30fps/
45–55s, verify audio presence and bookend count/offsets, scan black/silent spans,
inspect representative frames and preserve project/export/receipt hashes. Owner
visual/listening approval is separate from automated QC.

## Smallest missing integration and review limits

No client provider rewrite is justified: its current route, idempotency and WAV
validation contracts are reusable. Actual route/auth/narrator execution remains
the upstream blocker. Once a real receipt exists, bounded orchestration must
retime and assemble the final native project. Current affected interfaces are
`collector_editor_fixture.build`, `attach_narration_to_fixture`, `OpenShot.apply/
save/reopen/export`, `intro.render_intro`, `outro.verify_outro` and
`collector_narration_receipt.read_voxcpm2_receipt`.

If source changes are needed, the smallest dedicated acceptance helper should
reuse those calls and their ownership/revision checks. Existing fixture callers
are its CLI and `tests/test_collector_editor.py`; keep default50s technical
behavior and historical receipts unchanged. New tests should cover sample/frame
offsets, body-duration fit, no duplicate bookends, ducking endpoints and refusal
to overwrite manually changed captions/music. A helper must not create a second
timeline, bypass receipts or forge remote provenance. No helper was added while
real inputs and transport remain blocked; root must approve exact code scope.

PASS: connected source/interface review, retained asset evidence and current
OpenShot binary pin. Prepared commands were syntax checked without execution;
frame arithmetic checked exactly. No runtime source changed, so no repeated
whole test/render suite. Ponytail FULL/review applied to reuse, claim boundaries
and missing actual acceptance. No UI changed and no new design/browser gate is
claimed. NOT TESTED: configured real status, new request/receipt, live caption
attachment, native retiming/intro generation/final export or final listening.
