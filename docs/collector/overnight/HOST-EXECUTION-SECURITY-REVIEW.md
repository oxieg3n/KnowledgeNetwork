# KnowledgeNetwork host execution: independent security review

## Latest: owner task started; new control pipe repair pending

The checked continuation installed dispatcher 86b94a...; FORGE health passed with
twelve fixed commands, the accepted nonadmin bridge SID and unchanged host pin.
The owner reports the limited task Running. Actual pipe reconciliation was
BLOCKED before transmission. A genuine restricted-token test identified the
missing FILE_READ_ATTRIBUTES grant: 0x120103 fails with Win32 error 5; 0x120183
succeeds and still denies actual additional pipe-instance creation.

Source fixes cover that grant, early-disconnect handling, unread-reply retention,
and exclusive Windows HTTP binding. Two fixed task status/start commands use
native definition/DACL checks and a nonconnecting pipe probe. New private startup
evidence is redacted and bounded. These fixes are not yet deployed; see the
[current repair and evidence](V9-NARRATOR-CONTROL-REPAIR.md).

The repair's privileged bootstrap is limited to a never-used controller: native
identity/task association, a held process handle, and a zero-row SQLite writer
lock are required through one stop and confirmed exit. No direct kill or stop
retry is provided. File replacement/rollback require a disabled task with zero
instances. Existing unmanaged narration, Gateway, routes and worker data remain
outside that transaction. Earlier sections below retain their historical scopes.

## Current continuation: controller source reviewed; approved policy applied

Eight fixed narrator-control operations are implemented and source-tested with
one identity-checked local pipe and a limited-owner task bootstrap. Protected
source/interpreter/metadata, owner-only private descendants, anti-spoof checks,
query-only process/token grants, no unowned listener adoption and durable
uncertain UUID recovery were independently reviewed. Native FORGE task fixtures
verified actual descriptor/default RunLevel behavior and limited-owner query
permissions; all disposable tasks/folders were removed. New BLACKHAT-BASE
controller installation/pipe acceptance remains NOT TESTED; the live dispatcher
still has four diagnostic operations. See [the contract](../narrator-control.md).

The owner separately approved exact v5 tailnet policy. One ETag-conditional API
update was applied and post-verified. Approved/stored byte hashes differ only
through verified exact typed-object normalization. Official20 tests/400 valid
assertions and10 post-apply previews pass. Current permissions and explicit
maintenance/port0 limitations are documented in the
[policy review](V9-TAILNET-REMEDIATION.md). No narrator route, host process,
Gateway/configuration or firewall was changed. Publication stays PAUSED.

The approved API write succeeded, proving the supplied credential is not
read-only despite its target name; replace/revoke it for ongoing least-privilege
audits. No other mutation is authorized. New private API/policy evidence and an
unchanged-key/pinned controller config use a protected owner-profile namespace;
the unsafe C:/admin ancestor was not silently modified. All prior evidence and
rollback remain. The earlier sections retain their historical stage labels.

## Update: actual installed endpoint accepted from FORGE

November 15: coordinator executed the native client tests after owner bootstrap.
Health, fixed PowerShell SID self-test and native9443 availability returned PASS.
Empty/unknown/argument/path commands, PTY, subsystem, direct/reverse forwarding,
wrong authentication key and missing host pin were rejected. Independent review
read installed configuration and private receipt evidence without executing host
commands. The forwarding test explicitly overrode client ClearAllForwardings
only for the negative probe; production configuration remained unchanged.
Shared Gateway config digest and reviewed private policy digest are unchanged.

Accepted scope is four diagnostic operations under the dedicated nonadmin SID.
The remote narrator/service-management objective remains incomplete; no generic
shell or privilege extension was added. A real wrong-source peer test, host
disconnect/long-running timeout, reboot/restart and rollback remain NOT TESTED.
One closed-channel request has PASS then generic response-delivery failure in
audit and is not counted as received success. HTTPS9443 remains BLOCKED by the
existing broad grant; SSH acceptance does not override that access-control gate.

The investigation below is the preserved pre-bootstrap baseline, not a statement
that no subsequent native connection occurred.

