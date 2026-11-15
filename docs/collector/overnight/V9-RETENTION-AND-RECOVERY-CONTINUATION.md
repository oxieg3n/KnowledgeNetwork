# V9 retention and recovery continuation — November 15, 2026

Publication PAUSED. Continue `feature/collector-v7-overnight` from
`0ef8525cccaa875f4a077ae39ed1d6e150dae075`. PR20 stays draft/unmerged.
This record supersedes earlier statements that the inspector was not staged or
that the proposed helper still lacked C-API integration. Historical results
retain their original scope.

## Actual read-only host inspection: BLOCKED

The owner successfully executed the exact staged 12566-byte inspector, SHA-256
`6b5a48514c0691cb46a637c7310af34c95ee3e79c1c08f6a36277501de482f8b`.
The previous copy/paste path failure occurred before execution; it is resolved.
Do not run the inspector or blocked V2 repair again without a new reason.

Native report SHA-256:
`396eb85db9b9a2f75823c8ebf689db128ca4719b4dcf648204d2d16942ab1dbd`.
Original private report on BLACKHAT-BASE:
`C:/ProgramData/KnowledgeNetworkCollector/HostExec/broker-update-v1/recovery-ancestors-683d454bbad44fee99d278ede997cce9.private.json`.
All observed volumes are NTFS. Observed identity, ACL and path bindings were
stable. Four ancestors fail the existing strict trust check:

- `D:/`
- `D:/projects`
- `D:/projects/knowledgenetwork`
- `D:/projects/knowledgenetwork/collector-narrator-v9-004`

Each has an effective Authenticated Users Modify grant (`0x1301bf`) containing
DELETE (`0x10000`, rejected ancestor mask `0xD0040`). The private spool and ledger
leaf pass. The inspected C:/ProgramData execution/interpreter and report chains
pass. The fixed task was Running, result267009 (`0x41301`), last run
2026-11-15T17:15:06Z. This is an observation, not scheduled-operation acceptance.
No SQLite database was opened, and no task, ACL or runtime was changed.

Tightening only the kit cannot fix the higher unsafe ancestors. Broad D: changes
and trust-mask exceptions remain excluded. The real controller's persistent
connection has not been bound to the ledger under a proven protected namespace.

## Proposed recovery source: isolated integration PASS; live use BLOCKED

`collector_narrator_recovery.py` reuses the exact pinned legacy stop definitions,
task/process/creation-time/owner/image checks and one-attempt uncertainty rules.
It acquires the namespace guard and retained controller ledger binding BEFORE
opening an existing READWRITE-only helper connection through the public SQLite
C API. File-control29 exposes SQLite's borrowed main HANDLE; its volume and
128-bit file identity must match the guard and retained controller evidence.
SQLite owns that handle. SQL is allowlisted and bounded; sidecars, non-rollback
headers, mismatches and lock contention hold recovery. Original intent/backups
remain unchanged; new claims/results use a separate exclusive receipt root.

The public entry deliberately rejects even `operator_approved=True` with
`reviewed_recovery_deployment_unavailable`. This is source preparation, not a
deployed handler or a released repair command. The existing manifest does not
cover the new recovery/probe/caller. A protected independently pinned deployment,
hard process watchdog, actual host ledger evidence and separate mutation approval
are still required. Cooperative deadlines and partial PSS handle observations
must not be presented as complete live attestation.

Five serialized disposable native FORGE Limited-task cases passed in49.632s:
same-ledger single stop; wrong-ledger rejection before helper open; active writer;
uncertainty before stop with child alive; lost acknowledgement after actual stop
with held exit proof. Uncertain cases never retry or start another controller.
Fixture files remain retained; only disposable task registrations/handles close.
These tests do not prove live BLACKHAT-BASE recovery safe. The generic-ACE trust
preflight also passed its separate native PowerShell regression after tightening.

Focused local suite:50 discovered,45 passed,5 opt-in cases skipped in18.816s.
Those five native cases passed separately above. Independent security/Ponytail
FULL review passed after correcting row iteration and receipt-finalization
concurrency. Receipts under the private project root:
`narrator-recovery-integrated-native-v1.private.json` and
`narrator-recovery-preservation-continuation-v1.private.json`.
Original intent, all five backup/live old-pin pairs and rollback were rechecked
unchanged; no new shutdown/start/completion markers were present.

## Permanent data design: review plan only

The pure `collector_controller_data_plan.py` returns fixed paths and ordered
cutover/rollback prerequisites; three tests pass. It performs no file/service
operations and never declares itself executable. Proposed future control ledger
and startup logs: `C:/ProgramData/KnowledgeNetworkCollector/NarratorControl`.
Administrator-protected code/config stays separate; only the actual limited
owner, SYSTEM and Administrators may write private data. The SSH dispatcher
remains nonadministrator and gains no data-write permission. Narration job spool,
original D: ledger, narrator/model/reference and current task stay in place.

