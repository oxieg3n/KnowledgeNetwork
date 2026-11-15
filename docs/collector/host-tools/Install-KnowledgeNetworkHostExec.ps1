[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$HostAddress,
    [Parameter(Mandatory=$true)][string]$ForgeAddress,
    [Parameter(Mandatory=$true)][string]$PublicKeyFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PublicKeySha256,
    [Parameter(Mandatory=$true)][string]$DispatcherFile,
    [Parameter(Mandatory=$true)][string]$RuntimeArchiveFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$DispatcherSha256,
    [switch]$ResumePreparedRuntime
)
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$account = 'kncollector_exec'
$service = 'KnowledgeNetworkHostExec'
$firewall = 'KnowledgeNetworkHostExec-Forge'
$blockFirewall = 'KnowledgeNetworkHostExec-OtherSources'
$port = 22230
$sshd = 'C:/Windows/System32/OpenSSH/sshd.exe'
$python = "$root/runtime/python/python.exe"
$runtimeSha256 = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
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
$rootExists = Test-Path -LiteralPath $root
if ($rootExists -and -not $ResumePreparedRuntime) { throw 'Project execution root already exists; preserve it and reconcile instead of reinstalling.' }
if ($ResumePreparedRuntime -and -not $rootExists) { throw 'Prepared runtime resume requires the existing reconciled project root.' }
if (@(Get-LocalUser -ErrorAction Stop | Where-Object Name -eq $account).Count) { throw 'Dedicated account already exists; do not repurpose it.' }
if (@(Get-Service -ErrorAction Stop | Where-Object Name -eq $service).Count) { throw 'Dedicated service already exists; preserve its state.' }
foreach ($store in @('PersistentStore','ActiveStore')) {
    if (@(Get-NetFirewallRule -PolicyStore $store -ErrorAction Stop | Where-Object { $_.Name -in @($firewall,$blockFirewall) }).Count) { throw 'Dedicated firewall state already exists; do not overwrite it.' }
}
if (@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq $port).Count) { throw 'Dedicated port is occupied.' }
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction Stop)
if ($profiles.Count -ne 3) { throw 'Cannot establish effective Windows firewall profiles.' }
foreach ($profile in $profiles) {
    if ($profile.Enabled.ToString() -ne 'True' -or $profile.AllowLocalFirewallRules.ToString() -notin @('True','NotConfigured') -or $profile.AllowInboundRules.ToString() -notin @('True','NotConfigured')) { throw 'Effective firewall enforcement/merge does not permit the restricted project rules; existing profiles were not changed.' }
}
foreach ($name in @('MpsSvc','BFE')) { if ((Get-Service -Name $name -ErrorAction Stop).Status -ne 'Running') { throw 'Effective firewall service is unavailable; existing services were not changed.' } }
foreach ($file in @($sshd,$powershell,$hostKey,$sharedConfig,$PublicKeyFile,$DispatcherFile,$RuntimeArchiveFile)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required inspected bootstrap file missing.' }
}
$shellSettings = if (Test-Path -LiteralPath HKLM:/SOFTWARE/OpenSSH) { Get-ItemProperty -LiteralPath HKLM:/SOFTWARE/OpenSSH -ErrorAction Stop } else { $null }
if ($shellSettings.DefaultShell -and [IO.Path]::GetFullPath($shellSettings.DefaultShell) -ne [IO.Path]::GetFullPath($commandShell)) { throw 'Existing global SSH outer shell is not the supported system cmd.exe; it was not changed.' }
if ($shellSettings.DefaultShellCommandOption -and $shellSettings.DefaultShellCommandOption -cne '/c') { throw 'Existing SSH outer-shell command option is unsupported; it was not changed.' }
$commandProcessor = Get-ItemProperty -LiteralPath 'HKLM:/SOFTWARE/Microsoft/Command Processor' -ErrorAction Stop
if ($commandProcessor.AutoRun) { throw 'System cmd AutoRun would execute outside the dispatcher; it was not changed.' }
if ((Get-FileHash -LiteralPath $DispatcherFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $DispatcherSha256) { throw 'Dispatcher pin mismatch.' }
$keyFile = [IO.File]::Open([IO.Path]::GetFullPath($PublicKeyFile),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try {
    if ($keyFile.Length -le 0 -or $keyFile.Length -gt 4096) { throw 'Dedicated public key exceeds bounds.' }
    $keyMemory = [IO.MemoryStream]::new()
    try { $keyFile.CopyTo($keyMemory); $keyBytes = $keyMemory.ToArray() } finally { $keyMemory.Dispose() }
} finally { $keyFile.Dispose() }
$keyHasher = [Security.Cryptography.SHA256]::Create()
try { $keyDigest = ([BitConverter]::ToString($keyHasher.ComputeHash($keyBytes))).Replace('-','').ToLowerInvariant() } finally { $keyHasher.Dispose() }
if ($keyDigest -cne $PublicKeySha256) { throw 'Dedicated public key pin mismatch.' }
$key = [Text.UTF8Encoding]::new($false,$true).GetString($keyBytes).Trim()
if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/]+={0,3}(?: [^\r\n]*)?$') { throw 'Exactly one dedicated Ed25519 public key is required.' }
$key = ($key -split ' ',3)[0..1] -join ' '
$sharedHash = (Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant()
$archiveFile = [IO.File]::Open([IO.Path]::GetFullPath($RuntimeArchiveFile),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try {
    if ($archiveFile.Length -le 0 -or $archiveFile.Length -gt 32MB) { throw 'Dispatcher runtime archive exceeds bounds.' }
    $archiveMemory = [IO.MemoryStream]::new()
    try { $archiveFile.CopyTo($archiveMemory); $archiveBytes = $archiveMemory.ToArray() } finally { $archiveMemory.Dispose() }
} finally { $archiveFile.Dispose() }
$archiveHasher = [Security.Cryptography.SHA256]::Create()
try { $archiveDigest = ([BitConverter]::ToString($archiveHasher.ComputeHash($archiveBytes))).Replace('-','').ToLowerInvariant() } finally { $archiveHasher.Dispose() }
if ($archiveDigest -cne $runtimeSha256) { throw 'Official dispatcher runtime archive SHA-256 mismatch; no files were extracted.' }

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
foreach ($path in @($sshd,$powershell,$commandShell,$hostKey)) { Assert-TrustedPath $path }
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
function Expand-DispatcherRuntime([byte[]]$ArchiveBytes,[string]$Target,[switch]$VerifyExisting) {
    if ($ArchiveBytes.Length -le 0 -or $ArchiveBytes.Length -gt 32MB) { throw 'Runtime archive size invalid.' }
    $directory = Get-Item -LiteralPath $Target -Force -ErrorAction Stop
    if (-not $directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Runtime requires a regular protected directory.' }
    $allowed = @('python.exe','pythonw.exe','python314.dll','python3.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt','pyexpat.pyd','select.pyd','unicodedata.pyd','winsound.pyd','_asyncio.pyd','_bz2.pyd','_ctypes.pyd','_decimal.pyd','_elementtree.pyd','_hashlib.pyd','_lzma.pyd','_multiprocessing.pyd','_overlapped.pyd','_queue.pyd','_remote_debugging.pyd','_socket.pyd','_sqlite3.pyd','_ssl.pyd','_uuid.pyd','_wmi.pyd','_zoneinfo.pyd','_zstd.pyd','libcrypto-3.dll','libffi-8.dll','libssl-3.dll','libtommath.dll','sqlite3.dll','python314.zip','python314._pth','python.cat')
    $existing = @(Get-ChildItem -LiteralPath $Target -Force -ErrorAction Stop)
    if ($VerifyExisting) {
        if ($existing.Count -ne $allowed.Count) { throw 'Prepared runtime member count differs.' }
        foreach ($item in $existing) { if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.Name -cnotin $allowed) { throw 'Prepared runtime contains an unexpected or linked member.' } }
    } elseif ($existing.Count) { throw 'Runtime extraction requires a new empty regular protected directory.' }
    Add-Type -AssemblyName System.IO.Compression
    $memory = [IO.MemoryStream]::new($ArchiveBytes,$false)
    $archive = [IO.Compression.ZipArchive]::new($memory,[IO.Compression.ZipArchiveMode]::Read,$false)
    $records = @()
    try {
        if ($archive.Entries.Count -ne $allowed.Count) { throw 'Unexpected runtime archive member count.' }
        $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $total = [long]0
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName
            $type = ($entry.ExternalAttributes -shr 16) -band 0xF000
            if ($name -cnotin $allowed -or $name -match '[\\/:]' -or -not $seen.Add($name) -or $type -notin @(0,0x8000) -or ($entry.ExternalAttributes -band 0x410) -ne 0 -or $entry.Length -le 0 -or $entry.Length -gt 32MB) { throw 'Unexpected or unsafe runtime archive member.' }
            $total += $entry.Length
            if ($total -gt 128MB) { throw 'Runtime expanded size exceeds bounds.' }
        }
        foreach ($entry in $archive.Entries) {
            $bytes = New-Object byte[] ([int]$entry.Length)
            $entryStream = $entry.Open()
            try {
                $offset = 0
                while ($offset -lt $bytes.Length) {
                    $count = $entryStream.Read($bytes,$offset,$bytes.Length-$offset)
                    if ($count -le 0) { throw 'Runtime archive member truncated.' }
                    $offset += $count
                }
                if ($entryStream.ReadByte() -ne -1) { throw 'Runtime archive member exceeds declared size.' }
            } finally { $entryStream.Dispose() }
            $hasher = [Security.Cryptography.SHA256]::Create()
            try { $hash = ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
            $destination = Join-Path $Target $entry.FullName
            if (-not $VerifyExisting) {
                $output = [IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                try { $output.Write($bytes,0,$bytes.Length); $output.Flush($true) } finally { $output.Dispose() }
            }
            if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -cne $hash) { throw 'Extracted runtime member hash mismatch.' }
            $records += [ordered]@{name=$entry.FullName;sha256=$hash;bytes=$bytes.Length}
        }
    } finally { $archive.Dispose(); $memory.Dispose() }
    return $records
}
function Assert-RuntimeManifest([object]$Recorded,[object[]]$Actual) {
    if ($Recorded -isnot [array] -or $Recorded.Count -ne $Actual.Count) { throw 'Prepared runtime manifest member count differs.' }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($item in $Recorded) {
        $keys = @($item.PSObject.Properties.Name)
        if ($keys.Count -ne 3 -or @($keys | Where-Object { $_ -cnotin @('name','sha256','bytes') }).Count -or $item.name -isnot [string] -or $item.sha256 -isnot [string] -or $item.bytes -isnot [int] -or -not $seen.Add($item.name)) { throw 'Prepared runtime manifest schema differs.' }
        $expected = @($Actual | Where-Object { $_.name -ceq $item.name })
        if ($expected.Count -ne 1 -or $item.sha256 -cne $expected[0].sha256 -or $item.bytes -ne $expected[0].bytes) { throw 'Prepared runtime manifest differs from actual package bytes.' }
    }
}
function Assert-PreparedRuntimeReceipt([object]$Receipt,[string]$HostAddress,[string]$ForgeAddress,[string]$DispatcherSha256,[string]$SharedConfigSha256) {
    $keys = @('schema_version','status','service','execution_sid','account','port','host_address','forge_address','dispatcher_sha256','runtime_version','runtime_archive_sha256','shared_config_sha256','created_at','gateway_service_restarted','publication_paused')
    if ($null -eq $Receipt -or @($Receipt.PSObject.Properties).Count -ne $keys.Count -or @($Receipt.PSObject.Properties | Where-Object Name -cnotin $keys).Count) { throw 'Prepared receipt schema differs; no resume.' }
    foreach ($name in @('status','service','account','host_address','forge_address','dispatcher_sha256','runtime_version','runtime_archive_sha256','shared_config_sha256','created_at')) { if ($Receipt.$name -isnot [string]) { throw 'Prepared receipt field type differs; no resume.' } }
    if ($Receipt.schema_version -isnot [int] -or $Receipt.port -isnot [int] -or $Receipt.gateway_service_restarted -isnot [bool] -or $Receipt.publication_paused -isnot [bool]) { throw 'Prepared receipt field type differs; no resume.' }
    if ($Receipt.schema_version -ne 1 -or $Receipt.status -cne 'BOOTSTRAP_IN_PROGRESS' -or $null -ne $Receipt.execution_sid -or $Receipt.account -cne 'kncollector_exec' -or $Receipt.service -cne 'KnowledgeNetworkHostExec' -or $Receipt.port -ne 22230 -or $Receipt.host_address -cne $HostAddress -or $Receipt.forge_address -cne $ForgeAddress -or $Receipt.dispatcher_sha256 -cne $DispatcherSha256 -or $Receipt.runtime_version -cne '3.14.10' -or $Receipt.runtime_archive_sha256 -cne '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159' -or $Receipt.shared_config_sha256 -cne $SharedConfigSha256 -or $Receipt.gateway_service_restarted -ne $false -or $Receipt.publication_paused -ne $true) { throw 'Prepared receipt is not the exact reconciled pre-account state.' }
    $date = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse($Receipt.created_at,[ref]$date)) { throw 'Prepared receipt creation time is invalid.' }
    $result = [ordered]@{}
    foreach ($property in $Receipt.PSObject.Properties) { $result[$property.Name] = $property.Value }
    return $result
}
if (-not $ResumePreparedRuntime) {
    if ($parentWasMissing) { New-Item -ItemType Directory -Path $parent -ErrorAction Stop | Out-Null; Protect-Directory $parent '' $false }
    Assert-TrustedPath $parent
    New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
    Protect-Directory $root '' $false
}
Assert-TrustedPath $root
$encoding = [Text.UTF8Encoding]::new($false)
if (-not $ResumePreparedRuntime) {
    $receipt = [ordered]@{schema_version=1;status='BOOTSTRAP_IN_PROGRESS';service=$service;execution_sid=$null;account=$account;port=$port;host_address=$HostAddress;forge_address=$ForgeAddress;dispatcher_sha256=$DispatcherSha256;runtime_version='3.14.10';runtime_archive_sha256=$runtimeSha256;shared_config_sha256=$sharedHash;created_at=[DateTime]::UtcNow.ToString('o');gateway_service_restarted=$false;publication_paused=$true}
    [IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
}
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
$pythonDirectory = Join-Path $root 'runtime/python'
if ($ResumePreparedRuntime) {
    $expectedRoot = @('bootstrap-receipt.private.json','rollback-bootstrap.ps1','runtime','runtime-files.private.json','shared-sshd-config.before.private')
    $rootItems = @(Get-ChildItem -LiteralPath $root -Force -ErrorAction Stop)
    if ($rootItems.Count -ne $expectedRoot.Count) { throw 'Prepared root contains unexpected state; no resume.' }
    foreach ($item in $rootItems) { if ($item.Name -cnotin $expectedRoot -or $item.PSIsContainer -ne ($item.Name -ceq 'runtime')) { throw 'Prepared root shape differs; no resume.' } }
    foreach ($item in Get-ChildItem -LiteralPath $root -Recurse -Force -ErrorAction Stop) { Assert-TrustedPath $item.FullName }
    $runtimeChildren = @(Get-ChildItem -LiteralPath (Join-Path $root 'runtime') -Force -ErrorAction Stop)
    if ($runtimeChildren.Count -ne 1 -or $runtimeChildren[0].Name -cne 'python' -or -not $runtimeChildren[0].PSIsContainer) { throw 'Prepared runtime directory shape differs; no resume.' }
    $receiptPath = Join-Path $root 'bootstrap-receipt.private.json'
    if ((Get-Item -LiteralPath $receiptPath).Length -gt 16KB) { throw 'Prepared receipt exceeds bounds.' }
    $loaded = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $receipt = Assert-PreparedRuntimeReceipt $loaded $HostAddress $ForgeAddress $DispatcherSha256 $sharedHash
    $rollbackPath = Join-Path $root 'rollback-bootstrap.ps1'
    if ((Get-FileHash -LiteralPath $rollbackPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne '3ea650c9f46f9e77d4cf3dca88393e91c22098936170080e3b1173acc59869ed' -or [IO.File]::ReadAllText($rollbackPath).Replace("`r`n","`n") -cne $rollback.Replace("`r`n","`n")) { throw 'Prepared rollback evidence differs; no resume.' }
    if ((Get-FileHash -LiteralPath (Join-Path $root 'shared-sshd-config.before.private') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $sharedHash) { throw 'Prepared shared SSH backup differs; no resume.' }
} else {
    [IO.File]::WriteAllText((Join-Path $root 'rollback-bootstrap.ps1'),$rollback,$encoding)
    Copy-Item -LiteralPath $sharedConfig -Destination (Join-Path $root 'shared-sshd-config.before.private') -ErrorAction Stop
    New-Item -ItemType Directory -Path (Join-Path $root 'runtime') -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $pythonDirectory -ErrorAction Stop | Out-Null
    Protect-Directory $pythonDirectory '' $false
}
Assert-TrustedPath $pythonDirectory
$runtimeRecords = @(Expand-DispatcherRuntime $archiveBytes $pythonDirectory -VerifyExisting:$ResumePreparedRuntime)
if ($ResumePreparedRuntime) {
    $recordsPath = Join-Path $root 'runtime-files.private.json'
    if ((Get-Item -LiteralPath $recordsPath).Length -gt 64KB) { throw 'Prepared runtime manifest exceeds bounds.' }
    $recorded = Get-Content -LiteralPath $recordsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-RuntimeManifest $recorded $runtimeRecords
} else { [IO.File]::WriteAllText((Join-Path $root 'runtime-files.private.json'),($runtimeRecords | ConvertTo-Json),$encoding) }
foreach ($file in @($python,(Join-Path $pythonDirectory 'python314.dll'))) {
    $signature = Get-AuthenticodeSignature -LiteralPath $file -ErrorAction Stop
    if ($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Python Software Foundation(,|$)') { throw 'Protected dispatcher Python publisher signature is invalid; no interpreter was executed.' }
}
$pathLines = @([IO.File]::ReadAllLines((Join-Path $pythonDirectory 'python314._pth')) | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
if ($pathLines.Count -ne 2 -or $pathLines[0] -cne 'python314.zip' -or $pathLines[1] -cne '.') { throw 'Embedded runtime import path differs from the isolated reviewed package.' }
foreach ($file in Get-ChildItem -LiteralPath $pythonDirectory -Force -ErrorAction Stop) { Assert-TrustedPath $file.FullName }
& $python -I -S -B -c 'import sys; assert sys.version_info[:3] == (3,14,10); assert sys.flags.isolated and sys.flags.no_site'
if ($LASTEXITCODE -ne 0) { throw 'Protected dispatcher runtime isolation/version check failed.' }
$passwordBytes = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($passwordBytes) } finally { $rng.Dispose() }
$password = ConvertTo-SecureString ([Convert]::ToBase64String($passwordBytes)) -AsPlainText -Force
try { $user = New-LocalUser -Name $account -Password $password -AccountNeverExpires -PasswordNeverExpires -UserMayNotChangePassword -Description 'The Knowledge Network Collector SSH' } finally { [Array]::Clear($passwordBytes,0,$passwordBytes.Length); $password.Dispose() }
$sid = $user.SID.Value
$receipt.execution_sid = $sid
[IO.File]::WriteAllText((Join-Path $root 'bootstrap-receipt.private.json'),($receipt | ConvertTo-Json),$encoding)
$users = @(Get-LocalGroupMember -SID 'S-1-5-32-545' -ErrorAction Stop)
if (-not @($users | Where-Object { $_.SID.Value -eq $sid }).Count) { Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user -ErrorAction Stop }
$adminMembers = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop)
if (@($adminMembers | Where-Object { $_.SID.Value -eq $sid }).Count) { throw 'Dedicated account unexpectedly has administrator membership.' }
Protect-Directory $root $sid $false
foreach ($name in @('audit','receipts')) { New-Item -ItemType Directory -Path (Join-Path $root $name) -ErrorAction Stop | Out-Null }
Protect-Directory (Join-Path $root 'runtime') $sid $false
Protect-Directory $pythonDirectory $sid $false
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
