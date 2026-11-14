[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $PSScriptRoot '../../output/collector-windows'))
$ErrorActionPreference = 'Stop'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$project = Join-Path $PSScriptRoot 'Collector/Collector.csproj'
$dotnet = (Get-Command dotnet -ErrorAction SilentlyContinue).Source
if (-not $dotnet) { $dotnet = Join-Path $env:ProgramFiles 'dotnet/dotnet.exe' }
if (-not (Test-Path -LiteralPath $dotnet)) { throw '.NET 10 SDK is required.' }
$destination = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $destination) { throw 'Use a fresh output directory; existing packages are preserved.' }
& $dotnet restore $project --locked-mode -r win-x64
if ($LASTEXITCODE -ne 0) { throw 'Locked restore failed.' }
& $dotnet publish $project -c Release -r win-x64 --self-contained true --no-restore -p:UseSharedCompilation=false --disable-build-servers -o $destination
if ($LASTEXITCODE -ne 0) { throw 'Publish failed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Install-Worker.ps1') -Destination $destination
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Remove-WorkerService.ps1') -Destination $destination
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD-PARTY-NOTICES.md') -Destination $destination
$runtimeRoot = Split-Path -Parent $dotnet
Copy-Item -LiteralPath (Join-Path $runtimeRoot 'LICENSE.txt') -Destination (Join-Path $destination 'DOTNET-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $runtimeRoot 'ThirdPartyNotices.txt') -Destination (Join-Path $destination 'DOTNET-ThirdPartyNotices.txt')
$noticeDirectory = Join-Path $destination 'licenses'
New-Item -ItemType Directory -Path $noticeDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'licenses/Apache-2.0.txt') -Destination $noticeDirectory
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Collector/packages.lock.json') -Raw | ConvertFrom-Json
$nugetRoot = Join-Path $env:USERPROFILE '.nuget/packages'
foreach ($framework in $lock.dependencies.PSObject.Properties) {
    foreach ($dependency in $framework.Value.PSObject.Properties) {
        if (-not $dependency.Value.resolved) { continue }
        $id = $dependency.Name.ToLowerInvariant()
        $cache = Join-Path $nugetRoot ($id + '/' + $dependency.Value.resolved)
        Copy-Item -LiteralPath (Join-Path $cache ($id + '.nuspec')) -Destination $noticeDirectory -Force
        Get-ChildItem -LiteralPath $cache -File -ErrorAction Stop | Where-Object Name -Match '^(LICENSE|NOTICE|COPYING)' | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $noticeDirectory ($id + '-' + $_.Name)) -Force
        }
    }
}
$records = Get-ChildItem -LiteralPath $destination -Recurse -File | ForEach-Object {
    [ordered]@{ path = $_.FullName.Substring($destination.Length + 1); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$records | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $destination 'files.sha256.json') -Encoding UTF8
Get-FileHash -LiteralPath (Join-Path $destination 'kn-collector.exe') -Algorithm SHA256
Write-Output "Unsigned Windows worker package: $destination"