November 15, 2026. Read-only investigation of authorized project files and the
existing host SSH configuration through redirected storage. No SSH connection,
credential read, host command, account/service/configuration change or inference
was performed. Publication remains PAUSED.

## Existing access and bootstrap finding

FORGE has the Windows OpenSSH client. Redirected BLACKHAT-BASE C/D files are
accessible, but file access is not remote command execution. The observed host
OpenSSH configuration is dedicated to the Universal Gateway Android worker:
key-only authentication, one source-restricted worker identity, a fixed Gateway
forced command, no PTY, and one narrowly allowed reverse-forwarding exception.
No independently authorized KnowledgeNetwork execution endpoint was established
by the inspected SSH/project inventory. No Gateway identity/key was used.

The host also has a signed Gateway maintenance channel and a fixed SYSTEM
poller. Its scope is the Gateway worker, not this project. It cannot be treated
as a general project administration endpoint or reused to bootstrap this one.
No signer/request payload/private key was read.

**Must preserve the shared SSH configuration byte-for-byte.** The maintenance
implementation accepts only its two approved complete SSH templates and checks
the exact Gateway-only effective user allowlist. Adding a KnowledgeNetwork user
or Match block to that file would break this existing maintenance contract even
if the Gateway forced command otherwise appeared unchanged. Consequently a
shared-daemon config extension is not an acceptable bootstrap here.

Observed baseline SHA-256:

| File | Digest |
| --- | --- |
| Existing `ProgramData/ssh/sshd_config` | `39f452458c454ea6906015862774b3d73e2d71e16852de58c767ae178bd3794d` |
| Gateway `worker-ssh.ps1` | `818fee3f012b68760940c1d70a5ea5a12776ae0fbec565b3732b2521aebb5309` |
| Gateway maintenance `channel.ps1` | `251576fe52dd3b4b885a83ee6eeae6b45fb6b8157899145a63a48593746ea164` |

Private source addresses, account SIDs and configuration contents remain private.
The existing host public-key fingerprint was read from its `.pub` file for the
coordinator; no trust-on-first-use or private host-key access was used.

The technical bootstrap requirement is one elevated host-local setup of an
independent project identity and isolated restricted transport/configuration.
There is no existing authorized execution path in this session that can perform
those privileged operations. Standing authorization supplies permission, not
credentials or an execution channel. A separate supported SSH instance or another
equally constrained transport must avoid changing/restarting the Gateway daemon.

## Required boundaries for the new endpoint

Use a dedicated nonadministrator identity and a fresh key, with actual host-key
pinning and source restriction to the verified FORGE private address. Existing
broad tailnet grants do not establish FORGE-only network access. The narrator
HTTPS9443 route remains separately BLOCKED until effective policy prerequisites
are satisfied; this bridge must not silently repair or relax that policy.

The login identity must not be able to replace dispatcher code, its interpreter,
approved script manifest, executable parents or privileged configuration. Launch
Python with isolated imports and a fixed full interpreter path; a safe command
allowlist is ineffective if user-writable modules can execute before dispatch.
Project output/audit storage must be separated from administrator-owned code.

Exact original-command tokens only: no shell, PowerShell expressions, arbitrary
paths, commands, scripts, environment injection, PTY, SFTP/SCP subsystem, agent/
TCP/stream-local forwarding or user rc execution. A forced command alone does
not prevent SSH forwarding; transport configuration must also deny it. Validate
the effective configuration with the installed Windows daemon, not merely an
upstream example or parser.

All process handlers need fixed reviewed executables/scripts, bounded input and
output, deadlines, owned process-tree cancellation, and audit records that omit
request text, bearer values and raw private paths. Unknown cancellation outcomes
must hold execution rather than retry. Invalid commands must be denied before
any side effect. File handlers must enforce canonical containment/reparse-point
and replacement defenses; a string prefix or current directory is insufficient.

The current narrator bearer is user-scoped Credential Manager data under the
owner account. A new dedicated SSH identity cannot simply read it. Any later
authenticated narrator handler needs explicitly provisioned project credentials
for its actual identity or a separately reviewed narrow worker boundary. Do not
impersonate the owner or extract unrelated credentials to bridge that gap.

