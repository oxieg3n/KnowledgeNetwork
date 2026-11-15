# V9 pipefix-002 installer preparation

## Current retention continuation ? existing installer retained

Build-Installer now rejects an existing canonical InstallerDirectory before any
build; a focused source contract test passes. No installer was rebuilt, deployed
or run. Pipefix002 and its recorded hash below remain the accepted staging
artifact. Fresh/upgrade/uninstall/rollback acceptance still requires an isolated
Windows environment and retention-safe procedures; it is NOT TESTED. CI confirms
unchanged worker source objects against prior190-check evidence, not a new build.
See [current continuation](V9-RETENTION-AND-RECOVERY-CONTINUATION.md). All historical
packaging/rollback assets below remain protected; no automatic cleanup is allowed.

November 15, 2026. Branch `feature/collector-v7-overnight`, source HEAD
`3353a24efa3473c0e375dfec96cdd4fd757e6158`. No source changes, deployment,
service restart, registry change or live database operation was performed.
Publication remains PAUSED; PR #20 remains draft/unmerged.

## PASS: fresh staging package

New unsigned installer, 58,271,059 bytes:
`C:/admin/projects/KnowledgeNetwork/output/installer-v9-pipefix-002/The-Knowledge-Network-Collector-0.1.0-v9-pipefix-002-setup.exe`

SHA-256: `4149bd4c66347429f65a570925bc158cbc36a8b752c36c741d1cfabf4439517a`.
The product version remains 0.1.0; `v9-pipefix-002` identifies this distinct
staging release. Its worker metadata is
`0.1.0+3353a24efa3473c0e375dfec96cdd4fd757e6158`.
The verified pipe patch commit `d5132eb` is an ancestor of this source HEAD.

Fresh package: `output/collector-release-v9-pipefix-002`.

| Artifact | SHA-256 |
| --- | --- |
| kn-collector.exe | `bec287a0c48395049590c6787f2e52039006325fabfd2b794628a8d87b276880` |
| kn-collector.dll | `2e54718e444211be58aed4576bedf3cf8732db2b4098295d82002a4e9546dca4` |
| files.sha256.json | `9d31cd2b064617b25977cd8b215a7a618015c7535190357cdb7c0344780ffaf6` |

All 481 manifest entries matched their actual bytes; the manifest also covers
every package file except itself. Bundled notices retain the existing .NET
license/notices, NuGet package metadata/licenses and Apache-2.0 text.
The old Round5 installer was rehashed unchanged:
`58b73fd62cb3a2997e12b801a88686a6854bfa1421c67cd027b1b0c6dba9da5d`.
Existing installed worker hashes matched the recorded pipe-patch release before
the build; that installation was not overwritten.

The existing Build-Installer.ps1 invocation was denied by the default Windows
PowerShell script policy. No execution-policy setting changed. The inspected
Build-Release/Build-Installer steps were executed as direct shell commands:
locked win-x64 worker restore; self-contained Release worker/dashboard publish
with shared compilation/build servers disabled; the same notice copying and
manifest generation; existing Collector.iss compiled with installed Inno6.7.3.
The resulting executable was renamed within its new directory to include the
distinct release identifier. Logs are retained under `output/`:
`packaging-v9-pipefix-002.log`, `packaging-v9-pipefix-002-inno.log`, and
`packaging-v9-pipefix-002-selftest.log`.

## PASS: bounded checks and review

The freshly packaged worker ran `self-test`: exit0, 190 checks PASS. This covers
the production-used SCM identity/race decisions, fail-closed errors, manifest
parsing, durable data/recovery and companion behavior. It does not repeat or
replace the historical medium-integrity installed-client and fake-pipe native
acceptance in PIPE-TRUST-REPAIR.md.

Ponytail5.3.3 FULL and its installed `ponytail-review/SKILL.md` were applied.
Review traced Collector.iss prepare/postinstall/uninstall into Program and
ServiceInstall, package integrity checks, fixed install path, retained data,
companion restoration and existing tests. No concrete new code defect was found.
No new dependency, parallel installer framework or unnecessary source change
was introduced. No UI changed; native UI/web design gates were not rerun.

Inno6.7.3's actual compiler banner says non-commercial use only. Its installed
License.txt nevertheless explicitly permits commercial applications, subject
to its copyright/origin requirements. The official
[purchase FAQ](https://jrsoftware.org/inno-setup/purchase) checked November15
states that buying a commercial license is requested, not strictly required.
The banner alone is therefore not evidence of a commercial-use prohibition.
No purchase, key access or new license acceptance occurred. This finding is
specific to the inspected compiler; it does not clear narrator dependencies.

## NOT TESTED: actual new-installer upgrade and rollback

This installer uses the same fixed AppId, Program Files directory and named
service. Executing it on this VM would change the working installation. No
separate isolated Windows environment was available in this workstream, so
actual install/upgrade/uninstall, extracted-installer payload verification and
new-package rollback were not exercised. Build/manifest/self-test PASS is not
installer acceptance. The artifact remains unsigned local staging.

Source review shows upgrades retain ProgramData and worker identity, remember
companion enablement before removing service registration, then restore it on
installation. These paths are unchanged from the prior Round5 upgrade evidence;
their native acceptance is reused within that historical scope only.

Do not run the old Round5 installer as routine repair: it lacks the pipe fix.
Preserve both installers, the current installation and existing rollback
originals at `C:/admin/collector-v9/pipe-auth-20261114-01/pre-patch-worker`.
A controlled future upgrade needs its own consistent database backup and exact
pre-upgrade installed manifest/binary copy. Binary rollback must not blindly
restore an older database; the historical pre-patch rollback also restores the
known medium-client authentication bug. Use the existing verified installed
CLI for normal operation until a deliberate deployment is authorized.
