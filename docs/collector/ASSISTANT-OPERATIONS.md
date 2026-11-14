# Assistant operations — installed staging build

Run on FORGE, not on Dot's cloud localhost or BLACKHAT-BASE. A real scheduled
Assistant connection remains unverified. Publication is paused.

## Verified installed commands

```powershell
$nonce = [guid]::NewGuid().ToString('N')
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health $nonce
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' capabilities
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' research-snapshot
& 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' get 131f54611e5a41c8b9e0d178b1a11dde
& 'C:/Program Files/The Knowledge Network Collector/kn-collector-dashboard.exe'
```

Use a new caller nonce. Supported service jobs are diagnostic.echo and
research.snapshot, not editor/narration jobs. The snapshot is immutable staging
metadata, not a second production scheduler. Native install-service/remove-service
require elevation and the canonical installed path; ordinary queries do not.

## Remote provider development client

From `C:/admin/projects/KnowledgeNetwork`, these exact commands were run. Load
only nonsecret per-user configuration; the PIN is read from Credential Manager.

```powershell
$env:PYTHONPATH = 'src'
foreach ($name in @('COLLECTOR_VOICE_PROVIDER','COLLECTOR_VOICESTUDIO_BASE_URL','COLLECTOR_VOICESTUDIO_ROUTE_FILE','COLLECTOR_VOICESTUDIO_SPOOL')) {
    Set-Item -Path ('Env:' + $name) -Value ([Environment]::GetEnvironmentVariable($name,'User'))
}
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voice status
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voice inspect-capabilities
```

The latest status is blocked authentication; discovery earlier passed. To
refresh the existing consumption credential, credential-save prompts without
echo. Do not pass the secret in command arguments or put it in a URL. Then run
verify-auth once to obtain actual denied/accepted evidence; repeated negative
authentication probes can encounter host restrictions.

```powershell
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voice credential-save
& ./.venv/Scripts/python.exe -m youtube_ops.collector_voice verify-auth
```

An original request is already prepared under the configured private spool:
job1610ea5e060d431980e52af9f273ed85, with script/segments in
`C:/admin/collector-v8/demo-script.private.txt` and `demo-segments.private.json`.
It has not been submitted for speech. `generate --job-id ... --text-file ...
--segments-file ... --rights-file ...` is implemented syntax, but its required
reviewed rights file does not exist and its successful host execution is not
claimed. Never manufacture that evidence or bypass the observed-model check.

The native fixture client supports --narration-receipt for a completed,
verified remote narration.json and sibling narration.wav inside the editor
vault. It imports speech and only actual sample-derived cue timing. The
receipt path is not a host filesystem path. The real remote attachment path
remains unrun. See editor.md and voice.md for bounded operations and recovery.

## Copyable Assistant acceptance request

> Assistant, connect to FORGE and perform a LOCAL REVIEW-ONLY acceptance test of
> The Knowledge Network Collector. First run
> `$nonce = [guid]::NewGuid().ToString('N'); & 'C:/Program Files/The Knowledge Network Collector/kn-collector.exe' health $nonce`
> and verify its nonce and windows_service context. Read this file and the V8
> handoff. Load the existing private remote VoiceStudio configuration and run
> its status command. Use only BLACKHAT-BASE's authenticated HTTPS speech API,
> a verified commercially eligible loaded model and a stock/consented voice.
> If authentication, exact model/profile evidence or approved brand media is
> missing, return the exact blocker without claiming a complete Short or
> substituting another narrator/brand asset. Once those prerequisites are
> actually verified, create a new editable1080x1920 project and a45–55second
> original Short with three scenes, two visual layers, native titles, graphics,
> effects/keyframes, real returned speech, sample-aligned captions and separate
> ducked music. Reuse intro.py/outro.py and the exact approved assets once each,
> preserving outro speech and counting both bookends in duration. Save/reopen,
> perform a revision-aware edit, export with the same native engine, decode/QC,
> inspect actual frames and listen if supported. Return actual job/project/video
> paths, revisions, durations, hashes and separate technical/visual/listening
> results. Keep publication paused; do not upload anything publicly.

This is a copyable acceptance instruction, not a tested one-command complete
production recipe. Full remote narration, bookend assembly and the service/editor
bridge remain incomplete or blocked; no such successful command is invented.
