[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$service = Get-Service -Name 'KnowledgeNetworkCollector' -ErrorAction SilentlyContinue
if ($service) {
    $definition = Get-CimInstance -ClassName Win32_Service -Filter "Name='KnowledgeNetworkCollector'"
    $expectedPrefix = '"' + (Join-Path $env:ProgramFiles 'The Knowledge Network Collector/kn-collector.exe') + '" serve '
    if (-not $definition -or -not $definition.PathName.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Service does not point to the expected Collector installation; refusing removal.'
    }
    Stop-Service -Name 'KnowledgeNetworkCollector'
    (Get-Service 'KnowledgeNetworkCollector').WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20))
    & sc.exe delete 'KnowledgeNetworkCollector'
    if ($LASTEXITCODE -ne 0) { throw 'Service removal failed.' }
}
Write-Output 'Service removed. Installed binaries and private durable data were retained for recovery. No media or database was deleted.'
