# V9 handoff - The Knowledge Network Collector

Updated November 14, 2026. Publication remains **PAUSED**. No demonstration or
other media was publicly uploaded. Production workflows/permissions and the
separate poweredby repository were not changed.

## Outcome and checkpoint

Continued the existing `feature/collector-v7-overnight` branch from original
checkpoint `8c0e7f0`, retaining the V8 checkpoint `8403136`, all helper worktrees,
assets and history. Non-destructively fetched origin/main `1db0530` and read its
AGENTS/V9 master/architecture instructions. V9 supersedes VoiceStudio narration.
No reset, reclone, new repository, force push or merge into main occurred.

Installed worker source checkpoint: `6f34384f7c77437c74c7a178ce6be0642a75bbbb`.
Subsequent commits finish documentation; consult `git log` for the exact final
handoff commit. A noninteractive push lacked credentials earlier; no review PR
was created. Review preparation is local, not a claimed GitHub URL.

The service now dispatches narration and four bounded native editor operations
through an interactive-user companion. Actual inspect/apply/save/reopen and
synthetic export passed. Direct VoxCPM2 host/client implementation and negative
security/recovery tests passed locally. **No real V9 host speech was generated.**
A complete narrated/branded Short remains BLOCKED, not accepted on mock evidence.

## Installer and launch

Existing, installed unsigned staging installer (0.1.0):
`C:/Admin/Projects/KnowledgeNetwork/output/installer-v9-round5/The-Knowledge-Network-Collector-0.1.0-setup.exe`

SHA-256: `58b73fd62cb3a2997e12b801a88686a6854bfa1421c67cd027b1b0c6dba9da5d`.
Actual Round5 upgrade exited0 and preserved companion enablement and jobs.
Self-contained .NET runtime/notices/licenses are packaged. Python source clients,
OpenShot, models and owner media are not bundled; this is not a standalone full
studio acceptance. No signing certificate is claimed.

