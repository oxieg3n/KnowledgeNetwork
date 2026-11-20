# Assistant operations — installed staging build

## November20 current acceptance

See [verified execution results](overnight/FINALIZATION-RESULTS-2026-11-20.md).
Installed service health and17 native dashboard checks passed; a real queued
editor inspect passed through the owner-session companion. The new editable
body is saved/reopened/edited, but has no real narration or bookends yet.
The complete50-second command is therefore not accepted. Host SSH is unreachable;
one reviewed independent limited-owner bootstrap is staged, with fresh route
proof expiry enforced. Old V2 recovery is DEFERRED. Publication stays PAUSED.

For the current body use the environment-reopened-v2/body-state-reviewed-v2
private records, not the historical session below. Companion transport spool
must already exist with its private protected ACL. Keep the normal Windows
USERPROFILE for companion validation; use its project-specific editor vault and
OPENSHOT_SESSION_DIR. Missing/invalid pre-claim configuration now reports blocked
without claiming an uncertain media dispatch. Later uncertainty still holds.
These are Codex/user-context manual results; scheduled Dot connection, separate
Computer Use and human final listening remain unverified.

Run on FORGE, not on Dot's cloud localhost or BLACKHAT-BASE. A real scheduled
Assistant connection remains unverified. Publication is paused.

## Verified installed commands

```powershell
$nonce = [guid]::NewGuid().ToString('N')
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health $nonce
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' capabilities
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' research-snapshot
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' get 131f54611e5a41c8b9e0d178b1a11dde
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
```

Use a new caller nonce. Supported service jobs are diagnostic.echo,
research.snapshot, narration.generate and editor.operation (inspect/apply/save/reopen).
The installed bridge is explicitly enabled. Native export remains a direct
source-client operation, not a queued service job. The snapshot is immutable staging
metadata, not a second production scheduler. Native install-service/remove-service
require elevation and the canonical installed path; ordinary queries do not.

## V9 direct VoxCPM2 development client

VoiceStudio is retired. Do not call its root URL, reuse its PIN, start its app,
or revive the V8 credential commands. The fixed default body voice is
Oxiegen-Narrator on BLACKHAT-BASE. Approved outro audio is unchanged.

Use the existing project virtual environment and pinned FFmpeg process PATH:
`$env:PATH = 'C:/admin/tools/ffmpeg-9.0.2/ffmpeg-9.0.2-full_build/bin;' + $env:PATH`.
The actual CLI syntax below was checked. `status` currently exits 1 with
`BLOCKED_NARRATOR_CONFIG`; no dedicated host route/credential is configured.
Host deployment/inspection instructions are in [host-narrator.md](host-narrator.md).
Forge's Tailscale peer check is not proof that a narrator API exists.

```powershell
Set-Location C:/admin/projects/KnowledgeNetwork
$env:PYTHONPATH = 'src'
foreach ($name in @('COLLECTOR_NARRATOR_PROVIDER','COLLECTOR_NARRATOR_BASE_URL','COLLECTOR_NARRATOR_ROUTE_FILE','COLLECTOR_NARRATOR_SPOOL')) {
    $value = [Environment]::GetEnvironmentVariable($name, 'User')
    if ($value) { Set-Item ('Env:' + $name) $value }
}
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 status
```

Only provider=voxcpm2_remote and the new private spool are staged. The base URL
and route must come from an actually deployed, owner-approved dedicated HTTPS
route. No old endpoint fallback exists. Keep the real URL and route evidence
outside Git. The route schema requires schema_version=1, base_url,
host_identity=BLACKHAT-BASE, transport=https, auth_mode=scoped_bearer,
pinned_addresses (verified private literals), verified_by, verified_at,
transport_evidence_sha256 and expected_provenance. Copy the exact four provenance
fields from the verified host manifest: script_sha256, config_sha256,
model_revision, license_evidence_sha256. Do not invent these values.

