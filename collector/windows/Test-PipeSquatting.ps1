[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CollectorExecutable,
    [Parameter(Mandatory=$true)][string]$EvidencePath
)
$ErrorActionPreference = 'Stop'
$binary = [IO.Path]::GetFullPath($CollectorExecutable)
if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'Collector executable does not exist.' }
$service = Get-Service -Name 'KnowledgeNetworkCollector' -ErrorAction SilentlyContinue
if ($service -and $service.Status -ne 'Stopped') { throw 'Coordinator must stop the genuine Collector service before this serialized negative test.' }
if (Test-Path -LiteralPath $EvidencePath) { throw 'Evidence already exists; use a fresh path.' }
$security = New-Object IO.Pipes.PipeSecurity
$security.SetAccessRuleProtection($true,$false)
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$security.AddAccessRule((New-Object IO.Pipes.PipeAccessRule($identity.User, 'FullControl', 'Allow')))
$pipe = New-Object IO.Pipes.NamedPipeServerStream('KnowledgeNetworkCollector-v1', 'InOut', 1, 'Byte', 'Asynchronous', 4096, 4096, $security)
$probe = New-Object Diagnostics.Process
$start = New-Object Diagnostics.ProcessStartInfo
$start.FileName = $binary
$start.Arguments = 'health synthetic-pipe-squatting-test'
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$probe.StartInfo = $start
$started = $false
try {
    $accept = $pipe.WaitForConnectionAsync()
    if (-not $probe.Start()) { throw 'Collector CLI did not start.' }
    $started = $true
    $output = $probe.StandardOutput.ReadToEndAsync()
    $errorOutput = $probe.StandardError.ReadToEndAsync()
    if (-not $accept.Wait(10000)) { throw 'Negative-test client did not connect.' }
    [byte[]]$buffer = New-Object byte[] 1
    $read = $pipe.ReadAsync($buffer, 0, 1)
    if (-not $read.Wait(5000)) { throw 'Negative-test client did not close the fake pipe.' }
    if (-not $probe.WaitForExit(5000)) { throw 'Negative-test CLI did not exit.' }
    $response = $output.GetAwaiter().GetResult() | ConvertFrom-Json
    $passed = $read.Result -eq 0 -and $probe.ExitCode -eq 1 -and $response.ok -eq $false -and $response.error -eq 'untrusted_pipe_server'
    $record = [ordered]@{ status = $(if ($passed) {'PASS'} else {'FAILED'}); test = 'pipe_squatting_no_payload'; received_bytes = $read.Result; client_exit_code = $probe.ExitCode; client_error = $response.error; checked_at = [DateTime]::UtcNow.ToString('o') }
    $record | ConvertTo-Json | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
    $record | ConvertTo-Json -Compress
    if (-not $passed) { throw 'Fake pipe server test failed; inspect private evidence.' }
} finally {
    $pipe.Dispose()
    if ($started -and -not $probe.HasExited) { $probe.Kill(); $probe.WaitForExit() }
    $probe.Dispose()
    $identity.Dispose()
}
