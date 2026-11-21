# Restricted direct Oxiegen-Narrator host worker

## November21 verified deployment and model lifetime

The standalone Limited-owner task and protected ProgramData service are live;
127.0.0.1:39110 authentication passed401/401/200. Private HTTPS9443, verified TLS
and pinned FORGE access passed. One short remote WAV and the actual Collector's
eight-segment37.76s body passed host/FORGE digest and decoded PCM checks. The
resulting native50-second Short was rendered and owner-approved. Publication
remains PAUSED. See [exact receipts, hashes and current status](overnight/FINALIZATION-RESULTS-2026-11-20.md).
Older blocked descriptions below retain their historical scope; never rerun an
old installer or recover the deferred V2 controller to satisfy this workflow.

The owner requires one model load for a complete narration job, all its segments
in sequence, then process exit/unload on completion, failure or cancellation.
The implemented optional `segments` array uses the installed VoxCPM2 CLI's batch
command with the same reference/model/CFG2/ten steps/no-denoiser/no-optimization/
local-only/compile-disabled settings. A batch is one durable host job with one
owned process and a complete WAV plus measured sample cues. The HTTP server
remains available without keeping a model resident while idle. A new batch is
accepted only when authenticated health advertises `segment_batches=true`.
The restricted host accepts at most16 nonempty stripped segments, a total12000
characters and a literal-space join equal to `text`; callers cannot select CLI
arguments, paths, voices or models. Cues must cover the complete decoded WAV.

The installed CLI may exit0 after individual batch errors, so success requires
all expected files, successful log counts, valid PCM and confirmed process exit;
partial files never become successful speech. Bounded output/logs, cancellation,
idempotency and uncertain-outcome holds still apply. New FORGE multi-segment
requests require this capability and never fall back to per-segment submissions.
Existing legacy receipts recover the original IDs through GET only.

The reviewed fixed owner updater is staged; **live batch parity/activation is
pending**, so the current installed service still executes the canonical script
once per legacy segment. After an exact task/physical-ledger/idle-fence proof,
the updater preserves original code/task/database and runs a Limited-owner
technical parity batch before enabling support. The old script SHA remains the
settings oracle; a batch receipt truthfully identifies `cli_segment_batch_v1`,
rather than falsely claiming the script itself executed. Real batch CUDA and
FORGE acceptance remain untested until activation. No route/policy/Gateway or
original narrator files change in this update.

## Historical baseline and initial acceptance boundaries

Current continuation: the canonical diagnostic, owner listening approval,
private host manifest validation and original loopback authentication passed;
reuse the latest [handoff](overnight/HANDOFF.md) at that exact scope. The
[owner-context control extension](narrator-control.md) prepares restricted
lifecycle/verification handlers, without changing the live narrator or implying
their deployment. HTTPS9443 and real FORGE narration remain blocked by policy
and deployment gates. Historical untested statements below describe the initial
source baseline, not a new failure of the completed local diagnostic.

This V9 worker belongs on BLACKHAT-BASE. FORGE remains the Collector/editor.
The worker calls only the existing canonical
`D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1` through the Windows system
PowerShell executable and structured `-File`, `-Text`, `-Output` arguments.
There is no VoiceStudio UI, API, backend, model selector or sharing dependency.
The historical installation directory name is retained unchanged.

The supplied script uses `reference.wav` beside the script and the installed
`D:\tools\audio\voicestudio\data\engines\voxcpm2\voxcpm2\.venv\Scripts\voxcpm.exe`.
The owner reported its flags: `clone`, cfg2.0,10 inference steps, no denoiser,
no optimization, local files only, `TORCH_COMPILE_DISABLE=1`. The worker does
not replace those defaults or supply a different voice. The completed owner-run
inventory binds revision `7936080b41163874f38610f46f438e2c0757f9fd` and installed
VoxCPM 2.0.3/Python 3.11.16. Installed CLI source defaults are auto device,
seed unset, normalize/denoise false, no supplied control/prompt transcript/LoRA;
the script supplies the existing reference only. Soundfile writes the WAV;
actual returned format/device and quality remain untested, not inferred defaults.
See [the next integration procedure](overnight/NARRATOR-NEXT-INTEGRATION.md) for
the non-overwriting smoke, runtime diagnostics and separate host authorization.

