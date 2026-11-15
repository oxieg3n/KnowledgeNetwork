# Next narrator integration: owner-run gates

Prepared from checkpoint `6a76f44`. Inventory revision
`7936080b41163874f38610f46f438e2c0757f9fd` already PASSED; do not rerun the
inspector or rebuild/reinstall the Collector. Publication remains PAUSED.
These are prepared commands, **not executed host tests**. No host files, keys,
processes, routes, Gateway, model or original narrator assets were changed.

## Required evidence before speech

Keep the reference consent and commercial/YouTube-use evidence private and bind
it to reference SHA-256
`050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`.
The record must identify the reference's source and speaker/rightsholder,
permission for voice cloning/synthetic derivative speech and commercial channel
use, scope/conditions, date and reviewer. A model license or an owner-approved
voice name does not establish the speaker's consent. Resolve installed-component
obligations in [the rights report](NARRATOR-RIGHTS-AND-ASSETS.md) before declaring
commercial readiness. Do not populate reviewed-manifest booleans from this plan.

## Minimal proposed host smoke action

November 15: the owner explicitly authorized exactly one diagnostic inference
from checkpoint `eb5cb0e7f3a8132ab6628fa60a0348f3cf898240`, not a listener,
credential, route or commercial release. FORGE has redirected-drive file access
only; no authorized host execution channel was available. **Not executed.**
The script/reference/CLI/saved-inventory/declaration pins below were rehashed
through that drive and still match. Run only this first PowerShell block locally
on BLACKHAT-BASE, once, when the GPU is free. Do not run the later deployment
examples. After any attempted invocation, preserve its folder and reconcile the
outcome before another run; this authorization does not grant a retry.

Owner authorization is needed for **one local inference using the unchanged
canonical script**, creating only a fresh private folder under kit004 and its
logs/WAV. Run on BLACKHAT-BASE, in the same intended owner account/environment
as the existing narrator, with no other GPU/render job active. This action
does not authorize installing a listener or changing networking. Review rights
first. Do not stop unrelated processes to obtain the GPU slot.

Paste in Windows PowerShell after that approval. The existing kit source is
reused for PCM and ACL validation. No execution-policy bypass is used.

