# Owner-session media companion

The Knowledge Network Collector implements a typed bridge from its Windows
service to a one-shot Python companion in the configured owner's Windows user
session. The service owns the durable queue and SQLite journal. The companion
claims one job and calls the existing direct VoxCPM2 or OpenShot adapter.

This document describes the implemented contract. Consult the current
[handoff](overnight/HANDOFF.md) for installed build hashes, actual native tests
and remaining acceptance holds. Source support, an enabled capability and a
successful technical job are separate from verified host narration, listening,
editorial approval and real scheduled Assistant/Dot connectivity. Publication
remains paused.

## Supported jobs

All submissions use the existing version-1 envelope with `job_type`, a stable
`idempotency_key`, and typed `inputs`. Existing optional UTC creation/expiry and
priority fields retain their validation. Identical retries return the same job;
changing the request under its key is rejected. Keep the original request file
for recovery.

| Job type | Exact inputs |
| --- | --- |
| `diagnostic.echo` | Existing bounded `nonce` input. |
| `research.snapshot` | Empty object; reads the configured immutable staging snapshot. |
| `narration.generate` | `text`: nonempty string of at most 12,000 Unicode characters; optional `segments`: 1–16 nonempty strings, total at most 12,000 characters, matching the full text after whitespace normalization. |
| `editor.operation` | `session_id`: actual 32-character lowercase hexadecimal native session ID; `operation`: one of the four operations below; `request`: its exact typed object. |

| Editor operation | Exact request |
| --- | --- |
| `inspect` | `{}` |
| `apply` | `commands`: 1–128 existing adapter commands; `base_revision`: nonnegative integer. |
| `save` | `path`: bounded local absolute project path. |
| `reopen` | `path`: bounded local absolute project path; `sha256`: exact lowercase 64-character project digest. |

Apply commands retain the existing `method`, `params` and optional `as` envelope,
including nested native `$ref` values. The service accepts only the existing
method/parameter allowlist and bounded JSON. The owner-session adapter further
checks values, registered session ownership, vault confinement, media and native
expected revisions. Save/reopen paths and imported assets must pass those vault
checks. Executables, provider modules, narrator identity, credentials and remote
endpoints come from reviewed local configuration, never job fields.

There are no queued editor start, close, undo or export operations. Capabilities
list exactly `inspect`, `apply`, `save`, `reopen`, and keep
`editor_export_jobs_enabled=false`. Existing direct development tools have their
own documented scope; their availability does not add service job operations.

## Enablement and execution context

