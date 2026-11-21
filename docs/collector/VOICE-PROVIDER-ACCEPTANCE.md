# V9 direct narrator acceptance

Current result (November21): **REMOTE_NARRATION_PASS**. Authenticated private
host deployment and FORGE transfer are complete: the actual Collector body job
`632b3b9a21b34e92a944aae80b478a81` returned37.76s/48000Hz mono PCM16, SHA
`77a1448af4a4c4251afdd7498e19a93cb70735eb3917a2d0bd41a82ee3e070d4`.
All eight host/FORGE hashes match and joined PCM matches their concatenation.
The50-second branded native export is technically accepted and owner preview
approved; publication remains PAUSED. [Current verified results](overnight/FINALIZATION-RESULTS-2026-11-20.md)
supersede earlier missing-model/rights/transport descriptions below. The new
single-load segment-batch implementation is tested in isolation but still awaits
live owner-context activation/parity. Dependency redistribution remains uncleared.

## Historical acceptance log

Updated November 14, 2026. The active provider is `RemoteVoxCPM2Provider`, fixed narrator `oxiegen-narrator`. VoiceStudio's former provider, PIN, health and model-selection evidence are historical; they do not establish readiness for this narrator.

## PASS: observed host file identity

FORGE read the owner-authorized redirected host drive `\\tsclient\D`, not FORGE's own D drive. The canonical host `narrate.ps1` and `voxcpm.exe` hashes matched the owner's inspection, and the actual script retained the approved fixed reference, CFG 2.0, 10 steps, no denoiser, no optimization, local-files-only and `TORCH_COMPILE_DISABLE=1`. No script, reference, installed engine, model or existing host settings were changed by these reads.

The existing reference WAV was decoded: 17.12 seconds, 48,000 Hz, mono, PCM16, 821,760 frames. Its SHA-256 is `050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`. This is the existing reference, **not newly generated narration**; listening was NOT TESTED. Private identity evidence is in `C:/admin/collector-v9/host-file-verification.private.json`.

Installed package metadata reports **VoxCPM 2.0.3**, Apache-2.0 package license, and entry point `voxcpm.cli:main`. The host's `pyvenv.cfg` identifies **CPython 3.11**. Read-only installed-source inspection found the default `openbmb/VoxCPM2` model, effective Hugging Face cache selection through `refs/main`, device `auto`, and no explicit seed. These observations do not prove the selected checkpoint revision, weight license, voice consent, actual inference device or runtime parity.

## PASS: source and FORGE-local checks

- Restricted authenticated host loopback API; fixed narrator/script and internally allocated output. No caller commands, paths or model selection.
- Durable idempotency, content conflicts, one-GPU queue, cancellation, restart/outcome-unknown holds and fatal storage-fault hold.
- Reviewed artifact manifest validation binds the current effective canonical-engine cache/ref, exact model revision and selected checkpoint, as well as script/reference/component digests. No fabricated manifest is accepted.
- Forge HTTPS client enforces private destination pins, certificate/hostname checks, scoped Windows credentials, bounded requests/WAV transfers, PCM/hash/duration validation and sample-derived segment cues.
- Actual FORGE Credential Manager round-trip, local HTTP client/server contract with synthetic inference, and native Windows runner completion/cancel/timeout with synthetic PowerShell fixtures. Child processes stopped in both stop cases; no execution-policy bypass.
- Owner-run inventory tooling is prepared with new private report folders, DACL verification, bounded hashing and redacted staged diagnostics. FORGE-local synthetic tests verify this tooling; they are not host inference proof.

The observed owner-run installed-model inspection attempt returned a generic BLOCKED result and left an empty report folder. Its failing stage was not established. Later source adds private staged diagnostics; no successful host model inventory is claimed. The owner is away, and no further host execution, model load or inference is being attempted.

## BLOCKED: live acceptance evidence

1. **Selected model revision and component/weight licensing:** the actual effective cached revision and complete installed component inventory remain unverified. The package's Apache-2.0 declaration does not independently clear every model/component.
2. **Reference rights and consent:** the observed reference identity does not establish its license, speaker consent or commercial/YouTube permission. A substantive reviewed manifest is still required.
3. **Runtime parity:** no new canonical-script smoke WAV, actual inference device proof or separately reviewed direct-Python parity exists. Preserve the approved narrator/settings; no fallback voice or model is allowed.
4. **New host service and API:** source/kit preparation is not installation. A running dedicated loopback service, approved private HTTPS route and app-specific credential have not been verified. No existing Gateway/root route is treated as this API.
5. **Real end-to-end narration:** no new V9 host speech WAV has been generated or received by FORGE. Actual transfer/decode/hash, listening, retakes, editable speech/caption import, mix, approved bookends and final render QC remain blocked or unverified.

See [host setup](host-narrator.md), [owner-run inspector](host-tools/README.md), [operations](ASSISTANT-OPERATIONS.md) and [handoff](overnight/HANDOFF.md). Public publication remains PAUSED. No demonstration video has been publicly uploaded.


## Subsequent owner-run inventory

PASS: selected host revision7936080b41163874f38610f46f438e2c0757f9fd,
9 snapshot files/4,960,731,830 bytes and39 package files. Exact cached model card
matches upstream at that revision and declares Apache-2.0/commercial use;
installed package LICENSE hash matches inventory. See
[inspector repair evidence](overnight/INSPECTOR-SHARED-BLOB-REPAIR.md).
This supersedes selected-cache inventory as a blocker, not reference consent,
remaining dependency obligations, runtime parity, actual GPU speech, host route
or a real FORGE-to-host WAV. No valid runtime manifest is asserted.
