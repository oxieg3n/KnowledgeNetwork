[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$HostAddress,
    [Parameter(Mandatory=$true)][string]$ForgeAddress,
    [Parameter(Mandatory=$true)][string]$PublicKeyFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PublicKeySha256,
    [Parameter(Mandatory=$true)][string]$DispatcherFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$DispatcherSha256,
    [Parameter(Mandatory=$true)][string]$RuntimeArchiveFile,
    [Parameter(Mandatory=$true)][string]$BootstrapFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BootstrapSha256
)
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$account = 'kncollector_exec'
$service = 'KnowledgeNetworkHostExec'
$firewall = 'KnowledgeNetworkHostExec-Forge'
$blockFirewall = 'KnowledgeNetworkHostExec-OtherSources'
$port = 22230
$sshd = 'C:/Windows/System32/OpenSSH/sshd.exe'
$firewallProgram = [IO.Path]::GetFullPath($sshd)
$python = "$root/runtime/python/python.exe"
$powershell = 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
$commandShell = 'C:/Windows/System32/cmd.exe'
$sharedConfig = 'C:/ProgramData/ssh/sshd_config'
$hostKey = 'C:/ProgramData/ssh/ssh_host_ed25519_key'
$runtimeSha256 = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
$encoding = [Text.UTF8Encoding]::new($false,$true)
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Prepared networking completion requires an elevated host administrator.' }
foreach ($address in @($HostAddress,$ForgeAddress)) {
    $ip = $null
    if (-not [Net.IPAddress]::TryParse($address,[ref]$ip) -or $ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $ip.ToString() -cne $address) { throw 'Canonical tailnet IPv4 literals required.' }
    $bytes = $ip.GetAddressBytes()
    if ($bytes[0] -ne 100 -or $bytes[1] -lt 64 -or $bytes[1] -gt 127) { throw 'Only tailnet IPv4 addresses are accepted.' }
}
if ($HostAddress -eq $ForgeAddress) { throw 'Host and FORGE must differ.' }
if (-not @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $HostAddress -ErrorAction Stop).Count) { throw 'Host tailnet address is not local.' }
function Read-PinnedBytes([string]$Path,[string]$Hash,[long]$Limit) {
    $stream = [IO.File]::Open([IO.Path]::GetFullPath($Path),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if ($stream.Length -le 0 -or $stream.Length -gt $Limit) { throw 'Prepared source exceeds bounds.' }
        $memory = [IO.MemoryStream]::new()
        try { $stream.CopyTo($memory); $data = $memory.ToArray() } finally { $memory.Dispose() }
    } finally { $stream.Dispose() }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $actual = ([BitConverter]::ToString($hasher.ComputeHash($data))).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
    if ($actual -cne $Hash) { throw 'Prepared source SHA-256 mismatch.' }
    return ,$data
}
$bootstrapText = $encoding.GetString((Read-PinnedBytes $BootstrapFile $BootstrapSha256 128KB))
$tokens = $null; $parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseInput($bootstrapText,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'Pinned bootstrap source syntax failed.' }
foreach ($name in @('Assert-TrustedPath','Expand-DispatcherRuntime','Assert-RuntimeManifest','Ipv4-Text')) {
    $definitions = @($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
    if ($definitions.Count -ne 1) { throw 'Pinned bootstrap helper contract differs.' }
    . ([ScriptBlock]::Create($definitions[0].Extent.Text))
}
function Assert-PreparedNetworkingReceipt([object]$Receipt,[object]$Config,[string]$HostAddress,[string]$ForgeAddress,[string]$DispatcherSha256,[string]$SharedConfigSha256,[string]$ExecutionSid,[string]$PythonSha256,[string]$PowerShellSha256,[string[]]$BlockSources) {
    $keys = @('schema_version','status','service','execution_sid','account','port','host_address','forge_address','dispatcher_sha256','runtime_version','runtime_archive_sha256','shared_config_sha256','created_at','gateway_service_restarted','publication_paused','block_sources')
    if ($null -eq $Receipt -or @($Receipt.PSObject.Properties).Count -ne $keys.Count -or @($Receipt.PSObject.Properties | Where-Object Name -cnotin $keys).Count) { throw 'Prepared networking receipt schema differs.' }
    foreach ($name in @('status','service','execution_sid','account','host_address','forge_address','dispatcher_sha256','runtime_version','runtime_archive_sha256','shared_config_sha256','created_at')) { if ($Receipt.$name -isnot [string]) { throw 'Prepared networking receipt scalar type differs.' } }
    if ($Receipt.schema_version -isnot [int] -or $Receipt.port -isnot [int] -or $Receipt.gateway_service_restarted -isnot [bool] -or $Receipt.publication_paused -isnot [bool]) { throw 'Prepared networking receipt field types differ.' }
    if ($Receipt.block_sources -isnot [array] -or $Receipt.block_sources.Count -ne 2 -or $Receipt.block_sources[0] -isnot [string] -or $Receipt.block_sources[1] -isnot [string]) { throw 'Prepared networking source ranges differ.' }
    if ($ExecutionSid -notmatch '^S-1-5-21-[0-9-]+$' -or $Receipt.execution_sid -isnot [string] -or $Receipt.execution_sid -cne $ExecutionSid -or $Receipt.status -cne 'BOOTSTRAP_IN_PROGRESS' -or $Receipt.schema_version -ne 1 -or $Receipt.service -cne 'KnowledgeNetworkHostExec' -or $Receipt.account -cne 'kncollector_exec' -or $Receipt.port -ne 22230 -or $Receipt.host_address -cne $HostAddress -or $Receipt.forge_address -cne $ForgeAddress -or $Receipt.dispatcher_sha256 -cne $DispatcherSha256 -or $Receipt.shared_config_sha256 -cne $SharedConfigSha256 -or $Receipt.runtime_version -cne '3.14.10' -or $Receipt.runtime_archive_sha256 -cne '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159' -or $Receipt.gateway_service_restarted -ne $false -or $Receipt.publication_paused -ne $true -or @($Receipt.block_sources).Count -ne 2 -or $BlockSources.Count -ne 2 -or $Receipt.block_sources[0] -cne $BlockSources[0] -or $Receipt.block_sources[1] -cne $BlockSources[1]) { throw 'Receipt is not the exact reconciled pre-network state.' }
    $configKeys = @('schema_version','execution_sid','forge_address','python_sha256','powershell_sha256')
    if ($null -eq $Config -or @($Config.PSObject.Properties).Count -ne $configKeys.Count -or @($Config.PSObject.Properties | Where-Object Name -cnotin $configKeys).Count -or $Config.schema_version -isnot [int] -or $Config.schema_version -ne 1 -or $Config.execution_sid -cne $ExecutionSid -or $Config.forge_address -cne $ForgeAddress -or $Config.python_sha256 -cne $PythonSha256 -or $Config.powershell_sha256 -cne $PowerShellSha256) { throw 'Prepared dispatcher configuration differs.' }
    foreach ($name in @('execution_sid','forge_address','python_sha256','powershell_sha256')) { if ($Config.$name -isnot [string]) { throw 'Prepared dispatcher configuration scalar type differs.' } }
    $date = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse($Receipt.created_at,[ref]$date)) { throw 'Prepared networking creation time is invalid.' }
    $result = [ordered]@{}
    foreach ($property in $Receipt.PSObject.Properties) { $result[$property.Name] = $property.Value }
    return $result
}
Assert-TrustedPath $root
$expectedRoot = @('bootstrap-receipt.private.json','rollback-bootstrap.ps1','runtime','runtime-files.private.json','shared-sshd-config.before.private','audit','receipts','config.json','authorized_keys','sshd_config','effective-sshd.private.txt')
$items = @(Get-ChildItem -LiteralPath $root -Force -ErrorAction Stop)
if ($items.Count -ne $expectedRoot.Count) { throw 'Prepared networking root contains unexpected state.' }
foreach ($item in $items) {
    if ($item.Name -cnotin $expectedRoot -or $item.PSIsContainer -ne ($item.Name -cin @('runtime','audit','receipts'))) { throw 'Prepared networking root shape differs.' }
    if ($item.Name -cne 'audit') { Assert-TrustedPath $item.FullName }
}
foreach ($name in @('audit','receipts')) { if (@(Get-ChildItem -LiteralPath (Join-Path $root $name) -Force -ErrorAction Stop).Count) { throw 'Prepared networking stage already has job/audit state; reconcile instead.' } }
$runtimeChildren = @(Get-ChildItem -LiteralPath (Join-Path $root 'runtime') -Force -ErrorAction Stop)
if ($runtimeChildren.Count -ne 2 -or -not @($runtimeChildren | Where-Object { $_.Name -ceq 'python' -and $_.PSIsContainer }).Count -or -not @($runtimeChildren | Where-Object { $_.Name -ceq 'collector_host_exec.py' -and -not $_.PSIsContainer }).Count) { throw 'Prepared runtime shape differs.' }
foreach ($item in Get-ChildItem -LiteralPath (Join-Path $root 'runtime') -Recurse -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
$users = @(Get-LocalUser -ErrorAction Stop | Where-Object Name -eq $account)
if ($users.Count -ne 1 -or -not $users[0].Enabled) { throw 'Expected existing enabled dedicated identity.' }
$sid = $users[0].SID.Value
if (@(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop | Where-Object { $_.SID.Value -eq $sid }).Count -or -not @(Get-LocalGroupMember -SID 'S-1-5-32-545' -ErrorAction Stop | Where-Object { $_.SID.Value -eq $sid }).Count) { throw 'Dedicated account group membership differs.' }
$audit = Get-Item -LiteralPath (Join-Path $root 'audit') -Force
$auditAcl = Get-Acl -LiteralPath $audit.FullName
if (($audit.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or -not $auditAcl.AreAccessRulesProtected -or $auditAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544',$current.User.Value)) { throw 'Dedicated audit path trust differs.' }
foreach ($ace in $auditAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) { if ($ace.AccessControlType -eq 'Allow' -and ($ace.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544',$sid) -or ($ace.IdentityReference.Value -eq $sid -and ($ace.FileSystemRights -band 0xC0000) -ne 0))) { throw 'Dedicated audit access differs.' } }
$auditRules = @($auditAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if ($auditRules.Count -ne 3) { throw 'Dedicated audit DACL shape differs.' }
foreach ($expectedSid in @('S-1-5-18','S-1-5-32-544',$sid)) {
    $matches = @($auditRules | Where-Object { $_.IdentityReference.Value -eq $expectedSid })
    $rights = if ($expectedSid -eq $sid) { [int]([Security.AccessControl.FileSystemRights]::Modify -bor [Security.AccessControl.FileSystemRights]::Synchronize) } else { [int][Security.AccessControl.FileSystemRights]::FullControl }
    if ($matches.Count -ne 1 -or $matches[0].AccessControlType -ne 'Allow' -or $matches[0].IsInherited -or [int]$matches[0].InheritanceFlags -ne 3 -or [int]$matches[0].PropagationFlags -ne 0 -or [int]$matches[0].FileSystemRights -ne $rights) { throw 'Dedicated audit identity/rights differ.' }
}
if (@(Get-Service -ErrorAction Stop | Where-Object Name -eq $service).Count) { throw 'Project service already exists; no completion retry.' }
foreach ($store in @('PersistentStore','ActiveStore')) { if (@(Get-NetFirewallRule -PolicyStore $store -ErrorAction Stop | Where-Object { $_.Name -in @($firewall,$blockFirewall) }).Count) { throw 'Project firewall state already exists; no completion retry.' } }
if (@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq $port).Count) { throw 'Project port is occupied.' }
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction Stop)
if ($profiles.Count -ne 3) { throw 'Effective firewall profiles unavailable.' }
foreach ($profile in $profiles) { if ($profile.Enabled.ToString() -ne 'True' -or $profile.AllowLocalFirewallRules.ToString() -notin @('True','NotConfigured') -or $profile.AllowInboundRules.ToString() -notin @('True','NotConfigured')) { throw 'Effective firewall enforcement/merge unavailable; no policy changed.' } }
foreach ($name in @('MpsSvc','BFE')) { if ((Get-Service -Name $name -ErrorAction Stop).Status -ne 'Running') { throw 'Firewall service unavailable; no service changed.' } }
foreach ($file in @($sshd,$powershell,$commandShell,$hostKey)) { Assert-TrustedPath $file }
$shellSettings = if (Test-Path -LiteralPath HKLM:/SOFTWARE/OpenSSH) { Get-ItemProperty -LiteralPath HKLM:/SOFTWARE/OpenSSH -ErrorAction Stop } else { $null }
if (($shellSettings.DefaultShell -and [IO.Path]::GetFullPath($shellSettings.DefaultShell) -ne [IO.Path]::GetFullPath($commandShell)) -or ($shellSettings.DefaultShellCommandOption -and $shellSettings.DefaultShellCommandOption -cne '/c') -or (Get-ItemProperty -LiteralPath 'HKLM:/SOFTWARE/Microsoft/Command Processor' -ErrorAction Stop).AutoRun) { throw 'Existing SSH outer shell boundary differs; no registry changed.' }
$archiveBytes = Read-PinnedBytes $RuntimeArchiveFile $runtimeSha256 32MB
$runtimeRecords = @(Expand-DispatcherRuntime $archiveBytes (Join-Path $root 'runtime/python') -VerifyExisting)
foreach ($name in @('bootstrap-receipt.private.json','runtime-files.private.json','config.json','effective-sshd.private.txt','authorized_keys','sshd_config')) { if ((Get-Item -LiteralPath (Join-Path $root $name)).Length -gt 64KB) { throw 'Prepared state file exceeds bounds.' } }
$recorded = Get-Content -LiteralPath (Join-Path $root 'runtime-files.private.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-RuntimeManifest $recorded $runtimeRecords
$sharedHash = (Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant()
if ((Get-FileHash -LiteralPath (Join-Path $root 'shared-sshd-config.before.private') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $sharedHash -or (Get-FileHash -LiteralPath (Join-Path $root 'rollback-bootstrap.ps1') -Algorithm SHA256).Hash.ToLowerInvariant() -cne '3ea650c9f46f9e77d4cf3dca88393e91c22098936170080e3b1173acc59869ed') { throw 'Original Gateway/rollback evidence differs.' }
if ((Get-FileHash -LiteralPath $DispatcherFile -Algorithm SHA256).Hash.ToLowerInvariant() -cne $DispatcherSha256 -or (Get-FileHash -LiteralPath (Join-Path $root 'runtime/collector_host_exec.py') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $DispatcherSha256) { throw 'Prepared dispatcher pin mismatch.' }
$forgeBytes = ([Net.IPAddress]::Parse($ForgeAddress)).GetAddressBytes()
$forgeNumber = [uint64]$forgeBytes[0]*16777216 + [uint64]$forgeBytes[1]*65536 + [uint64]$forgeBytes[2]*256 + [uint64]$forgeBytes[3]
$otherSources = @(('0.0.0.0-'+(Ipv4-Text ($forgeNumber-1)));((Ipv4-Text ($forgeNumber+1))+'-255.255.255.255'))
$receipt = Assert-PreparedNetworkingReceipt (Get-Content -LiteralPath (Join-Path $root 'bootstrap-receipt.private.json') -Raw -Encoding UTF8 | ConvertFrom-Json) (Get-Content -LiteralPath (Join-Path $root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json) $HostAddress $ForgeAddress $DispatcherSha256 $sharedHash $sid ((Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()) ((Get-FileHash -LiteralPath $powershell -Algorithm SHA256).Hash.ToLowerInvariant()) $otherSources
$key = $encoding.GetString((Read-PinnedBytes $PublicKeyFile $PublicKeySha256 4096)).Trim()
if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/]+={0,3}(?: [^\r\n]*)?$') { throw 'Dedicated public key format differs.' }
$key = ($key -split ' ',3)[0..1] -join ' '
$expectedKey = 'from="'+$ForgeAddress+'",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding '+$key+"`n"
if ([IO.File]::ReadAllText((Join-Path $root 'authorized_keys')) -cne $expectedKey) { throw 'Prepared authorized key/source restriction differs.' }
$force = "$python -I -S -B $root/runtime/collector_host_exec.py"
$assignments = @($ast.FindAll({param($node) $node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -ceq '$sshdConfig'},$true))
if ($assignments.Count -ne 1) { throw 'Pinned SSH configuration contract differs.' }
. ([ScriptBlock]::Create('$expectedConfig = '+$assignments[0].Right.Extent.Text))
$configPath = Join-Path $root 'sshd_config'
if ([IO.File]::ReadAllText($configPath).Replace("`r`n","`n") -cne $expectedConfig.Replace("`r`n","`n")) { throw 'Prepared SSH configuration differs from current reviewed restrictions.' }
& $sshd -t -f $configPath
if ($LASTEXITCODE -ne 0) { throw 'Prepared SSH configuration fails native validation.' }
$effective = & $sshd -T -f $configPath -C "user=$account,host=forge,addr=$ForgeAddress,laddr=$HostAddress,lport=$port"
if ($LASTEXITCODE -ne 0 -or ($effective -join "`n") -cne [IO.File]::ReadAllText((Join-Path $root 'effective-sshd.private.txt')).Replace("`r`n","`n")) { throw 'Prepared effective SSH restrictions differ.' }
foreach ($file in @($python,(Join-Path $root 'runtime/python/python314.dll'))) { $signature = Get-AuthenticodeSignature -LiteralPath $file -ErrorAction Stop; if ($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Python Software Foundation(,|$)') { throw 'Prepared interpreter publisher signature differs.' } }
# Only the pinned reviewed networking tail runs; no account/runtime/config creation.
$marker = '# Explicit block precedence also closes any pre-existing broad program allow.'
$offset = $bootstrapText.IndexOf($marker,[StringComparison]::Ordinal)
if ($offset -lt 0 -or $bootstrapText.IndexOf($marker,$offset+1,[StringComparison]::Ordinal) -ge 0) { throw 'Pinned networking tail boundary differs.' }
. ([ScriptBlock]::Create($bootstrapText.Substring($offset)))
