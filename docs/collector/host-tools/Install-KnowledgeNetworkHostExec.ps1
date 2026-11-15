[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$HostAddress,
    [Parameter(Mandatory=$true)][string]$ForgeAddress,
    [Parameter(Mandatory=$true)][string]$PublicKeyFile,
    [Parameter(Mandatory=$true)][string]$DispatcherFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$DispatcherSha256
)
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$account = 'kncollector_exec'
$service = 'KnowledgeNetworkHostExec'
$firewall = 'KnowledgeNetworkHostExec-Forge'
$blockFirewall = 'KnowledgeNetworkHostExec-OtherSources'
$port = 22230
$sshd = 'C:/Windows/System32/OpenSSH/sshd.exe'
$python = 'D:/tools/audio/voicestudio/data/engines/voxcpm2/voxcpm2/.venv/Scripts/python.exe'
$powershell = 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
$commandShell = 'C:/Windows/System32/cmd.exe'
$sharedConfig = 'C:/ProgramData/ssh/sshd_config'
$hostKey = 'C:/ProgramData/ssh/ssh_host_ed25519_key'
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'One-time bootstrap requires an elevated host administrator.' }
foreach ($address in @($HostAddress,$ForgeAddress)) {
    $ip = $null
    if (-not [Net.IPAddress]::TryParse($address,[ref]$ip) -or $ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) { throw 'Exact tailnet IPv4 literals required.' }
    if ($ip.ToString() -cne $address) { throw 'Canonical dotted-decimal IPv4 literals required.' }
    $bytes = $ip.GetAddressBytes()
    if ($bytes[0] -ne 100 -or $bytes[1] -lt 64 -or $bytes[1] -gt 127) { throw 'Only Tailscale CGNAT addresses are accepted.' }
}
if ($HostAddress -eq $ForgeAddress) { throw 'Host and FORGE addresses must differ.' }
if (-not @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $HostAddress -ErrorAction Stop).Count) { throw 'Host tailnet address is not local.' }
if (Test-Path -LiteralPath $root) { throw 'Project execution root already exists; preserve it and reconcile instead of reinstalling.' }
if (Get-LocalUser -Name $account -ErrorAction SilentlyContinue) { throw 'Dedicated account already exists; do not repurpose it.' }
if (Get-Service -Name $service -ErrorAction SilentlyContinue) { throw 'Dedicated service already exists; preserve its state.' }
if (Get-NetFirewallRule -Name $firewall -ErrorAction SilentlyContinue) { throw 'Dedicated firewall rule already exists; do not overwrite it.' }
if (Get-NetFirewallRule -Name $blockFirewall -ErrorAction SilentlyContinue) { throw 'Dedicated block rule already exists; do not overwrite it.' }
if (@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq $port).Count) { throw 'Dedicated port is occupied.' }
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction Stop)
if ($profiles.Count -ne 3) { throw 'Cannot establish effective Windows firewall profiles.' }
foreach ($profile in $profiles) {
    if ($profile.Enabled.ToString() -ne 'True' -or $profile.AllowLocalFirewallRules.ToString() -notin @('True','NotConfigured') -or $profile.AllowInboundRules.ToString() -notin @('True','NotConfigured')) { throw 'Effective firewall enforcement/merge does not permit the restricted project rules; existing profiles were not changed.' }
}
foreach ($name in @('MpsSvc','BFE')) { if ((Get-Service -Name $name -ErrorAction Stop).Status -ne 'Running') { throw 'Effective firewall service is unavailable; existing services were not changed.' } }
foreach ($file in @($sshd,$python,$powershell,$hostKey,$sharedConfig,$PublicKeyFile,$DispatcherFile)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required inspected bootstrap file missing.' }
}
$shellSettings = if (Test-Path -LiteralPath HKLM:/SOFTWARE/OpenSSH) { Get-ItemProperty -LiteralPath HKLM:/SOFTWARE/OpenSSH -ErrorAction Stop } else { $null }
if ($shellSettings.DefaultShell -and [IO.Path]::GetFullPath($shellSettings.DefaultShell) -ne [IO.Path]::GetFullPath($commandShell)) { throw 'Existing global SSH outer shell is not the supported system cmd.exe; it was not changed.' }
if ($shellSettings.DefaultShellCommandOption -and $shellSettings.DefaultShellCommandOption -cne '/c') { throw 'Existing SSH outer-shell command option is unsupported; it was not changed.' }
$commandProcessor = Get-ItemProperty -LiteralPath 'HKLM:/SOFTWARE/Microsoft/Command Processor' -ErrorAction Stop
if ($commandProcessor.AutoRun) { throw 'System cmd AutoRun would execute outside the dispatcher; it was not changed.' }
if ((Get-FileHash -LiteralPath $DispatcherFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $DispatcherSha256) { throw 'Dispatcher pin mismatch.' }
$key = [IO.File]::ReadAllText([IO.Path]::GetFullPath($PublicKeyFile)).Trim()
if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/]+={0,3}(?: [^\r\n]*)?$') { throw 'Exactly one dedicated Ed25519 public key is required.' }
$key = ($key -split ' ',3)[0..1] -join ' '
$sharedHash = (Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant()

function Assert-TrustedPath([string]$Path,[bool]$AncestorOnly=$false) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    $first = -not $AncestorOnly
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Execution trust chain contains a reparse point.' }
        $acl = Get-Acl -LiteralPath $item.FullName
        $trusted = @('S-1-5-18','S-1-5-32-544',$current.User.Value,'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'Execution trust chain has a nontrusted owner; no ACL was changed.' }
        foreach ($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
            if (($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0) { continue }
            $mask = if ($first) { 0x000D0156 } else { 0x000D0040 }
            if ($ace.AccessControlType -eq 'Allow' -and ($ace.FileSystemRights -band $mask) -ne 0) {
                if ($ace.IdentityReference.Value -notin $trusted) {
                    $failure = [Security.SecurityException]::new('Execution trust chain is writable by a nontrusted principal; no ACL was changed.')
                    # Native diagnostic reads Data privately; console errors retain the fixed message.
                    $failure.Data['checked_path'] = $item.FullName
                    $failure.Data['principal_sid'] = $ace.IdentityReference.Value
                    $failure.Data['rights'] = [int]$ace.FileSystemRights
                    $failure.Data['checked_mask'] = $mask
                    throw $failure
                }
            }
        }
        $item = if ($item -is [IO.DirectoryInfo]) { $item.Parent } else { $item.Directory }
        $first = $false
    }
}
# -I -S prevents user environment, .pth and installed site-packages from executing.
$venv = Split-Path -Parent (Split-Path -Parent $python)
$venvConfig = Join-Path $venv 'pyvenv.cfg'
$homeLine = @(Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^home\s*=\s*' })
if ($homeLine.Count -ne 1) { throw 'Cannot identify the canonical interpreter base.' }
$base = ($homeLine[0] -replace '^home\s*=\s*','').Trim()
foreach ($path in @($python,$venvConfig,$sshd,$powershell,$commandShell,$hostKey,$base,(Join-Path $base 'python.exe'),(Join-Path $base 'python311.dll'),(Join-Path $base 'Lib'),(Join-Path $base 'DLLs'),(Split-Path -Parent $python))) { Assert-TrustedPath $path }
foreach ($item in Get-ChildItem -LiteralPath (Join-Path $base 'Lib') -Recurse -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
foreach ($item in Get-ChildItem -LiteralPath (Join-Path $base 'DLLs') -Recurse -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
foreach ($item in Get-ChildItem -LiteralPath $base -File -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
foreach ($item in Get-ChildItem -LiteralPath (Split-Path -Parent $python) -Recurse -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
foreach ($item in Get-ChildItem -LiteralPath $venv -File -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
$parent = Split-Path -Parent $root
$parentWasMissing = -not (Test-Path -LiteralPath $parent)
if (-not $parentWasMissing) { Assert-TrustedPath $parent } else { Assert-TrustedPath (Split-Path -Parent $parent) $true }

function Protect-Directory([string]$Path,[string]$ReadSid,[bool]$Writable) {
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @('S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')) }
    if ($ReadSid) { $rights = if ($Writable) { 'Modify' } else { 'ReadAndExecute' }; $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ReadSid),$rights,'ContainerInherit,ObjectInherit','None','Allow')) }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
if ($parentWasMissing) { New-Item -ItemType Directory -Path $parent -ErrorAction Stop | Out-Null; Protect-Directory $parent '' $false }
Assert-TrustedPath $parent
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
Protect-Directory $root '' $false
Assert-TrustedPath $root
$encoding = [Text.UTF8Encoding]::new($false)
$receipt = [ordered]@{schema_version=1;status='BOOTSTRAP_IN_PROGRESS';service=$service;execution_sid=$null;account=$account;port=$port;host_address=$HostAddress;forge_address=$ForgeAddress;dispatcher_sha256=$DispatcherSha256;shared_config_sha256=$sharedHash;created_at=[DateTime]::UtcNow.ToString('o');gateway_service_restarted=$false;publication_paused=$true}
[IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
$rollback = @'
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$receipt = Get-Content -LiteralPath (Join-Path $root 'bootstrap-receipt.private.json') -Raw | ConvertFrom-Json
if ($receipt.service -ne 'KnowledgeNetworkHostExec' -or $receipt.account -ne 'kncollector_exec' -or $receipt.port -ne 22230) { throw 'Unexpected project receipt; no rollback.' }
$svc = Get-CimInstance Win32_Service -Filter "Name='KnowledgeNetworkHostExec'" -ErrorAction Stop
if ($svc) {
    $expected = '"C:/Windows/System32/OpenSSH/sshd.exe" -f "C:\ProgramData\KnowledgeNetworkCollector\HostExec\sshd_config"'
    if ($svc.PathName -ne $expected -and $svc.PathName -ne $expected.Replace('\','/')) { throw 'Project service configuration differs; no rollback.' }
    Stop-Service -Name KnowledgeNetworkHostExec -ErrorAction Stop
    & C:/Windows/System32/sc.exe delete KnowledgeNetworkHostExec
    if ($LASTEXITCODE -ne 0) { throw 'Project service removal uncertain; preserve evidence.' }
}
foreach ($name in @('KnowledgeNetworkHostExec-Forge','KnowledgeNetworkHostExec-OtherSources')) {
    $rule = Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
    if ($rule) {
        $ports = $rule | Get-NetFirewallPortFilter -ErrorAction Stop
        $app = $rule | Get-NetFirewallApplicationFilter -ErrorAction Stop
        $addresses = $rule | Get-NetFirewallAddressFilter -ErrorAction Stop
        $expectedAction = if ($name -eq 'KnowledgeNetworkHostExec-Forge') { 'Allow' } else { 'Block' }
        $expectedSources = if ($expectedAction -eq 'Allow') { @($receipt.forge_address) } else { @($receipt.block_sources) }
        if (-not $receipt.host_address -or -not $expectedSources -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne $expectedAction -or $ports.Protocol -ne 'TCP' -or $ports.LocalPort -ne '22230' -or @($addresses.LocalAddress).Count -ne 1 -or $addresses.LocalAddress -ne $receipt.host_address -or (Compare-Object @($addresses.RemoteAddress | Sort-Object) @($expectedSources | Sort-Object)) -or [IO.Path]::GetFullPath($app.Program) -ne 'C:\Windows\System32\OpenSSH\sshd.exe') { throw 'Project firewall rule differs; preserve it for review.' }
        Remove-NetFirewallRule -Name $name -ErrorAction Stop
    }
}
$user = Get-LocalUser -Name kncollector_exec -ErrorAction SilentlyContinue
if ($user) {
    if (-not $receipt.execution_sid -or $user.SID.Value -ne $receipt.execution_sid) { throw 'Dedicated identity cannot be reconciled from receipt; preserve it.' }
    Disable-LocalUser -SID $user.SID -ErrorAction Stop
}
if ((Get-FileHash -LiteralPath C:/ProgramData/ssh/sshd_config -Algorithm SHA256).Hash.ToLowerInvariant() -ne $receipt.shared_config_sha256) { throw 'Gateway configuration differs externally; it was not restored or modified.' }
@{status='PROJECT_ENDPOINT_REMOVED_IDENTITY_DISABLED_EVIDENCE_RETAINED';publication_paused=$true} | ConvertTo-Json
'@
[IO.File]::WriteAllText((Join-Path $root 'rollback-bootstrap.ps1'),$rollback,$encoding)
Copy-Item -LiteralPath $sharedConfig -Destination (Join-Path $root 'shared-sshd-config.before.private') -ErrorAction Stop
$passwordBytes = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($passwordBytes) } finally { $rng.Dispose() }
$password = ConvertTo-SecureString ([Convert]::ToBase64String($passwordBytes)) -AsPlainText -Force
try { $user = New-LocalUser -Name $account -Password $password -AccountNeverExpires -PasswordNeverExpires -UserMayNotChangePassword -Description 'The Knowledge Network Collector fixed-operation SSH identity' } finally { [Array]::Clear($passwordBytes,0,$passwordBytes.Length); $password.Dispose() }
$sid = $user.SID.Value
$receipt.execution_sid = $sid
[IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
$users = @(Get-LocalGroupMember -SID 'S-1-5-32-545' -ErrorAction Stop)
if (-not @($users | Where-Object { $_.SID.Value -eq $sid }).Count) { Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user -ErrorAction Stop }
$adminMembers = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop)
if (@($adminMembers | Where-Object { $_.SID.Value -eq $sid }).Count) { throw 'Dedicated account unexpectedly has administrator membership.' }
Protect-Directory $root $sid $false
foreach ($name in @('runtime','audit','receipts')) { New-Item -ItemType Directory -Path (Join-Path $root $name) -ErrorAction Stop | Out-Null }
Protect-Directory (Join-Path $root 'audit') $sid $true
Copy-Item -LiteralPath $DispatcherFile -Destination (Join-Path $root 'runtime/collector_host_exec.py') -ErrorAction Stop
if ((Get-FileHash -LiteralPath (Join-Path $root 'runtime/collector_host_exec.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $DispatcherSha256) { throw 'Staged dispatcher mismatch.' }
$config = [ordered]@{schema_version=1;execution_sid=$sid;forge_address=$ForgeAddress;python_sha256=(Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant();powershell_sha256=(Get-FileHash -LiteralPath $powershell -Algorithm SHA256).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText((Join-Path $root 'config.json'),($config | ConvertTo-Json),$encoding)
[IO.File]::WriteAllText((Join-Path $root 'authorized_keys'),('from="'+$ForgeAddress+'",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding '+$key+"`n"),$encoding)
$force = "$python -I -S -B $root/runtime/collector_host_exec.py"
$sshdConfig = @"
Port $port
ListenAddress $HostAddress
HostKey $hostKey
PidFile $root/sshd.pid
AuthorizedKeysFile $root/authorized_keys
AllowUsers $account@$ForgeAddress
PubkeyAuthentication yes
PasswordAuthentication no
AuthenticationMethods publickey
PermitEmptyPasswords no
PermitTTY no
PermitUserEnvironment no
PermitUserRC no
DisableForwarding yes
AllowAgentForwarding no
AllowTcpForwarding no
AllowStreamLocalForwarding no
X11Forwarding no
MaxSessions 1
MaxAuthTries 3
LoginGraceTime 20
ForceCommand $force
"@
$configPath = Join-Path $root 'sshd_config'
[IO.File]::WriteAllText($configPath,$sshdConfig,$encoding)
& $sshd -t -f $configPath
if ($LASTEXITCODE -ne 0) { throw 'Installed SSH server rejected isolated configuration; no listener/service was created.' }
$effective = & $sshd -T -f $configPath -C "user=$account,host=forge,addr=$ForgeAddress,laddr=$HostAddress,lport=$port"
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify effective isolated SSH configuration.' }
foreach ($required in @('passwordauthentication no','pubkeyauthentication yes','authenticationmethods publickey','permittty no','permituserenvironment no','permituserrc no','disableforwarding yes','allowtcpforwarding no','allowagentforwarding no','allowstreamlocalforwarding no',("forcecommand $force"),("allowusers $account@$ForgeAddress"))) {
    if ($required -cnotin $effective) { throw 'Effective SSH restriction differs; no service was created.' }
}
[IO.File]::WriteAllText((Join-Path $root 'effective-sshd.private.txt'),($effective -join "`n"),$encoding)
if ((Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sharedHash) { throw 'Existing Gateway SSH configuration changed externally; stop.' }
function Ipv4-Text([uint64]$Number) { return '{0}.{1}.{2}.{3}' -f (($Number -shr 24) -band 255),(($Number -shr 16) -band 255),(($Number -shr 8) -band 255),($Number -band 255) }
$forgeBytes = ([Net.IPAddress]::Parse($ForgeAddress)).GetAddressBytes()
$forgeNumber = [uint64]$forgeBytes[0]*16777216 + [uint64]$forgeBytes[1]*65536 + [uint64]$forgeBytes[2]*256 + [uint64]$forgeBytes[3]
$otherSources = @(
    ('0.0.0.0-'+(Ipv4-Text ($forgeNumber-1)))
    ((Ipv4-Text ($forgeNumber+1))+'-255.255.255.255')
)
if ($otherSources.Count -ne 2) { throw 'Source complement construction failed.' }
$receipt.block_sources = $otherSources
[IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
# Explicit block precedence also closes any pre-existing broad program allow.
New-NetFirewallRule -Name $blockFirewall -DisplayName 'The Knowledge Network Collector SSH deny other sources' -Direction Inbound -Action Block -Protocol TCP -LocalPort $port -LocalAddress $HostAddress -RemoteAddress $otherSources -Program $sshd -Profile Any -ErrorAction Stop | Out-Null
New-NetFirewallRule -Name $firewall -DisplayName 'The Knowledge Network Collector SSH from FORGE only' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -LocalAddress $HostAddress -RemoteAddress $ForgeAddress -Program $sshd -Profile Any -ErrorAction Stop | Out-Null
foreach ($ruleName in @($firewall,$blockFirewall)) {
    $rule = Get-NetFirewallRule -Name $ruleName -PolicyStore ActiveStore -ErrorAction Stop
    $addresses = $rule | Get-NetFirewallAddressFilter -ErrorAction Stop
    $ports = $rule | Get-NetFirewallPortFilter -ErrorAction Stop
    $application = $rule | Get-NetFirewallApplicationFilter -ErrorAction Stop
    $expectedSources = if ($ruleName -eq $firewall) { @($ForgeAddress) } else { $otherSources }
    $expectedAction = if ($ruleName -eq $firewall) { 'Allow' } else { 'Block' }
    if ($rule.PrimaryStatus -ne 'OK' -or $rule.Enabled -ne 'True' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne $expectedAction -or $ports.Protocol -ne 'TCP' -or $ports.LocalPort -ne [string]$port -or @($addresses.LocalAddress).Count -ne 1 -or $addresses.LocalAddress -ne $HostAddress -or (Compare-Object @($addresses.RemoteAddress | Sort-Object) @($expectedSources | Sort-Object)) -or [IO.Path]::GetFullPath($application.Program) -ne [IO.Path]::GetFullPath($sshd)) { throw 'Effective dedicated firewall filters differ; no service was created.' }
}
$binaryPath = '"'+$sshd+'" -f "'+$configPath+'"'
New-Service -Name $service -DisplayName 'The Knowledge Network Collector Host Execution' -BinaryPathName $binaryPath -StartupType Automatic -ErrorAction Stop | Out-Null
$receipt.status = 'CONFIGURED_PENDING_NATIVE_CONNECTION'
[IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
Start-Service -Name $service -ErrorAction Stop
Start-Sleep -Seconds 2
$listener = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop)
$runningService = Get-CimInstance Win32_Service -Filter "Name='$service'" -ErrorAction Stop
if ($listener.Count -ne 1 -or $listener[0].LocalAddress -ne $HostAddress -or -not $runningService -or $runningService.State -ne 'Running' -or $runningService.StartName -ne 'LocalSystem' -or $runningService.PathName -ne $binaryPath -or $listener[0].OwningProcess -ne $runningService.ProcessId) { Stop-Service -Name $service -ErrorAction Stop; throw 'Unexpected project listener/service identity; dedicated service stopped.' }
if ((Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sharedHash) { Stop-Service -Name $service -ErrorAction Stop; throw 'Existing Gateway configuration changed externally; dedicated service stopped.' }
@{status='PROJECT_SSH_LISTENER_STARTED_PENDING_REMOTE_ACCEPTANCE';service=$service;port=$port;execution_identity=$account;publication_paused=$true} | ConvertTo-Json
