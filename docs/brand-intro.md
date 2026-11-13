# Powered By plasma intro template

The owner selected the latest circular-badge/plasma-and-crackle preview on
November 13, 2026 as the template for future videos. Template ID:
`poweredby-plasma-v1`. This is a reusable rendering component, not upload
permission or an assertion that an audio reviewer listened.

## Future production default

For each new production spec, include:

```json
"brand_intro": {
  "template": "poweredby-plasma-v1",
  "title": "The specific video title"
}
```

Supply `--local-assets /private/asset-paths.json` with a `poweredby_logo` entry
pointing to the locally materialized **Neon Cosmic Oxieg3n Emblem.png**.
The component pins its SHA-256 to
`5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54`;
it refuses a substitute badge. Keep logo bytes, private paths and finished media
outside this public repository. Existing unbranded renders remain supported for
recovery and technical tests; do not silently change old requests or receipts.
The producer must include this template in future owner-channel video specs.

The title is dynamic plain text, maximum 100 characters and two fitted lines.
Shorten the display title when necessary rather than clipping text. Both
1080×1920 and 1920×1080 at 30 fps are supported. The landscape composition uses
its own badge size/center and title position, not a distorted portrait image.

## Motion and sound

The 48-frame, 1.6-second bumper retains irregular root clusters and gaps around
the full circle, curved cubic paths, different filament strengths and widths,
drifting endpoints, and splayed boundary contact branches. Colors blend with the
cyan, blue and violet badge. It is a stylized procedural illustration, not a
physical simulation. No reference-video footage or audio is copied.

The title sits on a quiet black backing. The logo accelerates toward the viewer;
the last 0.18 seconds dissolve into the actual first content frame. No placeholder
or demo title is included. The content then starts with its original audio.
The synthesized stereo 48 kHz crackles share the filament seed and activity
function; brightness maxima trigger short panned crackle clusters, and a rising
discharge follows the zoom. No third-party sound samples are used. Font use is
DejaVu Sans under the existing Bitstream Vera/DejaVu notice.

The original preview uses the owner's selected brand artwork. This is permission
for this channel's branding, not permission to redistribute the artwork as a
generic asset or to imply endorsement by any featured speaker or source.

## Integration and exact-render review

The renderer prepends the bumper before final digest/QC creation. Narration and
licensed-excerpt caption offsets include the measured muxed bumper duration.
The manifest records the template, display title, exact badge/bumper hashes and
content offset. The final media hash changes, invalidating prior attestations.
Apply this same measured offset to any subsequently authored chapter times
(except YouTube's required first chapter at 00:00). Recheck source attribution,
captions and credit visibility in the final combined video.

Only the bounded intro interval is exempted from black-background detection.
The remainder is scanned normally, including a failure to transition into
content. Full-video silence/loudness and final Short-duration checks stay on;
do not truncate content to force a duration pass. The configured Short limit is
still 30–60 seconds, including branding.

Inspect the exact final video at desktop and phone scale, in both applicable
orientations: title fit, badge and tendril appearance, transition, narration start,
captions, licensed credits, duration, sound balance and abrupt transients. Listen
to the final combined audio and observe playback synchronization. FFmpeg
statistics and phase-coupled synthesis do not prove listening quality. All six
editorial checks and exact-render release gates remain required. No upload,
republish, OAuth change, public artifact or recurring renderer activation is
performed by this template.

### Technical validation, November 13, 2026

The final implementation passed 98 unit tests. Both aspect-ratio bumpers were
rendered, representative actual pixels inspected, and concatenation with a
three-second synthetic audiovisual test segment decoded end to end. The first
stream-copy experiment exposed an average-frame-rate mismatch; branded assembly
now uses explicit CFR finishing rather than bypassing the check. The corrected
combined tests both measure 4.608 seconds, H.264/yuv420p, 30 fps average and AAC
stereo, with no configured post-intro black span or full-video long silence.

Exact corrected technical-test hashes:
- Portrait: `e9f3a702b2055d237220036597d0ca626310008f9dab69b69ee60da395689d40`
- Landscape: `0ee29b46e732210d063065f8e8a7cc5ced2a7f47878876b4aa2fa3d2fa858a8a`

These short technical clips are not publishable Shorts. The complete
Piper-narrated production path has not been rerendered for this change; the
local test interpreter did not have Piper installed. Actual listening and
final episode playback review remain pending. Do not transfer these technical
results into an editorial or audio approval.

### Licensed-source metadata transition regression

A three-scene synthetic fixture exposed a decoder/filter reinitialization hazard
when the middle licensed-style segment changes color metadata: nominal 3.002-second
audio survived while video shortened to 2.100 seconds, despite reporting 30 fps.
Assembly now disables filter reinitialization across the uniformly sized generated
segments. The regression verifies at least 89 frames and matching approximately
three-second audio/video durations. This is a timeline test, not a listening or
licensed-content approval; actual episode transitions remain subject to review.