```powershell
$ErrorActionPreference = 'Stop'
$narratorKit = 'D:/projects/knowledgenetwork/collector-narrator-v9-004'
$narratorPython = 'D:/tools/audio/voicestudio/data/engines/voxcpm2/voxcpm2/.venv/Scripts/python.exe'
$narratorScript = 'D:/tools/audio/voices/Oxiegen-Narrator/narrate.ps1'
$narratorReference = 'D:/tools/audio/voices/Oxiegen-Narrator/reference.wav'
$narratorRights = 'D:/tools/audio/voices/Oxiegen-Narrator/reference-rights-private.md'
$narratorCli = 'D:/tools/audio/voicestudio/data/engines/voxcpm2/voxcpm2/.venv/Scripts/voxcpm.exe'
$narratorInventory = Join-Path $narratorKit 'docs/collector/host-tools/private-inventory-0fc6b750b895482c9421c2b5ae969066/inventory.json'
$narratorPins = @{
    $narratorScript = '98b75e5313d72d7aa65d160b41ebcb8726968bb7044700e2cffb510b5a72f189'
    $narratorReference = '050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44'
    $narratorRights = 'bc7d82dac515aadd72c061eebf9088df138f1e9ec746dd9b1287914eb6ede006'
    $narratorCli = '582115086868288000249adebbdfbf2de7db8392534d760fa9675ad9b0217492'
    $narratorInventory = '8db573cd5c002dd3e934f6b03dfbb6a78ad4245d263070a320a6db1914a08898'
}
foreach ($narratorFile in $narratorPins.Keys) {
    if ((Get-FileHash -LiteralPath $narratorFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $narratorPins[$narratorFile]) {
        throw 'Pinned narrator input changed; stop and review.'
    }
}
$narratorRun = Join-Path $narratorKit ('private-smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $narratorRun -ErrorAction Stop | Out-Null
$narratorAcl = Get-Acl -LiteralPath $narratorRun
$narratorAcl.SetAccessRuleProtection($true, $false)
foreach ($narratorRule in @($narratorAcl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))) {
    $narratorAcl.RemoveAccessRuleSpecific($narratorRule)
}
$narratorUser = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach ($narratorSid in @($narratorUser, 'S-1-5-18', 'S-1-5-32-544')) {
    $narratorRule = [Security.AccessControl.FileSystemAccessRule]::new(
        [Security.Principal.SecurityIdentifier]::new($narratorSid), 'FullControl',
        'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $narratorAcl.AddAccessRule($narratorRule)
}
Set-Acl -LiteralPath $narratorRun -AclObject $narratorAcl
$narratorRun
$env:PYTHONPATH = Join-Path $narratorKit 'src'
& $narratorPython -m youtube_ops.collector_narrator_host validate-spool --spool $narratorRun
if ($LASTEXITCODE -ne 0) { throw 'Private folder validation failed.' }

# Reuse the saved inventory; check only the effective ref and small package sources.
@'
import json, sys
from pathlib import Path
from youtube_ops.collector_narration_common import sha256_file
from youtube_ops.collector_narrator_host import _effective_model_ref
i = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert i['revision'] == '7936080b41163874f38610f46f438e2c0757f9fd'
r = _effective_model_ref()
assert r == Path(i['revision_ref'])
assert sha256_file(r) == i['revision_ref_sha256']
assert r.read_text(encoding='ascii').strip() == i['revision']
for p in i['package_files']:
    assert sha256_file(Path(p['resolved_path'])) == p['sha256']
print('PASS saved revision and package binding; no model inference yet')
'@ | & $narratorPython - $narratorInventory
if ($LASTEXITCODE -ne 0) { throw 'Runtime source/ref binding failed.' }

$narratorText = 'This is a private Knowledge Network narrator test.'
$narratorWav = Join-Path $narratorRun 'narration.wav'
if (Test-Path -LiteralPath $narratorWav) { throw 'Refusing existing output.' }
$narratorPowerShell = Join-Path ([Environment]::GetFolderPath('System')) 'WindowsPowerShell/v1.0/powershell.exe'
# Native stderr may be represented as ErrorRecords by Windows PowerShell 5.1.
$narratorPriorImportTime = $env:PYTHONPROFILEIMPORTTIME
try {
    $env:PYTHONPROFILEIMPORTTIME = '1'
    $ErrorActionPreference = 'Continue'
    & $narratorPowerShell -NoLogo -NoProfile -NonInteractive -File $narratorScript -Text $narratorText -Output $narratorWav 1> (Join-Path $narratorRun 'stdout.private.txt') 2> (Join-Path $narratorRun 'stderr.private.txt')
    $narratorExit = $LASTEXITCODE
} finally {
    $env:PYTHONPROFILEIMPORTTIME = $narratorPriorImportTime
    $ErrorActionPreference = 'Stop'
}
$narratorExit | Set-Content -LiteralPath (Join-Path $narratorRun 'exit-code.private.txt') -Encoding ASCII
if ($narratorExit -ne 0) { throw 'Narrator failed; preserve logs, do not automatically retry.' }
$narratorLog = Get-Content -LiteralPath (Join-Path $narratorRun 'stderr.private.txt') -Raw
if ($narratorLog -notmatch 'Running on device: cuda(?:\:\d+)?, dtype:') {
    throw 'No canonical runtime CUDA selection evidence; preserve WAV as unverified.'
}
foreach ($narratorFile in $narratorPins.Keys) {
    if ((Get-FileHash -LiteralPath $narratorFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $narratorPins[$narratorFile]) {
        throw 'Pinned input changed during smoke; output is unverified.'
    }
}
@'
import json, sys
from pathlib import Path
from youtube_ops.collector_narration_common import inspect_wav
p = Path(sys.argv[1])
r = {'scope': 'HOST_SCRIPT_SMOKE_ONLY', 'audio': inspect_wav(p),
     'cuda_evidence': 'canonical CLI selected cuda and completed generation; see private stderr',
     'listened': False, 'voice_parity_reviewed': False, 'publication_eligible': False}
with p.with_name('smoke.json').open('x', encoding='utf-8') as f:
    json.dump(r, f, indent=2)
print(json.dumps(r, indent=2))
'@ | & $narratorPython - $narratorWav
if ($LASTEXITCODE -ne 0) { throw 'PCM verification failed.' }
$narratorRun
```

