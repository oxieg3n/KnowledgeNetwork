# KnowledgeNetwork host execution: independent security review

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
