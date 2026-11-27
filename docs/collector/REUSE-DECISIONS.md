# Reuse decisions

The Knowledge Network Collector keeps the existing `youtube_ops` policies,
production receipts, four queues and publication pause. No production cutover
or second production scheduler is enabled.

The Windows worker uses .NET 10 LTS, SQLite and an ACL-protected Windows named
pipe. The small WPF operations client calls the same CLI. OpenShot remains the
Qt editing application; WPF is not a timeline engine. See
[the editor decision](ADR-001-native-editor.md) and [design spec](design-spec.md).

OpenShot 4.1.1 supplies native projects, revisioned editing and exports. The
adapter does not translate native projects into a reduced FFmpeg composition.
Its session-zero/user-desktop bridge is unfinished and is explicitly disabled
in worker capabilities. A standalone adapter is developer tooling, not proof
of an integrated Collector editor.

The existing VoiceStudio 0.5.8 installation is preserved. Its local API adapter
requires exact reviewed voice/model evidence. No silent narrator replacement,
model download, license acceptance or profile reset is implemented.

Self-contained worker/dashboard packages include .NET and SQLite notices.
OpenShot, VoiceStudio and FFmpeg remain separately installed dependencies;
their binaries/models are not bundled or published in this repository.
