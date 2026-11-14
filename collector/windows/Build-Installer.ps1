[CmdletBinding()]
param(
    [string]$PackageDirectory = (Join-Path $PSScriptRoot '../../output/collector-release'),
    [string]$InstallerDirectory = (Join-Path $PSScriptRoot '../../output/installer'),
    [string]$Compiler = "${env:ProgramFiles(x86)}/Inno Setup 6/ISCC.exe"
)
$ErrorActionPreference = 'Stop'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$dotnet = Join-Path $env:ProgramFiles 'dotnet/dotnet.exe'
$package = [IO.Path]::GetFullPath($PackageDirectory)
& (Join-Path $PSScriptRoot 'Build-Release.ps1') -OutputDirectory $package
$dashboard = Join-Path $PSScriptRoot 'Dashboard/Dashboard.csproj'
& $dotnet publish $dashboard -c Release -r win-x64 --self-contained true -p:UseSharedCompilation=false --disable-build-servers -o $package
if ($LASTEXITCODE -ne 0) { throw 'Dashboard publish failed.' }
# Regenerate after adding the dashboard; the installer verifies every packaged runtime file.
$records = Get-ChildItem -LiteralPath $package -Recurse -File | Where-Object Name -ne 'files.sha256.json' | ForEach-Object {
    [ordered]@{ path = $_.FullName.Substring($package.Length + 1); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$records | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $package 'files.sha256.json') -Encoding UTF8
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Pinned Inno Setup 6.7.3 compiler required.' }
& $Compiler "/DPackageDir=$package" "/DOutputDir=$([IO.Path]::GetFullPath($InstallerDirectory))" (Join-Path $PSScriptRoot 'Collector.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Get-FileHash -LiteralPath (Join-Path $InstallerDirectory 'The-Knowledge-Network-Collector-0.1.0-setup.exe') -Algorithm SHA256