## Acceptance matrix and evidence limits

Before deployment, test exact allowlisted success, invalid/empty/mixed-case or
shell-composed commands, bounded request framing, extra fields, path traversal,
UNC/device/reparse escapes, code replacement, timeout/cancellation and audit
redaction. Native acceptance must additionally prove the real remote Windows
identity is nonadmin and the allowed handler actually ran on BLACKHAT-BASE.

Verify key-only/no-password, host-key mismatch rejection, wrong key/source
denial, PTY/subsystem/forwarding refusal and unchanged Gateway baselines. Preserve
new endpoint rollback assets, test the actual startup configuration, and prove
that stopping its service/instance does not affect the existing Gateway daemon.
No successful local unit test may be reported as an installed endpoint test.

PASS: scoped file/config/source inspection, Gateway noninterference finding,
public host-key fingerprint read and baseline hashes. BLOCKED: existing suitable
host execution access and privileged bootstrap channel. NOT TESTED: new endpoint
deployment, Windows identity/privileges, remote commands or native denials.
Ponytail FULL and installed review skill applied; new code review follows when
the separate dispatcher/bootstrap changes are ready.

Primary references consulted: [Windows OpenSSH configuration](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration)
and [OpenSSH server configuration](https://man.openbsd.org/sshd_config).
Windows-specific supported options and actual installed behavior still require
native validation; upstream Unix support alone is not acceptance evidence.

## Independent review of the prepared implementation

Reviewed `collector_host_exec.py`, its connected tests, and the isolated
`Install-KnowledgeNetworkHostExec.ps1` bootstrap as they were prepared. These
are source/procedure findings, not remote host acceptance.

The chosen design uses a separate named SSH service/configuration on its own
tailnet-bound port, a new nonadmin account/key, and no shared-sshd edit/restart.
The official [Win32 OpenSSH considerations](https://github.com/PowerShell/Win32-OpenSSH/wiki/Various-Considerations)
document custom service registration; the installed host's actual independent
service startup still needs native proof. The existing host identity is pinned
through separately read public-key evidence.

Concrete issues found during review and corrected in the prepared source:

- The interpreter trust walk originally omitted native modules under the base
  `DLLs` directory and venv-adjacent runtime files. It now checks those trees,
  effective owner/write rights and reparse points, alongside isolated imports.
- An absent project parent could be race-created beneath ProgramData. Bootstrap
  now creates a known-new parent exclusively, protects it, and revalidates parent
  and execution-root trust before staging privileged files.
- A PowerShell expression joined the two source-address-complement ranges into
  one string. Explicit range expressions and boundary/count checks correct it.
  The dedicated allow plus explicit other-source block prevents an unrelated
  broad program allow from silently exposing this new port.
- Dispatcher token elevation alone would miss filtered administrator membership.
  It now checks the Administrators group, including deny-only membership.
- The audit append path now rejects hardlinks/reparse points, checks opened file
  identity, locks bounded appends, and fails closed at its retained size limit.
- Success now requires job quiescence; source tests cover an owned descendant
  dying when its dispatcher exits, not merely the immediate helper's exit.
- Rollback validates the dedicated firewall action/address/port/program filters
  against its private receipt before removing them, preserving externally
  changed configuration for review. It retains files/evidence and disables only
  the exact created identity rather than deleting data or resetting the Gateway.
- Effective firewall checks now require enabled ActiveStore profiles, compatible
  local-rule merging/inbound settings, running firewall services, and effective
  allow/block rule filters. Stored but unenforced rules cannot count as source
  isolation. The bootstrap does not enable profiles or relax existing policy.
- The final listener must match the actual dedicated SCM service PID, executable
  arguments and LocalSystem service identity before startup is reported. The
  remote dispatcher remains the separate nonadmin account.

The four exact initial commands are read-only `health`, fixed PowerShell
`self-test`, `native-port-9443`, and retained-snapshot `narrator-status`. They do
not accept arbitrary paths/scripts or provision the owner's credentials. A
retained narrator snapshot is explicitly not authenticated live health. This
initial set does not itself implement the full future narration/service update
workflow; additional capabilities require their own fixed reviewed handlers.

No remaining concrete dispatcher security defect was found in this bounded
source review after those changes. Dispatcher specialist reports 18 focused
checks, including actual FORGE Windows process/job, timeout and output-bound
fixtures; this reviewer reused that evidence without repeating it. Those are
not a successful host SSH connection, wrong-source network test or installed
nonadmin execution proof. Native bootstrap, remote identity/command denials,
effective firewall behavior, listener/service ownership and rollback acceptance
remain NOT TESTED until the one privileged owner bootstrap and subsequent real
connection tests. The narrator9443 policy blocker remains unchanged.

Final reviewed source digests:

| File | SHA-256 |
| --- | --- |
| `collector_host_exec.py` | `637c92f13126c2ccb5a2eeb888cc4ac48a8a540cf74652f96dc268ce12600bf2` |
| `Install-KnowledgeNetworkHostExec.ps1` | `29038f0827bb31f2673ae5c4fb360f900c664ced6ce9b578c75d7cd6e777d547` |

No remaining concrete must-fix source finding was identified at those digests
within the stated initial-command scope. This verdict is not host deployment
acceptance or a claim that broader standing-authorized operations are already
implemented. Review drift if source changes before packaging/bootstrap.

## Actual bootstrap trust failure and runtime isolation follow-up

The owner-run bootstrap stopped at its trust guard before creating the project
execution root, account, service or firewall rules. The subsequent private native
ACL diagnostic identifies the canonical venv Python executable as broadly
modifiable by Authenticated Users. This reviewer read the complete retained
diagnostic: four access entries and no deny entry. The observed broad Modify
permission is genuine exposure, not the earlier hypothetical conservative
allow-versus-deny false positive. Private SDDL, owner identity and complete ACL
contents are not reproduced here. No original ACL or narrator file was changed.

The correct response is to keep the guard. A protected project-only interpreter
can isolate the SSH dispatcher from the existing narrator environment; the
canonical narrator keeps its original interpreter, script, model and settings.
Do not claim that copying an unverified writable runtime establishes provenance.
The proposed package must have an exact official source/hash, retained notices,
strict archive validation and immutable administrative ownership before any
execution. The existing protected-parent and loader-search-directory checks
remain mandatory.

Official [Windows release listing](https://www.python.org/downloads/windows/)
and [embeddable runtime guidance](https://docs.python.org/3/using/windows.html#the-embeddable-package)
were consulted. The embedded distribution is intended for application packaging
and includes a restrictive `._pth` search-path configuration. Its exact contents
must be reviewed, with no enabled site import or outside path. Current proposed
runtime packaging/bootstrap changes still require independent source review and
actual host acceptance; the earlier source digests are historical checkpoints.

## Protected dispatcher runtime revision reviewed

Reviewed revised bootstrap SHA-256
`5f825db4a27320745d27cd556a93923444c2ba7a433188a95fae02fa08140940`.
It uses official CPython3.14.10 Windows amd64 embeddable archive SHA-256
`90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`.
This reviewer independently matched the digest to the
[official release file table](https://www.python.org/downloads/release/python-31410/).
It is a current maintenance/security binary release, unlike the superseded
3.13 binary line. No narrator runtime or reference setting is replaced.

The bootstrap captures bounded archive bytes under a read-only file lease and
hashes those same bytes before archive parsing. It prevalidates all37 members
against exact flat names, rejects separators/ADS, duplicate/case-variant names,
directories/reparse/symlink attributes and oversized/count mismatches. Extraction
writes only new regular files into a freshly protected project runtime directory,
with per-member content hash readback. ZIP metadata is not applied as filesystem
links or permissions. Existing runtime files cannot be overwritten.

Protected parent/root checks precede extraction. Before interpreter execution,
the bootstrap requires valid Python Software Foundation publisher signatures
on the executable/core DLL, immutable runtime-file/ancestor ACLs, and precisely
the two active `._pth` entries for its local standard-library ZIP and protected
runtime directory, without site import. Original license/catalog files are
retained. The dedicated nonadmin identity receives only read/execute runtime
access; mutable audit files remain separate.

No remaining concrete must-fix was found in this bounded archive/runtime review.
The coordinator reports four passing native bootstrap-helper tests (including
malicious archive/no-overwrite cases), production extraction of all37 official
members, valid PSF signatures, and18 dispatcher tests using the actual new
interpreter on FORGE. This reviewer reused those checks rather than duplicating
them. Real host bootstrap, account access, separate SSH startup, remote identity
and negative network tests remain NOT TESTED.

This isolates the dispatcher only. The original narrator executable's broad
write permission remains unchanged. A later privileged handler must not execute
that original mutable environment as privileged code. The original narrator's
local-code trust boundary and the pending narrator9443 policy restriction remain
separate from this protected dispatcher-runtime remedy.

## Narrow prepared-runtime continuation review

The next owner-run bootstrap prepared its protected runtime, then Windows
rejected the account description because it exceeded the actual48-character
parameter limit. No account SID was recorded. This is a bounded interrupted
pre-account stage, not a completed execution endpoint or permission to delete
and reinstall its evidence.

Reviewed continuation source SHA-256
`e93be3b374735c1c039d094c1f640ee20926cc5c63142e6fe14c66d39391599f`.
The product-preserving description is now34 characters. Explicit
`-ResumePreparedRuntime` accepts only the exact15-field pre-account receipt,
null SID, approved addresses/source digests/version/status and unchanged shared
SSH backup. Current account/service and both persistent/effective firewall
inventories are queried with terminating errors; provider failures cannot count
as absence. Any actual dedicated resource already present stops continuation.

The root must contain exactly its five expected pre-account entries; runtime
must contain only its Python directory and37 approved members. Native ownership,
ACLs and reparse checks run again. `VerifyExisting` independently hashes existing
bytes against the captured official archive, compares retained runtime metadata,
and preserves changed files rather than repairing them. The pinned rollback,
shared backup, runtime and original metadata are not overwritten during resume.
Signatures, import isolation and version gates still precede account creation.
This switch is not a general installer-repair or progressed-state retry mode.

No remaining concrete must-fix was found in this bounded continuation review.
Coordinator reports six passing native helper checks, including the real Windows
description limit, invalid receipt fields and corrupted-runtime rejection without
repair; prior dispatcher checks remain unchanged. Actual host continuation and
remote connection/identity/denial tests remain NOT TESTED. This reviewer made no
source or host changes and did not run the continuation.

## Exact pre-network completion review

After account/configuration preparation, Windows rejected the firewall Program
path format. The coordinator reproduced that failure with disabled temporary
FORGE rules and confirmed canonical backslash paths succeed; those probe rules
were removed. This is separate from the still-pending live host completion.

Reviewed `Complete-KnowledgeNetworkHostExec.ps1` SHA-256
`080bbe62410d1e44c0bef146aa4c09e05e35819141fee1c05e5a5b30980d5705`.
It admits only the exact reconciled pre-network state, not arbitrary progressed
or repair states. It requires the existing enabled account's matching SID and
nonadmin/Users membership; exact scalar receipt/config fields; expected root,
runtime and empty output directories; unchanged rollback/shared backup; verified
runtime/dispatcher/key bytes; matching SSH config/effective restrictions; and
absence of project services and rules in persistent/effective inventories.
Mutable audit ACLs are validated separately against their exact protected three-
entry contract instead of weakening immutable-code trust checks.

Two concrete draft issues were corrected during independent review: the old
PowerShell JSON-array wrapper comparison was replaced with the pinned strict
semantic runtime-manifest helper, and scalar/date/range type checks now reject
collection-shaped values that PowerShell comparison coercion could otherwise
accept. No retained manifest is rewritten to make a comparison pass.

The only mutation tail is captured from the same hash-pinned reviewed bootstrap:
canonical-program firewall rules, their effective checks, and the new dedicated
service. It recreates no account or runtime and overwrites no key/configuration.
Existing Gateway daemon/configuration and tailnet policy remain untouched.
No remaining concrete must-fix was identified at that digest. Actual host
completion, effective wrong-source denial and authenticated remote identity are
still NOT TESTED; source review is not operational acceptance.
