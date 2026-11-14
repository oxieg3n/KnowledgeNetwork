# V9 final change review

Ponytail FULL review applied to connected callers, persistence, receipts, native
jobs and tests. Reused existing Python pipeline/OpenShot/native Windows SQLite
worker instead of a new media framework or second scheduler. Historical voice
storage/helpers were extracted once; active VoiceStudio paths fail closed.

Resolved concrete failures: Python OWNER RIGHTS ACL compatibility without
allowing foreign ownership/null/public DACLs; chunked bounded pipe reads after a
real 300KB frame timed out; Inno companion-flag retention through service removal;
post-save native revision race; DNS/socket total deadlines; invalid/partial WAV
cleanup; fatal host queue storage failure; exact model ref/manifest binding.
Targeted tests and actual VM negative/positive runs are recorded in HANDOFF.
No rights/publication/test gate was removed to make a check pass.

Reviewed bounds include single GPU queue, max retained jobs, disk reserve,
12000-character requests,512KiB pipe frames, signed-in owner-session scope,
lease cancellation and no blind replay after uncertain side effects. Remaining
sequential host HTTP responsiveness, manual outcome reconciliation and one-shot
companion startup are documented limits. No generic remote command endpoint,
autostart scheduler, network exposure or speculative abstraction was added.

Not checked live: actual host service/WAV/GPU/license/parity, real Dot connection,
reboot, high-DPI/manual editor use and listening. Synthetic/local contract evidence
is labeled explicitly. Installer is unsigned; Python/OpenShot are prerequisites.
Review PR is not created because authenticated push was unavailable.
