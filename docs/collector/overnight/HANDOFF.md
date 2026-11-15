# V9 handoff - The Knowledge Network Collector

## V5 policy applied/post-verified; restricted narrator control staged

Branch `feature/collector-v7-overnight`, continuing from accepted checkpoint
`18006d9df188a486ee334f484fe4d9daf6d75ffc`. PR20 draft/unmerged; publication
PAUSED. No Collector rebuild/install, inference, render or public upload.

**PASS actual tailnet remediation after explicit owner approval.** Original
`grants[0]` allowed wildcard source/destination/IP permissions; no overlapping
network ACL/group/tag rule restricted9443. Actual Admin API collection confirmed
five devices/ten addresses and all five advertised/enabled route array pairs
explicitly empty, including no exit defaults. Missing tags were not interpreted
as proof of no tags. SSH and identity configuration were preserved.

V5 passed20 official tests/400 valid same-family assertions and independent
review of10 previews. Owner explicitly answered "Approve v5 policy only",
accepting static-inventory maintenance and reserved TCP destination-port0 limits.
Approved candidate SHA-256:
`c96c6e7c4682625ae1b6e0aba21e52bd9d697b6c76b71d539a8f0cc986235d19`.
Inside-script fresh inventory/routes/baseline checks preceded ONE conditional
POST with live ETag/If-Match and fsynced intent. HTTP200; no update retry or
automatic rollback. Tailscale normalized representation. Stored SHA-256:
`35697bcb6e06a9b2047d6056ab847fcff31f2d054ca8da7ba8e6a97222b10335`.
Independent recursive typed equality proved all approved/returned/stored values,
array orders and five sections equal. Original normalization-blocked receipt
remains intact. Actual stored-policy validation passed again;10 post-apply
previews match approved semantics. Current443/8443/Gateway permissions preserved.
Original rollback policy SHA-256:
`a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c`.
See [the full current policy review](V9-TAILNET-REMEDIATION.md).

New/renumbered destinations and approved subnets need reviewed policy updates;
remove/update the FORGE allowance before IP reassignment. This is not preserved
future wildcard behavior or all-raw-packet equivalence. Native ICMP/live
unauthorized-peer rejection are NOT TESTED. **HTTPS9443 remains OFF.** No Serve,
Funnel, firewall, Gateway, narrator process or shared SSH configuration changed.

Private evidence: `%USERPROFILE%/KnowledgeNetworkCollector-Private/` directories
`tailnet-api-live-002`, `policy-validate-004`, `policy-apply-001`,
`policy-postapply-001`. Host review pack:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001/review/tailnet-remediation-v5`.
Original/candidate/diffs and failed diagnostic attempts retained privately.
The successful approved POST proves the API key has write capability despite
its ReadOnly target name. Replace/revoke it with a strictly read-only OAuth
access token for continuing audits; no further mutation is authorized. The
earlier exposed key must be revoked if not already done; root never used it.
No credential value entered source/Git.

**PASS source preparation; NOT DEPLOYED host control.** Eight exact operations
are implemented through one fixed identity-checked local pipe: narrator-health,
narrator-validate, narrator-start, narrator-stop, narrator-credential-ensure,
narrator-verify, narrator-diagnostics, narrator-reconcile. The limited owner
runner reuses the existing HTTP/store/manifest/credentials. It never runs the
writable inference environment as SYSTEM/elevated, adopts an unowned39110
listener, sends it a bearer or cancels active work on control shutdown. Durable
UUID history includes lost finished replies; no hold-clear/replay operation.
Source/artifact pins, private child ACLs, PCM receipts and audit are checked.
Details: [narrator control](../narrator-control.md).

One elevated host-owner bootstrap remains technically necessary: the accepted
four-command endpoint cannot write protected code/register the task. Standing
authorization already supplies permission. Reviewed sources are staged in host
kit `narrator-control-setup-v1` and `narrator-control-deploy-v1` (139499bytes;
no model/runtime ZIP duplication). Installer SHA-256:
`689a32707edb995b2d6f81d83e7e59aa7fe60ecf89384d0d8572bc1dbd5f2761`;
bundle-manifest SHA-256:
`96d39745cb4e31bc9121a5836f1b73f1e3718e8cfda74541f898e6ac049b004d`.
Run the captured-byte/hash-checked single line in FORGE's
`output/Host-Narrator-Control-Setup.txt` from elevated BLACKHAT-BASE PowerShell.
It starts only the limited controller task, not narration or a route. Preserve
any failure; never blindly rerun. Existing rollback/source remain intact; the
new bootstrap creates checked source/ACL rollback before mutation and refuses
running/queued-task rollback.

PASS:383 repository tests in107.160s;7 skips (5 preexisting FFmpeg,2 opt-in task
fixtures). Both isolated FORGE task fixtures separately PASS: registration/
export/security and actual limited-owner process/token query grants. All created
tasks/folders removed. Native platform normalization defects were fixed before
host staging. Pinned CPython3.14.10 passed72 compatibility checks; its temporary
37-file extraction was removed. Independent security/Ponytail FULL review
applied. No UI/design gate or unavailable Prompt Sensei usage claimed.

Private-output guards correctly rejected C:/admin's delete-capable untrusted
ancestor. No unrelated ACL was changed. New API evidence and unchanged-key,
independently pinned client config use the protected owner-profile project root:
`%USERPROFILE%/KnowledgeNetworkCollector-Private/host-exec-client-v1/ssh_config`.
Post-policy actual SSH health PASS, nonadmin/four live capabilities. Old copies
retained for rollback. Reference/script/declaration/57-artifact manifest small
pins match; no4.96GB inventory rerun. Local-use/monetized-audio findings remain
separate from uncleared narrator dependency redistribution.

BLOCKED/NOT TESTED: new host task/pipe/controller acceptance, deliberate handoff
from existing foreground39110, managed lifecycle, FORGE bearer/route setup and
REMOTE_NARRATION_PASS. Exact approved brand originals including badge remain
recovered. Native plan:48 intro +1218 body +234 outro =1500frames/50s; actual
speech/caption timing awaits remote PCM. Existing synthetic .osp/MP4 preserved;
no completed branded Short claimed. Installer pipefix-002 remains unchanged/
undeployed; isolated upgrade and scheduled Assistant/reboot limits unchanged.

## Dedicated host SSH: actual FORGE acceptance PASS

November 15, 2026: owner ran the checked completion launcher. It reported
PROJECT_SSH_LISTENER_STARTED_PENDING_REMOTE_ACCEPTANCE. Root then connected
from FORGE with the dedicated private key and pinned BLACKHAT-BASE host key.
Actual remote `health`, `self-test` and `native-port-9443` returned PASS.
The reported SID matches the configured dedicated `kncollector_exec` identity;
the token is nonadmin, and the fixed PowerShell child returned the same SID.
Native9443 has zero listeners and exclusive IPv4/IPv6 binds succeeded without
starting a listener. This is a current availability snapshot, not a reservation.

Ten native rejection cases passed: empty shell, unknown shell command, extra
arguments, path command, PTY, SFTP subsystem, direct forwarding, reverse
forwarding, unrelated authentication key and an unpinned host alias. Forwarding
was confirmed with actual SSH channel requests and server refusal. The first
reverse-forward probe was suppressed by the production client's
ClearAllForwardings setting and timed out; it is NOT a server test result.
A corrected test-only override requested forwarding and received refusal.
Production client configuration was unchanged. The temporary negative-test
key was removed. Wrong-source rejection from another peer remains NOT TESTED.

Private receipts/logs are in
`C:/admin/collector-v9/host-exec-client-v1`: remote-health.private.json,
remote-acceptance.private.json, remote-key-negative.private.json,
direct_forward_denied.private.log, remote-reverse-negative.private.json,
post-start-bootstrap-receipt.private.json and post-start-audit.private.jsonl.
Host redacted audit remains under
`C:/ProgramData/KnowledgeNetworkCollector/HostExec/audit/execution.jsonl`.
The original rollback-bootstrap.ps1 and account/service configuration remain.
Do not rerun completed bootstrap launchers. Host bootstrap receipt deliberately
retains CONFIGURED_PENDING_NATIVE_CONNECTION; the separate client receipts
establish acceptance without rewriting installation evidence.

Shared Gateway SSH configuration still matches its recorded SHA-256; no
Gateway/shared-sshd restart or route edit was performed. The complete private
tailnet policy bytes still match the reviewed digest. HTTPS9443 remains
BLOCKED: its broad all-peer grant permits unauthorized peers. Native port
availability and restricted SSH22230 do not satisfy this separate policy gate.
The owner must narrow the effective overlapping grant before route activation;
adding a narrow allow while retaining the broad grant is insufficient.

Scope remains four fixed diagnostic operations. This is real remote execution
of the fixed project PowerShell self-test, not arbitrary PowerShell access or
completed narrator/service management. No privileged remote handler, owner
Credential Manager access, live authenticated narrator handler or WAV transfer
is supplied by this dispatcher. Next development needs concrete reviewed
handlers and credentials provisioned for their actual execution identity.
Do not copy the owner's bearer or invoke the writable narrator venv as SYSTEM.
No new inference, narrator route, installer deployment or media export ran.

An SSH probe's closed output channel produced a health PASS audit followed by
operation_unverified for the same request. Source records PASS before flushing
stdout; failed response delivery is the likely cause, not directly recorded.
That request is not counted as a successful client receipt. The separate
received health/self-test/port responses are valid. Host disconnect/long timeout,
restart/reboot, rollback execution, runtime tamper and another-source peer tests
remain NOT TESTED; reuse the 18 isolated native process tests at their scope.

Cleanup: after verifying all37 installed runtime files, dispatcher hash and
retained official archive, removed seven explicitly named completed staging
files (12,690,627bytes) from host-exec-bootstrap-v2/host-exec-complete-v1.
Compact completion evidence was copied and byte-verified privately first;
original rollback, keys, installed runtime, receipts, backups, media and model
files remain. Empty staging directories may remain. Automatic review rejected
an earlier computed-path cleanup; the successful cleanup used exact literal
file paths. No source logic changed this turn; reuse328-test regression and8
bootstrap tests. Ponytail FULL/review plus independent security and dispatcher
reviews applied. PR20 draft/unmerged; publication PAUSED.

## Native firewall Program path fixed — checked networking completion staged

Owner's single-command continuation passed account/config/native SSH preparation
then `New-NetFirewallRule` rejected its application path. Root reproduced on
FORGE with disabled temporary rules: forward-slash Program rejected, canonical
Windows backslash Program accepted. A second disabled probe confirmed exact
complement-source filter readback. All probes were removed by exact names;
none was enabled or changed effective traffic. Installer now normalizes only
the firewall Program value, preserving SSH/SCM/rollback path strings.

Actual private host receipt has BOOTSTRAP_IN_PROGRESS, recorded execution SID
and block-source ranges; config, authorized_keys, effective SSH state and empty
audit/receipts directories exist. Source failure occurred before service setup.
Root retained five hash-verified pre-networking evidence copies under
`C:/admin/collector-v9/host-exec-client-v1/pre-networking-failure`.
Do not use pre-account resume again: its prerequisite is no longer satisfied.

Added a narrow `Complete-KnowledgeNetworkHostExec.ps1`, which validates exact
pre-network root/receipt/config/account SID/nonadmin membership, mutable audit
ACL separately from immutable code, actual absent service/rules/listener,
effective firewall policy, all runtime bytes and signatures, key/source binding,
current native SSH syntax/effective config and shared/rollback evidence. Only
the pinned bootstrap networking tail then executes; no account/runtime/config
recreation, ACL rewrite, evidence clearing or Gateway restart. Security review
caught and corrected the old serialized-JSON comparison and scalar-array type
looseness in the draft before staging; strict tests cover both.

PASS:8 focused native bootstrap tests; direct Windows firewall-provider format
and filter tests; production completion data helper against the actual unchanged
host receipt/config/key formatting; independent source review and parsers.
Installer SHA-256 `07096d7f2f81bd6d6291a47819f9aab3e27ebdb55c1b16265b570e423877396b`;
completion SHA-256 `080bbe62410d1e44c0bef146aa4c09e05e35819141fee1c05e5a5b30980d5705`.
Final repository regression PASS:328tests in72.951s,5 existing skips; private
log `C:/admin/collector-v9/host-exec-python-3.14.10/network-completion-regression.log`.

Staged one self-contained owner command in host `host-exec-complete-v1`:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/host-exec-complete-v1/Complete-HostExec.ps1`.
Launcher SHA-256 `8301178d26459ae109692edc6d673b3a3775b59c546b27d4dcba87cc5ce845cc`.
Run only this file from elevated host PowerShell. It pins captured completion
code/arguments; no multi-line paste or prior variables required. Actual host
completion/remote identity remains NOT TESTED. Remove/disable nothing manually
if it stops; preserve outcome for reconciliation.

