# Narrator recovery preparation — no live mutation

## Current continuation ? integration completed in isolation, not live-ready

See [retention and recovery continuation](V9-RETENTION-AND-RECOVERY-CONTINUATION.md)
for the owner's actual full-ancestor report, integrated C-API helper, five native
Limited-task results, fixed ProgramData data-plan/rollback design and archival
manifest. Guard-before-open helper identity is now implemented and tested in
isolation; earlier statements that only a test-only mechanism exists are retained
as checkpoint history. The public helper remains disabled. Actual D: namespace
fails trust at all four ancestors; live persistent controller binding, protected
new-module deployment and hard watchdog are unresolved. No host mutation or live
SQLite access occurred. Historical tests below are reused, not repeated.

Publication PAUSED. PR20 stays draft/unmerged. The blocked V2 repair is held;
its bytes, prepared intent, five backups and rollback are not changed or rerun.
The running BLACKHAT-BASE task, narrator, Gateway, SSH authentication, policy and
Serve routes remain untouched.

## What is established

The prior native report identified inherited Authenticated Users Modify/DELETE
on the D: narrator kit. Stable metadata at one observation does not protect a
pathname against later replacement. The original first-failure check did not
inspect higher D: ancestors. Tightening just the kit cannot establish that the
entire chain is safe, and removing inherited permissions without an explicit
owner grant could also remove the limited owner's required access.

Read-only preservation reconciliation again matched all five original backup /
live-file pairs and the prepared intent's recorded SHA-256. No stop, start or
completion marker was present. The private receipt is
`C:/Admin/Projects/KnowledgeNetwork-Private/narrator-recovery-preservation-v1.private.json`.
This is file preservation evidence, not a fresh task-state query.

## Full ancestor observation

`docs/collector/host-tools/Inspect-NarratorRecoveryAncestors.ps1` inspects the
fixed ledger path, every ancestor to D:, protected C: execution ancestry and the
existing report directory. Security descriptors come from the same native
handle as identity metadata. It records every observed unsafe ACL rather than
stopping at the first one. A reparse or unavailable ancestor leaves all remaining
descendants explicitly uninspected. The 64-bit identity observation is restricted
to NTFS; unsupported filesystems cannot pass its trust classification.

Before writing one new private JSON report it verifies the existing protected C:
report chain, owner and pinned broker configuration. Output is exclusive, bounded
and flushed. It neither opens SQLite nor launches Python, stops the task or
changes permissions. Its observations explicitly say `namespace_protected=false`
and `live_ledger_binding_proven=false`. A stable snapshot is not a recovery gate.
The existing twelve-command SSH dispatcher cannot execute this new inspector;
redirected-drive access alone supplies no native host execution.

## Ledger binding and namespace evidence

`src/youtube_ops/collector_narrator_recovery_probe.py` is an internal inspection
library, not a new SSH operation or remote endpoint. No running installation
imports it. A future checked caller must first bind an exact held process to the
fixed scheduled-task instance, limited owner SID, creation time, protected image,
launcher and actual pinned code. The canonical controller's single persistent
`self.db` connection, opened at initialization and closed at controller exit, is
an explicit prerequisite; a process merely opening a same-named file is not enough.

The probe walks only that process's handles with count/time limits. PSS returns
handle values, not an atomic guarantee that a source handle cannot be reused.
Held duplicates, repeated observations and volume plus 128-bit file ID comparisons
provide evidence under the pinned controller invariant. Unsupported nonduplicable
objects remain recorded as partial coverage; access errors, inconsistent sets,
ambiguous candidates, changed creation or mismatched ledger IDs block the probe.
Synchronous native calls are not preempted by its cooperative deadline; a live
caller still needs a bounded helper-process watchdog.

The namespace context retains root-to-leaf directory/file handles with list/read
access and without delete sharing, then repeatedly checks current path identities.
It does not replace owner/DACL checks. In particular, POSIX target replacement
must be tested explicitly: holding an old object is not proof that its name still
refers to it. Reparse and multiple-link ledger objects are refused. A duplicated
SQLite handle must not release the controller's existing file locks when closed.

The first live identity inspection must not connect to SQLite. Opening a database
can involve journal recovery. Before any later approved locking/stop action,
uncertain `-journal`, `-wal` or `-shm` state must block; never delete sidecars or
force a checkpoint to obtain a pass. An isolated fixture lock is not a live lock.

## Smallest permanent correction to evaluate

Reuse the already administrator-protected ProgramData execution runtime. Consider
one separate private controller-data child below
`C:/ProgramData/KnowledgeNetworkCollector`, with administrator-controlled parent
namespace and owner/SYSTEM/Administrators-only data permissions. Verify the entire
C: chain natively before proposing any creation or ACL operation. The dedicated
SSH identity needs no write access to it.

Move only the control ledger and startup logs in an eventual approved cutover.
Do not move the current controller, narrator/model/reference, private rights
evidence or narration job spool to prepare this design. Splitting future control
data from the existing narration spool avoids a larger job-data migration. No
constant, installed configuration, task action or data path is changed now.

This removes the future privileged recovery dependency on a writable D: control
ledger namespace without modifying broad D: ACLs. It does not retroactively make
the currently running controller safe to stop or authorize skipping V2's checks.

## Recovery and rollback conditions

No live recovery command is released. The order is:

1. Capture the full native chains and bind the real running task/process to its
   actual open ledger file ID; match that ID to a protected current namespace.
2. Review all ACL, handle-coverage, sidecar and deadline uncertainties. Prove the
   integrated procedure in isolation, including namespace retention BEFORE opening
   the helper's SQLite connection and proof of that connection's physical file ID.
   Prepare the watchdog, exact change list/hashes, consistency and rollback plan.
3. Obtain owner approval before a live SQLite writer lock, shutdown intent, stop,
   task disable, file replacement, directory/ACL creation or migration. No broad
   drive permission operation or narrator configuration change is included.
4. Only after approval, establish exact empty-ledger schema/counts under its real
   writer lock with both connections bound to the protected physical ledger, and
   retain namespace/process identity through the approved bounded shutdown.
   Record the single shutdown intent durably. Unknown response/exit keeps the
   hold; do not retry, kill, start another controller or roll back as if it failed.
5. Require confirmed exit and disabled task with zero instances before replacing
   code or changing data paths. Preserve original task/config/security bytes and
   obtain a consistent verified backup before any migration.
6. Rollback is allowed only when the task is inactive/disabled with zero instances,
   retained old/new file pins and security match, and database consistency is
   established. Preserve the new data if it contains activity; never overwrite
   records with an older copy. Unknown shutdown means reconcile, not rollback.

## Validation scope

The native ancestor, ledger/namespace, SQLite contention and recovery-composition
fixtures are isolated FORGE work. The three composed Limited-task cases passed:
one native stop, an injected fault before stop with the child still alive, and a
lost acknowledgement after native stop with the held child's exit verified. Both
uncertain cases retained one attempt and the durable intent, released the helper's
writer lock, and made no retry or Ready/start call. Existing native replacement /
rollback gates are reused separately; transaction rollback is not file rollback.

The composed fixture acquires its namespace guard AFTER the old helper opens
SQLite and takes BEGIN IMMEDIATE. It does not inspect that helper connection's
native file handle. Consequently it does NOT prove atomic helper-connection to
guarded-ledger binding against prior or transient replacement. This is a required
remaining recovery prerequisite, not an approved exception to the old gate.
A separate test-only public SQLite C-API fixture now proves the direct helper
identity mechanism: acquire the namespace guard before READWRITE-only open of
an existing database, obtain its borrowed main-file HANDLE through
`SQLITE_FCNTL_WIN32_GET_HANDLE` (29), compare its volume/128-bit ID to the guard,
and retain that connection through locking. SQLite owns and closes the borrowed
handle. A wrong same-name database plus decoy handle cannot satisfy this test.
Actual INSERT/ROLLBACK and competing-writer rejection pass. No private CPython
connection layout is read and no generic PSS handle-delta attestation is added.

The verified mechanism is not a production port: the legacy helper and its
composed fixture still use stdlib SQLite. A complete reviewed helper integration
and live controller evidence remain prerequisites before mutation approval.
Protected host runtime metadata confirms an existing SQLite DLL version 3.50.4
with its selected inventory hash unchanged; it was not executed or copied on the
host. The private native receipt retains exact local DLL identity and hash.

Results and exact run counts are recorded in HANDOFF. These tests do not establish
a live-ready BLACKHAT-BASE recovery, safe installation, remote narration or a final
video. Host inspection and any later mutation are separate acceptance stages.

Primary contracts: [PSS capture flags](https://learn.microsoft.com/en-us/windows/win32/api/processsnapshot/ne-processsnapshot-pss_capture_flags),
[DuplicateHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle),
[physical file identity](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info),
[rename semantics](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information),
[SQLite rollback locking](https://www.sqlite.org/lockingv3.html) and
[WAL persistence](https://www.sqlite.org/wal.html) and
[the public SQLite file-control handle](https://www.sqlite.org/c3ref/c_fcntl_begin_atomic_write.html).

Hosted run43762391000 exposed a POSIX fixture control that returned success but
left old target bytes. The fixture now terminates its UTF-16 filename explicitly,
asserts ABI offsets and exercises four lengths with exact bytes/source-absence /
physical-ID controls. Eleven tests passed with normal and real 8.3 TEMP paths;
production inspection code and host files are unchanged. New hosted validation
is pending; the first run remains FAILED.

Run43762949968 passed the strengthened POSIX tests, Ubuntu and Windows build/190.
It FAILED one older mocked capture test: floating subtraction produced
90.00000000000006 versus90. That fixture now freezes monotonic time at1000 and
asserts the exact shared deadline1090. The production90-second limit is unchanged.
The ten mocked capture tests pass; the three direct C-API tests pass separately
(1.404s), and independent combined review/validation passed13tests in3.289s.
Both failed runs remain recorded. Fresh hosted validation follows this source.

Final hosted validation: [run43763988119](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43763988119)
PASS for source959f8ce2d9459410fda41e5b229cc58eec4866b4. Windows452 tests/12skipped,
Ubuntu452/87skipped, Windows build/dashboard and190worker checks plus tracking
guards passed. This includes the strengthened POSIX controls, deterministic
capture clock and three direct C-API fixtures; opt-in Limited-task composition
was run separately on FORGE. Actual host inspection and integrated recovery
remain BLOCKED. The inspector is prepared on FORGE only; staging approval is
pending. No approval to stop, open the live database or change host ACLs is sought.