Installed CLI: `C:/Program Files/The Knowledge Network Collector/kn-collector.exe`
SHA-256: `70ff38e9c81a6b7f2617f94fe6ad262fb734d45e867674429023d57242020a76`.
Managed DLL: same directory `kn-collector.dll`, SHA-256
`5b16b7ce9bd14b3ec7f58acf2847f5a973e007db261a091c5d683e6a53f859a5`.
Dashboard apphost SHA-256:
`4d38514a5d64e1cfe61b5ffe50a1a033884eda48880968e69d581b780889d667`.
Dashboard DLL SHA-256:
`9ea6504a1967707237c38e9a664905decabcf82cd924d92fb983bf39f3cdf19a`.
Complete installed hashes: `C:/admin/collector-v9/final-package-hashes.json`.

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' capabilities
```

Repair by rerunning this installer elevated as the configured owner, or using
canonical CLI `install-service`. Explicit `--enable-companion` and
`--disable-companion` are supported; noflag preserves the setting. Removal
preserves data. Upgrade now preserves the flag through Inno's remove/reinstall.
No PowerShell execution policy was bypassed or changed.

## Worker, recovery and backups

Service KnowledgeNetworkCollector: Running/Auto/LocalService. Stable worker ID
`cb6ce3cd482148e7b8b0c8661ec8c6e9`. Final health reports windows_service, companion
true, reconciliation hold false, publication_paused true and scheduler false.
Typed jobs: diagnostic.echo, research.snapshot, narration.generate,
editor.operation. Editor ops: inspect/apply/save/reopen. Queued export is disabled;
remote narrator readiness is explicitly false. Health is not a Dot connection.

Actual service restart retained all five sampled V9 job records/results exactly:
`C:/admin/collector-v9/native-final-restart.json`. Upgrade retained the original
three V1 jobs/IDs/hashes and worker identity. Schema2 uses consistent verified
pre-migration backup before changes, durable leases and media outcome-unknown
holds; no automatic replay of uncertain edits/speech. Read-only jobs can recover.

Final consistent SQLite backup (integrity_check=ok):
`C:/admin/collector-v9/worker-final-v9.sqlite`, SHA-256
`daca19da767c1ce7fd1a3149db358d42e31f0c3745ce42dc76f3f4e21f0adf4b`.
Automatic pre-v2 backup:
`C:/ProgramData/KnowledgeNetworkCollector/jobs.pre-v2-7f166ba07afc4dc099b17e46cc548f88.sqlite`,
SHA-256 `8456232e1201345733a877dac4545c8b0ac2ddafa3a4b8ba309fd374c5c554be`.
V1 cannot read schema2: rollback requires deliberate backup/outcome review, never
blind restore/replay. Reboot, locked/signed-out session and scheduled Dot access
remain NOT TESTED. Prior V8 uninstall/reinstall proof is preserved, not rerun V9.

Original verified backup `C:/admin/collector-backups/20261114-073652` untouched.
Its Git bundle was rechecked: SHA-256
`c09bd03678201fe4576e746246c7709ba32dbdc2b6b2c7992872f4c9367659cd`.
This is not a new rehash assertion for every original backup file.

One real negative fixture exposed OWNER RIGHTS ACL compatibility in Python3.13
private temp files. Completion was denied and lease expiry correctly held the
queue. Fixed at the shared ACL validation. Root reconstructed that this specific
synthetic job had never reached POST (missing provider route, no durable intent)
and performed a single stopped-service/exclusive-lock, backed-up reconciliation;
no other rows changed or generic clear/replay endpoint added. Original failure,
backup and assessment remain private:
`native-companion-roundtrip.json`, `fixed-negative-job-reconciliation.private.json`
(assessment SHA `c9cc45ed9860976ced83d8074ba9d1123ddb632cd05b75e236691d17155b5da2`).
The original child stage was not captured; reconstructed evidence is not called
a direct original provider observation. Normal production hold reconciliation
still requires operator evidence and remains a usability limitation.

## V9 narrator: observed facts and remaining gate

Read-only redirected `\\tsclient\D` access matched existing host bytes:
- canonical narrate.ps1: `98b75e5313d72d7aa65d160b41ebcb8726968bb7044700e2cffb510b5a72f189`
- reference.wav: `050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`
- voxcpm.exe: `582115086868288000249adebbdfbf2de7db8392534d760fa9675ad9b0217492`

Installed metadata: VoxCPM2.0.3, Python3.11, package Apache-2.0. Preserve fixed
Oxiegen-Narrator identity and exact script configuration: CFG2.0, ten steps,
no-denoiser, no-optimize, local-files-only, TORCH_COMPILE_DISABLE=1. Script,
reference and installed model files were not modified. The old reference is not
new narration and was not listened to. Model selected checkpoint/revision,
component license evidence/reference rights and runtime Python parity remain
BLOCKED. The owner-run old inspector returned a generic failure; cause is unknown.

The restricted loopback host service uses canonical script runner first. Direct
persistent Python model loading remains gated on verified runtime parity. It has
authenticated bounded routes, one GPU queue, durable idempotency, exact manifest
and artifact checks, no arbitrary command/path/voice/model API, process-tree
cancel/timeout and restart/storage-fault holds. Forge uses HTTPS/certificate and
private-address pins, scoped CredMan bearer, socket deadline and PCM/hash checks.
VoiceStudio app/API/PIN are retired and never used as fallback.

No host process, scoped key or dedicated HTTPS route was installed/configured;
no host screen or general execution channel used. Gateway and existing Tailscale
routes remain unchanged. Only new project kit files were placed with permission.
Latest kit is staged/readback-hash verified, **NOT EXECUTED**, at:
`D:/projects/knowledgenetwork/collector-narrator-v9-004` on BLACKHAT-BASE.
Owner next command when available:

```powershell
& 'D:/projects/knowledgenetwork/collector-narrator-v9-004/Inspect-InstalledVoxCPM.cmd'
```

Local ZIP:
`C:/Admin/Projects/KnowledgeNetwork/output/The-Knowledge-Network-Collector-Narrator-V9-004.zip`
SHA-256 `1ca74b22892fd13b138c3b804d5dd03005ef14a5d2dd9201fe47edd07bcec563`.
It contains no model/voice/key. Inspector reads/hashes installed files and creates
only a new protected private report. No inference/download/route changes. Older
kits002/003 and owner's differently spelled project folder remain intact.

Next live gate: inspect actual cache revision; review rights/component evidence;
run unchanged host narrator smoke, then parity comparison; owner-scoped route
setup; authenticated Forge status + actual new WAV transfer; import/caption/mix,
retake/listening and exact final render. Those steps cannot be replaced by mocks.

## Native editor and exact synthetic media

Actual service?user companion?OpenShot jobs:
inspect `313710c99fdc4aafa75449ebaca234c3`, apply
`42243403fca64f14af59384e3231ccf3`, save
`df260a58e18c4eb3b61d63a5da9c7fdd`, reopen
`9fe17030c3684cde80708c188c2a3334`. Revision56?59. The saved graphic alpha0.9
was read back with native float32 tolerance. Durable private receipts bind each
job; no mutation replay. Save exercised heartbeat across a 16-second call.

Project:
`C:/admin/collector-v9/editor-vault/service-editor-001/service-v9-reviewed-edit.osp`
SHA-256 `7d108fbe024e27fefe3e1373fc4ede4993b29ce8da3df4100996a2c410fe5e92`.
Video, same folder: `service-v9-local-review.mp4`
SHA-256 `f453bd15c060ac590bfe8beb58c93898e3acc249df40c43310fe72978fa77c63`.
Actual direct native export `897c917c5e2b4b18b6be561695ff67c6`, revision59:
50.000s, 1080x1920,30fps,1500frames,H264/yuv420p,AAC48k stereo. Full decode0;
black scan no events; silence scan only faded last0.508s. Six sources and revision
unchanged. Frames4/21/42s visually inspected: text, lower thirds, animated graphic,
three scenes and LOCAL REVIEW labels visible. Separate tones/music exist, not
real speech; no listening assertion. Report `native-editor-export-qc.json`.

Native OpenShot4.1.1/libopenshot1.1.1 remains authoritative, editable multitrack
`.osp`; WPF operations dashboard is not a replacement timeline. Existing adapter
covers trim/split/reorder/undo, titles, overlays/keyframes/effects, subtitle/retake
and mixing. Prior V8 native proofs remain separate historical evidence; manual Qt
GUI editing, preview/export parity, spoken retake, DPI and Dot remain unverified.
Older V8 exact project and video hashes were rechecked unchanged before V9 export.

Approved portrait/landscape outro MP4s and exact intro badge bytes are still
missing. Existing implementations and expected hashes preserved; bounded host
project-folder search found no candidates. No substitute or recreated approval.
All new fixtures are unbranded technical reviews, not full production acceptance.

## Tests, skills and review

Final configured-environment regression: **284 tests PASS, zero failures/skips,
55.991s** (`regression-final-venv.log`). Initial accidental system-Python run
failed26/errors with7skips from missing dependencies/FFmpeg; retained as
`regression-final.log`, corrected by using existing project venv and pinned tools,
not weakening tests. Installed worker **163 checks PASS**. Final dashboard
**17 checks PASS**,2727ms (`dashboard-smoke-v9-round5/smoke-results.json`). Real
shown WPF window, in-process UIA/focus/buttons, installed CLI/service/error/recovery;
96dpi rendered captures at800x600/1040x780. Not OS keystroke or high-DPI proof.

Real Windows checks: scoped credential write/read/delete; private ACL acceptance
and public/inherited denial; native runner complete/cancel/timeout stopping owned
children; inspector report ACL and redaction using MOCK inventories; service
negative narration blocked before POST; queued cancel without attempt; 288170-byte
valid unicode payload roundtrip;300085-byte invalid frame rejected in90ms after
shared chunked-pipe fix. Contract server/renderer MOCK tone tests are explicitly
local/synthetic; no host API/WAV acceptance. Logs/evidence root:
`C:/admin/collector-v9`; sanitized totals in TEST-RESULTS.json.

Ponytail5.3.3 FULL resolver/review skill actually applied. UI/UX Pro Max2.15.0
`C:/admin/tools/ui-ux-pro-max/.claude/skills/ui-ux-pro-max/SKILL.md` and Taste2.5.1
native visual judgment reuse reviewed charcoal/muted-blue tokens; no UI redesign.
Final dashboard captures were reviewed; web finish gates do not apply to native
WPF/Qt and are not claimed. No lifecycle trust/session restart performed.
Independent helpers owned worker/editor/voice changes in separate worktrees;
root serialized VM installs, service tests and heavy renders. Diff review focused
on trust boundaries, no duplicate scheduler/provider, cancellation, no-replay,
revision/hash binding, bounded storage/transport, installer migration and missing
integration tests. No speculative framework or general remote control was added.

## Assistant test and remaining follow-up

Copy the plain-English request in [Assistant operations](../ASSISTANT-OPERATIONS.md).
It includes real installed health/provider/companion syntax and requires a fresh
45-55s editable LOCAL REVIEW-ONLY Short with direct VoxCPM2 narration, captions,
text/graphics, effect, two video layers, ducked music, and both exact bookends
inside the duration. Full narrated/branded command has not run successfully;
missing live API/assets must return BLOCKED, never synthetic acceptance.

Real Assistant/Dot connection and scheduled execution remain NOT TESTED. Host
execution/setup/model rights, approved bookend bytes, manual GUI/audio review,
installer signing, reboot recovery and an authenticated review PR remain scoped
follow-up. Existing production rights/review/exact-render/duplicate-upload gates
remain intact; no public upload, workflow permission change or publication.