Cleaned the obsolete host-exec-resume-v2 launcher/source/arguments after verifying
replacement and payload references. Active archive/key/dispatcher, protected
runtime/account/config, audit/receipts, evidence backups and rollback preserved.
No host firewall/service action was executed by root, no new speech/render or
9443 policy/route change. Publication PAUSED; PR20 draft/unmerged. Ponytail FULL
and independent security review applied; no UI or narrator-setting change.

## Reverse-order paste recovered; obsolete staging cleaned

Owner pasted the multi-line launcher in reverse order, invoking the previous
installer still present in `$bridgeSource` before loading the new bytes. The
old serialized-manifest error/line therefore recurred; it is not execution
evidence for the corrected comparison. Root read actual receipt/state again:
BOOTSTRAP_IN_PROGRESS, null execution SID, no audit or sshd_config. No state
clearing, repeat installation, service start or inference was performed.

Staged a self-contained, syntax-checked single-command script:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/host-exec-resume-v2/Resume-HostExec.ps1`.
It loads and pins current installer/arguments internally in execution order,
without relying on prior console variables. Owner runs that file with `&` in
the elevated host PowerShell session; no multi-line copy is required. Actual
continuation/remote SSH acceptance remains pending. Corrected source is still
`1f769a2a71fd19ea344b6a2df89c7ecf457e205c1b83bb1ba889b7924ca45975`.

At owner's explicit cleanup request, removed only obsolete created staging:
host-exec-bootstrap-v1, host-exec-trust-diagnostic-v1, host-exec-resume-v1,
superseded v2 fresh installer/arguments, old output launch text files and the
redundant FORGE extracted test runtime. Nonrecursive native PowerShell deletion
validated exact project paths, flat expected files and no reparse points.
Reclaimed24,582,086bytes. Active v2 installer/arguments/single-command launcher,
referenced host archive/key/dispatcher, installed protected runtime, private
client key, receipts, evidence backups and rollback files remain. Active payload
references and hashes were checked after cleanup and pass. No approved media,
model/reference, original project backups or installed Collector was deleted.
Private cleanup receipt:
`C:/admin/collector-v9/host-exec-client-v1/obsolete-staging-cleanup.private.json`.
Historical handoff paths below may now refer to deliberately removed obsolete
staging; use the single-command path above. No source logic changed, so no
whole-suite repeat. Publication PAUSED; PR20 draft/unmerged.

## PowerShell5.1 manifest round-trip corrected — host bytes unchanged

Owner's checked resume stopped at runtime-manifest equality before account setup.
Root reproduced the cause under Windows PowerShell5.1: wrapping decoded JSON in
`@(... | ConvertFrom-Json)` retains a nested array, whose serialized pipeline
form differs from the extraction records despite identical fields. This was a
bootstrap comparison defect, not evidence of changed runtime bytes.

Removed the wrapper and serialized-text comparison. `Assert-RuntimeManifest`
now checks decoded array/count, exact three fields/types, unique case-sensitive
names and each hash/size against independently verified official ZIP records.
No existing manifest is rewritten or accepted merely because decoding succeeds.
All pre-account receipt/ACL/resource-absence/rollback/publisher gates remain.

PASS:7 focused native bootstrap tests, including the exact file/JSON round-trip
and rejection of changed hash/size/type, extra/duplicate/missing/wrapped entries.
Root also ran the corrected production extraction/manifest helpers against the
actual host files over redirected storage: all37 files and the unchanged actual
manifest match the pinned official ZIP. This was read-only, not host execution.
Independent source security review PASS at installer SHA-256
`1f769a2a71fd19ea344b6a2df89c7ecf457e205c1b83bb1ba889b7924ca45975`.
Prior326-test full suite remains the baseline; no whole-suite repeat for this
targeted PowerShell comparison fix. No runtime dispatcher source changed.

New installer/private arguments staged in host `host-exec-resume-v2`, preserving
prior bundles and all prepared state. Owner next action: paste complete contents
of `output/Host-Exec-Resume-Manifest-Fix.txt` in the same elevated host PowerShell.
Launcher SHA-256
`dd37939a79fd0f38b53e2bc093865672a589f0b2be3709687367660e1c073fb7`.
Captured bytes remain pinned before evaluation. Do not rerun old launchers,
delete files or bypass the manifest gate. Actual host continuation/remote SSH
acceptance remain NOT TESTED; no account/service/firewall action by root,
no inference/render, publication PAUSED and PR20 draft/unmerged.

## Account-description interruption — checked continuation prepared

Owner's v2 bootstrap reached local account creation, then Windows rejected the
description for exceeding48characters. This was a bootstrap defect, reproduced
by a new regression test against the installed cmdlet's actual ValidateLength
metadata. Description is now the full product name plus SSH,34characters.

Actual protected host state read privately: BOOTSTRAP_IN_PROGRESS receipt with
execution_sid=null, prepared37-file Python3.14.10 runtime, runtime manifest,
original rollback and shared-config backup; no audit directory or sshd_config.
Root independently hashed all37 host runtime files against the pinned official
ZIP; all match. Four partial-state evidence files were hash-verified into
`C:/admin/collector-v9/host-exec-client-v1/pre-resume-description-failure` and
remain unchanged on the host. Shared Gateway configuration is unchanged.
Parameter validation failed before account creation; native account/service/
firewall absence must still be positively checked on continuation.

Added only a narrow `-ResumePreparedRuntime` path for this exact pre-account
state. It fails closed on inventory errors or any account/service/firewall/
listener already present, progressed/extra/mismatched receipt fields or files,
unsafe ACLs, changed runtime, rollback or shared configuration. Existing runtime
is reverified read-only against captured official ZIP bytes; no repair, extraction
overwrites, receipt recreation, state clearing or second identity. Existing
publisher/import-path/native trust gates run again before continuing. Ordinary
fresh mode still refuses preexisting roots. No bootstrap was retried by root.

New installer SHA-256:
`e93be3b374735c1c039d094c1f640ee20926cc5c63142e6fe14c66d39391599f`.
New source and private resume arguments staged in host `host-exec-resume-v1`,
referencing preserved v2 archive/key/dispatcher. Owner next action is pasting
the complete eight-line `output/Host-Exec-Resume-Prepared-Runtime.txt` into the
same elevated host PowerShell session. Launcher SHA-256:
`767cfcad7fa86789be6c4f301c8ca6948e0cadb6683fdf24c28b8fadd210031b`.
It verifies captured installer/argument bytes, then enables only that checked
continuation. Do not rerun the v1/v2 fresh installers or delete prepared files.

PASS:6 focused native bootstrap tests, including real description metadata,
15 invalid receipt fields rejected, ordered receipt continuation, valid existing
runtime verification and corrupted bytes rejected without repair; independent
source security review and launcher/parser checks. Full regression PASS:326tests
in58.971s with5 existing skips; private log under
`C:/admin/collector-v9/host-exec-python-3.14.10/resume-regression.log`.
Actual native resume/remote SSH acceptance remains
NOT TESTED. No current service, firewall, ACL or narrator change by root; no
inference or media render. Ponytail FULL applied, PR20 remains draft/unmerged,
publication PAUSED, all prior bundles/backups preserved.

## Genuine writable narrator Python identified — protected dispatcher runtime ready

Owner returned `BLOCKED_TRUST_PATH_IDENTIFIED` at
`private-service-v9-001/review/trust-check-731d3bcc94f64147a1bdc0321ee342cb.private.json`.
Root and security specialist read the full private ACL: canonical venv
`Scripts/python.exe` grants Authenticated Users Modify, with no denying ACE.
This is a genuine trust failure, not grounds to weaken the guard. No account,
service, firewall or existing ACL mutation occurred. Full DACL/owner details
remain private. The original narrator environment is unchanged.

The bridge now uses its own protected CPython3.14.10 embeddable runtime under
`C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python` instead of
executing the writable narrator interpreter. Official archive SHA-256:
`90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`,
matched against https://www.python.org/downloads/release/python-31410/.
Downloaded12619664bytes/37files; original licenses retained. Both python.exe and
python314.dll have Valid Python Software Foundation Authenticode signatures.
Dependency lock updated; no model/voice download or global Python installation.

Updated bootstrap captures/pins ZIP and public-key bytes before parsing, requires
exact37 bounded flat regular members, refuses traversal/links/case duplicates/
overwrites, verifies extracted hashes and immutable native ACLs in a new protected
directory, checks publisher signatures and restrictive._pth, then checks isolated
version/no-site before use. No original runtime ACL repair. Dispatcher code and
its four-command scope remain unchanged; this does not fix or promote the
separate original narrator's local-code trust boundary. Never invoke that
original environment through a future privileged/SYSTEM handler.

New bootstrap SHA-256:
`5f825db4a27320745d27cd556a93923444c2ba7a433188a95fae02fa08140940`.
Staged archive, installer, unchanged dispatcher, dedicated public key and pinned
private arguments under host `host-exec-bootstrap-v2`, preserving prior bundles.
Owner next action: paste the complete eight-line contents of
`C:/Admin/Projects/KnowledgeNetwork/output/Host-Exec-Protected-Runtime-Launch.txt`
in the same elevated BLACKHAT-BASE PowerShell session. Launcher SHA-256:
`b15187b27d97c011981c225fa93e244fa423fbbc343e0b4bdb7aed87fc8239f7`.
It hashes captured installer/argument bytes and evaluates those same reviewed
bytes, avoiding file re-read races. No secret arguments or policy bypass flag.
Standing authorization already covers this; technical host execution remains
unavailable until actual bootstrap acceptance. Do not rerun old bundles.

PASS:18 dispatcher tests under the actual new3.14.10 runtime;4 native bootstrap
helper tests including malicious ZIP/no-overwrite cases; actual official package
through the production extraction helper, all37 members and both signatures;
final324-test repository regression in62.980s with5 existing FFmpeg skips.
Private logs under `C:/admin/collector-v9/host-exec-python-3.14.10`.
Independent source security review found no remaining concrete must-fix at the
new bootstrap digest. Native host extraction/trust/startup and SSH acceptance
remain NOT TESTED. Gateway configuration/routes, narrator settings/reference/
model, working FORGE installation and backups preserved; no new inference or
render. PR20 draft/unmerged; publication PAUSED.

## Host bootstrap stopped at interpreter trust — diagnostic pending

Owner ran the staged bootstrap on BLACKHAT-BASE and received the fixed
`Execution trust chain is writable by a nontrusted principal; no ACL was changed`
error from `Assert-TrustedPath`. Source flow places this rejection before
directory/account/service/firewall mutations. Root independently checked that
the HostExec directory and bootstrap receipt are absent. The exact rejected
path/ACE is still unknown; no runtime/drive/narrator ACL was modified, no
guard bypassed and no bootstrap retry or remote connection attempted.

Added structured private exception context while preserving the trust masks
and fixed console error. Security review also identified a separate omission:
loader directory roots `base/DLLs` and venv `Scripts` now receive full target
checks, including create-file rights, before descendant enumeration. This closes
a gap; it is not assumed to explain the actual host error.

Prepared read-only native diagnostic and staged it with the enriched bootstrap
source in `D:/projects/knowledgenetwork/collector-narrator-v9-004/host-exec-trust-diagnostic-v1`.
Original bootstrap bundle remains unchanged. Diagnostic hashes captured source
bytes once, then uses that same text for reviewed helper/preflight evaluation;
it does not execute privileged bootstrap setup. First failure's complete applied
DACL/SDDL, owner, target/ancestor path and rights are written only to a new
private JSON in the existing protected narrator spool's review directory. The
console returns only status/evidence path. No credentials or policy contents.

Owner action: paste the complete six-line contents of
`C:/admin/projects/KnowledgeNetwork/output/Host-Exec-Trust-Diagnostic-Launch.txt`
into the same elevated BLACKHAT-BASE PowerShell window, then return only its
status/evidence path. The launcher pins captured diagnostic bytes before use.
Launcher SHA-256 `ee0ae0f06ab4e5d53594d95447bb15e1c9c278b193b150d1735873d356a471ae`;
diagnostic SHA-256 `88bbaadfc79616a75e55d478316c126b0eee739bde0ad826e7f18eed7c363900`;
updated bootstrap SHA-256 `abb317e75933cfc2b7a4a0f8d9f0203ad00a3e5c6e7989e58662a8b9c7bad6a3`.

PASS:3 focused native FORGE tests, including full ACL/create-only/inherit-only
denial, private exception context, source-pin mismatch/size bounds and captured
text stability; PowerShell source/launcher syntax checked. Prior322-test result
remains historical baseline; no repeated whole-suite or runtime-source change
for this preflight/diagnostic correction. Ponytail FULL and independent bounded
security review applied; review caught and corrected a source-reread race.
Actual blocked host ACL, diagnostic execution, bootstrap and SSH acceptance
remain BLOCKED/NOT TESTED. Standing authorization remains valid; unavailable
technical host execution still requires this native diagnostic. Publication
PAUSED, Gateway/443/8443 and original narrator untouched; no new inference.

## Standing host authorization — restricted bridge prepared, bootstrap pending

Owner now explicitly authorizes a separate project execution channel and scoped
routine host operations. Continued from clean source
`7566fa2f848fe58fbd19519caadfe3e7b1d8f47b`; no reset/replacement/history rewrite.
The commit containing this entry records implementation on the existing feature
branch. PR20 remains draft/unmerged; publication remains PAUSED.

**Existing access investigated:** redirected host files and the existing Gateway
SSH/maintenance paths. No independently authorized KnowledgeNetwork management
endpoint was found. Gateway maintenance pins exact entire SSH configuration
templates and its Gateway-only allowlist, so extending the shared config would
break it. No Gateway credential was read/reused, no existing config changed and
no shared service restarted. Shared config remains SHA-256
`39f452458c454ea6906015862774b3d73e2d71e16852de58c767ae178bd3794d`.

**New implementation, not deployed:** separate `KnowledgeNetworkHostExec`
Windows OpenSSH service, dedicated nonadmin `kncollector_exec`, separate
tailnet-address-only TCP22230 listener/config, new FORGE Ed25519 key and strict
pinned host key. Initial four exact operations: `health`, `self-test` (fixed
PowerShell identity), `native-port-9443`, `narrator-status` (retained sanitized
snapshot only; never live authenticated health). No arbitrary shell, caller
scripts/paths/stdin, PTY, subsystem, forwarding or generic administration API.
The service is SYSTEM only for SSH logon; dispatcher execution must be the exact
nonadmin SID with no administrator group membership. No privileged operation
handler is exposed. Broader authorized narrator/service work is not yet supplied
by these four initial commands; add only concrete reviewed handlers and tests.

Dispatcher SHA-256:
`637c92f13126c2ccb5a2eeb888cc4ac48a8a540cf74652f96dc268ce12600bf2`.
Bootstrap SHA-256:
`29038f0827bb31f2673ae5c4fb360f900c664ced6ce9b578c75d7cd6e777d547`.
See [architecture/bootstrap/rollback](../host-execution.md),
[independent security review](HOST-EXECUTION-SECURITY-REVIEW.md) and root SECURITY.
The bounded dispatcher owns child processes, limits time/output, caps serialized
durable redacted audit at16MiB and fails closed on uncertain shutdown/audit fault.
Bootstrap verifies interpreter/import/ancestor trust without changing existing
ACLs, rejects unsafe global outer shell, validates actual isolated sshd config,
requires effective enabled firewall enforcement, and adds only per-project
FORGE allow plus complementary other-source block. Native start must match
the dedicated SCM PID/LocalSystem/path and exact private bind. Gateway untouched.

**Private client prepared:** `C:/admin/collector-v9/host-exec-client-v1` holds the
separate key, actual-address bootstrap input, known_hosts, SSH config and receipts.
Host public-key fingerprint independently read and pinned:
`SHA256:2J+57GgzHCHO9QBtxbrOW1gGDs8rdWaoFbQ/xNK6qRU`.
Native client `ssh -G` checks PASS for batch/key-only, strict host verification,
exact key, no PTY/agent/forwarding. No private key transferred or put in Git.
Future command form is OS-native
`ssh -F C:/admin/collector-v9/host-exec-client-v1/ssh_config knowledgenetwork-host health`;
it has NOT established a live connection yet.

**One unavoidable owner bootstrap:** no existing authorized privileged execution
path can create the account/service. Four reviewed files were copied with
exclusive creation and hash-verified readback into
`D:/projects/knowledgenetwork/collector-narrator-v9-004/host-exec-bootstrap-v1`.
Run `Bootstrap-KnowledgeNetworkHostExec.ps1` there once in elevated host Windows
PowerShell. Wrapper SHA-256
`e722fd585f97b32942674c48610ee3c5174124e893b9983ffb332b5df7d91d44`.
It pins bootstrap/dispatcher/public-key bytes and supplies actual private addresses;
no secret argument or execution-policy bypass. Native preflight may legitimately
stop on unsafe runtime ACL, shell, firewall or unsupported SSH settings. Preserve
any partial receipt; do not reinstall under another identity/port to evade it.
Rollback script and prior shared-config copy are created in protected
`C:/ProgramData/KnowledgeNetworkCollector/HostExec` before account/network changes;
rollback validates exact project resource filters, disables the created identity
and retains files/evidence, never restores unrelated config or deletes backups.

**Validation scope:** specialist18 dispatcher tests PASS, including real isolated
FORGE Windows fixed PowerShell identity, timeout/cancel/output cap, Job Object
descendant teardown, command/source/PTY/path denials and bounded audit contention.
Root2 bootstrap helper tests PASS: real temporary Windows ACL accept/deny and
inherit-only handling, plus IPv4 complement boundaries. Bootstrap/embedded rollback
and owner wrapper syntax PASS; dispatcher Python3.11 parse PASS. Independent
review found/corrected native loader trust, filtered-admin, audit-link, directory
race, firewall construction/effective-policy and listener-identity gaps. No
remaining concrete must-fix at the above source digests in the four-command scope.
Final frozen-source regression PASS:322 tests in100.545s,5 existing explicit
FFmpeg skips, using `PYTHONPATH=src` and project venv `python -m unittest discover
-s tests -v`. Private log:
`C:/admin/collector-v9/host-exec-client-v1/regression-final.log`.
An earlier319-test run also passed before the final cleanup/coverage additions;
the322-test run is the authoritative current-source result. These tests do not
prove deployed remote access.

**Actual host status:** narrator loopback/auth/manifest evidence remains PASS;
owner bearer stays in that owner's CredMan and is not available to the new SSH
identity automatically. No bearer extraction/owner impersonation. Saved native
9443 receipt now reports0 listeners and exclusive IPv4/IPv6 bind PASS, without
starting a listener; it is a snapshot, not a route authorization. The complete
tailnet-policy review remains BLOCKED by broad network permission; no policy or
9443 route changed. All exact branding sources remain available and validated.
Remote narration, new native video/export, installer isolation and scheduled
Assistant/reboot acceptance remain incomplete; no new GPU work/render/reboot.

Ponytail5.3.3 FULL and installed review applied; parallel dispatcher/bootstrap/
security ownership was nonoverlapping and root integrates. No UI changed, so no
new UI/UX Pro Max/Taste gate claimed. Existing model/reference/settings, protected
backups, working installed Collector and old staging installer remain intact.

## Private tailnet policy reviewed — BLOCKED

Read the complete owner-supplied private HuJSON policy through redirected
storage, SHA-256 `a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c`.
Parsed comments/trailing commas without printing raw contents or identities.
Reviewed every top-level section and active rule. The active network permission
is broad enough to allow other tailnet peers to reach host TCP9443; there are no
ACL/group/tag-owner definitions narrowing it. SSH access is a separate boundary
and does not restrict that HTTPS network grant. Adding a narrow FORGE grant
would not remove the broad permission. No policy snippet or private identifiers
are included in this report. Official policy syntax reference was consulted.

Result **BLOCKED**: the stated FORGE-only route prerequisite is not satisfied.
No policy modification, route start, weakening, credential change or inference.
Existing443/8443 routes and Gateway are untouched. Publication remains PAUSED.
The retained Serve snapshot has no configured9443, but that is not a native
port availability test. Root lacks host command execution, so native availability
is still NOT TESTED independently of policy/Serve.

Prepared private `review/check-native-port.py` for one owner-run native-only
check: query current Windows9443 listeners with fail-closed errors, then if none
attempt exclusive IPv4/IPv6 binds and immediately release them without ever
calling listen. Writes `native-9443.private.json` once; no route/firewall change.
AST syntax/readback checked on FORGE only, not executed on host. Any native PASS
is a point-in-time snapshot and does not resolve the policy blocker; recheck
before any future separately reviewed route mutation.

Policy remediation is outside this read-only review. A future concrete proposal
must remove/restructure the overlapping broad permission for this destination/
port while preserving approved access to443/8443 and unrelated services, and
include positive FORGE/negative other-peer tests. Do not apply changes without
the owner's scoped authorization and review of the exact proposed policy.

## Current Serve evidence received — policy export still missing

Owner returned PASS_READ_ONLY_STATE_CAPTURE; root read the two saved private
JSON files. Host identity matches BLACKHAT-BASE and exactly one FORGE peer is
present. Current Serve has TCP443 and8443 entries and no configured9443 entry;
no route was changed. This does not establish native port availability or
effective access restrictions. Existing routes must remain intact.
Serve JSON SHA-256:
`ad0ba0fe2b1d010bebb99749a2cfed346cb7fc90bdf0cc2ff48a8e4e1c121ec5`;
tailnet JSON SHA-256:
`ed016cc7bc37901b58011080bcf987edfac075fa200f84fadc74cf9e23c9bd3c`.
Actual addresses/peer metadata remain private.

`tailnet-policy.private.hujson` is not present in the protected spool. The
remaining immediate owner action is saving the current effective policy there
for review, not another state capture or auth test. Do not rerun completed
stages or create9443 before that prerequisite passes. No new inference or
remote transfer occurred; publication remains PAUSED.

## Local authentication PASS — route prerequisites next

Owner ran the direct auth check successfully. Root read the actual retained
`local-auth.private.json`, SHA-256
`a7209570a221f35909e3af74373e03aff485e2c64e56a9bca22ec7001be08c58`:
PASS_LOCAL_AUTH_ONLY, missing/wrong bearer401, authenticated health200 with exact
reviewed provenance, forbidden fields400, inference_submitted=false. No credential
value was returned or read by root. This supersedes local-auth pending below.

Prepared private `review/capture-tailnet-state.py` in the existing host spool,
SHA-256 `a25b4f059675a7ccd31eabe1c550b95372a15a20e920c48c089a819b415603be`.
AST parsed and exclusive write/readback checked, not executed. It captures only
`tailscale serve status --json` and `tailscale status --json` into new private
files, refuses overwrite, checks command exits/JSON and prints no addresses.
Owner executes it locally; no route, credentials or inference are changed.

Still required before9443: actual current Serve/unused-port review and effective
tailnet access policy including broad/additive grants and intended FORGE identity.
Owner must provide a private exported policy file for review; peer/state capture
alone does not establish restricted access. No route command has been run.
Remote narration remains BLOCKED and publication PAUSED.

## Stage3 paste recovery — authentication still NOT TESTED

Owner's pasted Stage3 arrived out of order and PowerShell raised ParserError
while parsing Python text. No local-auth/listener/Serve/tailnet receipts exist
in the protected spool, so no authentication result is inferred. Server restart,
new inference or credential reprovisioning is unnecessary.

Root extracted the same local-auth Python block, parsed it without execution,
and created only `review/check-local-auth.py` in the existing private spool,
with exclusive creation and byte readback. SHA-256
`d147a2614609b6aad50a0e5dc9e223b2e7585b8e73aafb355884214f44d6bfb3`.
Owner can invoke it directly with the canonical engine Python and kit PYTHONPATH,
avoiding PowerShell here-string paste. It uses host CredMan internally and sends
only local health/auth/invalid-schema tests; no valid narration or routing action.
Actual execution remains owner-side and pending. Publication remains PAUSED.

## Host manifest PASS and loopback listener observed

Owner reports Stage2 credential `SAVED` and a listener at127.0.0.1:39110,
PID2068. The foreground terminal remaining occupied is consistent with the
running narrator; do not rerun Stage2. Root read the actual host-private
`manifest-validation.private.json`: status PASS, script98b75e...f189,
model revision7936080b41163874f38610f46f438e2c0757f9fd,
config SHA-256 `976d46c19601b07d17160f8edd1c716e51b85e5610ec163d8b4e49f9271e9bc9`,
license evidence4f10acc...65e4. This establishes actual manifest validation;
listener identity/health and authentication remain NOT TESTED until Stage3.

Prepared exact syntax-checked Stage3 copy/paste file:
`output/Narrator-Stage3-Local-Auth-And-Status.txt`, SHA-256
`fa21ac2dd719c900ddbc8c3325607aa27033d4a30cde290f0830bb2cb336fb6b`.
Run in a second BLACKHAT-BASE PowerShell window while the foreground server
continues: loopback check, hidden in-process CredMan use, missing/wrong bearer
denial, authenticated health/provenance and forbidden-schema check without
inference, then read-only Serve/tailnet state capture. No routing change is in
this stage. Owner should return only completion/status; raw private state can
be inspected through the same protected spool. Publication remains PAUSED.

## Host spool accepted and reviewed files delivered

Owner returned actual BLACKHAT-BASE Windows PowerShell5.1 Stage1 result:
`{"status":"PASS","scope":"host_spool_acl_only"}` for
`D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001`.
This is owner-returned host ACL validation, not listener/auth/manifest acceptance.
Do not repeat Stage1 or create a second spool.

Root then delivered exactly three new files into that spool's `review` directory
via authorized redirected storage, with exclusive create/no overwrite and
readback SHA-256 verification against the private delivery receipt:
`active-runtime-review.md`, `operational-review.private.json`, and
`narrator-manifest.LOCAL-USE-CANDIDATE.private.json`. Candidate digest remains
`42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84`.
No private contents were added to Git; original drafts/assets are unchanged.

Prepared exact syntax-checked Stage2 extraction:
`C:/admin/projects/KnowledgeNetwork/output/Narrator-Stage2-Validate-And-Start.txt`,
SHA-256 `b2cc281564675b885a6d6febb9d3efc32ac50f289ccc38a13fad37f31f5c5e31`.
Owner runs this in the same host PowerShell session: actual manifest validation
(including required model hashing), ACL recheck, refuse existing dedicated
credential, hidden-prompt new scoped bearer, free-loopback-port check, foreground
existing narrator process. No inference or Serve command is in this stage.
The owner must retain the new secret securely for FORGE and never return its
value in chat/logs. Actual host validation, credential provisioning, listener and
local auth remain NOT TESTED until receipts arrive. No root host command was
executed. Publication remains PAUSED; PR20 remains draft/unmerged.

## Badge follow-up — all branding sources available

Owner supplied the original badge in main and reports creating/owning/licensing
it through Dot. Fetched main to `74224b5cc1b1f5c0ec703957dd6236de5aa02d47`
without merge/rebase. Binary Git recovery of the PNG yields exactly
`5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54`;
2,211,740 bytes,1254x1254 RGB, PNG integrity and existing production intro
validator PASS. Local original:
`C:/admin/collector-v9/approved-badge-main-74224b5cc1b1/Neon Cosmic Oxieg3n Emblem.png`.
The three exact videos recovered below remain unchanged. **BLOCKED_ASSET is
resolved for all required branding sources.** No replacement or changed pin.
The4s preview is still reference-only; dynamic1.6s intro and complete native
export await the actual body and verified remote narration. No new render was
performed merely to repeat old technical evidence.

The remaining immediate action is still owner-side Stage1 protected-spool
creation described below; host execution is unavailable from this session.
No host service, credential, route or new inference was run. No completed
narrated/branded project/export exists yet. PR20 stays draft/unmerged and
publication PAUSED. This follow-up supersedes the badge blocker in older entries.

## Final integration continuation — recovered branding and authorized deployment

November 15: resumed clean `feature/collector-v7-overnight` at
`89b134a85e094b2b2a584e2c719f6ef2a5a07a00`. Fetched main to
`0ec0c05cb2fa6976fc87cfcb321c60d1a747c10d` without merge/rebase. The commit
containing this section records the continuation; `git rev-parse HEAD` gives its
exact ID. No runtime implementation was restarted or replaced. PR #20 remains
draft/unmerged, publication PAUSED, and existing backups/worktrees/installers
and original narrator files are preserved.

**Owner listening approval recorded:** owner reports the narrator sounds perfect
and approves project use, tied to exact diagnostic WAV SHA-256
`1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7`.
This supersedes historical listening-pending statements below. It is an
owner-reported positive review, not an automated assessment or invented detailed
observations. The completed diagnostic was not rerun.

**PASS — recovered approved videos:** extracted only the three owner-requested
video members through binary-safe `git archive` into
`C:/admin/collector-v9/approved-brand-main-0ec0c05cb2fa`.
All match main's exact `.github/workflows/ci.yml` pins:

| File | SHA-256 |
| --- | --- |
| `Powered-By-Plasma-With-Sound-Preview.mp4` | `1eeec90cda8dec320e078e77d5a6c4b6034be6e9dd07e00220ccc601f688e781` |
| `Powered-By-Outro-Portrait.mp4` | `62496803360e377d81ab54b6970d94fcce3eee125f5d22c2fe08377dcf1b5c9b` |
| `Powered-By-Outro-Landscape.mp4` | `3720a160cd8acb46c828d448cca740252fb8c6a80eba892f1573dc5b56479ee3` |

All decode completely with FFmpeg `-xerror`: H.264 30fps, AAC stereo 48kHz.
Preview is 1080x1920/4.0s, portrait outro 1080x1920/7.8s and landscape outro
1920x1080/7.8s. Both outros pass the existing production validator. Exact bytes
retain original CTA speech. No old media overwritten or pins changed, and no
new media tracked on this branch. [Full branding update](V9-BRANDING-CONTINUATION.md).

**BLOCKED_ASSET — original badge only:** no PNG badge is in fetched main or the
examined Git path history; prior exhausted searches were not repeated. Required
`Neon Cosmic Oxieg3n Emblem.png` must match
`5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54`.
An owner-provided private path/Library materialization remains necessary. The
4-second preview stays a reference, never a substitute for the 48-frame/1.6s
dynamic production intro. The older missing-outros blocker is resolved.

**PASS review / NOT HOST-VALIDATED:** [active-runtime review](V9-ACTIVE-RUNTIME-REVIEW.md)
separates fixed private no-denoiser use, generated commercial audio and packaged
dependency redistribution. NVIDIA install/use and retained BSD/LGPL notices
are reviewed at that bounded scope; redistribution of the narrator environment
remains uncleared. Successful trace/source support inactive kaldiio/FunASR/
ModelScope/ZipEnhancer in this path; their installed restrictions remain intact.
No dependency changed or new license accepted.

A new private 57-artifact local-use manifest candidate binds actual reviewed
evidence and owner listening. Private delivery directory:
`C:/admin/collector-v9/local-use-review-v9-001`; manifest SHA-256
`42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84`.
Supported review fields reflect the scoped evidence, while publication and
dependency-redistribution approval stay false. Existing drafts are preserved.
Actual host validator/cache/artifact checks remain mandatory; no validation PASS
is invented from the candidate's existence.

**BLOCKED execution / deployment:** owner now authorizes the one protected spool,
truthful validated manifest, dedicated CredMan bearer, existing loopback process
on 127.0.0.1:39110, local auth tests and private HTTPS9443 only after all stated
preconditions. Authorization is sufficient; the remaining blocker is absence of
host command execution in this session. Redirected storage does not grant it.
[Owner-side deployment and FORGE acceptance](V9-DEPLOYMENT-ACCEPTANCE.md) prepares
the actual current implementation, not a second server. No listener, credential,
Serve route, firewall/Gateway change or inference was executed here.
Actual local authentication, current Serve/9443/effective-tailnet-policy proof,
HTTPS transport and `REMOTE_NARRATION_PASS` remain **NOT TESTED/BLOCKED**.
FORGE status still fails before network with `BLOCKED_NARRATOR_CONFIG`.

Next exact owner-side action is the syntax-checked first stage only:
`C:/admin/projects/KnowledgeNetwork/output/Narrator-Stage1-Create-Private-Spool.txt`,
SHA-256 `04ffe4ba0655687283c07feb913e433457c928248cb659d34923329515b7e088`.
Paste its contents once into local BLACKHAT-BASE Windows PowerShell in the
intended narrator account, then return the printed spool path. It verifies kit
source pins/free39110, creates `private-service-v9-001` with protected ACL and
validates it; no inference, bearer, listener or route is created by this stage.
After that, root can deliver the three reviewed files via redirected storage.
Root checked all57 manifest references by file existence: only the two newly
declared review artifacts are absent before materialization;55 existing paths
are present. This is not a substitute for host validator/hash acceptance.
Full numbered procedure:
`output/Narrator-Restricted-Deployment-Owner.txt`, SHA-256
`3cf6f0b80f780ff5c7c89370b015f282fef8849eb65c82e042823712ef4d9fbf`.
Independent security review found and corrected a free-port error-handling gap;
current Serve JSON/9443 checks and all listener queries now fail closed. Actual
tailnet policy review remains a hard stop before the route command. No further
permission question is needed for authorized actions; actual host execution and
prerequisite evidence are what is missing.

**Native video:** preserved prior editable project/export and receipts. No real
remote receipt exists to attach; the host diagnostic file copy cannot be labeled
a successful API transfer. The first real receipt enables a fresh unbranded
local review project; the complete branded project additionally needs the badge.
For a 50s final target, nominal bookends reserve 9.4s, leaving 40.6s/1218 frames
at30fps for measured body timing. Use actual audio/bookend durations and retime
three editable scenes/cues, never append bookends to the old50s body or truncate
speech to force acceptance. No final narrated/branded `.osp` or MP4 is claimed.

**Installer/operations:** existing staging installer hash still
`4149bd4c66347429f65a570925bc158cbc36a8b752c36c741d1cfabf4439517a`;
481 package checks/190 worker tests reused, no rebuild/install. No disposable
Windows target exists here: Sandbox/Hyper-V disabled, vmms and tested VM tools
absent. Fixed AppId/path/service prevents safe alternate-directory install.
[Operational matrix and bounded scheduled/restart checks](V9-OPERATIONAL-ACCEPTANCE.md)
are prepared, not executed. Working service observed Running/Automatic; no
scheduled Assistant, restart/reboot or new installer lifecycle PASS is claimed.

Ponytail5.3.3 FULL applied with parallel, nonoverlapping rights/transport/QA
documents; root owns integration and asset checks. No UI changed, so no new
UI/UX Pro Max/Taste visual gate is claimed. No source defect justified a new
implementation or repeating the full model/editor/regression suites. Checks
new to this continuation are binary recovery/hash comparison, full asset decode,
existing outro validation, bounded license/manifest review, source parity and
owner-procedure syntax checks. Independent security review is recorded in the
deployment report. No private audio, credentials, declaration or generated media
was added to Git. Nothing was publicly published.

## Owner-run diagnostic received — PASS, host smoke only

November 15: owner supplied host run directory
`D:/Projects/knowledgenetwork/collector-narrator-v9-004/private-smoke-9c04d8494b2945c8ac8d2c4ee6e3727d`.
This supersedes the execution blocker immediately below. The single authorized
diagnostic has been performed by the owner; do not rerun it. FORGE inspected
only this exact directory over the existing redirected drive. No host command,
listener, credential, network/installer change or additional inference was run.

**PASS:** saved child exit code 0; no Python traceback marker in private stderr.
New `narration.wav`: 291,884 bytes, 3.04 seconds, 48,000 Hz, mono PCM16,
145,920 decoded frames. SHA-256:
`1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7`.
FORGE independently decoded every PCM frame, recomputed the digest and matched
the host smoke receipt. This is file inspection/copy, not narrator API transfer.

**PASS device evidence:** canonical stderr reports
`Running on device: cuda, dtype: bfloat16`; successful exit and decoded output
support completed CUDA-selected inference. This is not GPU kernel profiling,
proof of a particular GPU ordinal/model, listening or performance acceptance.

**PASS bindings:** canonical script/reference/CLI/declaration hashes still match
their recorded pins. Current selected revision ref and all 39 small inventoried
package files were independently rehashed through redirected storage and match
the saved inventory at revision
`7936080b41163874f38610f46f438e2c0757f9fd`. No 4.96 GB model re-inventory.
The unchanged script retains CFG 2.0, ten steps, no denoiser/optimization,
local-files-only, compile disabled and original reference conditioning.

**Observed runtime scope:** parsed 2,485 named Python import records. None are
`kaldiio`, `funasr`, `modelscope`, `voxcpm.zipenhancer` or their submodules.
The log says `zipenhancer_model_path: None, enable_denoiser: False`; its one
ZipEnhancer-name occurrence is a settings report, not an import. Together with
the inspected lazy source branch, this supports those denoising components not
participating in this successful canonical no-denoiser run. Absence from one
trace is not a full transitive license audit or permission to enable denoising.

**Private evidence preserved:** five source files were copied into an ACL-protected
FORGE directory and each copy hash verified:
`C:/admin/collector-v9/smoke-review-9c04d8494b2945c8ac8d2c4ee6e3727d`.
Host originals remain unchanged. Private stderr SHA-256:
`c8e3348f161691bf5cf9a1900750d0af056c2c642ab3a9794f19b103c8249208`;
host smoke receipt SHA-256:
`3c8b88157ff217afa920f501e382d928edd48bb3c8b7df8631f4dc62e3ce3283`.
Raw logs/audio/rights documents remain outside Git. No credential value is
included in this report. The bounded log credential-pattern check found none;
this does not replace the previously requested token rotation.

**Remaining commercial questions:** reconcile the observed active modules with
the prior component/notices inventory for actual local operation, including
bundled NVIDIA and LGPL components; separately review any runtime redistribution.
The installed kaldiio restriction is unchanged, but this trace/source evidence
supports excluding its inactive denoising path from this exact diagnostic's
runtime scope. No package deletion, broad rights certification or approved
manifest flag promotion follows automatically. Original voice-design history
corroborates synthetic provenance but remains distinct from authenticated
generation receipts. Commercial approval remains **BLOCKED pending final review**.

**Owner listening remains NOT TESTED:** play this exact WAV locally at a
comfortable level and compare identity with the approved reference/known output.
Note pronunciation, naturalness, noise, clipping and truncated onset/ending;
record the above digest with the private result. Automated PCM checks do not
establish speech intelligibility, voice identity or quality.

**Minimum next steps:** review listening and active-component obligations;
complete a truthful reviewed manifest; separately approve the loopback host
listener/scoped bearer, then a dedicated private HTTPS route after read-only
Serve/port/policy inspection. Authenticate locally before one FORGE request;
match host/local hashes and provenance. Remote API/transfer remains **NOT TESTED**.
Exact branding and final editable branded Short remain blocked as documented.

Ponytail FULL/review applied to receipt/source boundaries and unsupported claims.
PASS: private copy/hash checks, sample decode, receipt equality, ref/package pins
and bounded import-log parsing. No runtime source changed, so no repeated full
regression, GPU job or media render. PR #20 stays draft/unmerged; publication
remains **PAUSED**, with no public audio/video upload.

## One-time diagnostic authorization — BLOCKED at host execution

November 15: continued from clean checkpoint
`eb5cb0e7f3a8132ab6628fa60a0348f3cf898240`. Owner authorized exactly one
unchanged-script local diagnostic inference and its private output/logs.
Available host access is redirected-drive file access only; no authorized host
execution tool/channel exists in this session. No inference was attempted and
the one authorized invocation remains unconsumed. No host directory, listener,
credential, route, installer deployment or networking change was made.

PASS: rehashed script, reference, CLI, saved inventory and rights declaration;
all match the full recorded digests below. Read the canonical script again:
CFG 2.0, ten steps, no denoiser/optimization, local-files-only, compile disabled,
same reference conditioning. No expensive model inventory repeated. Effective
model-ref/package revalidation requires the local host preflight; it is not
claimed from saved inventory identity alone.

Prepared the [existing first PowerShell block](NARRATOR-NEXT-INTEGRATION.md)
for owner execution in Windows PowerShell on BLACKHAT-BASE, adding the verified
rights-declaration pin and durable child exit-code record. Procedure was parsed
locally without executing it or its embedded Python. Only the first block is
authorized; later listener/credential/Serve examples remain unapproved.
Copy-and-paste version on FORGE:
`C:/admin/projects/KnowledgeNetwork/output/Narrator-One-Time-Diagnostic-eb5cb0e.txt`,
SHA-256 `34acb427bf1f0a4a1749104a4066bb389a54680641c2f9437fdfdc4186f8c56c`.
PowerShell and both embedded Python blocks parsed successfully; a self-check
confirmed exactly one canonical invocation. This is syntax validation only.

BLOCKED / NOT TESTED: actual new WAV path/format/duration/hash, CUDA selection,
host exit status and FunASR/kaldiio runtime participation. No runtime error exists
to report because execution was not attempted. Commercial questions remain the
actual restricted-component participation, applicable transitive local-use
obligations and any separate redistribution obligations; owner declaration and
static no-denoiser branch do not resolve them. Existing private draft stays
fail-closed. No new commercial clearance or listening assertion.

After the one owner-run attempt, retain the printed `private-smoke-<guid>` path,
`exit-code.private.txt`, stdout/stderr and `smoke.json` if produced. Keep raw logs
private; do not paste credentials or full logs into GitHub/chat. With the same
redirected drive available, FORGE can inspect that exact folder and report the
runtime results without rerunning inference. A failure/uncertain outcome must
be reconciled before any further authorization or execution.

Listening: play the new WAV locally at a comfortable level, compare identity
against the approved reference/known output, and note pronunciation, clipping,
noise, truncation and naturalness. Record the exact WAV hash and review result
privately. Listening does not establish commercial license compliance.

Minimum next integration steps remain: review actual diagnostic/import evidence
and voice quality; complete a truthful reviewed manifest; separately authorize
the loopback listener/scoped bearer and, after route inspection, private HTTPS
route; then test one short FORGE request with matching host/local WAV digests.
PR #20 remains draft/unmerged and publication PAUSED. Existing checkpoints,
backups and original narrator assets are preserved. Ponytail FULL applied;
documentation-only change, no repeated runtime regression or media render.

## November 15 continuation — evidence and staging package

Continued clean `feature/collector-v7-overnight` from exact source checkpoint
`3353a24efa3473c0e375dfec96cdd4fd757e6158`. The continuation commit is the commit
containing this section (`git log -1`); packaging uses the exact source checkpoint
above. PR [#20](https://github.com/oxieg3n/KnowledgeNetwork/pull/20) stays draft
and unmerged. Earlier receipts, worktrees, installers and backups are preserved.
No runtime source change, service restart/deployment, host inference, host write,
network change or public upload was performed in this continuation.

**PASS — reuse:** installed worker EXE/DLL hashes were read again and match the
pipe-repair values below. The corrected trust implementation and actual-context
health evidence are reused; no new pipe diagnosis or 4.96 GB inventory. Current
`state/operations.json` still hashes to
`d61551c51fc46bc65b6e3c11b0e6d12e38b13efdef44121a07c8570ee22b799d`.
Publication remains **PAUSED** and production scheduler remains disabled by the
preserved verified configuration; no new scheduled Assistant result is claimed.

**PASS / BLOCKED — rights:** the new private declaration exists and was read
through the already-authorized redirected host drive. Its actual SHA-256 is
`bc7d82dac515aadd72c061eebf9088df138f1e9ec746dd9b1287914eb6ede006`.
Canonical reference and saved original voice-design WAV both match
`050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`.
Relevant text-controlled design/copy history and installed CLI source corroborate
synthetic origin without reference-audio arguments. History is not an independent
execution receipt. Private evidence and an intentionally fail-closed draft
manifest retain the declaration as `consent_evidence`; no deployment-valid or
fully reviewed manifest is asserted. See [rights review](V9-RIGHTS-CONTINUATION.md)
for evidence hashes, limitations and remaining runtime/component review.
Private draft: `C:/admin/collector-v9/rights-continuation-7d0ce6c8e5594529b3dfe85ea50d22bb/narrator-manifest.DRAFT.private.json`,
SHA-256 `b6d1e866fb775c747122702b29e38f5a8ceb88d3b6bf280ccecce3902e04f04e`.
Root independently rehashed the declaration, canonical reference, draft and new
installer; all matched the specialist receipts. Only sanitized reports enter Git.

Installed source supports the canonical no-denoiser branch avoiding ZipEnhancer;
actual runtime imports remain **NOT TESTED**. The installed kaldiio restriction
is unresolved until the real trace and call path are reviewed. No packages were
removed, edited or replaced, and no stack-wide commercial clearance is claimed.

**PASS — staging package:** new unsigned local installer, not deployed:
`C:/admin/projects/KnowledgeNetwork/output/installer-v9-pipefix-002/The-Knowledge-Network-Collector-0.1.0-v9-pipefix-002-setup.exe`.
SHA-256 `4149bd4c66347429f65a570925bc158cbc36a8b752c36c741d1cfabf4439517a`.
Fresh worker identifies source build `0.1.0+3353a24efa3473c0e375dfec96cdd4fd757e6158`;
190 self-tests PASS and all 481 package manifest records match. Product version
remains 0.1.0; `v9-pipefix-002` identifies this staging release. Old Round5 package
is preserved. [Packaging, license, install/rollback limits](V9-PACKAGING-CONTINUATION.md).
Actual isolated install/upgrade is **NOT TESTED**: this installer uses the fixed
live AppId/service/Program Files path. Do not run it over the working service as
a test. Reuse an isolated Windows snapshot for installation acceptance first.
Keep a consistent private database backup, service/companion settings and current
patched binaries for rollback; never restore old data merely to roll back code.

**PASS — focused and integration checks:** 22 host and 17 client tests using
synthetic inference, 302 Python regression tests (5 existing FFmpeg skips), and
190 fresh packaged-worker checks. Regression command:
`$env:PYTHONPATH='src'; & ./.venv/Scripts/python.exe -m unittest discover -s tests -v`.
Private log: `C:/admin/collector-v9/v9-continuation-regression.log`.
Actual FORGE narrator status remains `BLOCKED_NARRATOR_CONFIG`, before network.
[Transport review and exact next gates](V9-TRANSPORT-CONTINUATION.md).

**BLOCKED — complete Short:** no exact approved branding recovered in the new
bounded host/VM Pictures/Videos check (20 files) or connected Drive name searches.
Earlier project/backup searches were reused. Existing native project/export
hashes still match; [branding/native report](V9-BRANDING-CONTINUATION.md) preserves
their paths and digests. The fixed 50-second unbranded fixture accepts narration
but does not already assemble branded bookends. A fresh editable assembly must
retime body/captions and use existing native operations once exact assets and
real audio exist. Full branded assembly, export, GUI interaction and listening
remain **NOT TESTED**. No completed narrated/branded Short is claimed.

**Owner actions genuinely required:**

- Approve/run exactly one canonical-script smoke from
  [the existing procedure](NARRATOR-NEXT-INTEGRATION.md), after reviewing the new
  rights evidence: new private `private-smoke-<guid>` folder under host kit004,
  one short original sentence, unchanged narrator settings, private import logs,
  WAV/exit/CUDA/PCM/hash evidence. This is evaluation evidence for unresolved
  runtime licensing, not commercial release clearance. No automatic retry.
  This continuation does not treat its preparation as inference authorization.
- Separately authorize any loopback listener/credential and dedicated 9443 route
  only after runtime/voice review and read-only Serve-state verification. No
  approved host command channel exists here; redirected files are not execution.
- Materialize the exact badge and portrait outro from Library into an authorized
  private source path; landscape original remains required for that orientation.
- Rotate the unrelated Hugging Face access token exposed in a helper tool output
  during history inspection. Its value was not retained in evidence or Git.
  Further history extraction was narrowed to relevant credential-screened lines.

The working plain-English Assistant instruction remains the local-only request
in [Assistant operations](../ASSISTANT-OPERATIONS.md), starting with the actually
tested installed health command below. The full request must stop at these real
prerequisites; no fabricated successful end-to-end command is provided. First
remote acceptance should use one short unsegmented request; the prepared full
13-segment demo entails 13 serialized canonical script/model invocations.

**Skills/review:** Ponytail 5.3.3 FULL is explicitly active; its installed skill,
plugin metadata, lifecycle hook configuration and review skill were inspected.
No new plugin/hook trust or environment setting was needed. Specialists used
nonoverlapping document paths; only root integrates. Prompt Sensei was not found
in the installed catalog/local skill search and was not applied. Google Drive
skill was read for connected exact-asset discovery. No UI changed: UI/UX Pro Max,
Taste visual/native gates were not rerun or claimed. Final review checks evidence
claims, private-data exclusion, package identity, unchanged controls and missing
native tests. Reboot, scheduled Assistant reliability and forced native race
faults remain later operational acceptance. The demo has **not** been publicly
uploaded.

## Current continuation from pushed checkpoint6a76f44

November14 continuation on `feature/collector-v7-overnight`; PR
[#20](https://github.com/oxieg3n/KnowledgeNetwork/pull/20) remains draft/unmerged.
This section supersedes older installed-worker hashes and pipe-status blockers
below. Historical receipts, installers, backups and passed inspector remain intact.

**PASS — installed pipe repair:** exact original medium-client failure was
OpenProcess/error5 (access denied), before QueryFullProcessImageName. SCM status
and config queries succeeded. Source `d85ab96`/`d5132eb` now validates the live
pipe PID against stable running own-process LocalService SCM identity/config
first, with strict fail-closed SCM errors and unchanged strict console fallback.
Native medium client now passes, despite process-query denial remaining in place.
Owner returned Assistant's actual FORGE health response: healthy,
windows_service, nonce `1587a1afca4a490c9075638f997625e1`, same worker identity,
companion true, reconciliation hold false, publication paused, scheduler false.
This is manual actual-context health, not a scheduled connection.
[Full diagnosis, test matrix, exact response and rollback](PIPE-TRUST-REPAIR.md).

Only three worker files plus their package-manifest entries were patched in
place; no entire-Collector reinstall. Current installed EXE:
`C:/Program Files/The Knowledge Network Collector/kn-collector.exe`, SHA-256
`60516f07332facbbfa484cb5a2b4b430cc42c12128bc6525283e589b812e2754`.
Current DLL SHA-256:
`cb1d2debccce27e47c0046bd6c2f60aaa8113600fc207429347f3d8f3545b3d3`.
Source build: `0.1.0+d5132ebba7fe8ae83b7ce9cb056904f926cabdd7`.
Fresh published worker: `output/collector-pipefix-001`. Existing Round5 installer
is preserved with original hash but lacks this fix; do not run it as routine
repair or claim a new installer was built. Dashboard/editor/runtime unchanged.

Service restart PID14316→4188 retained all13 jobs,39 events, metadata/sequence
rows exactly; integrity_check=ok. Worker ID remains
`cb6ce3cd482148e7b8b0c8661ec8c6e9`. Consistent pre-patch DB backup hash remains
`daca19da767c1ce7fd1a3149db358d42e31f0c3745ce42dc76f3f4e21f0adf4b`.
Private patch originals/verification: `C:/admin/collector-v9/pipe-auth-20261114-01`.
Native fake pipe rejected at ServiceIdentity with zero transmitted request bytes.
The triggerless least-privilege test task was removed. No service/process ACL
expansion or execution-policy changes. Original protected backups untouched.

**PASS — PR conflicts/CI:** exactly three V8 add/add documentation conflicts
resolved by adopting main's V9 supersession notices. No merge/rebase/force-push.
CI push filter now includes this branch; read-only Python Windows/Linux jobs and
Windows .NET worker/self-test/WPF compile jobs added using pinned official actions.
Hosted first Windows failure was synthetic short-TEMP alias mismatch; fixed test
roots only, preserving production inspector and all assertions. Both hosted
workflows at67a5cdb passed:
[push43647910451](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43647910451),
[PR43647914711](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43647914711).
Pipe-source head d5132eb also passed both hosted workflows:
[push43648989366](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43648989366),
[PR43648993931](https://github.com/oxieg3n/KnowledgeNetwork/actions/runs/43648993931).
Actual hosted Python3.12:302 tests per OS, OK with7 Linux/5 Windows explicit
skips; Windows builds zero warnings/errors and190 worker checks PASS.
Subsequent evidence-only commits do not change installed/source runtime code.
[Exact investigation/strategy](PR20-CI-INTEGRATION.md).

**PASS — reuse/validation:**302 Python tests with5 explicit FFmpeg skips in
source-review environment, including an actual Windows8.3 TEMP alias regression;
190 published worker self-test checks;23 narrator host/contract and17 direct
client tests (synthetic inference). PowerShell and embedded Python examples in
the prepared smoke procedure parse; no host commands were executed. Ponytail
5.3.3 FULL and review skill read/applied from
`C:/Users/oxieg3n/.codex/plugins/cache/ponytail/ponytail/5.3.3/skills/ponytail/SKILL.md`
and sibling `ponytail-review/SKILL.md`; runtime explicitly reports FULL active.
No plugin installation, new hook trust or session restart. Independent
source/rights/CI specialists
used nonoverlapping worktrees. No UI changed, so no new UI/UX/Taste gate claimed.

**BLOCKED — narrator rights/live acceptance:** inventory remains PASS at
VoxCPM2 revision7936080b41163874f38610f46f438e2c0757f9fd; not repeated.
Consent/commercial-use evidence for exact reference still absent. Installed
kaldiio has evaluation-limited terms; actual involvement in the no-denoiser
runtime is not established. Preserve environment and resolve actual runtime
scope rather than deleting dependencies or assuming all-component clearance.
[Rights and exact-assets review](NARRATOR-RIGHTS-AND-ASSETS.md).

Prepared a new non-overwriting canonical-script smoke with private logs, saved
inventory/package/ref binding, CUDA device-report check, actual PCM/duration/hash
validation and import diagnostics. It awaits scoped host authorization and rights
evidence. No host inference, listener, credential or dedicated Serve route was
created. [Exact owner commands and separate deployment gates](NARRATOR-NEXT-INTEGRATION.md).
FORGE status actually returns BLOCKED_NARRATOR_CONFIG. Real cross-machine WAV,
caption alignment and45–55s branded/narrated acceptance remain BLOCKED. The exact
badge and portrait/landscape outros remain missing; original hash enforcement
is unchanged. Existing50s synthetic project/render below are preserved, not
rebuilt or relabeled full acceptance. No listening claim.

Working Assistant health command (actually exercised; owner returned actual
Assistant-context JSON):

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))
```

