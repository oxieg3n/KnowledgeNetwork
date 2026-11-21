# The Knowledge Network Collector: local Windows worker

This first worker implements a bounded diagnostic connection test and read-only
research staging snapshot. It has no
publication operation, media subprocess or production scheduler. Existing Python
queues and publication controls remain authoritative and unchanged. It is not
proof of Assistant/Dot reachability or a finished editing service.

V8 places production VoiceStudio on BLACKHAT-BASE. The Collector service does
not yet dispatch `narration.generate`; capabilities explicitly return
`narration_jobs_enabled=false` and
`remote_voice_provider_not_bound_to_service_identity`. A successful standalone
Python provider probe is separate from a working LocalService job. No remote
endpoint or credential is accepted in a submitted job.

Before enabling that one job type, register an administrator-configured, pinned
provider executable/module and fixed private endpoint on FORGE; verify its
bounded REST allowlist and returned WAV validation. Provision the narrow
credential in Windows-protected storage readable by the exact service identity
and prove restart access without printing it. Register licensed model/profile
evidence and resolve project/output IDs inside the private vault. The worker
must persist the script/profile/request digests before sending, serialize one
speech request, and reconcile uncertain host responses rather than blindly
replay generation after a timeout/restart. A cancelled local request is not
proof that host synthesis stopped. Only then add the typed job, its recovery
policy and native end-to-end tests. Never expose arbitrary URLs, paths,
provider commands, host settings, cloning or general remote HTTP through this
boundary. Current diagnostic/snapshot scheduling and publication holds remain
unchanged. See [V8 architecture](v8/REMOTE_VOICESTUDIO_ARCHITECTURE.md).

Build with the .NET 10 LTS SDK on Windows:

```powershell
dotnet restore collector/windows/Collector/Collector.csproj --locked-mode
dotnet build collector/windows/Collector/Collector.csproj -c Release --no-restore
dotnet run --project collector/windows/Collector -c Release --no-build -- self-test
dotnet publish collector/windows/Collector/Collector.csproj -c Release -r win-x64 --self-contained true -o output/collector
```

The executable is `output/collector/kn-collector.exe`. The console worker and CLI
use the same binary; the service uses .NET Windows Service hosting. Installation
must select a dedicated low-privilege service identity (for example LocalService),
a private data directory outside the repository, and the owner's Windows SID.
Running the service as LocalSystem is rejected. Do not install it with a default
LocalSystem service command. Service installation, ACLs, launch and recovery must
be tested by the VM coordinator before claiming installed readiness.

The installed executable has two local, administrator-only maintenance verbs:

```text
"C:/Program Files/The Knowledge Network Collector/kn-collector.exe" install-service
"C:/Program Files/The Knowledge Network Collector/kn-collector.exe" remove-service
```

`install-service` optionally takes the intended Windows owner SID; it defaults
to the elevated caller's SID and rejects a different owner because it cannot
authenticate on that user's behalf. Both verbs require this exact canonical
installed executable path. They are not service jobs and cannot be submitted
through the pipe. No PowerShell script or execution-policy change is required.
The Inno installer should call these verbs and preserve their exit status.

Before touching SCM, native installation checks the bounded `files.sha256.json`
manifest, all listed runtime hashes, path confinement, regular files and the
absence of unlisted files/reparse points (Inno-generated uninstall files are the
sole exception). It creates/configures only the named Collector service through
fixed System32 `sc.exe` argument arrays, runs it as LocalService, configures
bounded recovery and restricts the private ProgramData directory ACL. An
existing service must already point at the canonical Collector executable.
If the fixed private `research-staging.json` exists, installation pins its
measured SHA-256, requiring a regular file of at most 8 MiB. No production writer
or migration is enabled. An obsolete/unmanifested binary blocks upgrades until
the package discrepancy is reviewed; installation never deletes private data.
Removal stops/deletes only the matching service and retains media, database and
binaries. PowerShell scripts remain optional advanced staging tools; a restricted
execution policy must not be bypassed to run them.

The installation script declares healthy only after two authenticated installed
CLI responses with fresh matching nonces, healthy Windows-service context,
publication pause and scheduler hold, the same persistent worker ID and the
same running SCM process ID before and after both calls. It also verifies the
service account resolves to LocalService (`S-1-5-19`) and the exact configured
binary command remains unchanged. Probes have a 45-second deadline, individual
CLI processes are bounded to ten seconds, and CIM calls have five-second
timeouts. A failed check throws without deleting the database. When elevated
under a different user from `OwnerSid`, installation cannot authenticate on the
owner's behalf and explicitly fails health verification after service setup;
run verification as the intended owner rather than broadening pipe access.

For a local same-user diagnostic run, launch the first command in one terminal:

