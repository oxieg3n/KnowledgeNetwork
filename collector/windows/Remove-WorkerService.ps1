[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$service = Get-Service -Name 'KnowledgeNetworkCollector' -ErrorAction SilentlyContinue
if ($service) {
    Stop-Service -Name 'KnowledgeNetworkCollector'
    (Get-Service 'KnowledgeNetworkCollector').WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20))
    & sc.exe delete 'KnowledgeNetworkCollector'
    if ($LASTEXITCODE -ne 0) { throw 'Service removal failed.' }
}
Write-Output 'Service removed. Installed binaries and private durable data were retained for recovery. No media or database was deleted.'