## Current acceptance boundary

Source, synthetic-manifest tests and authenticated loopback HTTP fixtures can
be tested on FORGE without model inference. They are not host narrator parity,
commercial-rights clearance, GPU proof or a FORGE-to-host transfer. No host
installation or Serve change is performed by this module. Deployment remains
blocked until the owner approves and performs the host steps below or supplies
an appropriately scoped deployment channel. The script and private reference
stay on the host and are never included in the public repository or release.

## API contract

All routes require `Authorization: Bearer <new app-specific secret>` even over
loopback. The server accepts only a loopback bind; default proposed port39110.
The credential must contain at least32 printable non-space characters. Store
it in Windows Credential Manager under the fixed user-scoped generic target
`KnowledgeNetworkCollector/OxiegenNarrator/Host`. A root/admin API key from a
different product is not an appropriate credential.

- `GET /health`: schema_version1, service `knowledge-network-voxcpm2`, fixed
  narrator_id `oxiegen-narrator`, process/queue status and pinned provenance.
  `model_state=not_probed` and `device=not_verified` avoid inventing GPU readiness.
- `POST /v1/narrations`: exactly `{idempotency_key,text,narrator_id}`. The key
  is32 lowercase hexadecimal characters, text is nonempty and at most12000
  characters, and narrator_id is fixed. The returned bare job's `id` equals
  the key, so a lost POST response can be reconciled with GET by that same ID.
- `GET /v1/narrations/{id}`: bare job, state queued/running/completed/failed/
  cancelled, text_sha256, provenance, stable error and cancel_requested.
- `GET /v1/narrations/{id}/audio`: completed exact WAV bytes only, rechecked
  against stored digest/size, with Content-Length and X-Content-SHA256.
- `POST /v1/narrations/{id}/cancel`: exactly `{}`. Queued cancellation commits
  immediately. Running cancellation remains pending until the owned process
  tree is confirmed stopped; a completed job remains completed.

Completed `audio` contains sha256,frames,sample_rate,channels,sample_width,
duration (seconds),bytes. Provenance contains exactly script_sha256,
config_sha256,model_revision,license_evidence_sha256. Source text, private paths,
credentials and subprocess output never appear in API responses or access logs.
The worker supplies no guessed word timestamps. FORGE may request meaningful
sentences separately and align captions using each returned PCM sample count.

Idempotency is persisted in SQLite; a changed text under the same key returns409.
Only one GPU job executes. The startup file lease rejects a second worker using
the same spool. WAL/FULL SQLite commits precede acceptance and dispatch. Stored
text/request hashes and provenance are rechecked before execution. A running
record recovered after restart becomes failed/outcome_unknown, with a durable
execution hold blocking all new dispatch. Unknown process outcomes and worker
storage faults also hold the queue. No automatic expiry, replay or unsafe clear
endpoint exists; resolution needs actual host outcome evidence and coordinator
reconciliation. Do not delete a hold or choose another key to force another run.

The limits are64 queued jobs,10000 retained jobs,256MiB free-disk reserve,
64KiB JSON requests,64MiB WAVs,600 seconds decoded audio and900 seconds script
runtime. The HTTP server is intentionally sequential with a bounded backlog and
30-second whole-request watchdog. Slow body reads or downloads can delay health
and cancellation by up to that bound; this is a single-operator service, not a
high-concurrency web platform. Private data is retained; there is no cleanup API.

## Host inspection and reviewed manifest

Run these only on BLACKHAT-BASE after reviewing the extracted Collector source
package and authorizing this project-specific host work. They do not run model
inference, change the script or configure networking:

