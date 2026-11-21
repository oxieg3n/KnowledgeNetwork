# Third-party components

The Knowledge Network Collector is not the author of the following components.
Exact tested versions and download digests are in `dependencies.lock.json`.

- .NET runtime, WPF and Microsoft.Extensions packages: Microsoft/contributors,
  MIT; preserve runtime LICENSE and ThirdPartyNotices in self-contained packages.
- Microsoft.Data.Sqlite: MIT; SQLite: public domain. SQLitePCLRaw: Apache-2.0.
  The worker NuGet lock records exact transitive package content hashes; the build
  copies available license/notice files into the release.
- OpenShot GUI: GPL-3.0; libopenshot: separately licensed LGPL-3.0. The installed
  distribution also includes Qt/PyQt/FFmpeg and their respective notices. It is
  not redistributed by this installer. Rebranding/source integration will need
  its own complete source/notice compliance review before distribution.
- VoiceStudio application: AGPL-3.0; models/voices have separate terms. Default
  OmniVoice weights are not cleared for this commercial channel. No VoiceStudio
  binaries, models or user profiles are redistributed.
- FFmpeg Gyan full build: GPL-3.0 build with component-specific notices. Installed
  separately for local QC; not included in the Collector package.
- Python: PSF license; tzdata: Apache-2.0 data package. Pillow: HPND; NumPy: BSD.
  The Python development environment is separate from the self-contained worker.
- Inno Setup: Jordan Russell and Martijn Laan; the Inno Setup license permits
  commercial use and redistribution with notices intact. The official compiler
  produces the unsigned installer. No signing certificate is claimed.

Skills are development aids, not shipped runtime dependencies. Ponytail, UI/UX
Pro Max and Taste each identify MIT licensing in their official sources.