For the full local-only Short use the plain-English acceptance request in
[Assistant operations](../ASSISTANT-OPERATIONS.md), with current installed hash
and real provider/companion syntax. No successful full command or output is
invented while host/rights/exact-assets gates are blocked. Publication remains
**PAUSED**; no demo or other media was publicly uploaded. operations.json hash
`d61551c51fc46bc65b6e3c11b0e6d12e38b13efdef44121a07c8570ee22b799d`
is unchanged. Gateway, all host routes, original narrator and separate website
were untouched. Reboot and scheduled Assistant execution remain NOT TESTED.

## Earlier checkpoint evidence (preserved)

Updated November 14, 2026. Publication remains **PAUSED**. No demonstration or
other media was publicly uploaded. Production workflows/permissions and the
separate poweredby repository were not changed. Final operations.json SHA-256
remains `d61551c51fc46bc65b6e3c11b0e6d12e38b13efdef44121a07c8570ee22b799d`.

## Remote review status

GitHub CLI authentication verified as oxieg3n; repository access verified.
Existing implementation branch pushed without force or history changes:
[feature/collector-v7-overnight](https://github.com/oxieg3n/KnowledgeNetwork/tree/feature/collector-v7-overnight).
Draft review PR: [#20](https://github.com/oxieg3n/KnowledgeNetwork/pull/20),
target main, not merged. Docs-only snapshot branch remains at29f493f untouched.
Pre-push audit covered247 unpublished historical blobs/2,662,489 bytes, largest
36,775 bytes: no credential-pattern or private/binary candidates. Two credential
URL matches were reviewed dummy negative tests on fixture.invalid/127.0.0.1.
Audit receipt stays private at `C:/admin/collector-v9/pre-push-audit-final.json`.
No workflow files/permissions changed. This is a bounded audit, not a guarantee
against every possible secret. No media/model/executable/database was pushed.

## Subsequent inspector repair

Owner-run host inventory now PASS at revision
`7936080b41163874f38610f46f438e2c0757f9fd`;9 snapshot files/4,960,731,830 bytes
and39 package files. This supersedes only the earlier inventory blocker below.
[Repair evidence, kit command, hashes,24+23 focused tests and remaining rights/API gates](INSPECTOR-SHARED-BLOB-REPAIR.md).
Actual reference consent, runtime parity/GPU/WAV and remote API remain blocked
or untested. No Collector rebuild or Gateway/network change. Earlier checkpoints,
backups and results below are historical evidence and remain preserved.

## Outcome and checkpoint

Continued the existing `feature/collector-v7-overnight` branch from original
checkpoint `8c0e7f0`, retaining the V8 checkpoint `8403136`, all helper worktrees,
assets and history. Non-destructively fetched origin/main `1db0530` and read its
AGENTS/V9 master/architecture instructions. V9 supersedes VoiceStudio narration.
No reset, reclone, new repository, force push or merge into main occurred.

Installed worker source checkpoint: `6f34384f7c77437c74c7a178ce6be0642a75bbbb`.
Evidence/docs checkpoint: `675fa9736cfc27d67d1fd24e890c26afe36e93d9`.
The final receipt commit only adds backup references; consult `git log` for its ID. An earlier noninteractive push lacked credentials. This was resolved by the
owner-configured GitHub CLI; current draft PR is linked above. Review preparation is local, not a claimed GitHub URL.

The service now dispatches narration and four bounded native editor operations
through an interactive-user companion. Actual inspect/apply/save/reopen and
synthetic export passed. Direct VoxCPM2 host/client implementation and negative
security/recovery tests passed locally. **No real V9 host speech was generated.**
A complete narrated/branded Short remains BLOCKED, not accepted on mock evidence.

## Installer and launch

Existing, installed unsigned staging installer (0.1.0):
`C:/Admin/Projects/KnowledgeNetwork/output/installer-v9-round5/The-Knowledge-Network-Collector-0.1.0-setup.exe`

SHA-256: `58b73fd62cb3a2997e12b801a88686a6854bfa1421c67cd027b1b0c6dba9da5d`.
Actual Round5 upgrade exited0 and preserved companion enablement and jobs.
Self-contained .NET runtime/notices/licenses are packaged. Python source clients,
OpenShot, models and owner media are not bundled; this is not a standalone full
studio acceptance. No signing certificate is claimed.

Installed CLI: `C:/Program Files/The Knowledge Network Collector/kn-collector.exe`
SHA-256: `70ff38e9c81a6b7f2617f94fe6ad262fb734d45e867674429023d57242020a76`.
Managed DLL: same directory `kn-collector.dll`, SHA-256
`5b16b7ce9bd14b3ec7f58acf2847f5a973e007db261a091c5d683e6a53f859a5`.
Dashboard apphost SHA-256:
`4d38514a5d64e1cfe61b5ffe50a1a033884eda48880968e69d581b780889d667`.
Dashboard DLL SHA-256:
`9ea6504a1967707237c38e9a664905decabcf82cd924d92fb983bf39f3cdf19a`.
Complete installed hashes: `C:/admin/collector-v9/final-package-hashes.json`.

```powershell
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health ([guid]::NewGuid().ToString('N'))
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' capabilities
```

Repair by rerunning this installer elevated as the configured owner, or using
canonical CLI `install-service`. Explicit `--enable-companion` and
`--disable-companion` are supported; noflag preserves the setting. Removal
preserves data. Upgrade now preserves the flag through Inno's remove/reinstall.
No PowerShell execution policy was bypassed or changed.

## Worker, recovery and backups

Service KnowledgeNetworkCollector: Running/Auto/LocalService. Stable worker ID
`cb6ce3cd482148e7b8b0c8661ec8c6e9`. Final health reports windows_service, companion
true, reconciliation hold false, publication_paused true and scheduler false.
Typed jobs: diagnostic.echo, research.snapshot, narration.generate,
editor.operation. Editor ops: inspect/apply/save/reopen. Queued export is disabled;
remote narrator readiness is explicitly false. Health is not a Dot connection.

Actual service restart retained all five sampled V9 job records/results exactly:
`C:/admin/collector-v9/native-final-restart.json`. Upgrade retained the original
three V1 jobs/IDs/hashes and worker identity. Schema2 uses consistent verified
pre-migration backup before changes, durable leases and media outcome-unknown
holds; no automatic replay of uncertain edits/speech. Read-only jobs can recover.

Final consistent SQLite backup (integrity_check=ok):
`C:/admin/collector-v9/worker-final-v9.sqlite`, SHA-256
`daca19da767c1ce7fd1a3149db358d42e31f0c3745ce42dc76f3f4e21f0adf4b`.
Automatic pre-v2 backup:
`C:/ProgramData/KnowledgeNetworkCollector/jobs.pre-v2-7f166ba07afc4dc099b17e46cc548f88.sqlite`,
SHA-256 `8456232e1201345733a877dac4545c8b0ac2ddafa3a4b8ba309fd374c5c554be`.
V1 cannot read schema2: rollback requires deliberate backup/outcome review, never
blind restore/replay. Reboot, locked/signed-out session and scheduled Dot access
remain NOT TESTED. Prior V8 uninstall/reinstall proof is preserved, not rerun V9.

Original verified backup `C:/admin/collector-backups/20261114-073652` untouched.
Its Git bundle was rechecked: SHA-256
`c09bd03678201fe4576e746246c7709ba32dbdc2b6b2c7992872f4c9367659cd`.
This is not a new rehash assertion for every original backup file.

Fresh private backup: `C:/admin/collector-backups/v9-final-20261114-1410`.
Contains complete-history Git bundle (52refs, verified), source ZIP at675fa97,
all149 copied evidence/source/package files hash-verified, synthetic project/render,
consistent database backup and installed installer copy. Manifest SHA-256:
`322d0312bcc00374de03a69ef974c6050509b98334b9ba7c37ff00eb60357313`.
Bundle SHA-256: `8eb8f4a30c75c217afaf07016e345084cbe19f310f3dd9b67c08a9477c601365`.
Source ZIP SHA-256: `ad732c623446ecfa8e6be5922fd5e74696b03806e2dbf4e9d73cd4d7f11d1fb6`.
Private verification receipt: `C:/admin/collector-v9/final-backup-receipt.json`.
An initial ACL-construction error affected only this new empty backup directory;
corrected using explicit SID objects before files were written. Original backup
and existing project ACLs were not touched.

One real negative fixture exposed OWNER RIGHTS ACL compatibility in Python3.13
private temp files. Completion was denied and lease expiry correctly held the
queue. Fixed at the shared ACL validation. Root reconstructed that this specific
synthetic job had never reached POST (missing provider route, no durable intent)
and performed a single stopped-service/exclusive-lock, backed-up reconciliation;
no other rows changed or generic clear/replay endpoint added. Original failure,
backup and assessment remain private:
`native-companion-roundtrip.json`, `fixed-negative-job-reconciliation.private.json`
(assessment SHA `c9cc45ed9860976ced83d8074ba9d1123ddb632cd05b75e236691d17155b5da2`).
The original child stage was not captured; reconstructed evidence is not called
a direct original provider observation. Normal production hold reconciliation
still requires operator evidence and remains a usability limitation.

## V9 narrator: observed facts and remaining gate

Read-only redirected `\\tsclient\D` access matched existing host bytes:
- canonical narrate.ps1: `98b75e5313d72d7aa65d160b41ebcb8726968bb7044700e2cffb510b5a72f189`
- reference.wav: `050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`
- voxcpm.exe: `582115086868288000249adebbdfbf2de7db8392534d760fa9675ad9b0217492`

Installed metadata: VoxCPM2.0.3, Python3.11, package Apache-2.0. Preserve fixed
Oxiegen-Narrator identity and exact script configuration: CFG2.0, ten steps,
no-denoiser, no-optimize, local-files-only, TORCH_COMPILE_DISABLE=1. Script,
reference and installed model files were not modified. The old reference is not
new narration and was not listened to. Model selected checkpoint/revision,
component license evidence/reference rights and runtime Python parity remain
BLOCKED. The owner-run old inspector returned a generic failure; cause is unknown.

The restricted loopback host service uses canonical script runner first. Direct
persistent Python model loading remains gated on verified runtime parity. It has
authenticated bounded routes, one GPU queue, durable idempotency, exact manifest
and artifact checks, no arbitrary command/path/voice/model API, process-tree
cancel/timeout and restart/storage-fault holds. Forge uses HTTPS/certificate and
private-address pins, scoped CredMan bearer, socket deadline and PCM/hash checks.
VoiceStudio app/API/PIN are retired and never used as fallback.

No host process, scoped key or dedicated HTTPS route was installed/configured;
no host screen or general execution channel used. Gateway and existing Tailscale
routes remain unchanged. Only new project kit files were placed with permission.
Latest kit is staged/readback-hash verified, **NOT EXECUTED**, at:
`D:/projects/knowledgenetwork/collector-narrator-v9-004` on BLACKHAT-BASE.
Owner next command when available:

```powershell
& 'D:/projects/knowledgenetwork/collector-narrator-v9-004/Inspect-InstalledVoxCPM.cmd'
```

Local ZIP:
`C:/Admin/Projects/KnowledgeNetwork/output/The-Knowledge-Network-Collector-Narrator-V9-004.zip`
SHA-256 `1ca74b22892fd13b138c3b804d5dd03005ef14a5d2dd9201fe47edd07bcec563`.
It contains no model/voice/key. Inspector reads/hashes installed files and creates
only a new protected private report. No inference/download/route changes. Older
kits002/003 and owner's differently spelled project folder remain intact.

Next live gate: inspect actual cache revision; review rights/component evidence;
run unchanged host narrator smoke, then parity comparison; owner-scoped route
setup; authenticated Forge status + actual new WAV transfer; import/caption/mix,
retake/listening and exact final render. Those steps cannot be replaced by mocks.

## Native editor and exact synthetic media

Actual service?user companion?OpenShot jobs:
inspect `313710c99fdc4aafa75449ebaca234c3`, apply
`42243403fca64f14af59384e3231ccf3`, save
`df260a58e18c4eb3b61d63a5da9c7fdd`, reopen
`9fe17030c3684cde80708c188c2a3334`. Revision56?59. The saved graphic alpha0.9
was read back with native float32 tolerance. Durable private receipts bind each
job; no mutation replay. Save exercised heartbeat across a 16-second call.

Project:
`C:/admin/collector-v9/editor-vault/service-editor-001/service-v9-reviewed-edit.osp`
SHA-256 `7d108fbe024e27fefe3e1373fc4ede4993b29ce8da3df4100996a2c410fe5e92`.
Video, same folder: `service-v9-local-review.mp4`
SHA-256 `f453bd15c060ac590bfe8beb58c93898e3acc249df40c43310fe72978fa77c63`.
Actual direct native export `897c917c5e2b4b18b6be561695ff67c6`, revision59:
50.000s, 1080x1920,30fps,1500frames,H264/yuv420p,AAC48k stereo. Full decode0;
black scan no events; silence scan only faded last0.508s. Six sources and revision
unchanged. Frames4/21/42s visually inspected: text, lower thirds, animated graphic,
three scenes and LOCAL REVIEW labels visible. Separate tones/music exist, not
real speech; no listening assertion. Report `native-editor-export-qc.json`.

Native OpenShot4.1.1/libopenshot1.1.1 remains authoritative, editable multitrack
`.osp`; WPF operations dashboard is not a replacement timeline. Existing adapter
covers trim/split/reorder/undo, titles, overlays/keyframes/effects, subtitle/retake
and mixing. Prior V8 native proofs remain separate historical evidence; manual Qt
GUI editing, preview/export parity, spoken retake, DPI and Dot remain unverified.
Older V8 exact project and video hashes were rechecked unchanged before V9 export.

Approved portrait/landscape outro MP4s and exact intro badge bytes are still
missing. Existing implementations and expected hashes preserved; bounded host
project-folder search found no candidates. No substitute or recreated approval.
All new fixtures are unbranded technical reviews, not full production acceptance.

## Tests, skills and review

Final configured-environment regression: **284 tests PASS, zero failures/skips,
55.991s** (`regression-final-venv.log`). Initial accidental system-Python run
failed26/errors with7skips from missing dependencies/FFmpeg; retained as
`regression-final.log`, corrected by using existing project venv and pinned tools,
not weakening tests. Installed worker **163 checks PASS**. Final dashboard
**17 checks PASS**,2727ms (`dashboard-smoke-v9-round5/smoke-results.json`). Real
shown WPF window, in-process UIA/focus/buttons, installed CLI/service/error/recovery;
96dpi rendered captures at800x600/1040x780. Not OS keystroke or high-DPI proof.

Real Windows checks: scoped credential write/read/delete; private ACL acceptance
and public/inherited denial; native runner complete/cancel/timeout stopping owned
children; inspector report ACL and redaction using MOCK inventories; service
negative narration blocked before POST; queued cancel without attempt; 288170-byte
valid unicode payload roundtrip;300085-byte invalid frame rejected in90ms after
shared chunked-pipe fix. Contract server/renderer MOCK tone tests are explicitly
local/synthetic; no host API/WAV acceptance. Logs/evidence root:
`C:/admin/collector-v9`; sanitized totals in TEST-RESULTS.json.

Ponytail5.3.3 FULL resolver/review skill actually applied. UI/UX Pro Max2.15.0
`C:/admin/tools/ui-ux-pro-max/.claude/skills/ui-ux-pro-max/SKILL.md` and Taste2.5.1
native visual judgment reuse reviewed charcoal/muted-blue tokens; no UI redesign.
Final dashboard captures were reviewed; web finish gates do not apply to native
WPF/Qt and are not claimed. No lifecycle trust/session restart performed.
Independent helpers owned worker/editor/voice changes in separate worktrees;
root serialized VM installs, service tests and heavy renders. Diff review focused
on trust boundaries, no duplicate scheduler/provider, cancellation, no-replay,
revision/hash binding, bounded storage/transport, installer migration and missing
integration tests. No speculative framework or general remote control was added.

## Assistant test and remaining follow-up

Copy the plain-English request in [Assistant operations](../ASSISTANT-OPERATIONS.md).
It includes real installed health/provider/companion syntax and requires a fresh
45-55s editable LOCAL REVIEW-ONLY Short with direct VoxCPM2 narration, captions,
text/graphics, effect, two video layers, ducked music, and both exact bookends
inside the duration. Full narrated/branded command has not run successfully;
missing live API/assets must return BLOCKED, never synthetic acceptance.

Real Assistant/Dot connection and scheduled execution remain NOT TESTED. Host
execution/setup/model rights, approved bookend bytes, manual GUI/audio review,
installer signing and reboot recovery remain scoped follow-up. The review PR
is now created as a draft; GitHub authentication is no longer a blocker. Existing production rights/review/exact-render/duplicate-upload gates
remain intact; no public upload, workflow permission change or publication.