```powershell
$script = 'D:\tools\audio\voices\Oxiegen-Narrator\narrate.ps1'
$reference = 'D:\tools\audio\voices\Oxiegen-Narrator\reference.wav'
$cli = 'D:\tools\audio\voicestudio\data\engines\voxcpm2\voxcpm2\.venv\Scripts\voxcpm.exe'
$python = Join-Path (Split-Path -Parent $cli) 'python.exe'
foreach ($file in @($script,$reference,$cli,$python)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required inspected file missing: $file" }
}
Get-Content -LiteralPath $script -TotalCount 200
Get-FileHash -LiteralPath $script,$reference,$cli -Algorithm SHA256
& $python --version
& $python -c "import importlib.metadata as m; d=m.distribution('voxcpm'); print(d.version); print('\n'.join(str(d.locate_file(p)) for p in d.files if str(p).endswith(('cli.py','__main__.py'))))"
```

Keep the resulting paths and inspection records private. Inspect the installed
CLI source/metadata to resolve the actual local checkpoint/snapshot revision,
seed/defaults, conditioning, output format and license obligations without
downloading anything. Verify the existing reference's commercial-use consent.
Hash each actual checkpoint/component and the retained license, consent and
inspection records. Do not substitute model-card claims for reference consent.

The private reviewed manifest is schema_version1 and narrator_id
`oxiegen-narrator`. It requires actual script_sha256, model_id
`openbmb/VoxCPM2`, exact model_revision, installed cli_version, license,
reviewed_by/reviewed_at, and reviewed booleans rights_reviewed,commercial_use,
youtube_use,voice_consent,script_reviewed,voice_identity_verified,
independent_runtime_verified. These booleans record substantive review; setting
them is not evidence by itself. No valid manifest is generated from placeholders.

`settings` must exactly match:

```json
{"cfg_value":2.0,"inference_timesteps":10,"denoiser":false,"optimize":false,"local_files_only":true,"torch_compile_disable":"1"}
```

`artifacts` is a private array of `{role,path,sha256}` using actual absolute
local host files. Required roles are cli_executable,narrator_reference,
model_checkpoint,license_evidence,consent_evidence,inspection_record. There must
be exactly one canonical cli_executable, one canonical narrator_reference and
one license_evidence record; add actual supporting runtime/model/tokenizer files
as additional records. Capture effective defaults and the actual inspected
Python/CLI/model binding in inspection_record, not guessed values. Every listed
file and the canonical script are rehashed before each job. This deliberately
adds checkpoint hash I/O; no unmeasured warm-cache performance claim is made.
config_sha256 binds those artifact digests, settings, revision and CLI version
without disclosing private paths.

After the owner chooses an extracted package directory, set its `src` on
PYTHONPATH. The following are real implemented syntax; their paths must be
actual owner-selected host locations:

```powershell
$env:PYTHONPATH = Join-Path $package 'src'
& $python -m youtube_ops.collector_narrator_host --help
& $python -m youtube_ops.collector_narrator_host inspect-script
& $python -m youtube_ops.collector_narrator_host validate-manifest --manifest $manifest
```

inspect-script hashes the three canonical files only. It explicitly leaves
model revision, rights and narrator parity unverified. validate-manifest refuses
missing, changed or unreviewed evidence. Neither command synthesizes audio.

## Owner-approved start, then separately reviewed networking

Create an empty VM/host-local private spool directory owned by the intended host
user, with inheritance disabled and access restricted to that identity, SYSTEM
and Administrators. Before opening the database or binding the API, production
startup performs a read-only Windows DACL preflight. It requires a protected,
nonnull DACL, an owner among those three identities, allow entries only for
those identities, and explicit FullControl for the current host user. The path
is passed as JSON on stdin to fixed system PowerShell code, never interpolated
as code; the check has a10-second timeout and redacted bounded result. Unsafe or
unverified permissions stop startup. No ACL is rewritten. This checks the spool
root policy; use a newly created private spool rather than assuming it repairs
preexisting child-file permissions. Unit-test stores can bypass production
startup deliberately; their mocked ACL results are not Windows security proof.
The selected spool must also sit beneath trusted, owner-controlled parent
directories. This check trusts local administrators and does not audit every
ancestor's ownership, all host accounts or the host filesystem as a whole.

