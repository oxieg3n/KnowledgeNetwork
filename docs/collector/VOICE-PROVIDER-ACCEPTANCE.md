# Remote voice acceptance — V8

FORGE consumes BLACKHAT-BASE's existing VoiceStudio0.5.6 API. No host screen,
mouse, keyboard, clipboard, filesystem, settings, firewall, Gateway or Tailscale
handler was changed. Remote Workers is not required for this REST path.

PASS: supplied HTTPS endpoint matched the existing BLACKHAT-BASE tailnet peer;
TLS hostname/certificate verification remained enabled. Real health, OpenAPI and
voice-catalog GETs succeeded. An invalid PIN returned401 while the supplied PIN
returned200. The credential is in the Forge user's Windows Credential Manager,
never a URL query, process argument, environment secret or repository file.
Only nonsecret endpoint/route/spool configuration was persisted for that user.

Latest live check: **BLOCKED authentication**. The same stored PIN later failed
with401/403, independently confirmed with the standard HTTPS client. Its cause
(rotation, sharing change or an authentication restriction) was not proven.
Retries stopped; no host configuration or authentication bypass was attempted.

Additional observed reads: speech capabilities and `/models` succeeded;
`/model/loaded` was denied. The client retains partial evidence and does not
request administrative credentials. Model discovery reported only
`k2-fsa/OmniVoice` installed for TTS; the publisher's
[model card](https://huggingface.co/k2-fsa/OmniVoice) identifies pretrained weights
as noncommercial. No commercially cleared model/profile was verified. Engines
reported not_loaded and null actual execution provider/device. Health seeing
an RTX3060 does not prove actual GPU speech execution.

**No speech POST, host WAV, listening or real narration import/render occurred.**
Prepared original97-word request `1610ea5e060d431980e52af9f273ed85` is durably held
as blocked_remote_voice/rights_not_verified in the private editor media vault.

The provider uses fixed private destinations, TLS, bounded streamed files,
Credential Manager, exact observed model identity and rights evidence, measured
PCM segment cues, cross-process serialization and interruption watchdogs.
Uncertain POSTs retain a durable global hold across process restarts; no new
job, automatic retry, expiry or unsafe override clears an unknown host outcome.
Tests include real local socket fixtures for slow headers/body, cancellation
and TLS-handshake deadlines. These fixtures are not actual host synthesis proof.

Runtime still needs: a currently valid consumption credential, a loaded eligible
model and stock/consented voice with exact provenance, two distinct actual host
WAVs, imported editable speech/captions, listening/mix review and host lifecycle
tests. The LocalService worker intentionally does not read the interactive user's
credential or dispatch narration until that identity boundary is implemented.