This verifies decoded PCM, sample-derived duration and SHA-256 only after actual
generation. The CUDA evidence is the inspected canonical runtime's device report
plus successful generation, not a CUDA kernel profiler trace or a GPU-availability
probe. Preserve complete private logs; errors must not be posted publicly.
If interrupted, inspect owned process outcome before retrying; no automated
timeout/replay or process killing is introduced by this manual smoke procedure.
The temporary Python import-time diagnostic records actual imports in private
stderr without changing voice parameters; inspect it for FunASR/kaldiio and
other component use before narrowing the runtime license review. It adds timing
overhead, so this is not a performance benchmark. Missing an import name is not
by itself a complete transitive license audit.

Compare the saved script settings (CFG 2.0, ten steps, no denoiser/optimization,
local files only, compile disabled) with the unchanged script and the inspected
CLI defaults: auto device, seed unset, normalize/denoise false, no control,
prompt transcript or LoRA supplied. The installed model reports device/dtype.
The CLI writes soundfile's WAV default; use observed PCM metadata above rather
than guessing a sample rate. Unset seed means output hashes need not repeat.
Have the owner listen against the approved reference/known prior output and
record voice identity, pronunciation, quality and conditions privately. The
reference WAV itself is not a same-text golden output. No direct persistent
Python replacement or claimed waveform equality is part of this smoke.
Record whether VoiceStudio was already stopped; do not stop unrelated processes
or claim independence from a process-state check that was never collected.

## Host listener and route: separate authorization

After substantive consent/component/runtime review, use the existing private
manifest schema in [host-narrator](../host-narrator.md). Bind actual resolved
shared-blob targets from the PASSED inventory, actual ref and supporting files;
do not use linked logical checkpoint paths or invented approval values. Include
the smoke/settings/rights review as private evidence. Service startup rehashes
the selected artifacts and therefore remains heavier than this smoke preflight.

The minimal authorized host action would be: create one new protected private
spool with the ACL block above, provision one app-specific CredMan credential,
and start the loopback process using the existing engine. With `$narratorManifest`
set to the actual reviewed private manifest and `$narratorSpool` to that new
validated spool (neither exists by assertion here):

```powershell
& $narratorPython -m youtube_ops.collector_narrator_host validate-manifest --manifest $narratorManifest
if ($LASTEXITCODE -ne 0) { throw 'Manifest review failed.' }
& $narratorPython -m youtube_ops.collector_narrator_host validate-spool --spool $narratorSpool
if ($LASTEXITCODE -ne 0) { throw 'Spool validation failed.' }
& $narratorPython -m youtube_ops.collector_narrator_host credential-save
if ($LASTEXITCODE -ne 0) { throw 'Credential provisioning failed.' }
& $narratorPython -m youtube_ops.collector_narrator_host serve --manifest $narratorManifest --spool $narratorSpool --port 39110
```

No autostart/service install is proposed yet. Review loopback unauthorized denial
and authenticated health first; never put the bearer in shell history or logs.
Separately approve a dedicated Serve route only after read-only
`tailscale serve status` confirms HTTPS 9443 is unused and tailnet policy permits
only FORGE. Then the proposed command is
`tailscale serve --bg --https=9443 http://127.0.0.1:39110`, followed by
`tailscale serve status`. Preserve the existing root/8085 and 8443/43130 routes;
never reset Serve or enable Funnel. An occupied route is a blocker, not permission
to overwrite it. Actual URL/address and transport evidence go in private FORGE
route config per [Assistant operations](../ASSISTANT-OPERATIONS.md).

## FORGE acceptance after deployment

Use the existing `youtube_ops.collector_voxcpm2 status`, interactive
`credential-save` and `generate --job-id <fresh-guid-N> --text-file <private-file>
--segments-file <private-JSON-array>` syntax in the configured project venv.
Do not execute before actual route, credential and expected provenance are
reviewed. Preserve the generated job ID and receipt for reconciliation; never
choose another ID to retry an unknown result. Generate meaningful short phrases;
the consumer concatenates actual returned PCM and derives captions from sample
counts, rather than estimating word timings. A host smoke alone is not this test.

Require new downloaded WAV bytes, matching remote/local SHA-256, PCM/duration,
exact model/script/config/license provenance and sample-bound caption cues.
Then use the existing native fixture's `--narration-receipt` option and the exact
approved bookends for the full 45–55-second acceptance request in
[Assistant operations](../ASSISTANT-OPERATIONS.md). Missing assets, consent,
actual Assistant context or host transport keep the full test BLOCKED.