No live migration executor is released. Current ledger/code deployment pins and
fresh task attestation are unresolved. Before a cutover: establish protected
namespace and both physical connection identities, review exact pins/backup and
obtain approval before a writer lock or shutdown intent. After confirmed exit,
disable the task and require zero instances. Use a consistent backup, fresh
fixed staging path and no-replace ledger publication; a durable journal covers
the separate task/config changes. Collisions or uncertainty stop progress.
Rollback requires known inactive/disabled task, exact retained pins and no new
ledger activity. Preserve both ledgers and reconcile if activity or uncertainty
exists. Never overwrite new records with an old copy. The private review plan is
`controller-data-migration-plan-v1.private.json`; it is not approval to migrate.

## Permanent archive policy and actual archive

Root AGENTS section11 and `/old/` gitignore now enforce the owner's retention
directive. Fresh data fixtures retain originals under the private project's
`fixtures` directory and write bounded private indexes. Only executed Limited-task
fixtures request the separately checked protected TEMP namespace; the placement
flag itself proves no ACL trust. No broad moving automation or automatic deletion
was added. Installer packaging rejects an existing output before building.

One verified never-run superseded draft was safely archived:

- Original: `C:/Admin/Projects/KnowledgeNetwork-Private/Host-Narrator-Control-Repair-v2.DRAFT-01.txt`
- Archive: `C:/Admin/Projects/KnowledgeNetwork-Private/old/2026-11-15-obsolete-command-08283d04/Host-Narrator-Control-Repair-v2.DRAFT-01.txt`
- SHA-256: `7ccf80322a972e97fa97b3cb2e7577148242fef92c1284a79b06ccf6fcf7d42e`;951 bytes.
- Receipt: `archive-receipt.private.json` in that archive folder records time,
  reason, paths and property checks. Destination bytes, physical identity and
  security descriptor match; no overwrite occurred.

Original V2, prepared intent, five backups, rollback, referenced receipts,
approved assets, live SQLite/runtime and credentials remain in place. The four
SSH authentication files retain their original protected user-profile paths.
Previously denied cleanup targets remain untouched; this policy is not a move
bypass. Public/host archive roots had no safely eligible work this continuation.
Host staging rollback now says archive only after specific safe checks, otherwise
leave in place; the original authorizing staging plan is retained unchanged.

## Independent media/transport progress

The client retains failed partial downloads and recovers the SAME job after
joined-WAV/checkpoint uncertainty only if decoded PCM and digest match previously
verified segments. No new ID or resubmission bypass is allowed. Editor protocol
receipts finalize with no-replace, byte/identity/security verification and a
serialized durable hold; failed transitions preserve evidence.17 new focused
transport/editor tests passed. These use synthetic transport, not real narration.

Existing50-second synthetic fixture defaults remain intact. New optional timing
budgets1218 body frames:48 intro +1218 body +234 outro =1500 frames/50s at30FPS.
Three equal406-frame body scenes retime captions, graphics and music; narration
that does not fit is rejected. Approved source hashes/decodes are reused, including
the original badge; no branding blocker remains. The four-second preview is
reference-only, never a substitute for the48-frame dynamic intro.

The new bounded single-frame thumbnail operation was attempted once against the
existing enrolled native session. Initial inspection failed `connection_failed`
before thumbnail intent/RPC. No OpenShot process was running; no new session,
project change or retry occurred. Installed source reports4.1.1; executable
version resources are blank, actual executable SHA-256 is
`3637d631e5b01f263c87e7bbc0c9d3dd5b75274f7489bd2f56da8940ce292ca7`.
Existing reviewed project `C:/admin/collector-v9/editor-vault/service-editor-001/service-v9-reviewed-edit.osp`
remains SHA-256 `7d108fbe024e27fefe3e1373fc4ede4993b29ce8da3df4100996a2c410fe5e92`.
Receipt: `native-single-frame-continuation-v1.private.json` under private storage.
Existing native save/export/startup cleanup paths require retention review before
running again. No new PNG, narrated .osp or export was produced. Real transferred
narration and native final-video acceptance remain BLOCKED.

## Release and CI scope

The existing pipefix002 installer, installed working Collector and accepted190
worker checks are reused; no rebuild/install/upgrade occurred. Fresh/upgrade/
rollback installation acceptance and scheduled Assistant/reboot tests remain
NOT TESTED. No reboot is authorized. Worker Git-object scope must match before
CI reuses old evidence; that is not a fresh build result.

The legacy full-suite preflight now fails closed on110 destructive fixture sites
before installing/running those tests. Its CI job is intentionally BLOCKED, not
a successful full regression. Separate Windows/Linux retention-safe focused jobs
test this continuation. The previous accepted452-test hosted run43763988119
retains its historical scope. No automatic fixture deletion is permitted merely
to recover a green check. New hosted run/results are recorded in HANDOFF.

Ponytail FULL and installed ponytail-review were applied; independent security
review covered recovery gates, retention boundaries and editor concurrency. No
UI was changed; no UI/UX Pro Max, Taste browser gate or Prompt Sensei pass is
claimed. Commercial redistribution review remains separate; the approved local
diagnostic audio and tested inactive kaldiio path are not rerun or reclassified.

Next: complete the retention migration of relevant legacy/native editor cleanup,
then establish a separately reviewed live namespace/ledger-binding procedure and
protected deployment/watchdog. Only after those facts support a concrete safe
operation should owner approval be requested. Do not rerun V2, relax D: checks,
start9443 or request an unsafe stop to make progress.
