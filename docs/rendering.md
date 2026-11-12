# Local renderer and qualification boundary

The renderer produces an original graphic sequence with local Piper narration. It does not download YouTube footage, upload anything, or grant editorial approval. `publication_eligible` is always false at this layer. A separate reviewed production package must clear facts, rights, pronunciation, captions, distinct value, and mobile readability.

Install `requirements-render.txt` in an isolated environment. FFmpeg and ffprobe must be installed from the official distribution. Dependencies are version-pinned, not yet a transitive hash lock. Do not run sustained production on GitHub-hosted machines before the acceptable-use/runtime decision is resolved.

Run:

```
PYTHONPATH=src python -m youtube_ops.render examples/render_smoke.json \
  --output /absolute/new/ephemeral/directory \
  --voice /approved/local/model.onnx \
  --voice-metadata /approved/local/voice.json
```

The `.onnx.json` sidecar must be beside the model. Voice metadata requires `rights_reviewed: true`, `license`, `proof_url`, `rights_holder`, `model_sha256`, `commercial_use: true`, and `youtube_use: true`. No model is downloaded implicitly. Rights fields record a human/agent review; they are not proof by themselves. Preserve the underlying evidence and verify license scope before approving.

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
