# November 20 finalization execution results

## Current verified result: completed local video, owner preview approved

The owner reported watching and approving the exact MP4 below. The private
`qc-real-final-v4/owner-preview-approval.private.json` binds that statement to
its SHA and the rendered project. No detailed listening observations are
invented. This approval **does not authorize publication**. PR20 is draft and
unmerged. Older blocked/pending entries below are historical evidence; never
rerun their bootstrap commands against the now-running service.

### Actual host and FORGE acceptance

The V5 owner bootstrap completed. The fixed standalone service runs as the
recorded limited owner, bound to127.0.0.1:39110. Its native startup receipt
records401 missing bearer,401 incorrect bearer and200 authenticated health with
the expected model/script/config/license provenance. Independent source/task/
receipt review passed. The dedicated nonadmin, key-pinned SSH health passed.

Private HTTPS9443 has normal CA/hostname TLS verification and literal private
address pins. FORGE status PASS; absent/incorrect bearer401; command/model/path/
voice fields400. Before/after Serve comparison shows only the new9443 proxy;
443/8443 and Gateway are unchanged, Funnel absent. The existing approved v5
policy and official ten-preview review were reused. An unauthorized-peer packet
probe was not performed; policy-level restriction is the recorded evidence.
The bearer was transferred only as an RSA-wrapped envelope and saved in the
owner-scoped VoxCPM2 Credential Manager namespace. Four nonsecret user variables
now point to the verified configuration; no token is in environment, Git or logs.

First real remote request `331bd2e40aff46b790256bf156204c12` returned48000Hz
mono PCM16/192000frames/4.00s, SHA
`b484dce32179e079b4b428d831e4294ea42839fdb99479747325e59c2aef9e46`.
Host and FORGE bytes match; reference/script pre/post hashes are unchanged.
This is `REMOTE_NARRATION_PASS`, not a fixture or file-copy substitute.

Actual installed Collector job `632b3b9a21b34e92a944aae80b478a81` succeeded
through the owner-session companion at attempt1. Its eight measured segments
are3.84/4.16/5.76/6.72/4.80/4.96/4.16/3.36s. All host/FORGE WAV hashes match;
joined PCM equals their exact concatenation. Body audio:37.76s,48000Hz mono
PCM16,1812480frames, SHA
`77a1448af4a4c4251afdd7498e19a93cb70735eb3917a2d0bd41a82ee3e070d4`.
Receipt SHA `c7703a97860fd3efd3b7b2e70385b11946e05ea0949834df6ec8caaa28b1cd11`.
Approved prior CUDA/bfloat16/import evidence is reused; this new run was not
separately instrumented for device/import tracing. Canonical settings/reference
and model revision were validated by the actual host manifest path.

### Actual final media

Vault: `C:/Admin/Projects/KnowledgeNetwork-Private/final-video-20261120-9a672d28298d400f803b234ee26d9d87`.
Paths below are relative to that vault.

| Artifact | Bytes / SHA-256 |
| --- | --- |
| `project-final-real-v4/knowledge-network-50s-local-review.mp4` |38590437 / `b77d0d341eabae4e36c38048673ea09269b0dfd00705062ad6691b87aa214fe8` |
| `project-final-real-v4/knowledge-network-review-v2.osp` |930165 / `033a328c119523b6fa764c79242f858a4df364509e81572c47a6a443952d88d9` |

Actual native project:24 editable clips, five independent layers, three body
scenes/three native effects, titles/lower thirds, animated graphics, eight
sample-derived captions and separate ducked music. Exactly48 intro frames,
1218 body frames and234 original portrait-outro frames:1500frames/50.0s.
Exact badge/outro source pins passed; the four-second preview was not inserted.
Original outro source, speech and gain1 are preserved. Save/reopen/real graphic
edit/save/reopen passed; final heading is “Verify the bytes. Check the source.”
Single export job `e98ae02ddd7640c1aaf5d5cddcc31ce4` completed at revision71.

