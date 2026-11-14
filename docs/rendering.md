# Local renderer and qualification boundary

Current host setup and private configuration: [V9 Assistant operations](collector/ASSISTANT-OPERATIONS.md).

The renderer produces an original graphic sequence using verified, Forge-local VoxCPM2 Oxiegen-Narrator WAV receipts. It does not synthesize local body speech, download YouTube footage, upload anything, or grant editorial approval. `publication_eligible` is always false at this layer. A separate reviewed production package must clear facts, rights, pronunciation, captions, distinct value, and mobile readability.

Install `requirements-render.txt` in an isolated environment. FFmpeg and ffprobe must be installed from the official distribution. Dependencies are version-pinned, not yet a transitive hash lock. Do not run sustained production on GitHub-hosted machines before the acceptable-use/runtime decision is resolved.

Run:

```
PYTHONPATH=src python -m youtube_ops.render examples/render_smoke.json \
  --output /absolute/new/ephemeral/directory \
  --narration-receipt /private/scene-one/narration.json \
  --narration-receipt /private/scene-two/narration.json \
  --narration-receipt /private/scene-three/narration.json \
  --font /reviewed/local/font.ttf
```

Repeat `--narration-receipt` once for each original narrated scene, in scene order; licensed excerpts retain their existing source audio/captions. Each absolute local receipt has sibling `narration.wav`, fixed `provider=voxcpm2_remote`, `narrator_id=oxiegen-narrator`, exact scene-text SHA-256, script/config/model/license provenance, verified PCM metadata/hash and measured sample-based cues. Missing, mismatched, linked or uncaptioned narration fails closed before encoding. Cues must preserve the scene's words and fit the readable two-line caption layout; request actual shorter synthesized segments when needed rather than dividing existing audio by word count.

The new path never imports Piper/ONNX. Retired `--voice` and `--voice-metadata` inputs are recognized only to reject new local synthesis; there is no boolean legacy bypass. Historical requests, receipts and media stay unchanged. Existing exact-approved media can still use their separate finishing/recovery controls; re-synthesis needs a separately reviewed recovery binding. No model is downloaded implicitly. Receipt metadata is retained evidence, not independent rights clearance or proof somebody listened. The November 12 Piper evaluations and render hashes below are historical records, not the active narration path.

## Smoke test

`examples/render_smoke.json` is a technical test, visibly labeled NOT FOR PUBLICATION, with no news claims. Three original schematics test the pipeline, not an editorial treatment. It must never enter an upload queue. Repeatable cards are not a substitute for topic-specific storytelling. For real reporting, expand the graphics vocabulary and review distinctive visuals before qualification.

Local model evaluated November 12, 2026: `rhasspy/piper-voices` en_US/ljspeech/medium. Its repository README specifies MIT; its MODEL_CARD and the LJ Speech dataset page identify public-domain source recordings. Record model hash in the output manifest. Generic licensed synthesis only; no owner/creator impersonation or endorsement.

- https://huggingface.co/rhasspy/piper-voices/blob/main/README.md
- https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD
- https://keithito.com/LJ-Speech-Dataset/

Piper software licensing is distinct from model/data licensing. The installed piper-tts version is GPL-3.0-or-later; do not redistribute its binaries without satisfying that license. DejaVu Sans uses the Bitstream Vera/DejaVu font license. No font or voice binaries are committed by this project.

## Output and review

Ephemeral output contains scene WAV/PNG/MP4 files, final MP4, exact script hash, model provenance/hash, encoding checks, scan logs, and phrase-aligned transcript timestamps and burned-in subtitles. Technical checks cover H.264, yuv420p, expected dimensions, 30 fps, AAC, Short duration, black segments and long silence. FFmpeg records loudness analysis. Human listening, pronunciation and measured loudness acceptance remain pending; a codec pass is not a sound-quality pass.

Narration is split into short clauses with at most ten words and two rendered lines. Each phrase is synthesized separately, and its actual PCM sample count supplies the start/end times; no word-count timing estimate is used. Phrase WAVs are joined without inserting gaps. Captions are burned in through libass inside reserved safe margins and retained in `captions.json` with global offsets based on actual muxed scene duration. ASS sidecars retain per-scene timings. Text that could introduce ASS override syntax is rejected. The diagram caption remains distinct from the verbatim narration captions. This is phrase synchronization, not word highlighting or forced-aligned recognition. Full listening, pronunciation, prosody and mobile playback review remain publication gates. Never label a generated or schematic image as product evidence.

The module refuses to overwrite an existing output directory. Do not commit media, models, or logs. Delete recovery media only under the publication/retention protocol after durable receipts are recorded.

