# Windows worker dependencies

The Knowledge Network Collector worker uses the .NET 10 runtime and
Microsoft.Extensions.Hosting.WindowsServices 10.0.15 (MIT), and
Microsoft.Data.Sqlite 10.0.15 (MIT). SQLite is public domain. The transitive
SQLitePCLRaw packages use Apache-2.0; retain their notices and license text when
redistributing the self-contained runtime/native SQLite libraries.

The exact transitive graph and NuGet content hashes are in
`Collector/packages.lock.json`. Reproducible builds must use locked restore.
The .NET runtime's `LICENSE.txt` and `ThirdPartyNotices.txt` must accompany a
distributed self-contained package. Packaging/install smoke tests and the full
third-party notice bundle must be checked before external release.

Official sources:

- https://github.com/dotnet/runtime
- https://github.com/dotnet/extensions
- https://github.com/dotnet/efcore
- https://github.com/ericsink/SQLitePCL.raw
- https://www.sqlite.org/copyright.html
