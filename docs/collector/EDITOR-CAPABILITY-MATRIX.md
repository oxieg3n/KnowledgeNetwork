# Editor acceptance — V8

OpenShot4.1.1/libopenshot1.1.1 on FORGE; native `.osp` remains authoritative.
The stock Qt editor is separate from the WPF operations panel. No source-level
Collector editor workspace or Windows user-session companion is claimed complete.

| Capability | Actual evidence |
| --- | --- |
| Native import, overlapping tracks, text/lower thirds | PASS: actual1080p export, three sampled scenes visually inspected |
| Keyframes, graphic effect, independent music/audio | PASS: native fixture/export; technical tones, not narration |
| Trim/split/reorder, grouped undo | PASS: real native operations and restored clip summaries |
| 30000/1001 timing | PASS: split at1.001s and grouped undo; final fixture remains30fps |
| Save/edit/save/reopen/export | PASS: native project and exact render revision104 |
| Windows headless text | PASS after supported child-only QT_QPA_FONTDIR configuration; V7 missing-glyph failure preserved |
| Native music reset/ducking/undo | PASS property proof; original frame31 gain.25 became.05, longer-retake curve removed stale restore, two undos restored original clip JSON |
| Remote WAV import and measured captions | Source + unit tests only; no actual host speech generated |
| Caption/music retakes | Stateful unit tests + native music-property proof; real spoken retake and listening NOT TESTED |
| Manual Qt GUI edit followed by agent edit | NOT TESTED |
| Preview/final visual/audio parity | NOT TESTED |
| Protected approved bookends | BLOCKED: approved media bytes not materialized |
| Editor/narration dispatched by worker | Disabled; credential identity/user-session bridge unfinished |

Actual50.000s1080x1920 export: `C:/admin/collector-v8/editor-vault/technical-1080-001/native-final-1080.mp4`.
Full decode and configured black/silence scans passed. This is an unbranded,
unnarrated, local technical fixture. It is not full V7/V8 production acceptance.
