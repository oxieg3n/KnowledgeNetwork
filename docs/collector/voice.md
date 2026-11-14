# Remote VoiceStudio on BLACKHAT-BASE

V8 supersedes the earlier Forge-local voice adapter. The single
`RemoteVoiceStudioProvider` consumes a verified private authenticated host API;
it never launches, installs or configures VoiceStudio on Forge or the host.
There is no host desktop access, root-key fallback, model download, license
acceptance, cloning, admin route or publication operation.

## Private configuration and bootstrap

Keep actual addresses, credentials, profiles, evidence and media outside Git.
The operator must first identify the exact existing Sharing URL and verify the
private route. The adapter does not guess a hostname or port. Configure:

```powershell
$env:COLLECTOR_VOICE_PROVIDER = 'voicestudio_remote'
$env:COLLECTOR_VOICESTUDIO_BASE_URL = '<exact verified origin, without trailing slash>'
$env:COLLECTOR_VOICESTUDIO_ROUTE_FILE = '<private route evidence JSON>'
$env:COLLECTOR_VOICESTUDIO_SPOOL = '<existing ACL-private Forge spool directory>'
```

Route JSON schema1 requires `base_url` equal to that environment value,
`host_identity: "BLACKHAT-BASE"`, `pinned_addresses` containing only verified
private/tailnet IP literals, `verified_by`, `verified_at` and
`transport_evidence_sha256` identifying the underlying inspection record.
`transport` is `https`, `tailscale_http` or `isolated_link_http`; the scheme must
match. HTTP requires an actually verified encrypted tailnet route or an isolated
trusted link, not merely a private IP. These transport declarations are operator
evidence, not automatic network isolation proof. Public, loopback and link-local
destinations are denied. The operator verifies the hostname/peer mapping while
establishing the pins. Connections use an approved literal address directly,
avoiding DNS blocking/rebinding, while retaining the original hostname for TLS
certificate verification. System certificate and hostname
checks remain enabled. Environment proxies and redirects are never used.

`auth_mode` is `share_pin` or `scoped_bearer`. A scoped bearer also requires
`route_scoped: true` backed by review of a default-deny consumption-only proxy.
This boolean cannot turn a VoiceStudio root key into a narrow token. Never
provision the root key or an administrator session. Plain HTTP scoped bearer
is accepted only on a verified encrypted tailnet route, never an ordinary LAN.
PIN-only sharing is transient and needs replacement after sharing restarts.

Provision from an interactive Forge console, using the worker's intended
user-session companion identity:

```powershell
$env:PYTHONPATH = 'src'
python -m youtube_ops.collector_voice credential-save
python -m youtube_ops.collector_voice status
python -m youtube_ops.collector_voice verify-auth
python -m youtube_ops.collector_voice inspect-capabilities
```

`credential-save` uses an interactive hidden `getpass` prompt and Windows
`CredWriteW`; noninteractive entry is rejected. The generic credential target is
`KnowledgeNetworkCollector/VoiceStudio/` plus SHA-256 of the exact base URL.
The credential remains user-scoped in Windows Credential Manager. No secret is
accepted through arguments, environment variables, repository config or logs.
An installed LocalService worker does not inherit the desktop user's store;
that user-session broker integration must be verified separately.

Read-only discovery is possible before authentication evidence exists.
`verify-auth` actually sends an invalid credential to the protected voices route,
requires401/403, then requires a valid authenticated catalog. It atomically saves
private `remote-auth.json` bound to endpoint, route evidence and the credential's
Windows LastWritten version. Generation requires that receipt. Credential or
route changes invalidate it. A reachable unprotected `/health` is not proof.

Only `/health`, `/openapi.json`, `/v1/audio/voices`, `/v1/audio/speech` and the
three exact read-only capability routes `/.well-known/voicestudio-speech`,
`/model/loaded`, `/models` are callable. The latter must be GET routes in the
live schema. Their private responses are retained in
`host-capabilities.private.json`; console output contains only their digest.
Each optional route retains its own PASS/data or BLOCKED/safe-error result.
A denied loaded-model read does not discard a successful catalog read:
the command reports `PARTIAL`, `complete=false` and keeps both outcomes.
Mandatory health, schema and voice-catalog authentication still fail the whole
discovery before optional reads. A denied route is never retried with broader
credentials or replaced by an administrative endpoint.
No generic HTTP, transcription, settings or host-path operation exists. In
pinned0.5.6, even GET `/api/settings/license/{engine_id}` is on a require_admin
router. The consumption PIN does not authorize it; it remains denied here.
Acceptance of a notice would not itself establish commercial rights.

## Rights and model identity

Use `status --engine-id <discovered engine> --voice-id <discovered profile>` to
obtain the selected capability fingerprint. It binds installed backend version,
speech operation schema, exact engine/profile, exposed active model identity,
implementation, observed provider/device, precision and runtime versions.
Missing actual device remains unknown; the adapter never infers GPU use from
hardware availability. Catalog profiles and engine presets are accepted; generic
compatibility aliases are not selected as real voices.

Private rights JSON schema2 retains exact `engine_id`, `voice_id`, `model_id`,
`model_revision`, `license`, `reviewed_by`, `reviewed_at`, `voice_basis`, nonempty
HTTPS `evidence_urls`, and actual reviewed `rights_reviewed`, `commercial_use`,
`youtube_use`, `voice_consent` booleans. It additionally requires:

- `capability_fingerprint`: the reviewed selected live projection digest;
- `host_model_evidence_sha256`: the reviewed host model/license inspection record;
- `model_artifacts`: nonempty `{logical_name, sha256}` records for the exact host
  model/tokenizer assets. Host `path` fields are rejected and never opened on Forge.

These fields retain a substantive rights/model review; filling them does not
grant rights. The API does not attest every host file digest. A trusted owner
inspection record must establish the exact host files; generation additionally
requires a nonempty live `active_model_id` exactly matching reviewed `model_id`.
A loaded engine with missing/null model identity is
`BLOCKED_HOST_MODEL_UNVERIFIED`; a self-declared binding or fingerprint cannot
substitute for the missing observation. The live capability fingerprint also
detects exposed configuration changes. Generation
requires a loaded engine to avoid implicit first-use downloads. App licensing
does not authorize default noncommercial weights or a person's reference voice.

## Durable requests and real audio

If connectivity is absent, retain the actual request without inventing rights:

```powershell
python -m youtube_ops.collector_voice prepare --job-id <32-lowercase-hex-Collector-ID> --text-file <private-original-script.txt> --spool <existing-private-Forge-spool>
```

This intentionally returns exit1 and `blocked_remote_voice`, with script hash,
request identity and no claimed generation. Private `JOB_ID/request.json` retains
the original text. Repeating the same preparation is idempotent; changed text
conflicts. A later configured generation can adopt that exact unsubmitted request.

```powershell
python -m youtube_ops.collector_voice generate --job-id <same-Collector-ID> --text-file <private-original-script.txt> --rights-file <reviewed-private-rights.json> --segments-file <optional-private-sentence-list.json>
```

`--segments-file` is optional; omit the entire option when not supplied. It holds
one to16 meaningful sentence/paragraph strings whose transcript must match the
text file; total input is at most4096 characters. One cross-process file lease
allows only one active generation using the configured spool; a contender gets
backpressure. The service remains the authoritative scheduler/job owner.

Intent is fsynced before every actual POST. Read-only capacity retries are bounded
and respect short Retry-After values; long requested delays return backpressure.
POSTs are never automatically retried, including ambiguous timeouts or cancellation.
Partial files and receipts are retained for reconciliation. Repeated completed
job IDs return the same verified output; changed inputs conflict. A blocked or
uncertain submitted job cannot silently restart. A host API timeout does not
prove cancellation of its GPU work.

Before every segment POST, a fsynced global `remote-active.json` hold records the
job and segment identity. It clears only after actual completed audio is decoded,
hashed and durably recorded. A crash, timeout, cancellation or unvalidated response
leaves the hold blocking generation under **every** new job ID, including after a
process restart. Completed idempotent output reads remain allowed without POSTs.
There is no automatic expiry or override command. Resolution requires actual
host outcome evidence and a scoped coordinator reconciliation; deleting a pending
file or choosing another job ID is not a retry procedure.

WAV bytes stream into the new local job directory with bounded incremental reads,
socket/total deadlines,64MiB limits and disk reserve. A cancellation/deadline
watchdog closes the active transport even while waiting for connect, TLS, headers
or stalled body bytes. This bounds the consumer request, not the host GPU job;
its result remains uncertain and is never replayed. JSON bodies are never accepted as
audio. Actual PCM format, complete sample count, measured duration and SHA-256
are checked. Segment formats must match; exact frames are joined without gaps.
The final artifacts are sibling `JOB_ID/narration.json` and `narration.wav`.
The receipt retains provider/version, selected model/profile, host execution,
rights/model/capability/auth digests, elapsed time, segment audio hashes and:

```text
audio: frames, sample_rate, channels, sample_width, duration_seconds, sha256
cues: [{text, start_sample, end_sample, start, end}]
```

Cue seconds derive only from actual segment sample counts. This is sentence/
paragraph synchronization, not forced alignment or word timestamps. The editor
must enforce caption readability and allow correction. Successful output stays
`generated_pending_review`, `review_only=true`, `publication_eligible=false`,
`listening=NOT_TESTED`. Technical decoding never establishes actual listening.

## Evidence and limits

Upstream documentation/source was pinned for this implementation to
[`f7248260078120a812ae06674399d4baea862ee2`](https://github.com/debpalash/VoiceStudio/tree/f7248260078120a812ae06674399d4baea862ee2):
[Sharing](https://github.com/debpalash/VoiceStudio/blob/f7248260078120a812ae06674399d4baea862ee2/docs/sharing.md),
[authentication](https://github.com/debpalash/VoiceStudio/blob/f7248260078120a812ae06674399d4baea862ee2/docs/api-auth.md),
[private API](https://github.com/debpalash/VoiceStudio/blob/f7248260078120a812ae06674399d4baea862ee2/docs/production-private-api.md).
No recommended Docker installation, host setting or network change was executed.
The actual0.5.6 discovery handlers were additionally inspected at peeled release
commit `3915a62cb482bb43117aaebab57d22745bd1cc21`: setup/models.py (cached catalog
and local install scan), services/model_lifecycle.py (loaded inventory),
speech_platform.py (capabilities) and settings.py (administrative boundary).

Tests use explicit mocks and synthetic loopback TCP fixtures. The latter exercise
real byte-dripping headers/body and stalled-header/body cancellation on Windows.
These tests do not prove host reachability,
PIN enforcement, selected voice rights, GPU use, audible speech, host lifecycle,
Dot connectivity or publication acceptance. These require root's separately
serialized cross-machine tests. The exact endpoint was not provided to this
helper and no host API request was made.