```powershell
./output/collector/kn-collector.exe serve --data "$env:LOCALAPPDATA/KnowledgeNetworkCollector"
./output/collector/kn-collector.exe health unique-caller-nonce
./output/collector/kn-collector.exe capabilities
./output/collector/kn-collector.exe research-snapshot
./output/collector/kn-collector.exe submit collector/windows/diagnostic-echo.json
./output/collector/kn-collector.exe get ACTUAL_JOB_ID_FROM_SUBMIT
./output/collector/kn-collector.exe cancel ACTUAL_JOB_ID_FROM_SUBMIT
```

`--client-sid S-1-...` on `serve` grants exactly that additional Windows identity
pipe read/write access. It does not grant database access or command execution.
Never grant Everyone/Authenticated Users. The private directory ACL permits only
the worker identity, SYSTEM and local administrators. The OS pipe mode rejects
remote clients, the protected pipe ACL admits only the worker and configured
owner, and first-instance creation fails if another server already owns the pipe.
There is one fixed pipe, `KnowledgeNetworkCollector-v1`; no TCP listener.
Before sending any job bytes, the CLI verifies the connected server process ID,
its executable path against the CLI's own image, and either its registered
running Collector service PID or the current user's process token SID. A fake
server from another executable/identity is rejected. Use the installed CLI for
the installed service; a CLI from a different build directory fails closed.
The native client requests read/write without pipe-instance creation rights and
limits the server to identification-level client impersonation.

CLI replies are JSON: `ok`, and either `result` or a stable `error` code. The CLI
returns exit status 1 for a rejected request, timeout or missing worker. `health`
requires a fresh caller nonce and returns it with the persistent worker ID.

`diagnostic.echo` jobs require schema version 1, a bounded idempotency key and
`inputs.nonce`. Optional `created_at` and `expires_at` must be explicit UTC ISO
timestamps; expiry defaults to one hour and cannot exceed seven days. Optional
priority is an integer from 0 through 9. Unknown/duplicate fields are rejected.
Repeating the exact canonical request returns its existing job; changing a
payload under the same key fails. An accepted job is committed before a reply.

Configure research readback only with server-side `--research-snapshot PATH`
and `--research-sha256 LOWERCASE_SHA256`. The immutable staging file is limited
to 8 MiB, checked against its pinned digest on every read, and is never written.
`research-snapshot` reads it immediately; a `research.snapshot` job with empty
`inputs` performs the same read durably. Results retain the four original queue
IDs, counts, first eight sorted item IDs (explicitly marked when truncated),
source revision, exact digest and observed source pause. Missing config or a
changed snapshot blocks the job. This is staging evidence, not a live migration,
research scheduler or production cutover.

Jobs transition from queued to running to succeeded, or queued to cancelled or
expired. A failed snapshot is blocked with a stable error. Terminal cancellation
is a harmless status read. Results retain exact
SHA-256 digests, review-only status and publication ineligibility. SQLite uses
WAL plus FULL synchronous commits, a single writer, transactionally appended
events, protected journal triggers and an exclusive worker lock. On restart,
only the implemented replay-safe read-only jobs are recovered from running to
queued. A future side-effecting job needs its own reconciliation policy.

Capacity limits are a 64 KiB framed pipe request, 5-second client handling,
256 MiB free-disk reserve for submission, 100,000 jobs and 65,536 SQLite pages.
No automatic pruning or public export exists. Logs must not include job text or
private paths. The self-test leaves its uniquely named local evidence database
for inspection; never commit it.

`shortcut: diagnostic.echo and research.snapshot are the only dispatched jobs; add editor/voice work only
through validated project/asset IDs and a tested user-session boundary.`

The self-test checks deduplication/conflicts, denied shell/publication fields,
duplicate fields, result hashes, cancellation, restart persistence, journal
immutability, snapshot hash mismatch and recovery. It does not establish native pipe ACL enforcement,
Windows service restart, reboot, sign-out behavior or scheduled Assistant access.

For the serialized fake-server negative test, the coordinator first stops the
genuine Collector service and confirms no console worker is active. Then run:

```powershell
./collector/windows/Test-PipeSquatting.ps1 -CollectorExecutable 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' -EvidencePath 'C:/admin/collector-evidence/pipe-squatting.json'
```

The evidence parent directory must already exist and the output file must be
new. The script briefly hosts a user-ACL-protected fake pipe inside PowerShell,
starts the real CLI, and verifies `untrusted_pipe_server`, exit status 1 and zero
request bytes received. It never stops/starts a service or sends a publication
request. Its process and pipe are closed in cleanup. Restore the real service
and repeat authenticated health after this test. Merely parsing this helper is
not a native negative-test pass.
