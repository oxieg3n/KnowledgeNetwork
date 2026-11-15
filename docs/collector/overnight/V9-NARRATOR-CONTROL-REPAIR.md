# V9 narrator control pipe acceptance and repair

Publication PAUSED. PR #20 remains draft/unmerged. Continue the existing branch;
the accepted Collector worker, installed pipe-trust correction, database, native
editor fixture, approved narration and recovered original branding are retained.

## Actual host acceptance

The owner completed the checked continuation from ce79a341. The protected
dispatcher is SHA256 `86b94ada8cc7097fee5b8d0a095826bfb4932526d8a2ab5ea4da7b70ee68c3ef`.
FORGE's pinned SSH health passed with all 12 fixed capabilities, nonadministrator
bridge identity and the unchanged host key. Private request receipt:
`%USERPROFILE%/KnowledgeNetworkCollector-Private/host-exec-client-v1/after-control-upgrade-health.private.json`.

The owner reports the Limited InteractiveToken task Running. FORGE's first
read-only `narrator-reconcile` attempt was BLOCKED before request transmission:
`broker_unavailable`, request `9b8aaf1d844a4fc4b01f3a4ca8513695`.
The original transport conflates missing-pipe and access-denied errors. A copied
private startup database contains the requests and audit tables, both with 0 rows;
this copy establishes observed startup progress, not a live concurrency lock.

## Confirmed source defect

A genuine Windows restricted-token fixture reproduced the bridge ACL failure:
the old grant 0x120103 rejects CreateFile with Win32 error 5; 0x120183 succeeds.
Windows requires FILE_READ_ATTRIBUTES in addition to the explicitly requested
data/attribute access. The corrected grant includes that bit and still omits
FILE_CREATE_PIPE_INSTANCE. Actual second-instance creation is denied under the
corrected grant; a separate fixture with the creation bit permits it. Earlier
same-owner clients had full access and did not test this bridge boundary.

The source also corrects two independently reproduced transport defects:
an early connection/close can raise ERROR_NO_DATA before the original try block,
and DisconnectNamedPipe discards a reply the client has not yet read. Connection
errors are handled inside the loop, and the server waits boundedly for client
closure after sending a reply. No request is automatically replayed.

The actual HTTP listener now uses exclusive Windows binding in source. Native
tests reject a competing SO_REUSEADDR bind and preserve an existing listener.
These corrections have NOT yet been installed on BLACKHAT-BASE.

## Bounded repair

The owner control task runs under the intended owner's limited token. The
ordinary SSH account cannot modify its administrator-owned runtime or task ACL.
The source repair therefore requires a checked owner-side bootstrap. It reuses
the existing runtime, six-module package, canonical script, manifest and spool.
No original inference environment is run elevated.

The repair must preserve backups and write a durable intent before changing
anything. A running old controller can be stopped only after native task/process
identity checks and a SQLite BEGIN IMMEDIATE lock prove its requests AND audit
tables are empty. The lock remains held through one Task Scheduler Stop and
confirmed process exit. This condition excludes any controller-accepted action.
An owned 39110 listener, any ledger row, ambiguous process/task identity, lock
failure or uncertain exit blocks replacement. There is no force-kill fallback.
The existing unmanaged foreground narrator and GPU processes remain untouched.

An isolated FORGE Stop test ended its task but did not produce Python's normal
exit receipt. This is NOT proof of graceful shutdown. The empty-controller lock
is therefore essential; do not generalize this repair to a controller that has
accepted work. Task Scheduler's AllowHardTerminate setting alone is not an
application cleanup guarantee. See [Microsoft's setting documentation](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-allowhardterminate).

The update disables the verified inactive task while replacing files, validates
all new pins and preserved ACLs, then requests one limited-task start. An
originally disabled task remains disabled. Rollback requires an inactive task
and exact byte/ACL/task checks; it never kills audio or starts inference.

Two fixed SSH commands provide native task status and one Ready-only start.
The bridge receives only dedicated task/folder read-execute permissions, without
edit or registration rights. Status uses a nonconnecting availability probe and
does not claim pipe authentication. Startup records are private, exclusive,
fsynced, redacted JSONL files capped at 100 starts; they contain stages and numeric
errors, never exception text, credentials or narration.

## Remaining acceptance

After the checked repair, use the existing pinned SSH alias for actual task
status, pipe reconciliation, manifest verification and lifecycle tests. A start
request alone is not a ready broker or a ready narration API. Do not automatically
repeat an uncertain start or infer an empty live ledger from the retained copy.

The existing foreground 39110 service is not owned by the new broker. Its prior
local authentication pass remains separate evidence; the new controller refuses
to adopt it or send it a bearer. Managed handoff must preserve any jobs first.

HTTPS 9443 has not been activated. The approved/post-verified v5 tailnet policy,
existing 443/8443 routes, Gateway and firewall are preserved. Real authenticated
FORGE narration, matching returned PCM, and the complete native branded Short
remain BLOCKED pending host control and service/transport acceptance. Installer
isolation and scheduled/reboot acceptance retain their previous NOT TESTED scope.