### Observed local smoke result (2026-11-12)

- 34.319336 seconds, 1080 × 1920, 30 fps, H.264/yuv420p and AAC.
- No black segments of ≥0.5 seconds or silent spans of ≥2 seconds found by the configured scan.
- Actual frame at 18 seconds inspected: text fits within safe margins, no missing visible glyphs or overlap, technical-test warning visible.
- Five focused unit tests passed. No claim of full editorial, listening, caption or publishing acceptance.
- Final MP4 SHA-256: `8bd59a4bd689a85e50870811e8f04d6e17b1c81ca056eb2949595afd9d4ba9bc`.
- Evaluated model SHA-256: `6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22`.
- Final MP4 is ephemeral and not committed, uploaded or published.

### Caption improvement smoke result (2026-11-12)

- Eight focused tests passed, including exact PCM timing, phrase preservation, markup rejection, safe positioning and centisecond rollover.
- Actual local Short: 34.986333 seconds, 1080 × 1920, 30 fps, H.264/yuv420p, AAC. 19 burned-in phrase cues; no configured black/silence detections.
- Four actual frames across all three scenes inspected at mobile scale: at most two lines, no clipping/overlap, readable safe margins, technical-test label visible. Full audio listening and playback acceptance remain pending.
- Exact MP4 SHA-256: `ead66581c634caac022bc9167072a208c913858afa17e105b27fa89796113d8c`.
- `publication_eligible` remains false. No upload or public publication performed.

## Subject-specific landscape scene preparation

Landscape supports 1920 × 1080, up to 30 scenes. Split each story across multiple scenes when narration exceeds 600 characters. No duration is padded to meet a target. Actual synthesized narration determines runtime; editorial review must enforce the requested duration.

A scene can add `graphic = {kind, items, emphasis}` in JSON form. `kind` is `flow`, `comparison`, or `timeline`. `items` is an ordered list of two to four objects, each with `label` (1–45 characters) and `detail` (1–100 characters). Optional `emphasis` is a zero-based item index. Example:

```json
{"title":"How this process works","narration":"Approved narration goes here.","caption":"Original explanatory diagram.","graphic":{"kind":"flow","items":[{"label":"Source","detail":"Read original documentation"},{"label":"Evidence","detail":"Verify the specific claim"}],"emphasis":1}}
```

These are qualitative diagrams, not measured charts. Relationships, dates, descriptions and emphasis must be justified by the actual story and verified sources. Timeline spacing does not represent elapsed duration. Text is checked for overflow and fails rather than clipping. These layouts currently support landscape only. Static diagrams do not satisfy a purposeful-motion requirement by themselves: the final production treatment must still be reviewed for scene-specific visual explanation and pacing.

This tool cannot substitute for listening review. A November 12 capability test extracted and emitted a 12-second WAV; the model interface returned "audio content omitted because you do not support audio input". Do not mark pronunciation or auditory/prosody checks passed based on FFmpeg statistics, a waveform, captions, or ASR alone. An audio-capable reviewer or owner must listen to the final narration and review playback synchronization.

### Deliberate visual sequencing

Each scene has a brief 180 ms maximum artwork fade-in and a thin elapsed-narration progress bar in 60 increments. The bar uses the measured synthesized duration, not text-length estimates. Captions are applied last and remain opaque: no zoom, cropping or caption fade is used. The separate bottom episode-position indicator remains static per scene. Neither progress indicator claims to measure a news subject.

For narration-linked emphasis, split a story into consecutive scenes with the same verified graphic items, changing `emphasis` to the item actually discussed in each scene's narration. The transition occurs at that scene's measured audio boundary. Do not rotate highlights arbitrarily or imply a causal flow not supported by the story. These subtle effects support a deliberate explanatory sequence; they do not independently establish editorial distinctness or satisfy listening/playback review.

## Required telemetry opt-out

Start every rendering Python process with `ORT_DISABLE_TELEMETRY=1` before any legacy Piper or ONNX Runtime imports. Official native ONNX Runtime builds can send telemetry by default, and disabling events after import may miss initialization. The V9 receipt-only renderer rejects Piper synthesis entirely and imports neither Piper nor ONNX Runtime; the older opt-out guard is historical evidence, not a fallback route. This is a local privacy control, not authorization to transmit telemetry. Official reference: https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md

The November12 full-recap first render was interrupted by safety review after seven completed scenes and an empty eighth scene. No finalMP4 or upload resulted. Keep that attempt as interrupted; reconcile process termination and record a distinct authorized recovery attempt before restarting with telemetry disabled.