PASS: both streams50.000000s;1080x1920/30/1FPS/1500decoded frames; H264/AAC48k
stereo; full decode exit0 and empty errors; no black interval at the recorded
threshold. One0.685s quiet interval at41.613–42.298 spans the final music fade
and original outro lead-in. Peak−5.88dBFS; integrated loudness−28.5LUFS. Signal
metrics do not substitute for listening. Seventeen exported representative
frames were inspected; root independently inspected intro, all three body
scenes/captions and original CTA. The owner subsequently approved the preview.

QC/launch instructions and exact source/timeline hashes are under
`qc-real-final-v4/`. The OpenShot GUI was left clean with the final project.
Keep the complete vault together and save future edits under a new version;
edits invalidate this exact render's approval. Local playback:

```powershell
Start-Process 'C:/Admin/Projects/KnowledgeNetwork-Private/final-video-20261120-9a672d28298d400f803b234ee26d9d87/project-final-real-v4/knowledge-network-50s-local-review.mp4'
```

### Program changes and remaining operational gate

The observed music ownership false-positive was JSON integer0→float0.0 on
position/start after native save/reopen. Retained pre-save native output matches
the original baseline; volume/keyframes were identical. The shared fix accepts
only exact integral numeric encoding equivalents, never rounded timing or gain
changes. Four new negative/positive tests and independent review passed. The
failed pre-mutation intent remains in place; a new reconciled output revision
was used. Original83aa/820f projects remain unchanged. Native autosave updated
the active preflight working project, but exact1283 bytes remain in its retained
recovery ZIP and an exclusive QC copy; no checkpoint data was lost.

The owner requested job-scoped model lifetime: load once, generate every
segment, unload after that job. Existing VoxCPM2 CLI batch is reused with the
same voice/settings, one owned process, strict complete-output checks, private
bounded logs, durable single-job/cue receipts, cancellation and uncertain-outcome
holds. Client recovery keeps legacy IDs; new batches require advertised support
and never fall back to repeated submissions. Model remains unloaded while idle.
Source/focused tests and isolated native process tests passed. **Live new-batch
parity/activation is not yet accepted.** The nonadmin bridge cannot update
administrator-protected code/task action. The reviewed updater is staged below.
No old V2 recovery, D: ACL alteration or extra server is required.

Full local supported regression:565 tests,546 passed/19 skipped in266.668s.
Initial hosted run44866552307 exposed the old cross-component fixture expecting
two host jobs; it was updated to exercise one real loopback HTTP batch, keeping
PCM/caption/idempotency assertions and asserting one executor call/host row.
Focused integration then passed. Hosted push44867598017 and PR44867601802
passed at536828a: Windows565/546 passed/19 skipped; Ubuntu565/458 passed/107
skipped; worker190 checks and native WPF build PASS. Durable synthetic logs and
hashes are retained in `KnowledgeNetwork-Private/ci-durable-44867598017/`.
New updater-only hosted acceptance is tracked separately after the final push.

Existing pipefix002 installer/hash/rollback and installed worker identity are
retained, without reinstall or rebuild. Isolated install/upgrade/rollback,
scheduled Assistant/reboot and separate Dot/CUA operation remain NOT TESTED.
Local-use/media rights review and actual manifest42f270ac…9d84 remain applicable;
kaldiio's tested inactivity is scoped, and dependency redistribution remains
uncleared. Original declarations/licenses/model/reference files are unchanged.

The owner requests cleanup after finalization under the permanent archive-only
policy. Archive inventory is bounded to confirmed superseded staging copies;
no cleanup move or deletion is claimed here. Active media, credentials, trusted
runtime, referenced receipts, original assets and rollback backups stay put.

## Current batch activation: one required elevated host step

