# VoiceStudio adapter

The Knowledge Network Collector reuses the separately installed VoiceStudio.
`youtube_ops.collector_voice` is a standard-library local client, not a second
speech backend. It never installs engines, accepts model terms or selects a
fallback provider. It has no publication operation.

```powershell
$env:PYTHONPATH = 'src'
python -m youtube_ops.collector_voice status
```

This checks health, the running OpenAPI speech route and the voice/engine
catalog. Catalog availability does not prove installed weights, selected voice
rights or successful speech. Status deliberately leaves rights unverified.
Only numeric loopback endpoints with explicit ports are accepted. The client
disables environment proxies and redirects. An optional existing
`OMNIVOICE_API_KEY` is sent as a bearer credential without logging it.

An operator-reviewed private evidence JSON file is required for generation:

```powershell
python -m youtube_ops.collector_voice generate --text-file <body-text-file> --rights-file <reviewed-evidence-json> --output <new-private-output-directory>
```

These angle-bracket values must be actual local paths; the command is a syntax
reference, not evidence that a licensed voice or recording exists.
Evidence requires schema_version 1; exact engine_id and voice_id; model_id and
model_revision; license, reviewed_by, reviewed_at and voice_basis strings;
rights_reviewed, commercial_use, youtube_use and voice_consent all true;
nonempty HTTPS evidence_urls; and model_artifacts with local path and SHA-256
for every reviewed model component. These declarations record a substantive
rights review; filling fields is not itself that review. Do not manufacture
evidence or confuse application licensing with model/tokenizer/voice rights.
The client verifies referenced files before calling the backend and rejects
compatibility voice aliases unless they are actual engine presets. An exposed
active_model_id must match reviewed evidence. Single-model engine binding still
needs an exact installed-version/operator review; model-file hashes alone do
not prove which files an independently configured backend will use.
The backend must report execution_evidence.evidence_state=loaded for the exact
engine. Merely available dependencies cannot trigger a first-use model download.
Cold models must be loaded through the existing application after the operator
has verified their installed files, terms and configuration.

Generation writes and fsyncs a private intent before the one speech request.
The directory cannot already exist. A timeout is recorded as an unknown result
and is never automatically retried; reconcile the original VoiceStudio request
before starting another. HTTP, auth, unavailable session, unsupported schema,
voice/engine mismatch, disk space, content type, WAV structure, PCM format,
frame count and measured duration fail closed. Successful narration.wav and
narration.json retain review_only=true, publication_eligible=false and
listening=NOT_TESTED. No machine check claims a person listened.

Each invocation can generate one sentence or paragraph into its own new
directory for a selective retake. Its duration comes from actual PCM frames.
This client does not invent word timestamps or claim forced alignment. The
service must persist the containing job, bind its idempotency key and register
the output into the authoritative native editor project; standalone generation
does not establish that integration or its lifecycle/reboot acceptance.

## Installation observed on the VM

VoiceStudio.exe ProductVersion 0.5.8.0 / FileVersion 0.5.8 was detected in the
existing Program Files installation. Shipped config/app.json specifies backend
3900, web3901 and Electron development3902. Shipped routers/openai_compat.py
documents explicit engine model, profile ID and response_format=wav for
POST /v1/audio/speech. The shipped license notice distinguishes AGPL application
rights from default OmniVoice CC-BY-NC pretrained weights and separate
tokenizer terms. No commercial clearance was inferred.

Initial live GET /health, /openapi.json and /v1/audio/voices on loopback3900
were unavailable. No model/profile or legally usable narration was verified
by the initial probe. Native startup and latest results belong in HANDOFF.md.

Pinned upstream references consulted:

- [VoiceStudio v0.5.8 agent skill](https://github.com/debpalash/VoiceStudio/blob/v0.5.8/skills/voicestudio/SKILL.md)
- [v0.5.8 speech discovery](https://github.com/debpalash/VoiceStudio/blob/v0.5.8/docs/speech-platform.md)

The external skill was read as upstream operational guidance; no plugin or hook
was installed. Ponytail FULL was applied; ten focused unit tests cover the
client's trust boundaries and output validation. These tests use labeled
fixtures and mocks and do not count as VoiceStudio speech acceptance.
