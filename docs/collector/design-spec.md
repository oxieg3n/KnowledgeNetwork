# Collector operations dashboard design

Scope: a native WPF operations window for The Knowledge Network Collector.
OpenShot is a separate Qt editor. This dashboard does not claim an integrated
timeline, playback or voice/editor acceptance. It operates the real worker CLI.

The existing owner direction governs tokens: charcoal background #171B20,
surface #222830, border #687785, foreground #F0F3F6, secondary #BCC7D1,
muted cyan focus/accent #80C6DC and caution #F2C879. Segoe UI is the installed
native interface font; Consolas is used only for secondary raw JSON. Spacing
uses 8/16/24 DIP; base text 15 DIP, section heading20 and title24. No external
fonts, images, decorative cards, metrics, animation or network requests.

Layout is one real operational task surface: product heading and explicit local
review scope; current request/result feedback; worker queries; a harmless durable
echo test; job ID field/get/cancel; read-only selectable raw JSON. Actions wrap
at narrower widths. Minimum800x600, initial1040x780; flexible result pane and
native scrollbars. Native WPF scaling remains enabled. All actions have visible
text, access keys, tab order and UI Automation names. Focus uses a visible cyan
outline; status text also exposes UIA live updates. Color never carries status
alone. Controls disable during a request; field validation is explicit.

No success appears until a real CLI result. Health sends a fresh nonce and
checks the returned nonce. Echo submits a unique diagnostic.echo request and
polls its returned job ID for a terminal state, checking the exact nonce. A
timeout means status must be reconciled with Get job; it does not cancel or
resubmit work. Cancel requests actual cancellation and displays the returned
state without assuming the job stopped. No publication action exists.

CLI calls use the explicitly adjacent kn-collector.exe, fixed verbs,
ProcessStartInfo.ArgumentList, no shell, asynchronous bounded stdout and stderr,
15-second child timeout and no automatic retries. Job IDs must be32 hexadecimal
characters. Child failures show safe error codes and a recovery instruction;
raw JSON stays secondary. Closing the dashboard closes only its own CLI child,
not the worker or an accepted durable job.

## Skills and verification

Read UI/UX Pro Max at C:/admin/tools/ui-ux-pro-max/.claude/skills/ui-ux-pro-max/
SKILL.md; queried desktop media production workspace --design-system. Its
first result was a marketing showcase, so rejected. One narrower retry,
professional desktop operations dashboard, matched Minimalism & Swiss Style;
used functional hierarchy and restraint, with owner charcoal tokens replacing
its light palette. Queried keyboard focus error feedback --stack wpf,
focus visible keyboard --domain ux, and error recovery status semantics --domain
ux. Read quick-reference sections1-3 and pro-rules scope/checklist.

Read installed Taste2.5.1 SKILL.md at the cached taste-skill path. Applied
native-relevant visual judgment: real operational evidence, aligned edges,
consistent geometry/type, restrained native controls, no fake dashboard content.
Web hero/dealer/browser gates do not apply to this WPF window. Native screenshots,
keyboard interactions, resize/DPI and live service flows must be verified by root
after integration. Compilation alone is not UI acceptance.