The final updater source is `docs/collector/host-tools/Update-KnowledgeNetworkNarratorBatch.ps1`,
SHA `5002de3dd3680cbd89ab55915f211cf816e8d8c07b30e42ef049024b2413ba46`.
Independent security review PASS, including the final bounded private failure-log
change. Focused tests16:12 passed/4 opt-in native skipped in15.033s. The four
native cases were separately accepted before the diagnostic-only follow-up:
physical SQLite identity/mismatch/rename/writer contention; exact child/PID/raw
FILETIME/held-exit binding; PowerShell parsing; Restricted-policy captured,
SHA-verified strict UTF8 execution with negative controls. Fixtures are retained.

The exact seven-file bundle is staged on both computers with identical bytes:

- FORGE: `C:/Admin/Projects/KnowledgeNetwork-Private/narrator-batch-update-v1/`.
- Host: `D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-batch-update-v1/`.
- Private bundle SHA: `c372224c6299419ea4575cb303a640708ab3cbbcc696e9a017c01a66b1159a5d`.
- Checked command: FORGE stage's `Host-Narrator-Batch-Update.txt`; supplied to owner.

Run that captured-byte command once in Administrator PowerShell on BLACKHAT-BASE
as its recorded owner. The restricted SSH identity deliberately cannot perform
this protected task/code update. This is an OS privilege prerequisite, not a new
permission request. A failed/uncertain run must preserve `batch-update-v1` for
reconciliation; never rerun it or select another work directory.

The updater revalidates installed protected Python3.14.10 and37 runtime files,
original source/manifest/audio, exact task/owner/PID/raw creation time and the
same physical ledger under a held protected namespace. It commits its own idle
maintenance fence, retains a writer lock through confirmed old-process exit,
backs up the original consistent database/code/task/descriptors, then tests one
new two-segment batch under a Limited owner task. Only a successful complete
batch/process-exit/parity receipt permits capability activation. No route,
Gateway, firewall, canonical script/reference/model or old controller changes.
The original nine completed host jobs must remain intact. Idle model memory is
released by the owned batch CLI process exiting, not an always-resident model.

New task registration/switch, actual batch CUDA/parity, a real FORGE batch and
manual rollback remain **NOT TESTED live** until execution. A rollback is a
reviewed new-code configuration with batching disabled and a fresh startup
receipt directory, preserving the current database; never restore schema1 over
new schema2 records. Unknown task/exit/fence outcomes stay held for review.
The original working service and approved final video are preserved while this
step is pending. No media job is automatically retried.

## Historical execution log: earlier bootstrap commands are superseded

Everything below is retained development history. The standalone service and
final video now pass; earlier absent-root, missing-media and bootstrap commands
must not be treated as current instructions. Do not rerun V3/V4/V5 installation.

## V5 bootstrap: missing-task regression fixed

The V4 owner attempt reported FileNotFoundException/0x80070002. Native read-only
FORGE reproduction found the bootstrap's typed COMException catch misses the
actual FileNotFoundException returned for an absent scheduled task. The new
regression reproduced that failure before the correction and passes afterward.
Only the single GetTask lookup accepts the exact missing-file HRESULT; denied
access, other errors and existing tasks still block. Independent review PASS.
Without the original host stack, that exact host failure location is inferred.

PASS:5 standalone tests and48 combined standalone/host/client tests in27.651s;
retention preflight, command parse and private-stage permissions PASS. The
standalone root/task files remain absent and original controller task file
present. No host execution, service/route mutation, credential transfer, model
inventory or inference was performed during this correction.

Full hosted run44860391334 PASS for source `3f45dfee8b9b3764279630d4f217b0a60ab3dfd8`:
Windows517/500 passed/17 skipped in60.851s; Ubuntu517/412 passed/105 skipped in
8.326s; worker190checks and WPF build PASS. The Windows log confirms the new
native missing-task test passed. Durable synthetic ZIPs and SHA receipts are at
`C:/Admin/Projects/KnowledgeNetwork-Private/ci-durable-44860391334/`.

