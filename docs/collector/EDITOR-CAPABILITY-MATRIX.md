# Editor acceptance — V9

OpenShot 4.1.1/libopenshot 1.1.1 on FORGE; native `.osp` remains authoritative.
The stock Qt editor is separate from the WPF operations panel. The one-shot
Windows user-session companion has a verified service-to-native round trip for
four operations. A Collector editor workspace, manual Qt editing, and a real
Assistant/Dot connection have separate acceptance gates.

| Capability | Actual evidence |
| --- | --- |
| Native import, overlapping tracks, text/lower thirds | PASS: V8 actual 1080p export, three sampled scenes visually inspected |
| Keyframes, graphic effect, independent music/audio | PASS: native fixture/export; technical tones, not narration |
| Trim/split/reorder, grouped undo | PASS: real native operations and restored clip summaries |
| 30000/1001 timing | PASS: split at 1.001s and grouped undo; final fixture remains 30fps |
| Save/edit/save/reopen/export | PASS: V8 native project and exact render revision 104; V9 service save/reopen separately verified below |
| Windows headless text | PASS after supported child-only `QT_QPA_FONTDIR` configuration; V7 missing-glyph failure preserved |
| Native music reset/ducking/undo | PASS property proof; original frame 31 gain .25 became .05, longer-retake curve removed stale restore, two undos restored original clip JSON |
| Worker-dispatched editor inspect/apply/save/reopen | PASS: actual installed service, user-session companion, and native OpenShot; fresh V9 fixture advanced from revision 56 to 59 |
| Editor export through worker queue | Disabled; export queue capability remains false |
| V9 direct native export | Completed: 50s, 1080×1920, 1,500 frames; decode/QC and visual review pending at this checkpoint |
| Remote WAV import and measured captions | Source + unit tests only; no actual host speech generated |
| Caption/music retakes | Stateful unit tests + native music-property proof; real spoken retake and listening NOT TESTED |
| Worker-dispatched narration | Implemented source; genuine host narration BLOCKED, no completed live generation accepted |
| Manual Qt GUI edit followed by agent edit | NOT TESTED |
| Preview/final visual/audio parity | NOT TESTED |
| Protected approved bookends | BLOCKED: approved media bytes not materialized |
| Real Assistant/Dot-to-VM editing connection | NOT TESTED; local service calls do not establish this connection |

The actual V9 service jobs were inspect `313710c99fdc4aafa75449ebaca234c3`,
apply `42243403fca64f14af59384e3231ccf3`, save `df260a58e18c4eb3b61d63a5da9c7fdd`,
and reopen `9fe17030c3684cde80708c188c2a3334`.
The saved project is
`C:/admin/collector-v9/editor-vault/service-editor-001/service-v9-reviewed-edit.osp`,
SHA-256 `7d108fbe024e27fefe3e1373fc4ede4993b29ce8da3df4100996a2c410fe5e92`.
It contains no real narration or approved bookends. The V9 direct native export
passed full decode and black scan; silence scan detected only the faded final
0.508s. This is technical tone output, not listening or publication acceptance.
Video SHA-256: `f453bd15c060ac590bfe8beb58c93898e3acc249df40c43310fe72978fa77c63`.

Preserved V8 evidence: actual 50.000s 1080×1920 export at
`C:/admin/collector-v8/editor-vault/technical-1080-001/native-final-1080.mp4`.
Its full decode and configured black/silence scans passed. Both fixtures are
unbranded, unnarrated, local technical reviews. Publication remains paused;
neither fixture is full V7–V9 production acceptance or a publicly uploaded demo.
