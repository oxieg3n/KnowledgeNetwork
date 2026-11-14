# Installed pipe authentication repair

November 14, 2026. Feature branch `feature/collector-v7-overnight`; PR #20 stays
draft and unmerged. Publication PAUSED. Source commits `d85ab96`, `d5132eb`
integrate the helper's `d26b345`, `b27a5c8` without rewriting history.

## Exact original failure: PASS diagnosis

The original installed build rejected the normal medium-integrity
`forge\oxieg3n` client at **OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)**,
Win32 error **5 / ERROR_ACCESS_DENIED**, pipe server PID14316.
QueryFullProcessImageName was never reached. SCM queryex and queryconfig both
succeeded for the registered running own-process LocalService worker.
The original CLI returned `untrusted_pipe_server`, exit1. The diagnostic probe
sent zero request bytes. The high-integrity developer shell passed health and
therefore could not establish this failure on its own.

Native before/after runs used a temporary, triggerless Task Scheduler task with
the existing user's interactive token and RunLevel=LeastPrivilege. Receipts
show Medium Mandatory Level and Administrators deny-only. This was a test
launcher, not a runtime requirement or administrative workaround. The task was
exported privately and removed after completion. Earlier linked/restricted-token
launch attempts failed or stalled before a receipt; their exact owned test
children were stopped after command-line verification. Those attempts are not
counted as successful medium-token tests. No execution policy was changed.

## Correction and trust boundary

The OS-provided connected-pipe server PID is checked against SCM first.
The named service must be RUNNING, WIN32_OWN_PROCESS, use LocalService and the
canonical quoted Program Files Collector executable with `serve` arguments.
The same service handle is retained while configuration/status and pipe PID are
checked again. Changed status/PID/configuration fails closed before transmitting
a request. A copied executable name alone supplies no trust.

Every SCM lookup/status/configuration failure denies authentication. Only
ERROR_SERVICE_DOES_NOT_EXIST1060 permits the intentionally supported console
worker path, which still requires exact executable path, same-user token,
unchanged pipe PID and a second service-absence check. No bypass flag, service
ACL/process ACL expansion or elevation requirement was introduced.
Denied responses preserve `error=untrusted_pipe_server` and add fixed `stage`
and numeric `win32_error`. They contain no bearer, job text or raw private path.

## Installed patch and data preservation

Published source build `d5132ebba7fe8ae83b7ce9cb056904f926cabdd7` to fresh
`output/collector-pipefix-001`; locked restore, publish and190 self-test checks
PASS. Updated only installed `kn-collector.exe`, `.dll`, `.pdb`, and their
existing package-manifest entries. No entire-Collector reinstall, dashboard,
editor, runtime, service-registration/ACL, schema or host change occurred.

Before stopping the service, verified every installed manifest entry, copied
the three original worker files and manifest, and made a consistent SQLite
backup. Backup SHA-256:
`daca19da767c1ce7fd1a3149db358d42e31f0c3745ce42dc76f3f4e21f0adf4b`.
All13 jobs,39 events, metadata and SQLite sequence rows compare exactly after
restart; integrity_check=ok. Stable worker ID:
`cb6ce3cd482148e7b8b0c8661ec8c6e9`. Service PID changed14316 to4188;
registration/configuration/companion enablement are unchanged. Original backups
were not overwritten or restored.

Installed current SHA-256:

| File | Digest |
| --- | --- |
| kn-collector.exe | `60516f07332facbbfa484cb5a2b4b430cc42c12128bc6525283e589b812e2754` |
| kn-collector.dll | `cb1d2debccce27e47c0046bd6c2f60aaa8113600fc207429347f3d8f3545b3d3` |
| kn-collector.pdb | `df10e08b72d5194c7ca46425fb0835c55130e3ed61aacfff8dc9e8dbe2b4e9e5` |

Private evidence and rollback originals:
`C:/admin/collector-v9/pipe-auth-20261114-01`. Its protected DACL was copied from
the existing private provenance directory before writing evidence. Logical
database rows, task XML and user-context output remain private.

The old Round5 installer remains intact and **does not contain this patch**.
Do not rerun it as routine repair: it would restore the old authentication code.
For deliberate worker rollback, stop the service, restore only the three
original worker files plus their original manifest from `pre-patch-worker`, then
start and verify health/data. Never restore the old database merely to roll back
these binaries. Such rollback also restores the known medium-client bug.

## Test results and actual Assistant response

| Check | Result |
| --- | --- |
| Source regression, service identity/status/config/SCM errors | PASS190 checks, including stale/spoof PID, restart/config changes and explicit query failures |
| Original native LocalService/medium client | FAIL as reproduced: OpenProcess/error5, CLI exit1 |
| Patched installed native medium client | PASS exit0; OpenProcess still error5, SCM trust succeeds, healthy windows_service response |
| Native stopped registered service with fake pipe endpoint | PASS rejection at ServiceIdentity; zero request bytes, exit1 |
| Actual service stop/start and data preservation | PASS, all logical rows equal, stable worker identity |
| Assistant's actual FORGE health | PASS owner-returned response below; exit code was not separately supplied |
| Forced native SCM API errors/precise mid-auth restart interleaving | NOT TESTED natively; managed production-used validation tests cover these decisions |
| Scheduled Assistant connection, reboot, narrator/editor acceptance | NOT TESTED in this IPC repair |

Owner returned Assistant's actual-context response after the installed update:

```json
{"ok":true,"result":{"schema_version":1,"product":"The Knowledge Network Collector","version":"0.1.0","worker_id":"cb6ce3cd482148e7b8b0c8661ec8c6e9","build":"0.1.0\u002Bd5132ebba7fe8ae83b7ce9cb056904f926cabdd7","status":"healthy","transport":"windows-local-named-pipe","nonce":"1587a1afca4a490c9075638f997625e1","execution_context":"windows_service","narration_companion_enabled":true,"media_reconciliation_hold":false,"publication_paused":true,"production_scheduler_enabled":false}}
```

Ponytail FULL review read callers in Program/ServiceInstall, native structures,
handle cleanup, request-before-auth ordering, console fallback and regression
checks. Reused SCM and current self-test infrastructure; no new dependency or
remote-control framework. No UI changed, so no UI skills/gates were rerun.