After deployment, configure the new nonsecret user variables and enter the
new app-specific bearer interactively (at least 32 characters):

```powershell
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 credential-save
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 status
```

This uses a separate VoxCPM2 Windows Credential Manager namespace. It never reads
the old consumption PIN. The owner-provided reference script is the identity
oracle: CFG2.0, 10 steps, no denoiser/optimization, local files only and compile
disabled. Installed script/reference/CLI hashes were matched by read-only redirected-drive
inspection. Actual selected model revision, rights and runtime parity remain BLOCKED.

A fresh original 98-word/13-segment demo script is staged privately at
`C:/admin/collector-v9/demo-script.private.txt` and
`C:/admin/collector-v9/demo-caption-segments.private.json`. It has not been submitted.
After actual status/provenance pass, this is implemented generation syntax;
its successful host execution is NOT claimed:

```powershell
$job = [guid]::NewGuid().ToString('N')
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 generate --job-id $job --text-file C:/admin/collector-v9/demo-script.private.txt --segments-file C:/admin/collector-v9/demo-caption-segments.private.json
```

For an intended cancellation, run
`& ./.venv/Scripts/python.exe -m youtube_ops.collector_voxcpm2 cancel --job-id $job`
as a separate operation.
Reuse the SAME job ID/text for recovery. A recorded submission intent recovers
by GET and never blindly reposts. Host-not-found after uncertain submission
requires reconciliation; do not generate a new ID as a retry. Unknown host
execution/storage failures hold the GPU queue until evidence is reconciled.

A successful generation writes `narration.json` and sibling `narration.wav`
under the configured private spool/job ID. The native fixture's actual
`--narration-receipt` option imports verified PCM and sample-derived cues into
its editable project. Real remote attachment/render remains BLOCKED until the
host route is deployed; a synthetic unit receipt is not narration acceptance.

## Copyable Assistant acceptance request

> Assistant, connect to FORGE and test The Knowledge Network Collector in LOCAL
> REVIEW-ONLY mode. Run a fresh nonce with
> `& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))`
> and verify the nonce and windows_service context. Read the current handoff and
> these operations instructions. Use only the direct authenticated VoxCPM2
> Oxiegen-Narrator service on BLACKHAT-BASE for body narration, preserving the
> existing narrator script/reference/settings and approved outro audio. Run the
> configured `youtube_ops.collector_voxcpm2 status` before speech. If the dedicated
> API, exact narrator/model evidence or approved badge/outro bytes are missing,
> report the exact blocker and preserve the project; do not substitute a voice,
> use VoiceStudio, forge evidence or claim a completed Short. Once verified,
> create a fresh editable 1080x1920 Short totaling 45-55 seconds, including the
> approved 1.6-second intro and 7.8-second outro exactly once each. Use original
> media, three body scenes, two visual layers, titles/lower thirds, graphic
> overlays, an animated effect, real returned speech, measured captions and
> separate ducked music. Save/reopen, revise a caption or graphic, export that
> exact revision, decode/QC and inspect frames. Report actual paths, duration,
> SHA-256, provenance and separate visual/listening results. Keep publication
> paused; do not upload to YouTube, GitHub artifacts or any public site.

This is an acceptance request, not a successfully tested complete production
command. Host transport, exact bookends and live narration and branded rendering remain blocked; the four editor
companion operations passed real service/native round trips. A Dot connection is also unverified.

## Actual user-session companion

Run from the project environment in the configured Windows owner's interactive
session; do not run as LocalService or SYSTEM. The companion is one-shot, not a
second scheduler. The service owns claims/leases/state; native receipts retain
private details. Current installed apphost SHA (managed DLL/build also verified):
`60516f07332facbbfa484cb5a2b4b430cc42c12128bc6525283e589b812e2754`.