New service installations default to the companion bridge being disabled.
The canonical installed CLI supports these administrator maintenance commands:

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' install-service --enable-companion
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' install-service --disable-companion
```

The optional owner SID remains supported. The flags are mutually exclusive;
omitting both preserves an existing setting or defaults off. Installation
retains canonical-path, administrator, package-integrity, LocalService and
authenticated stable-health checks. These commands reconfigure the local
service, so use them within the coordinator's serialized maintenance window.

The underlying service flag is `serve --enable-companion`. Capabilities report
the actual flag through `narration_jobs_enabled` and `editor_jobs_enabled`.
Remote narrator readiness is a separate check; enabling typed jobs does not
verify a host route, model, license or credential.

Start one companion explicitly as the configured owner in a Windows user
session. From the repository with its development environment available:

```powershell
$env:PYTHONPATH = 'src'
$collector = 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe'
$collectorHash = (Get-FileHash -LiteralPath $collector -Algorithm SHA256).Hash.ToLowerInvariant()
& ./.venv/Scripts/python.exe -m youtube_ops.collector_companion --once --collector-sha256 $collectorHash --private-spool 'C:/admin/collector-v9/companion-spool'
```

The spool path is an example: create/verify the actual private local spool and
use the installed hash confirmed by the deployment receipt. The companion
requires a user session, rejects session zero/service identities, verifies the
canonical installed CLI and its SHA-256, and checks the private spool ACL.
It exits after one claim, or returns `idle` when no claim is available. It
does not install an autostart task, polling daemon or second scheduler.

LocalService keeps the database under its restricted ProgramData ACL. The
companion uses the owner's private editor vault/session registry and protected
narrator credential store. It does not need writable access to the database.
Closing the dashboard leaves the service running; companion availability after
sign-out/reboot or scheduled Dot access requires separate runtime evidence.

## Lease and pipe contract

The local Windows pipe is ACL-restricted to the service identity and configured
owner. It rejects remote clients. The CLI authenticates the connected server's
process/image and registered service or same-user identity. The Python companion
also verifies its installed CLI and current user session. Authorization trusts
the configured owner account; lease tokens bind its claims to one running job.

Frames are bounded to **512 KiB**, read in 4 KiB chunks with strict UTF-8
validation. Each connection executes one frame. Native project dumps, audio,
credentials and arbitrary commands are outside the result contract.

| Pipe operation | Request fields after `schema_version=1` and `operation` | Result |
| --- | --- | --- |
| `companion.claim` | None. | `job`: ordinary metadata-only job record; `inputs`: exact typed inputs; `lease_token`: fresh 32-character hexadecimal token. All three are null when nothing can be claimed. |
| `companion.heartbeat` | `job_id`, `lease_token`. | `cancel_requested`: boolean. Renews the 60-second lease. |
| `companion.complete` | `job_id`, `lease_token`, `result`. | Updated ordinary job record after validation and durable completion. |

The companion heartbeats every **10 seconds** by default. A single global media
lease covers both narration and editor jobs. The service stores its token hash;
ordinary `jobs.get` results and journal events omit the secret and job inputs.
The claim response and temporary lease files must stay private.

Implemented maintenance-client syntax is:

```text
kn-collector.exe companion-claim
kn-collector.exe companion-heartbeat ABSOLUTE_PRIVATE_JSON_FILE
kn-collector.exe companion-complete ABSOLUTE_PRIVATE_JSON_FILE
```

Heartbeat files contain exactly `job_id` and `lease_token`; completion files add
`result`. The CLI adds the protocol envelope. Tokens are file/body values,
never command-line arguments. Files are bounded to 512 KiB and must be local,
non-reparse paths with trusted ownership and a private DACL. Trusted-owner
`OWNER RIGHTS` entries are supported; NULL DACLs, public access and untrusted
owners are rejected. The Python companion captures replies privately and removes
its temporary RPC files.

## Completion and cancellation

Every result requires `status`, its fixed `provider` and
`publication_eligible=false`. An optional error is a bounded sanitized code.
Unknown fields, raw paths, narration text and native project/result dumps are
rejected.

| Result kind | Additional fields |
| --- | --- |
| Narration | `provider=voxcpm2_remote`, `narrator_id=oxiegen-narrator`; completed results require `narration_receipt_sha256` and `audio_sha256`. |
| Editor | `provider=openshot_native`, `operation` matching the claimed request; completed results require nonnegative `revision` and `native_receipt_sha256`. |

Completion status `completed` maps to service state `succeeded`. `blocked`,
`failed`, `cancelled` and `reconciliation_required` retain those state names.
Success records technical output digests, never publication or human-review
approval. The owner-session adapters retain full receipts and source evidence
privately.

Cancelling a queued job is terminal and safe before execution. Cancelling a
running media job sets `cancel_requested`; the service waits for the companion's
observed outcome. A local cancellation event does not prove host inference or a
native edit stopped. Known pre-submission failures can complete as blocked.
Uncertain side effects, lost leases or unverified cancellation require
reconciliation. Editor intents/outcomes and native expected-revision checks
protect existing manual edits; they do not make a timed-out native batch atomic.

## Recovery and limits

Schema 1 migrates to schema 2 only after a consistent SQLite backup, integrity
check, durable file flush and SHA-256 backup receipt. Migration is transactional
and preserves stable job IDs, payload digests and events. These backups remain
in the private data directory. Narration and editor jobs share the schema-2
queue and lease columns; adding the four editor operations needs no new DDL.

After restart, only the legacy read-only diagnostic/snapshot jobs are requeued.
Interrupted media jobs enter `reconciliation_required`. A stale 60-second lease
does the same, invalidates late completion and persists a global media hold.
New IDs cannot bypass unresolved possible side effects. Read-only jobs and
service health remain available during that hold.

There is no generic clear, reconcile, replay or expiry-bypass API. Owner/coordinator
reconciliation needs specific evidence of the actual outcome, private evidence
digests, appropriate review and a durable journal record. Preserve database
backups, native/provider intents and media. Never delete a receipt or resubmit
under a new key merely to escape a hold.

This bridge adds no production scheduler cutover or publication route. The four
existing content queues, rights checks, exact-render approvals, receipts and
publication pause retain their separate controls. Actual installed/runtime
proof belongs in the current handoff, including any blocked host or session
lifecycle steps.
