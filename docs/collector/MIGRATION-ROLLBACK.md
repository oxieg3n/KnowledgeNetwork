# Staging and rollback

No production migration occurred. `state/operations.json`, publication receipts
and hosted workflows retain their existing authority. The local worker has a
different SQLite database and accepts only diagnostic jobs and immutable
read-only research snapshots. It has no uploader or production scheduler.

To stage research, copy the existing public operations file outside the source
tree, compute its SHA-256, and pass both to `Install-Worker.ps1` using
`-ResearchSnapshot` and `-ResearchSha256`. A changed file fails digest checking;
it does not replace production state. Queue IDs and source revision are retained.

Before a future cutover, reconcile all active/ambiguous production work and
publication IDs, compare the complete imported state, verify backup/restore,
and coordinate disabling overlapping schedulers. None of these are implied by
a successful diagnostic or snapshot read.

For this staging build, stop/remove the service with the packaged
`Remove-WorkerService.ps1`. Its fixed executable-path guard refuses unrelated
services. The installer/uninstaller retain ProgramData SQLite and media. Keep
the previous package and an offline backup before upgrade. Never restore stale
production receipts or delete the only ambiguous-upload copy. No off-VM backup
or reboot recovery is claimed without the handoff's actual test evidence.
