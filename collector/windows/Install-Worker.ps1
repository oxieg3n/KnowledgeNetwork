[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$OwnerSid,
    [string]$PackageDirectory = $PSScriptRoot,
    [string]$ResearchSnapshot,
    [string]$ResearchSha256
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run installation elevated.' }
$owner = New-Object Security.Principal.SecurityIdentifier($OwnerSid)
if (-not $owner.AccountDomainSid) { throw 'OwnerSid must identify the intended local/domain user, not a broad built-in group.' }
$package = [IO.Path]::GetFullPath($PackageDirectory)
$destination = Join-Path $env:ProgramFiles 'The Knowledge Network Collector'
$dataDirectory = Join-Path $env:ProgramData 'KnowledgeNetworkCollector'
$serviceName = 'KnowledgeNetworkCollector'
foreach ($path in @($package, $destination, $dataDirectory)) {
    if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse-point package/install/data directory denied.' }
}
$manifest = Get-Content -LiteralPath (Join-Path $package 'files.sha256.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest) {
    $source = [IO.Path]::GetFullPath((Join-Path $package $entry.path))
    if (-not $source.StartsWith($package.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Package path escapes its root.' }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Package integrity mismatch.' }
}
if ($ResearchSnapshot -or $ResearchSha256) {
    if (-not $ResearchSnapshot -or $ResearchSha256 -notmatch '^[a-f0-9]{64}$') { throw 'Supply both an immutable snapshot and its lowercase SHA-256.' }
    $ResearchSnapshot = [IO.Path]::GetFullPath($ResearchSnapshot)
    if ((Get-FileHash -LiteralPath $ResearchSnapshot -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ResearchSha256) { throw 'Snapshot integrity mismatch.' }
}
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    $definition = Get-CimInstance -ClassName Win32_Service -Filter "Name='KnowledgeNetworkCollector'"
    $expectedPrefix = '"' + (Join-Path $destination 'kn-collector.exe') + '" serve '
    if (-not $definition -or -not $definition.PathName.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Existing service does not point to the expected Collector installation; refusing takeover.'
    }
    Stop-Service -Name $serviceName
    (Get-Service $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20))
}
New-Item -ItemType Directory -Path $destination,$dataDirectory -Force | Out-Null
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
foreach ($sid in @('S-1-5-19','S-1-5-18','S-1-5-32-544')) {
    $rule = New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($sid)), 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $dataDirectory -AclObject $acl
foreach ($entry in $manifest) {
    $source = Join-Path $package $entry.path
    $target = [IO.Path]::GetFullPath((Join-Path $destination $entry.path))
    if (-not $target.StartsWith($destination.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Install path escapes its root.' }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
    if (-not [string]::Equals([IO.Path]::GetFullPath($source), $target, [StringComparison]::OrdinalIgnoreCase)) {
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
}
if (-not [string]::Equals($package.TrimEnd('\'), $destination.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
    Copy-Item -LiteralPath (Join-Path $package 'files.sha256.json') -Destination $destination -Force
}
$binary = Join-Path $destination 'kn-collector.exe'
$command = '"' + $binary + '" serve --data "' + $dataDirectory + '" --client-sid ' + $owner.Value
if ($ResearchSnapshot) {
    # Copy only the explicitly selected immutable staging file; no production store is opened for writing.
    $staged = Join-Path $dataDirectory 'research-staging.json'
    Copy-Item -LiteralPath $ResearchSnapshot -Destination $staged -Force
    $command += ' --research-snapshot "' + $staged + '" --research-sha256 ' + $ResearchSha256
}
if ($existing) {
    & sc.exe config $serviceName binPath= $command obj= 'NT AUTHORITY\LocalService' start= auto
    if ($LASTEXITCODE -ne 0) { throw 'Service configuration failed.' }
} else {
    New-Service -Name $serviceName -DisplayName 'The Knowledge Network Collector' -BinaryPathName $command -StartupType Automatic -Description 'Local-only bounded review worker; publication remains paused.' -Credential (New-Object Management.Automation.PSCredential('NT AUTHORITY\LocalService',(New-Object Security.SecureString))) | Out-Null
}
& sc.exe failure $serviceName reset= 86400 actions= restart/5000/restart/15000/none/0
if ($LASTEXITCODE -ne 0) { throw 'Recovery configuration failed.' }
Start-Service -Name $serviceName
(Get-Service $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
Write-Output "Installed The Knowledge Network Collector. CLI: $binary"
Write-Output "Private durable data preserved at: $dataDirectory"
Write-Output 'Run the CLI as the configured owner: kn-collector.exe health fresh-nonce'
