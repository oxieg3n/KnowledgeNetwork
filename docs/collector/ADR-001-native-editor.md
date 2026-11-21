# ADR 001: reuse OpenShot's native CLI and project

Status: preferred integration under local acceptance testing. November 14, 2026.

The live baseline contains a Python operational pipeline but no native editor or
Windows service. OpenShot v4.1.1 exposes native session/revision-aware edits and
snapshot exports. Use that interface before adding another bridge or timeline.
The small Collector adapter uses Python's standard library and adds no dependency.

Upstream pin: [OpenShot v4.1.1](https://github.com/OpenShot/openshot-qt/releases/tag/v4.1.1),
commit prefix `eead0c7`; compatible library release advertised upstream is
libopenshot 1.1.1. The root coordinator records the actual downloaded Windows
distribution checksum/signature, installed file digests, runtime versions and
test logs separately. Do not infer installed provenance from this source pin.

OpenShot GUI/source is GPL-3.0-or-later. libopenshot has its separate LGPL license;
neither license erases Qt/PyQt, FFmpeg, font or codec obligations. Keep upstream
notices and satisfy source/distribution requirements before redistribution. The
Collector packaging must not silently bundle an unreviewed editor distribution.
The stock editor remains separately installed during this proof.

The CLI is experimental. Native batches preflight but can partially mutate on a
runtime failure. Persist intent before edits, retain uncertain outcomes, inspect
the native revision/operation/export state, and never blindly replay. Native
`.osp` plus referenced local assets is authoritative; an `.osp` is not an archive.
Preview/final must use the same native engine and exact project snapshot.

No fallback editor selected yet. A concrete failed requirement and bounded
upstream-supported repair must be recorded before testing Shotcut/MLT against
the same fixture. A reduced FFmpeg translation cannot establish editor parity.

Update strategy: intentional official release pin changes, rehash executable,
repeat safe-boundary unit tests and the real Windows multitrack/manual-save/
reopen/export fixture before adopting a new release. No automatic editor update.