The corrected V5 source SHA is
`b75fd594a9a1af5d9b45e934589f53115b940f4632ae536e11321061370e8eb9`.
The bundle SHA remains
`8f91a5a90427fe051e59c6e8309ea0f946710988fdb8d97e8b6844d4a720d3c6`;
all four backend modules and the still-valid V4 proof are unchanged. Host stage:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-standalone-v5`.
Command/receipts are under the FORGE private root's `narrator-standalone-v5/`.
Proof expires **2026-11-21 05:05:49 UTC / November21 12:05AM Eastern**. Retain
all older stages as evidence; use only the V5 command in the recorded owner's
Administrator PowerShell. Its wrapper emits a script stack on failure. Do not
blindly retry uncertain mutations. Actual remote narration/final video remain
BLOCKED pending host acceptance; earlier app/editor/CI results remain applicable.

## Bootstrap retry: elevation gate and refreshed proof

The owner's V3 attempt stopped at the elevated/non-SYSTEM owner check, before
installation changes. The standalone root remains absent. No task, service,
route, ledger or narrator was changed by that attempt. The System32 working
directory does not establish administrator elevation. Use an Administrator
PowerShell window under the same recorded owner account, never SYSTEM or a
different administrator account.

The old proof expired before this reply. Fresh read-only capture/validation002
passed: same five device ID/address bindings, explicit empty routes, unchanged
approved v5 policy and ten byte-identical accepted previews. No policy write.
The source and six host-execution pins are unchanged. V4 refreshes only the
private proof and bound bundle; V3 is retained as attempt evidence.

- Host stage: `D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-standalone-v4`.
- Source SHA: `86c75d277f540b90a3cd7f63de53a9da4c71533e6ff883e5c5ecf40a661d5fe7` (unchanged).
- New bundle SHA: `8f91a5a90427fe051e59c6e8309ea0f946710988fdb8d97e8b6844d4a720d3c6`.
- Proof valid until **2026-11-21 05:05:49 UTC / November21 12:05AM Eastern**.
- FORGE command copy: `C:/Admin/Projects/KnowledgeNetwork-Private/narrator-standalone-v4/Host-Narrator-Standalone-Bootstrap.txt`.

Use only the refreshed command; never remove elevation, expiry or digest checks.
This is a native Windows privilege requirement, not a request for renewed owner
permission. All earlier app/body/CI acceptance remains applicable; real narration
and the final MP4 are still blocked. Publication PAUSED; PR20 draft/unmerged.

**Overall: BLOCKED on native BLACKHAT-BASE execution; final video NOT COMPLETE.**
Publication PAUSED. PR20 remains draft/unmerged. Continued the existing branch
from owner authorization `d7f571ce862c82562792719ed8fdada11a3673fa`, preserving
history. Validated application source: `f7ccdb43fa7d509eae636948fd7dce4c43434dcf`.
The old V2 narrator-controller repair is **DEFERRED**, not a prerequisite.

## Actual acceptance

| Stage | Observed result |
| --- | --- |
| FORGE services | Existing Tailscale and Collector services were stopped; started their existing verified installations. No reinstall or database replacement. |
| Installed worker | PASS: healthy windows_service context, stable worker `cb6ce3cd482148e7b8b0c8661ec8c6e9`, companion enabled, publication paused, production scheduler disabled. |
| Native WPF application | PASS:17 actual programmatic GUI checks in27.156s: real worker health/capabilities/research snapshot, durable echo/get/cancel, invalid input, named controls/focus order,1040x780 and800x600 rendered windows. |
| Collector to native editor | PASS: job `543e1edb7a694dda96995186431cadd3` reached the actual OpenShot session through the owner-session companion, completed at revision58 and worker state succeeded. Native receipt SHA `a58455657af83e433d84ab1cc896acc639ae68112ed602c7e27529befdcf6179`. |
| Research/content | Original evergreen “Verify the bytes” script, eight natural segments, original diagrams and original procedural music. Research: [NIST hash functions](https://csrc.nist.gov/projects/hash-functions). No current-news claim or third-party recording. |
| Editable native body | PASS: actual1080x1920/30FPS/1218-frame40.6s body,13clips, four used layers, three native Saturation effects, animated scale/fades, titles/lower thirds and separate music. Native frames1/120/500/1000 captured and inspected. |
| Native reopen/edit/save | PASS: restarted only the exact saved/idle owned editor, reopened the saved body, changed graphic text and saved a new native revision. Original project unchanged. |
| Host narration/API | BLOCKED: host tailnet peer is online, but dedicated SSH22230 times out. Redirected-drive access is file access, not execution. New standalone bootstrap is staged and reviewed, NOT EXECUTED. |
| Real WAV/remote receipt | NOT GENERATED. No new inference, transfer or `REMOTE_NARRATION_PASS`; prepared request IDs have not been submitted. |
| Branded50-second export | NOT COMPLETE: real narration/captions,48-frame dynamic intro and234-frame original outro are not attached to this body. No new MP4 exists. |

The dashboard's17 checks use its shown WPF window and actual automation peers;
PNG captures are rendered visual trees, not OS compositor screenshots. Computer
Use failed to enumerate windows even after one reset. No OS mouse/keyboard input
or separate Dot connection was verified. Manual Codex/user-context CLI acceptance
must not be relabeled scheduled Assistant reliability or human approval.

## Actual local artifacts

Vault:
`C:/Admin/Projects/KnowledgeNetwork-Private/final-video-20261120-9a672d28298d400f803b234ee26d9d87`

| Artifact relative to vault | SHA-256 |
| --- | --- |
| `project-revision-2/incomplete-body-v1.osp` (659200bytes, retained original) | `83aa5e5ff18d9ce7b8b351085fb0ccd5b5ebf370ec829a4b9d03b8b557449131` |
| `project-revision-2/incomplete-body-reviewed-v2.osp` (706943bytes, current body) | `820f8a3f0e41d844af7cdde654aba7111b93d7e500d5099357bbb9ce805161b0` |
| `project-revision-2/body-reviewed-frame-1000.png` | `e20f2b8a31d9b76e8098bf8c5c33015c553488463bde6238a1ce221c62f1aed1` |

Current native session `ead88b5f4ebe441983045e9c15809b9d`, process6856,
revision4, running idle at acceptance. Recheck identity/state before use. Resume
from `project-revision-2/body-state-reviewed-v2.json` and
`environment-reopened-v2.private.json`, not the old revision58/session.
`reviewed-body-acceptance-v2.private.json` and `body-technical-qc.private.json`
retain native evidence. Owner final mix/listening review remains PENDING.

Dashboard evidence: `KnowledgeNetwork-Private/dashboard-finalization-001`,
including17-check report and two PNGs. Native service-job evidence:
`KnowledgeNetwork-Private/collector-editor-finalization-001`.
Initial configuration failures are retained: missing transport directory, then
an isolated USERPROFILE that timed out the ACL probe. The earlier editor job
was definitively blocked before native dispatch; a correctly configured fresh
read-only job succeeded. No uncertain media operation was replayed.

Open the reviewed body through OpenShot's File/Open; it is **body-only**, not
the requested finished Short. The Collector's actual installed entry points are:

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
```