The isolated read-only check needs no narrator manifest or model load:

```powershell
& $python -m youtube_ops.collector_narrator_host validate-spool --spool $spool
```

Provision a newly generated app secret using the interactive hidden prompt,
then start only the loopback worker:

```powershell
& $python -m youtube_ops.collector_narrator_host credential-save
& $python -m youtube_ops.collector_narrator_host serve --manifest $manifest --spool $spool --port 39110
```

Keep this process running. Its startup, sign-out and reboot recurrence are not
yet verified; no host Windows service is installed automatically. First test
invalid and valid authorization locally without exposing or logging the secret.
Then inspect the existing private route state read-only:

```powershell
tailscale serve status
```

Only after owner approval, confirm private HTTPS9443 is unused and tailnet policy
limits callers to FORGE. This is a **proposed** dedicated route, not a deployed
or verified URL. The owner may then add that specific route:

```powershell
tailscale serve --bg --https=9443 http://127.0.0.1:39110
tailscale serve status
```

Do not modify the existing HTTPS root/8085 or Gateway8443/43130 routes, reset
Serve, enable Funnel, open public/firewall ports or disable certificate checks.
If9443 is occupied, stop and choose a separately reviewed free route. Provide
the actual displayed private HTTPS origin to FORGE's protected route config;
do not infer it from the host name. Use app auth in addition to tailnet identity.
The Serve command follows [official CLI documentation](https://tailscale.com/docs/reference/tailscale-cli/serve)
but has not been run by this helper.

## Process-boundary evidence

The production runner uses supported Windows CreateProcessW with a pinned system
PowerShell application, suspended creation, assignment to a kill-on-close Job
Object, then resume. Children cannot opt into breakaway through this API. It
waits for all owned job processes, not just the wrapper, and distinguishes
confirmed cancellation from an unknown outcome. No shell string from a caller,
taskkill by caller PID, ExecutionPolicy bypass or host administration route exists.
Actual script review must also confirm it does not delegate through WMI or an
external broker that escapes ordinary process ownership.

An opt-in native runner harness is provided separately from automatic unit tests:

```powershell
python tests/test_collector_narrator_host.py --native-runner-smoke NEW_PRIVATE_OUTPUT_DIRECTORY
```

It patches only the internal argument constructor to fixed trusted PowerShell
built-ins writing synthetic PCM or sleeping with a child process. It tests actual
Windows process exit, cancellation and timeout ownership on FORGE without calling
the narrator, changing execution policy or loading a model. Results are labeled
FORGE_SYNTHETIC_WINDOWS_RUNNER_ONLY. This harness must be explicitly run in the
coordinator's serialized native slot. Even a PASS does not establish canonical
host script parity, consent, GPU quality, listening or cross-machine acceptance.


Selected-model binding: manifests additionally require one `model_revision_ref` artifact containing the actual effective Hugging Face `models--openbmb--VoxCPM2/refs/main`, with its observed hash. `model_revision` must be the exact 40-character lowercase commit read from that ref. Before every dispatch the worker invokes only the canonical engine sibling `python.exe` with fixed isolated code importing `huggingface_hub.constants` (no Torch, model, download or arbitrary caller code) to resolve the current cache. It rejects a different cache/ref/revision even if the previous weights remain unchanged. `model_checkpoint` must resolve to the selected snapshot's `model.safetensors` (preferred) or `pytorch_model.bin` fallback, including the blob target of that snapshot file. All artifact hashes remain checked. Keep the host cache, environment and kit under trusted owner control; simultaneous administrator mutation of a model during execution is outside this local integrity check.
