# V9 operational acceptance — bounded QA continuation

November 15, 2026. Reviewed source checkpoint
`89b134a85e094b2b2a584e2c719f6ef2a5a07a00` on
`feature/collector-v7-overnight`. Publication remains **PAUSED**. This workstream
performed read-only capability/source/file inspection only: no installer run,
service restart, scheduled task creation, reboot, model load, render or database
write. It does not establish actual scheduled Assistant reliability.

## Installer isolation: BLOCKED, staging package preserved

FORGE reports Microsoft Corporation / Virtual Machine with a hypervisor present.
The local Windows optional features `Containers-DisposableClientVM` and
`Microsoft-Hyper-V-All` both report **Disabled**. `vmms` is absent;
`Get-VM`, `Get-VMSnapshot`, `vmrun`, `VBoxManage`, and `WindowsSandbox.exe` are
unavailable in this shell. No disposable isolated Windows installation target
was established. These checks do not inventory or authorize unrelated host VMs.
No optional feature was enabled and no test VM was created.

`KnowledgeNetworkCollector` remains **Running / Automatic** as observed through
Get-Service. This is process/service state, not a new authenticated health test.
The staging installer was independently rehashed, unchanged:

`C:/admin/projects/KnowledgeNetwork/output/installer-v9-pipefix-002/The-Knowledge-Network-Collector-0.1.0-v9-pipefix-002-setup.exe`

SHA-256 `4149bd4c66347429f65a570925bc158cbc36a8b752c36c741d1cfabf4439517a`.
The earlier 481 manifest matches and 190 worker self-tests remain applicable;
they were not repeated. This artifact remains unsigned and not installer-accepted.

`Collector.iss` uses a fixed AppId, Program Files directory and service name.
An alternate output directory or installer `/DIR` override is not safe isolation:
the installer validates the canonical path and removes/registers that service.
Consequently it was not run over the working installation.

The minimum missing resource is an owner-designated disposable Windows x64
snapshot/VM where the fixed service/AppId/ProgramData paths can be exercised.
Use a local owner account and no production credentials/media. In that environment:

| Phase | Required evidence |
| --- | --- |
| Fresh install | Installer log, all installed manifest hashes, LocalService identity, fixed canonical path, authenticated health, publication paused/scheduler false |
| Medium-integrity client | Non-elevated owner shell health with exact nonce; record token integrity and exit status; do not weaken pipe ACL/trust |
| Companion opt-in | Run the installed `install-service --enable-companion` elevated as that same configured owner, then verify the actual service configuration and health |
| Upgrade | Seed only a synthetic diagnostic job, capture worker ID/job/result hashes and consistent data backup, upgrade to this staging installer, compare identity/jobs/results/companion flag |
| Uninstall | Remove service/binaries through the actual uninstaller and verify private ProgramData remains; no dangling service |
| Rollback | Restore the controlled pre-upgrade binaries/manifest in the isolated target and prove compatible data access; do not blindly restore stale data |

The older Round5 installer can be a controlled historical upgrade input only in
that disposable target; it must never be run over FORGE's working installation.
Its known medium-integrity trust failure is expected before the patched upgrade.
Do not accept a failed fresh/upgrade test merely because source self-tests pass.

## Prepared Assistant scheduled-operation check — NOT EXECUTED

The smallest first scheduled check is read-only, with no media generation:

> Assistant, at the agreed single test time, use your actual FORGE connection
> under the intended owner's normal token. Run the installed Collector health
> command with a new nonce, then capabilities. Return the run time, nonce, actual
> JSON and exit codes. Require windows_service, publication_paused=true and
> production_scheduler_enabled=false. Do not publish, submit narration, restart
> services, register a Windows task or retry a failed connection. Report a missed
> or unavailable connection as a failed scheduled test rather than substituting
> a local Codex execution.

These are the source-verified actual CLI commands for that future test:

```powershell
$collectorCli = 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe'
$collectorNonce = [guid]::NewGuid().ToString('N')
& $collectorCli health $collectorNonce
& $collectorCli capabilities
```

Scheduling/controller setup has not been performed. A local Task Scheduler run
would establish only local scheduled execution, not Assistant-to-FORGE access.
Any optional local task must use the configured owner's normal token, a single
trigger, no stored password or highest-privilege workaround, and only these
bounded read-only commands. Export its definition/results privately and remove
only the task created for that test after review. No such task was created here.

## Prepared persistence/restart acceptance — NOT EXECUTED

Use only an isolated target or a separately coordinator-approved quiet service
maintenance window. Before interruption, preserve current service configuration,
all installed binaries/manifest and a consistent SQLite backup. Do not raw-copy
a live SQLite database while ignoring its WAL. Require no running narration,
editor operation or unknown execution outcome. A held/uncertain job is a blocker,
not permission to clear state or replay it.

The actual bounded job interface is `submit <json-file>` and `get <32-hex-job-id>`.
For one future synthetic test, create a private JSON with schema_version=1,
job_type=`diagnostic.echo`, a new recorded idempotency_key and an original nonce,
matching `collector/windows/diagnostic-echo.json`. Record the returned job ID
before polling; retain the exact original file for an idempotency check. The
following are templates with actual CLI syntax, not claims that files/jobs exist:

```powershell
& $collectorCli submit $actualPrivateEchoJson
& $collectorCli get $recordedJobId
```

After state=succeeded, retain worker_id, payload_sha256, result_sha256, nonce,
attempt and job ID. The coordinator can then perform exactly one approved
`Restart-Service -Name KnowledgeNetworkCollector` in the quiet window and
repeat health/get with a fresh health nonce. Require the same worker ID,
unchanged completed job/result hashes and companion enablement, valid database
integrity and no added media execution. Resubmitting the same recorded echo file
must return the same job ID. This test introduces no new speech request.

No restart was performed. Reboot is a separate owner-approved phase: after a
planned reboot, run the same identity/get checks through the actual Assistant
connection and distinguish service auto-start, interactive companion availability
and remote narrator availability. No reboot command is supplied or run here.
Sign-out survival of the owner-session companion remains a separate unverified
boundary; LocalService running does not prove a companion is available.

## Native acceptance readiness

Reviewed `collector_editor_fixture.py`: `--narration-receipt` imports verified
real speech into the native project and its measured caption/music workflow.
The existing builder remains a fixed 50-second unbranded technical fixture,
placing its body at zero. It does not itself assemble the approved bookends.
Keep the previous successful `.osp`/MP4 intact. A fresh remote receipt must be
materialized in the private editor vault; a host-only diagnostic copy is not a
successful FORGE API narration receipt. Full 45–55-second assembly must reserve
the measured intro/outro intervals and retime editable body/captions rather
than append bookends to the existing 50 seconds. Existing structured native
commands and the branding workstream cover that assembly; no second editor or
flattened body is proposed.

## Review and limits

Ponytail 5.3.3 FULL is active; installed Ponytail and ponytail-review skills were
read. Bounded review traced Collector.iss into Program/ServiceInstall/JobStore
and existing companion/native interfaces for fixed-path effects, retained data,
actual CLI syntax and unsupported acceptance claims. No concrete new source
defect was identified. No runtime code changed; no redundant regression or media
suite was run. UI was not changed, so no new UI/UX Pro Max/Taste gate is claimed.

PASS: read-only isolation inventory, staging installer hash, current service
state and source/interface review. BLOCKED: disposable installer target.
NOT TESTED: fresh install/upgrade/uninstall/rollback, new medium-token installer
acceptance, scheduled Assistant execution, restart/reboot and new native export.
Existing backups and pipe-repair rollback originals remain present; no data or
working installation was restored, overwritten or migrated.