There is no verified complete50-second production command to advertise yet.
After genuine audio acceptance, existing `collector_final_short.finish` attaches
the exact receipt, measured captions/ducking, dynamic intro and unchanged outro,
then saves/reopens/revises/saves. Final export/QC remains a separate actual stage.

## One necessary host action

The owner has already authorized operations. The missing requirement is a native
execution capability, not more consent. One reviewed elevated owner bootstrap
was supplied in the pending owner question and saved at:
`C:/Admin/Projects/KnowledgeNetwork-Private/narrator-standalone-v3/Host-Narrator-Standalone-Bootstrap.txt`.
Host staging directory:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-standalone-v3`.

- Bootstrap SHA: `86c75d277f540b90a3cd7f63de53a9da4c71533e6ff883e5c5ecf40a661d5fe7`.
- Bundle SHA: `aa72b84f0eb62a7e2a56a6e6fa216d83b4ae567b5082a9ff03a33be9ea61eed3`.
- Captured source/bundle bytes are checked before use. The D: stage is transport,
  not trusted privileged execution storage.
- A new protected ProgramData code/private-data root and Limited InteractiveToken
  task reuse the current host implementation, protected Python and approved owner
  Credential Manager bearer. Old controller, ledger, spool and runtime stay intact.
- A live39110 collision stops before mutation. Missing/wrong bearer401 and valid
  health/provenance must pass locally before opening the private route.
- The exact existing dedicated SSH service may start once only if stopped and
  its service/image/config/module/listener checks pass. No Gateway change.
- Optional HTTPS9443 requires fresh pinned policy proof, host identity/address,
  native port availability and Serve collision checks; before/after evidence
  preserves443/8443. No Funnel, public firewall or generic administration API.
- The owner's bearer crosses only as an RSA-OAEP ciphertext for the dedicated
  FORGE recipient. No plaintext token in argv, files, chat or Git. FORGE private
  recipient key remains in its user Credential Manager, two bounded records.

The fresh proof expires **2026-11-21 00:23:34 UTC / November20 7:23PM Eastern**.
Expired evidence must be refreshed; never remove that check or alter pins to
proceed. A failed/uncertain bootstrap must be reconciled, not rerun blindly.
No live task, route, credential transfer or GPU result is implied by four passing
bootstrap contract/native ACL/RSA tests and independent security review.

Read-only audit PASS: five current devices and all ID/address bindings match the
accepted inventory; explicit advertised/enabled route arrays remain empty; v5
typed policy unchanged, stored SHA
`35697bcb6e06a9b2047d6056ab847fcff31f2d054ca8da7ba8e6a97222b10335`;
official validation passed and ten previews match accepted bytes exactly. No
policy write occurred. Sensitive raw API evidence stays in FORGE's protected
`C:/ProgramData/KnowledgeNetworkCollector-Finalization`; the existing validator
rejected the Projects ancestor chain, so it was not weakened. Normal diagnostic
reports/media/indexes remain under KnowledgeNetwork-Private.

Prepared but unsubmitted requests and provenance are under
`KnowledgeNetwork-Private/narration-finalization-001`. Preserve their original
IDs for submission/recovery. After bootstrap: verify actual startup/route/identity,
unwrap the bearer only in memory into the existing VoxCPM2 client namespace,
configure real route evidence, run status and one new short request, then the
measured body. Never substitute the old diagnostic or synthetic voice.

## Changes, retention and regression

All110 legacy teardown sites were migrated without removing assertions. Fresh
fixtures and explicit replacement faults retain owned outputs. Parent traversal
is rejected before any fault-helper IO. Companion transport files, dispatcher
output and retired voice markers remain retained. Full CI and source preflight
are restored; no global monkeypatch or archive sweep was introduced.

Native testing found and fixed cold-start timeout headroom, audio-reader rounding
(silent music-source tail; timeline still1218frames), and thumbnail self-audit.
Only startup gets90s outer headroom; normal commands stay40s/CLI25s. Exact own
thumbnail intent is checked with metadata/digest before/after; other pending work
still blocks. Known constructor failures now report blocked before claim; later
transport uncertainty is preserved.

Ten conditional installed OpenShot retention edits are active for the Collector
flag, preserving original sources, notices and security descriptors. Private
manifest/source/rollback evidence: `KnowledgeNetwork-Private/openshot-retention-review-v1`.
Latest `retention-v2.patch`:198lines/SHA
`430392e97cb3abe0256604e74b9c75ab90a07158d5799fb5667f6cf3e420f3a7`.
The first startup exposed one previously missed empty-cache-directory cleanup;
no original/project asset loss was observed. The corrected fresh startup logged
zero cache clears and zero backup deletions. This is scoped workflow review,
not a claim that every unrelated OpenShot subsystem was audited.

One exact saved/idle owned editor process was stopped for that correction; no
narrator process was touched. An initial check failed before any stop intent
because CIM lost six100ns ticks. Fresh native64-bit FileTime fixed the comparison
without tolerance or weaker identity checks. Both attempts' evidence remains.

No cleanup/archive sweep was run. The only observed removal was the newly
created empty cache directories noted above; no original/project file loss was
observed. Active
runtime/data, original assets, original five backups/intent/rollback, previous
denied cleanup targets and the four protected SSH authentication files remain
in place. New staging/fixtures are current evidence, not silently obsolete.
AGENTS retention/authorization sections and `/old/` ignore survived the ordinary
main merge; approved source binaries/pins remain unchanged. PR20 is mergeable
again at integration, still draft/unmerged.

[Hosted run44835027428](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/44835027428)
PASS for source `f7ccdb43fa7d509eae636948fd7dce4c43434dcf`:
Windows516 discovered/499 passed/17 skipped47.872s; Ubuntu516/412 passed/104
skipped7.738s; actual190worker checks and WPF build passed. Earlier failed
run44829308878 remains recorded (receipt selection and artifact-path errors,
subsequently fixed). Synthetic log/index artifacts have90-day server retention;
local durable copies are retained for owner review. No generated media, private
policy, consent or host logs were uploaded.

Ponytail FULL and independent security reviews were applied. Taste native visual
judgment was applied to actual frames/screens. UI/UX Pro Max was not installed;
no active-skill or browser-gate pass is claimed. No gratuitous UI redesign.

## Reused evidence and remaining limits

Original VoxCPM2 2.0.3/revision7936080b41163874f38610f46f438e2c0757f9fd,
script/reference/settings, approved3.04s CUDA diagnostic and owner listening
approval remain unchanged. Manifest SHA42f270ac…9d84 and local-use review are
reused; kaldiio/FunASR inactivity applies to the tested no-denoiser path, not all
possible imports. Dependency redistribution remains separately uncleared.
Exact badge/outro/preview originals are present; no repeated asset search or
model inventory/inference was performed. The preview is not a production intro.

Retained exact hashes (reused evidence, not a new smoke):

| Evidence | SHA-256 |
| --- | --- |
| Canonical script | `98b75e5313d72d7aa65d160b41ebcb8726968bb7044700e2cffb510b5a72f189` |
| Reference WAV | `050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44` |
| Private rights declaration | `bc7d82dac515aadd72c061eebf9088df138f1e9ec746dd9b1287914eb6ede006` |
| Reviewed local-use manifest | `42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84` |
| Owner-approved diagnostic WAV | `1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7` |

The earlier diagnostic is48000Hz mono PCM16,145920frames/3.04s, CUDA/bfloat16,
canonical exit0, owner-reported positive listening. No new listening claim.

Existing pipefix002 installer remains SHA
`4149bd4c66347429f65a570925bc158cbc36a8b752c36c741d1cfabf4439517a`
at `output/installer-v9-pipefix-002/The-Knowledge-Network-Collector-0.1.0-v9-pipefix-002-setup.exe`.
No rebuild/deployment over the working installation. Isolated install/upgrade/
rollback NOT TESTED; no ready disposable environment was established and the
FORGE Windows Sandbox executable is absent. Scheduled Assistant, reboot and
actual final-mix owner review remain NOT TESTED/PENDING. No reboot or upload.
