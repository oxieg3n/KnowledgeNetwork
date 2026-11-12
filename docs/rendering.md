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

Ephemeral output contains scene WAV/PNG/MP4 files, final MP4, exact script hash, model provenance/hash, encoding checks, scan logs, and segment-aligned transcript timestamps. Technical checks cover H.264, yuv420p, expected dimensions, 30 fps, AAC, Short duration, black segments and long silence. FFmpeg records loudness analysis. Human listening, pronunciation and measured loudness acceptance remain pending; a codec pass is not a sound-quality pass.

Current captions are a transcript sidecar with scene boundaries, not word-synchronized accessible burned-in captions. The visible short text is a diagram caption, not a verbatim transcript. Caption chunking/timing plus actual mobile and audio review is a publication blocker, not silently marked passed. Never label a generated or schematic image as product evidence.

The module refuses to overwrite an existing output directory. Do not commit media, models, or logs. Delete recovery media only under the publication/retention protocol after durable receipts are recorded.

### Observed local smoke result (2026-11-12)

- 34.319336 seconds, 1080 × 1920, 30 fps, H.264/yuv420p and AAC.
- No black segments of ≥0.5 seconds or silent spans of ≥2 seconds found by the configured scan.
- Actual frame at 18 seconds inspected: text fits within safe margins, no missing visible glyphs or overlap, technical-test warning visible.
- Five focused unit tests passed. No claim of full editorial, listening, caption or publishing acceptance.
- Final MP4 SHA-256: `8bd59a4bd689a85e50870811e8f04d6e17b1c81ca056eb2949595afd9d4ba9bc`.
- Evaluated model SHA-256: `6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22`.
- Final MP4 is ephemeral and not committed, uploaded or published.
