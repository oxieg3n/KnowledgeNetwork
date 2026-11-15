# Restricted owner-context narrator control

This extends the accepted KnowledgeNetworkHostExec dispatcher. It reuses the
existing narrator HTTP server, manifest validator, durable job store and canonical
script runner. It adds neither a narration provider nor a remote shell.
Publication remains PAUSED; PR20 remains draft/unmerged.

## Fixed operations

These source operations are implemented and tested, **not deployed or accepted
on BLACKHAT-BASE**. The live endpoint still has its accepted four-command scope.
After the separately checked protected update, use the existing SSH alias with
one exact argumentless operation:

| Operation | Scope |
| --- | --- |
| `narrator-health` | Actual authenticated loopback health of this broker's owned server; fixed identity/provenance required. |
| `narrator-validate` | Pinned private manifest plus actual artifact and model/ref validation. |
| `narrator-start` | Validate and start the existing loopback server inside the limited owner broker; refuse an occupied/unowned listener or unresolved jobs. |
| `narrator-stop` | Stop only this broker's idle server; refuse pending speech or holds. |
| `narrator-credential-ensure` | Verify this owner's app-specific Credential Manager entry; create only after native ERROR_NOT_FOUND; never export or rotate an existing entry. |
| `narrator-verify` | Check private spool/data ACLs and retained completed WAV digests/PCM, without inference. |
| `narrator-diagnostics` | Owned-server authentication/provenance, missing/wrong bearer rejection; no narration submission. |
| `narrator-reconcile` | Inspect jobs, holds and retained uncertain control UUIDs; never clear, replay or resubmit. |

Example after deployment:

```powershell
ssh -F "$env:USERPROFILE/KnowledgeNetworkCollector-Private/host-exec-client-v1/ssh_config" knowledgenetwork-host narrator-reconcile
```

The SSH diagnostic account remains `kncollector_exec`, nonadministrator. It
cannot provide request text, paths, secrets, Python, PowerShell or arbitrary
arguments. The dispatcher generates the control UUID before forwarding and
retains it in its audit and response. The controller commits started-before-action
and records final owner SID, operation, duration and response digest atomically.
An unfinished request holds further lifecycle/credential mutations. Reconciliation
reports bounded retained UUIDs for inspection. It supplies no unsafe hold reset.

## Owner boundary and local pipe

One limited InteractiveToken scheduled task runs the fixed protected CPython
launcher as the owner. The owner must be logged on; sign-out/reboot recovery is
not accepted. The task has no automatic execution deadline or restart trigger
that would kill active speech. The dedicated bridge cannot edit its task or code.
No writable narrator Python/CLI is invoked as SYSTEM or elevated administrator.
The protected runtime hosts standard-library control/API code; the original
script still launches the unchanged original inference environment.

The fixed local named pipe rejects remote clients and duplicate first instances.
Its DACL permits only owner/admin/SYSTEM and the exact bridge SID. Bridge access
omits FILE_CREATE_PIPE_INSTANCE. Only bounded JSON messages cross it; no pickle
or general file-transfer protocol is present. The client checks pipe owner,
server PID, exact protected interpreter path/hash, owner token and elevation,
with repeated PID verification before transmitting. Query failures fail closed.
Only query-limited access to this broker process and query access to its primary
token are added for the exact bridge SID; no duplicate/impersonate/write rights.
The server reads one bounded frame before identifying its sender through Windows
pipe impersonation, then verifies exact bridge identity before dispatch.

Code, metadata and interpreter stay administrator-owned. The owner's additional
read/execute permissions allow its limited task to import them without granting
write access. Private root and existing ledger/database/sidecar/manifest/audio
ACLs are verified individually; permissive child ACLs cause rejection. Model and
canonical environment permissions are preserved. Same-owner code remains inside
the trusted owner boundary; interpreter pinning does not attest every command
that the trusted owner could launch themselves.

## Existing foreground narrator and credentials

The existing owner-started port39110 process is not broker-owned. It is never
adopted, terminated or sent the owner's bearer by this new controller. Its previous
successful authentication evidence remains valid at that original scope. For a
managed handoff the owner must finish any active job, preserve its receipts and
stop that foreground process deliberately before `narrator-start` can succeed.
The new broker starts no API or inference merely by starting its task.

The owner's existing Credential Manager entry stays in the owner context. This
does not provision FORGE's separate user-scoped client entry, export a bearer or
claim remote authentication. Provision that entry using the existing hidden
client prompt after the private endpoint and policy are accepted.

## Bounds and deployment

Pipe I/O has a180-second deadline and explicit cancellation. Closed/uncertain
delivery preserves the request ID; it does not cause a second action. Model
artifact hashing checks a120-second cooperative deadline between64KiB blocks.
Audio verification checks between bounded files/batches. These checks cannot
preempt a blocked Windows filesystem call. A late action retains an uncertain
receipt and must be inspected. No model or media work is automatically retried.

`host-tools/Install-KnowledgeNetworkNarratorControl.ps1` prepares a narrowly
checked update to the existing protected dispatcher and registers only the new
limited owner task. It requires one elevated owner-side bootstrap because the
accepted endpoint deliberately cannot write protected code or register tasks.
Standing authorization grants permission, not that technical privilege. Stage
captured, SHA-pinned package bytes and run only after source/security tests pass;
never execute an unverified writable staging script as administrator.
The script preserves the old dispatcher, original ACLs and scoped rollback.
Rollback refuses a running broker or changed descriptors, does not kill audio,
and preserves private evidence. No Gateway, existing service/configuration,
firewall or Tailscale change belongs to this bootstrap.

Native cross-account task/pipe acceptance, existing-listener handoff, actual
model validation under the limited owner, service lifecycle and credential
access are NOT TESTED until that host bootstrap and acceptance run. Unit/native
FORGE tests must never be reported as those results.

The [private tailnet remediation review](overnight/V9-TAILNET-REMEDIATION.md)
records the subsequently approved/applied and post-verified v5 policy. That does
not imply narrator-route deployment or live denied-peer acceptance. Recheck live
policy/Serve/native-port state before a later route action; preserve443/8443 and
Gateway. Every further tailnet-wide policy change still needs owner approval.
