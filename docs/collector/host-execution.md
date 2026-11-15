# Restricted Knowledge Network host execution

This endpoint is separate from the Universal Gateway Android worker. The owner
authorized project-scoped host execution on November 15, 2026. Authorization
does not create credentials, native execution access or a security-test result.
Publication remains PAUSED, and PR20 stays draft/unmerged.

## Endpoint and identity

Use the installed official Windows OpenSSH executable as a **second** Windows
service named `KnowledgeNetworkHostExec`, with a separate admin-owned config
and a dedicated nonadministrator account `kncollector_exec`. Proposed port22230
is checked natively before creation; the only bind is the actual BLACKHAT-BASE
Tailscale IPv4 address. No shared `sshd` restart, global registry modification,
Gateway configuration edit or existing key reuse for client authentication.

The Gateway maintenance code pins its complete shared configuration and exact
AllowUsers profile. Adding a Match stanza there would violate that contract,
even if Gateway's effective forced command stayed unchanged. It must not be
used as a shortcut. The project daemon reads its own `-f` configuration and the
existing host Ed25519 key read-only. Its public host identity is independently
pinned on FORGE; private host keys never leave BLACKHAT-BASE.

Microsoft documents [alternate configuration files and key-only Windows access](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration).
The official Win32 OpenSSH project documents [custom Windows service names](https://github.com/PowerShell/Win32-OpenSSH/wiki/Various-Considerations).
These establish a supported implementation choice, not successful startup of
this machine's installed binary. Actual `sshd -t`, effective `-T` restrictions,
native service startup and remote acceptance remain mandatory.

## Fixed dispatcher boundary

Runtime layout is fixed beneath
`C:/ProgramData/KnowledgeNetworkCollector/HostExec`:

- `runtime/collector_host_exec.py`: reviewed standalone standard-library code.
- `runtime/python/`: separately pinned protected CPython embeddable runtime for
  the dispatcher only; never the narrator environment.
- `config.json`: exact expected execution SID, FORGE address and executable pins.
- `authorized_keys`: only the newly generated project Ed25519 public key.
- `sshd_config`: isolated server configuration, no subsystems or includes.
- `audit/`: the dedicated account's only project-writable directory.
- `receipts/`: optional admin-maintained sanitized narrator snapshot.
- `bootstrap-receipt.private.json`, original shared-config backup and rollback
  script: retained private bootstrap evidence.

All code/configuration is admin/SYSTEM-owned and read-only to the login identity.
The forced command invokes only the protected dispatcher interpreter with `-I -S -B` and
the fixed dispatcher file. No PYTHONPATH, user site, `.pth`, bytecode write or
caller-selected script is involved. Only exact allowlisted SSH command tokens
are accepted. Arbitrary shell/PowerShell, PTY, subsystems, client environment,
user rc, X11, agent/TCP/stream forwarding and passwords are denied by server and
dispatcher boundaries. OpenSSH invokes a Windows outer shell; bootstrap accepts
only default/trusted system cmd.exe with its supported `/c` option and no system
AutoRun. A different configured shell is a precise bootstrap blocker, not a
reason to change Gateway's global shell or trust profiles.

Initial operations are `health`, `native-port-9443`, `narrator-status` and
`self-test`. The last executes a fixed PowerShell SID echo with no caller code.
Narrator status reads an optional bounded sanitized snapshot; it cannot read
the narrator owner's Credential Manager, canonical reference, private spool or
arbitrary logs. Missing snapshot fails explicitly. The existing narrator's
credential belongs to a different user and is not automatically available to
this account. No privilege, narrator API submission, model load, generic file
transfer or Tailscale administration handler is supplied by this bootstrap.
Future operations need concrete reviewed handlers and tests under the same
closed boundary, not an argument accepting arbitrary scripts or commands.

The dispatcher verifies the execution SID, FORGE source and executable hashes,
uses a Windows Job Object for owned child termination, bounds time/output and
writes redacted audit events. Its tests distinguish fixed-operation execution,
denials, timeout and output bounds. Local tests are not remote SSH acceptance.

## One-time privileged bootstrap

If the trust preflight rejects a writable path, stop rather than changing the
trusted-principal set or narrator/drive ACLs. The read-only
`host-tools/Inspect-KnowledgeNetworkHostExecTrust.ps1` can identify the first
blocked path and full applied DACL privately. Its reviewed bootstrap bytes are
captured once, hash-verified and reused for both AST parsing and the read-only
preflight; it never evaluates account/service/firewall setup. The AST command
check is a regression guard, not a general PowerShell sandbox. A pinned launcher
is staged for native host execution; redirected-drive ACL metadata is not proof
of actual host permissions. Resolve the exact evidence before retrying setup.

`host-tools/Install-KnowledgeNetworkHostExec.ps1` is the one elevated host action
when no existing independently authorized endpoint can perform account/service
setup. Root supplies the actual private `HostAddress`/`ForgeAddress`, dedicated
public-key file and SHA-256, reviewed dispatcher file and its exact SHA-256,
and staged `RuntimeArchiveFile`. No secret is
accepted as a script argument. The account gets a cryptographically random
unreported local password; SSH supports publickey only. FORGE retains its separate
private key in a protected local store, never the emulator key.

Preflight refuses preexisting project root/account/service/rules and occupied
port. The canonical narrator venv failed its native trust check because
Authenticated Users can modify its launcher. That is a real boundary, not
permission to change the working narrator ACLs or ignore the check. The
dispatcher now uses a separate protected runtime; narrator files, settings and
permissions remain intact.

Bootstrap captures staged ZIP bytes once under a read lock, verifies the fixed
official digest before parsing, and extracts only the exact 37 flat regular
members into a new protected `runtime/python` directory. It rejects path/ADS/
drive syntax, directory/symlink/reparse attributes, case-insensitive duplicate
names, unexpected entries, oversized archives/members and existing target files.
Every new file hash is compared with its entry bytes. No archive metadata or
package installer is executed, and the original Python license is retained.

Pinned runtime: [CPython 3.14.10 Windows x64 embeddable package](https://www.python.org/downloads/release/python-31410/),
official URL `https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip`,
SHA-256 `90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`.
The release page publishes that digest and a Sigstore bundle. Root's actual
download matches; Authenticode on `python.exe` and `python314.dll` reports Valid
with Python Software Foundation organization. Bootstrap repeats native publisher
checks before executing the interpreter. The retained `python314._pth` is
accepted only with `python314.zip` and `.` as active lines; `import site` remains
commented. No external/user import path is permitted. File/path ownership and
ACL checks precede a fixed version/no-site/isolated startup assertion. This
runtime does not import VoxCPM2 or replace model inference.

Reparse points and nontrusted write, delete-child, ownership or DACL control
stop setup; it does not repair existing system or unrelated ACLs. It separately protects a newly created product
parent and refuses an attacker-raced existing directory. Existing parent/data
ACLs are never modified. Redirected-drive ACL metadata is not used as native
proof. Actual native ACL checks must pass inside bootstrap.

The dedicated firewall ALLOW has only the exact FORGE source, host tailnet local
address, TCP22230 and fixed sshd executable. A matching dedicated BLOCK covers
the IPv4 complement of FORGE, so a preexisting broad program ALLOW cannot admit
other source addresses. Both rules are read back and checked before service
start through `ActiveStore`; enabled effective profiles, local-rule merge and
firewall services must also permit enforcement. Disabled/centrally suppressed
profiles or rules fail without changing existing policy. Microsoft documents
[block-rule precedence and policy merging](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules).
There is no IPv6 listener, public address bind or change to unrelated
firewall rules. SSH `AllowUsers` and authorized-key `from=` independently bind
the exact source. Tailnet policy is still evaluated at its actual scope; this
new endpoint must not be described as narrowing the narrator9443 policy.

Shared Gateway configuration is backed up and hash-checked before/after without
being rewritten or restored. Native config validation precedes firewall/service
creation. Effective configuration must show every required restriction. Service
startup is followed by a single exact-address listener check; unexpected binding
stops only the new service. On any failed/uncertain bootstrap, preserve receipt
and files and reconcile before another attempt; do not select another identity
or port to bypass the outcome.

One observed partial preparation is explicitly resumable with
`-ResumePreparedRuntime`: the protected runtime was completely extracted and
verified, then Windows rejected the original account-description length before
creating any account. The corrected full-product description fits the native
48-character limit. Resume is accepted only for that pre-account state: exact
five root entries, one `runtime/python` child, 37 original runtime files, exact
in-progress receipt with null execution SID, matching host/source/dispatcher/
archive/shared-config pins, unchanged rollback/backup/runtime manifests, trusted
owners/ACLs, and actual absence of the account, service, project firewall rules
and listener. Query errors fail rather than counting as absence. Existing bytes
are rehashed against the same official ZIP using verification-only mode; no
runtime, receipt or rollback artifact is overwritten during verification. The
publisher/import-isolation checks run again before continuing at new-account
creation. Any later-stage artifact, changed field/byte, existing identity or
uncertain outcome stops this narrow resume; it is not a general repair mode.

## Acceptance and rollback

Keep one current launcher and the payloads it actually references. After a
replacement is verified, remove obsolete troubleshooting scripts and duplicate
extracted test runtimes with exact project-path checks. Retain compact receipts,
keys, active runtime/package, original backups and rollback evidence; never
classify approved media or uncertain job output as disposable staging. Prefer
a single-command owner launcher over multi-line pastes for unavoidable bootstrap
work. The latest handoff names the active path and records completed cleanup.

Record separately: bootstrap native ACL/config PASS; account nonadmin identity;
source/key/host pin PASS; actual FORGE health/self-test; denied shell, PTY,
forwarding, subsystem, malformed command and wrong-source/key cases; native
timeouts/process cleanup; redacted audit receipt; Gateway unchanged. Do not
claim a runtime or remote connection result from source compilation alone.

Bootstrap writes `rollback-bootstrap.ps1` before account/network mutation and
records the actual created SID. Rollback removes only this named service and
the two project firewall rules after checking their descriptors against the
receipt, disables only the exact dedicated SID, and retains all files/logs.
It never deletes a project directory or reference/model/spool, restores an old
database, touches the shared `sshd` service, or resets Tailscale. Descriptor or
identity drift stops rollback for review rather than overwriting external edits.
An incomplete account-creation receipt is a manual reconciliation condition.

## Remaining production gates

The reviewed private tailnet policy currently permits more than FORGE to reach
the proposed narrator9443 route. That route remains BLOCKED irrespective of
whether project SSH works or native9443 is free. Preserve routes443/8443 and
Gateway; no Funnel, public firewall, TLS bypass or policy weakening. Once a
secure project endpoint is actually accepted, use only its supported handlers
for remaining project work. Privileged narrator-service/network handlers require
their own closed implementation and evidence before use. Reboots, publication
and merging PR20 remain excluded.

Ponytail FULL and the installed review skill govern this small bootstrap and
closed dispatcher. No new package, general remote-control framework, UI, model
inventory, inference or media render is needed for its source preparation.