```powershell
Set-Location C:/Admin/Projects/KnowledgeNetwork
$env:PYTHONPATH = 'src'
$env:COLLECTOR_EDITOR_VAULT = 'C:/admin/collector-v9/editor-vault'
& ./.venv/Scripts/python.exe -m youtube_ops.collector_companion --once --collector-sha256 60516f07332facbbfa484cb5a2b4b430cc42c12128bc6525283e589b812e2754 --private-spool C:/admin/collector-v9/companion-control
```

The prior build exercised narration's missing-config negative and all four
editor operations; the hash above now pins the installed pipe-authentication
patch. Those media round trips were not repeated for this IPC-only correction.
Private request files are submitted with
`kn-collector.exe submit <local-json-path>`, queried with `get <job-id>` and
cancelled with `cancel <job-id>`. See [bridge contract](COMPANION-INTEGRATION.md)
for exact typed payloads. Never fabricate an ID to retry an uncertain media job.
Interrupted media jobs hold further claims pending evidence reconciliation.

The existing inspector entry point is at host
`D:/projects/knowledgenetwork/collector-narrator-v9-004/Inspect-InstalledVoxCPM.cmd`.
Its inventory has PASSED; do not rerun completed inspection as routine setup.
No host command channel was used.
Do not configure the proposed host listener/HTTPS route until its manifest and
separate scoped deployment permission are established. Existing Gateway remains
unchanged.

## Inspector follow-up

The owner ran the repaired existing kit004 successfully. Its private manifest now
binds revision7936080b41163874f38610f46f438e2c0757f9fd and actual resolved shared
blob content hashes. Read [repair evidence](overnight/INSPECTOR-SHARED-BLOB-REPAIR.md)
for the exact rerun command and source/artifact checks. Do not repeat the earlier
claim that the selected model cache is wholly uninspected. Status still blocks
on undeployed narrator API and unresolved consent/runtime provenance gates.
Do not weaken pipe trust to resolve Assistant's reported untrusted_pipe_server;
actual Assistant context is required to identify the mismatch.

For the reported pipe failure, run this **from Assistant's actual FORGE client
context**, keeping output private. Do not substitute the developer shell:

```powershell
hostname
whoami /user
whoami /groups
(Get-Process -Id $PID).SessionId
sc.exe queryex KnowledgeNetworkCollector
sc.exe qc KnowledgeNetworkCollector
$collectorExe = 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe'
Get-FileHash -LiteralPath $collectorExe -Algorithm SHA256
$collectorService = Get-CimInstance Win32_Service -Filter "Name='KnowledgeNetworkCollector'" -ErrorAction Continue
$collectorService | Select-Object Name,State,ProcessId,StartName,PathName
if ($collectorService.ProcessId -gt 0) {
    Get-Process -Id $collectorService.ProcessId -ErrorAction Continue |
        Select-Object Id,SessionId,Path
}
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))
"collector_exit_code=$LASTEXITCODE"
```

Use the canonical EXE. The installed worker now uses SCM-first service identity;
the non-service path retains strict executable and user checks. Read
[the verified repair](overnight/PIPE-TRUST-REPAIR.md) for the original
OpenProcess/error5 failure, native medium-integrity PASS and owner-returned
Assistant-context healthy response. Scheduled Assistant execution remains untested.

The historical `pipe-squatting.json` negative fixture deliberately produced this
same error with zero request bytes; it is not Assistant's failure receipt. The
client validates the server before transmitting any health/job request. Trust
failures now include a fixed stage and numeric Win32 error without credentials
or private paths. Preserve the actual error/access-denied output above.
Do not elevate or change Assistant's token for
this collection, substitute the developer shell, copy the CLI, or disable trust.

Prepared owner-scoped narrator smoke and deployment gates are in
[next integration](overnight/NARRATOR-NEXT-INTEGRATION.md). Those commands have
not run on BLACKHAT-BASE; the passed inventory must not be repeated as a setup
prerequisite. Consent and component obligations remain separately reviewed gates.
