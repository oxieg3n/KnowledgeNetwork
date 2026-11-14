# Proposed local editor/narrator companion

Status: read-only design proposal. No companion, media job type, scheduler cutover
or service capability is enabled by this document. Live V9 host transport remains
a separate acceptance gate.

## Existing boundary

- [Program.cs](../../collector/windows/Collector/Program.cs) runs one pipe loop and
  calls synchronous `JobStore.ExecuteNext`. Long HTTP/model/editor/render work
  here would block health, status and cancellation requests.
- [JobStore.cs](../../collector/windows/Collector/JobStore.cs) is the sole SQLite
  writer. Its constructor currently requeues every interrupted running job because
  accepted jobs are read-only. That recovery is unsafe for narration/edit/export.
  Capabilities correctly advertise those job types as disabled.
- [LocalPipe.cs](../../collector/windows/Collector/LocalPipe.cs) rejects remote pipe
  clients and authenticates the service image/identity. The configured owner SID
  may call the service; this does not yet authenticate a companion process/lease.
- [ServiceInstall.cs](../../collector/windows/Collector/ServiceInstall.cs) uses
  LocalService and a database directory ACL excluding ordinary owner access.
  Keep that boundary. The interactive user's credential store and native editor
  session are not LocalService's credential store/session.

## Smallest implementation to evaluate

Add a `companion` mode to the same installed `kn-collector.exe`, started explicitly
by the owner or through a separately verified per-user logon launch. Do not use
LocalSystem, token theft or service-session GUI launches. It calls only fixed,
configured Python adapter modules and pinned editor binaries, with bounded JSON
files, output limits and shell execution disabled.

The service retains the only queue, priority decisions and state transitions.
The companion executes a lease; it has no second scheduler or writable access
to the job database. A separate private media spool needs explicit owner/service
ACLs without broadening database or credential access. Keeping narrator credentials
in the user's protected store makes narration depend on the companion session;
do not claim sign-out/reboot independence before testing it.

Proposed typed operations, not existing CLI syntax:

| Operation | Required binding |
| --- | --- |
| `companion.claim` | Service verifies actual pipe-client PID, installed image, configured SID and user session. Return one durable job ID, payload hash and private lease token. |
| `companion.complete` | Bind lease, job/payload hash, project/base revision, native operation/export ID and compact result/artifact digests. Validate bytes through configured media-ID mappings. |
| `companion.reconcile` | Recover the same lease/native operation/provider job from persisted evidence. Observe completion/failure/continued work; never create a fresh side effect merely because a reply was lost. |

No request chooses an executable, module, endpoint, credential, host path, output
path or narrator. Use fixed `oxiegen-narrator` and verified V9 configuration.
Project/media IDs resolve through service-owned registrations. Do not trust claimed
PID/SID fields; use Windows pipe/process identity. Do not expose lease tokens in
ordinary `jobs.get`, public logs or manifests.

## Required changes and proof before enabling

1. Migrate existing SQLite state without losing IDs/events. Interrupted leases
   for side-effecting jobs enter reconciliation/held state, never automatic queue
   replay. Losing the companion must not start a second render/narration.
2. Keep pipe handling responsive while a companion executes. Never hold a SQLite
   transaction or the one pipe connection for model/render duration.
3. Bind the service job ID to the provider's durable idempotency identity and
   native intent. Preserve remote/native IDs before reporting acceptance.
4. Preserve native expected revisions and pending-operation receipts. Snapshot
   export revision and actual source/render hashes invalidate older approvals.
5. Keep results compact: the current protocol reads at most 65,536 bytes. Native
   project dumps, WAV bytes and private credentials cannot be pipe result bodies.
6. Confirm cancellation against the actual provider/editor. A local cancel
   request is not proof a running host or native export stopped.
7. Test forged companion/lease replies, owner/service ACLs, user credential
   isolation, disconnect/restart reconciliation, changed WAV/project bytes,
   disk limits and real session lifecycle before changing capability flags.

This proposal supplies no publication route. Publication stays paused, existing
production schedulers/queues remain untouched, and service health alone is not
Assistant/Dot or scheduled-connection acceptance.
