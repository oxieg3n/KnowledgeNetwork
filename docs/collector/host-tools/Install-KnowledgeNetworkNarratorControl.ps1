[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BundleDirectory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PinnedManifestSha256
)
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$kit = 'D:/projects/knowledgenetwork/collector-narrator-v9-004'
$spool = "$kit/private-service-v9-001"
$runtime = "$root/runtime"
$python = "$runtime/python/python.exe"
$package = "$runtime/youtube_ops"
$upgrade = "$root/broker-upgrade-v1"
$taskPath = '\KnowledgeNetworkCollector\'
$taskName = 'NarratorControl'
$sharedConfig = 'C:/ProgramData/ssh/sshd_config'
$oldDispatcherHash = '637c92f13126c2ccb5a2eeb888cc4ac48a8a540cf74652f96dc268ce12600bf2'
$files = @('__init__.py','collector_narrator_pipe.py','collector_narrator_control.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
$launcherText = "import sys`nsys.path.insert(0, 'C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime')`nfrom youtube_ops.collector_narrator_control import main`nraise SystemExit(main())`n"
$encoding = [Text.UTF8Encoding]::new($false,$true)

function Get-BytesHash([byte[]]$Bytes) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hasher.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
}
function Initialize-FileIdentity {
    if ('KNCollectorNarratorBootstrap.Native' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
namespace KNCollectorNarratorBootstrap {
  [StructLayout(LayoutKind.Sequential)] public struct FileIdentity {
    public uint Attributes;
    public System.Runtime.InteropServices.ComTypes.FILETIME Creation;
    public System.Runtime.InteropServices.ComTypes.FILETIME Access;
    public System.Runtime.InteropServices.ComTypes.FILETIME Write;
    public uint Volume; public uint SizeHigh; public uint SizeLow; public uint Links;
    public uint IndexHigh; public uint IndexLow;
  }
  public static class Native {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool GetFileInformationByHandle(SafeFileHandle handle, out FileIdentity info);
  }
}
'@
}
function Read-RegularBytes([string]$Path,[long]$Limit,[string]$ExpectedHash) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Regular source file required.' }
    $parent = $item.Directory
    while ($null -ne $parent) {
        if (($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Source ancestor reparse point rejected.' }
        $parent = $parent.Parent
    }
    $stream = [IO.File]::Open($item.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $info = [KNCollectorNarratorBootstrap.FileIdentity]::new()
        if (-not [KNCollectorNarratorBootstrap.Native]::GetFileInformationByHandle($stream.SafeFileHandle,[ref]$info) -or $info.Links -ne 1 -or ($info.Attributes -band 0x400) -ne 0) { throw 'Source hardlink/reparse identity rejected.' }
        if ($stream.Length -gt $Limit) { throw 'Source file exceeds its limit.' }
        if ($stream.Length -eq 0 -and ($item.Name -cne '__init__.py' -or $ExpectedHash -cne 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')) { throw 'Only the explicitly pinned empty package marker is accepted.' }
        $memory = [IO.MemoryStream]::new()
        try { $stream.CopyTo($memory); $bytes = $memory.ToArray() } finally { $memory.Dispose() }
        $after = [KNCollectorNarratorBootstrap.FileIdentity]::new()
        if (-not [KNCollectorNarratorBootstrap.Native]::GetFileInformationByHandle($stream.SafeFileHandle,[ref]$after) -or $after.Links -ne 1 -or $after.Volume -ne $info.Volume -or $after.IndexHigh -ne $info.IndexHigh -or $after.IndexLow -ne $info.IndexLow -or $after.Write.dwLowDateTime -ne $info.Write.dwLowDateTime -or $after.Write.dwHighDateTime -ne $info.Write.dwHighDateTime) { throw 'Source identity changed during capture.' }
    } finally { $stream.Dispose() }
    if ($ExpectedHash -and (Get-BytesHash $bytes) -cne $ExpectedHash) { throw 'Captured source SHA-256 mismatch.' }
    return ,$bytes
}
function Assert-TrustedExecutionPath([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    $first = $true
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Execution trust chain contains a reparse point.' }
        $acl = Get-Acl -LiteralPath $item.FullName -ErrorAction Stop
        $raw = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if ($null -eq $raw.DiscretionaryAcl) { throw 'Execution trust chain has a null DACL.' }
        $trusted = @('S-1-5-18','S-1-5-32-544',$ownerSid,'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'Execution trust chain has an untrusted owner.' }
        foreach ($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
            if (($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0) { continue }
            $mask = if ($first) { 0x000D0156 } else { 0x000D0040 }
            if ($ace.AccessControlType -eq 'Allow' -and ($ace.FileSystemRights -band $mask) -ne 0 -and $ace.IdentityReference.Value -notin $trusted) { throw 'Execution trust chain is writable by an untrusted identity.' }
        }
        $item = if ($item -is [IO.DirectoryInfo]) { $item.Parent } else { $item.Directory }
        $first = $false
    }
}
function Assert-DeploymentManifest([object]$Value) {
    $keys = @('schema_version','old_dispatcher_sha256','dispatcher_sha256','files','manifest_sha256','server_python_sha256','shared_config_sha256','launcher_sha256')
    if ($null -eq $Value -or $Value -is [array] -or @($Value.PSObject.Properties.Name).Count -ne $keys.Count -or @($Value.PSObject.Properties.Name | Where-Object { $_ -cnotin $keys }).Count) { throw 'Deployment manifest fields differ.' }
    if ($Value.schema_version -isnot [int] -or $Value.schema_version -ne 1 -or $Value.old_dispatcher_sha256 -cne $oldDispatcherHash) { throw 'Deployment version or old source differs.' }
    foreach ($key in @('old_dispatcher_sha256','dispatcher_sha256','manifest_sha256','server_python_sha256','shared_config_sha256','launcher_sha256')) { if ($Value.$key -isnot [string] -or $Value.$key -cnotmatch '^[a-f0-9]{64}$') { throw 'Deployment digest is invalid.' } }
    if ($null -eq $Value.files -or $Value.files -is [array] -or @($Value.files.PSObject.Properties.Name).Count -ne $files.Count -or @($Value.files.PSObject.Properties.Name | Where-Object { $_ -cnotin $files }).Count) { throw 'Deployment package fields differ.' }
    foreach ($name in $files) { if ($Value.files.$name -isnot [string] -or $Value.files.$name -cnotmatch '^[a-f0-9]{64}$') { throw 'Package digest is invalid.' } }
    return $Value
}
function Assert-RuntimeLayout([string]$Path) {
    $members = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)
    if ($members.Count -ne 2) { throw 'Existing execution runtime has unexpected entries; none were removed.' }
    foreach ($item in $members) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
            ($item.Name -ceq 'python' -and -not $item.PSIsContainer) -or
            ($item.Name -ceq 'collector_host_exec.py' -and $item.PSIsContainer) -or
            $item.Name -cnotin @('python','collector_host_exec.py')) { throw 'Existing execution runtime shape differs; none were removed.' }
    }
}
function Convert-StrictJson([byte[]]$Bytes,[string]$Python) {
    $validator = @'
import json,sys
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError()
        result[key]=value
    return result
def invalid(value): raise ValueError()
try:
    value=json.loads(sys.stdin.read(),object_pairs_hook=unique,parse_constant=invalid)
    print(json.dumps(value,ensure_ascii=True))
except Exception: sys.exit(1)
'@
    $json = [Text.UTF8Encoding]::new($false,$true).GetString($Bytes) | & $Python -I -S -B -c $validator 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Deployment JSON contains duplicate fields or invalid syntax.' }
    return ($json | ConvertFrom-Json)
}
function Write-NewBytes([string]$Path,[byte[]]$Bytes) {
    $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($Bytes,0,$Bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}
function New-ProtectedDirectory([string]$Path,[bool]$BridgeRead) {
    if (Test-Path -LiteralPath $Path) { throw 'Protected deployment target already exists; preserve and reconcile.' }
    New-Item -ItemType Directory -Path $Path -ErrorAction Stop | Out-Null
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @('S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')) }
    foreach ($sid in @($ownerSid,$(if ($BridgeRead) { $bridgeSid }))) { if ($sid) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'ReadAndExecute','ContainerInherit,ObjectInherit','None','Allow')) } }
    Set-Acl -LiteralPath $Path -AclObject $acl
    Assert-TrustedExecutionPath $Path
}
function Assert-TaskXml([string]$Text,[string]$OwnerSid,[string]$Python,[string]$Arguments,[string]$WorkingDirectory,[string]$EffectiveRunLevel='') {
    $xml = [xml]$Text
    $ns = [Xml.XmlNamespaceManager]::new($xml.NameTable); $ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $principals = @($xml.SelectNodes('/t:Task/t:Principals/t:Principal',$ns))
    $actions = @($xml.SelectNodes('/t:Task/t:Actions/*',$ns))
    $settings = $xml.SelectSingleNode('/t:Task/t:Settings',$ns)
    $runLevel = [string]$principals[0].RunLevel
    # Native export omits the default; require actual CIM Limited readback then.
    $limited = ($runLevel -ceq 'LeastPrivilege' -or (-not $runLevel -and $EffectiveRunLevel -ceq 'Limited')) -and (-not $EffectiveRunLevel -or $EffectiveRunLevel -ceq 'Limited')
    $zeroLimit = $false
    try { $zeroLimit = [Xml.XmlConvert]::ToTimeSpan([string]$settings.ExecutionTimeLimit) -eq [TimeSpan]::Zero } catch { }
    if ($principals.Count -ne 1 -or $principals[0].UserId -cne $OwnerSid -or $principals[0].LogonType -cne 'InteractiveToken' -or -not $limited -or $actions.Count -ne 1 -or $actions[0].LocalName -cne 'Exec' -or $actions[0].Command -cne $Python -or $actions[0].Arguments -cne $Arguments -or $actions[0].WorkingDirectory -cne $WorkingDirectory -or @($xml.SelectNodes('/t:Task/t:Triggers/*',$ns)).Count -ne 0 -or $null -eq $settings -or -not $zeroLimit -or $settings.MultipleInstancesPolicy -cne 'IgnoreNew' -or $settings.StopIfGoingOnBatteries -cne 'false' -or $settings.DisallowStartIfOnBatteries -cne 'false' -or $settings.AllowHardTerminate -cne 'false' -or $null -ne $settings.RestartOnFailure) { throw 'Registered limited owner task differs from reviewed action.' }
}
function Assert-TaskSecurity([string]$Sddl,[string]$OwnerSid) {
    $descriptor = [Security.AccessControl.RawSecurityDescriptor]::new($Sddl)
    if ($null -eq $descriptor.DiscretionaryAcl -or $descriptor.Owner.Value -cne $OwnerSid -or ($descriptor.ControlFlags -band [Security.AccessControl.ControlFlags]::DiscretionaryAclProtected) -eq 0) { throw 'Task owner/DACL protection differs.' }
    $seen = @()
    foreach ($ace in $descriptor.DiscretionaryAcl) {
        if ($ace.AceType -ne [Security.AccessControl.AceType]::AccessAllowed -or $ace.SecurityIdentifier.Value -notin @($OwnerSid,'S-1-5-18','S-1-5-32-544')) { throw 'Task grants an unexpected identity or right type.' }
        $seen += $ace.SecurityIdentifier.Value
    }
    foreach ($sid in @($OwnerSid,'S-1-5-18','S-1-5-32-544')) { if ($sid -notin $seen) { throw 'Required task identity missing.' } }
}

$current = [Security.Principal.WindowsIdentity]::GetCurrent()
$ownerSid = $current.User.Value
if ($ownerSid -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'One-time deployment requires the intended owner elevated, never SYSTEM.' }
if ([IO.Path]::GetFullPath($BundleDirectory) -ine [IO.Path]::GetFullPath("$kit/narrator-control-deploy-v1")) { throw 'Only the fixed reviewed project staging directory is accepted.' }
$BundleDirectory = [IO.Path]::GetFullPath($BundleDirectory)
foreach ($path in @($upgrade,$package,"$runtime/narrator-control-launch.py","$runtime/collector_host_exec.next","$root/narrator-broker.json")) { if (Test-Path -LiteralPath $path) { throw 'Broker deployment state already exists; preserve it and reconcile, never retry blindly.' } }
if (@(Get-ScheduledTask -ErrorAction Stop | Where-Object { $_.TaskPath -ceq $taskPath -and $_.TaskName -ceq $taskName }).Count) { throw 'Owner broker task already exists; no replacement.' }
foreach ($path in @($root,$runtime,"$runtime/python",$python,"$root/config.json",$sharedConfig,"$runtime/collector_host_exec.py")) { Assert-TrustedExecutionPath $path }
Assert-RuntimeLayout $runtime
Initialize-FileIdentity
$oldDispatcher = Read-RegularBytes "$runtime/collector_host_exec.py" 128KB $oldDispatcherHash
$config = $encoding.GetString((Read-RegularBytes "$root/config.json" 64KB $null)) | ConvertFrom-Json
$configKeys = @('schema_version','execution_sid','forge_address','python_sha256','powershell_sha256')
if (@($config.PSObject.Properties.Name).Count -ne 5 -or @($config.PSObject.Properties.Name | Where-Object { $_ -cnotin $configKeys }).Count -or $config.schema_version -isnot [int] -or $config.schema_version -ne 1 -or $config.execution_sid -isnot [string] -or $config.execution_sid -cnotmatch '^S-1-5-21-(?:\d+-){3}\d+$') { throw 'Existing dedicated execution configuration differs.' }
$bridgeSid = $config.execution_sid
if ($bridgeSid -ceq $ownerSid) { throw 'Owner and dedicated execution identity must differ.' }
$bridge = @(Get-LocalUser -ErrorAction Stop | Where-Object { $_.Name -ceq 'kncollector_exec' -and $_.SID.Value -ceq $bridgeSid })
if ($bridge.Count -ne 1 -or -not $bridge[0].Enabled) { throw 'Dedicated account/SID changed.' }
if (@(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop | Where-Object { $_.SID.Value -ceq $bridgeSid }).Count) { throw 'Dedicated execution account is an administrator.' }
$spoolItem = Get-Item -LiteralPath $spool -Force -ErrorAction Stop
if (-not $spoolItem.PSIsContainer -or ($spoolItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Existing private spool differs.' }
$spoolAcl = Get-Acl -LiteralPath $spool -ErrorAction Stop
$spoolRaw = [Security.AccessControl.RawSecurityDescriptor]::new($spoolAcl.GetSecurityDescriptorBinaryForm(),0)
if ($null -eq $spoolRaw.DiscretionaryAcl) { throw 'Existing private spool has a null DACL; no ACL rewritten.' }
$allowedSpool = @($ownerSid,'S-1-5-18','S-1-5-32-544')
if (-not $spoolAcl.AreAccessRulesProtected -or $spoolAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowedSpool) { throw 'Existing spool owner/protection differs; no ACL rewritten.' }
$ownerFullControl = $false
foreach ($ace in $spoolAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
    if ($ace.AccessControlType -ne 'Allow' -or $ace.IdentityReference.Value -notin $allowedSpool) { throw 'Existing spool permissions differ; no ACL rewritten.' }
    if ($ace.IdentityReference.Value -ceq $ownerSid -and -not $ace.IsInherited -and ($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -eq 0 -and ($ace.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -eq [Security.AccessControl.FileSystemRights]::FullControl) { $ownerFullControl = $true }
}
if (-not $ownerFullControl) { throw 'Intended owner lacks existing private spool rights.' }
$scheduler = New-Object -ComObject 'Schedule.Service'
$scheduler.Connect()
$taskFolder = $null
try { $taskFolder = $scheduler.GetFolder('\KnowledgeNetworkCollector') } catch { if ($_.Exception.HResult -ne -2147024894) { throw 'Task folder query failed.' } }
if ($null -ne $taskFolder) { Assert-TaskSecurity ($taskFolder.GetSecurityDescriptor(7)) $ownerSid }
$manifestBytes = Read-RegularBytes (Join-Path $BundleDirectory 'narrator-control-deployment.json') 64KB $PinnedManifestSha256
$deployment = Assert-DeploymentManifest ($encoding.GetString($manifestBytes) | ConvertFrom-Json)
$expectedNames = @($files + @('collector_host_exec.py','narrator-control-launch.py','narrator-control-deployment.json'))
$members = @(Get-ChildItem -LiteralPath $BundleDirectory -Force -ErrorAction Stop)
if ($members.Count -ne $expectedNames.Count -or @($members | Where-Object { $_.PSIsContainer -or $_.Name -cnotin $expectedNames }).Count) { throw 'Staged bundle must contain only the exact reviewed flat files.' }
$sources = @{}
foreach ($name in $files) { $sources[$name] = Read-RegularBytes (Join-Path $BundleDirectory $name) 128KB $deployment.files.$name }
$sources['collector_host_exec.py'] = Read-RegularBytes (Join-Path $BundleDirectory 'collector_host_exec.py') 128KB $deployment.dispatcher_sha256
$sources['narrator-control-launch.py'] = Read-RegularBytes (Join-Path $BundleDirectory 'narrator-control-launch.py') 4096 $deployment.launcher_sha256
if ($encoding.GetString($sources['narrator-control-launch.py']) -cne $launcherText) { throw 'Broker launcher differs from fixed protected imports.' }
if ((Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant() -cne $config.python_sha256 -or $deployment.server_python_sha256 -cne $config.python_sha256) { throw 'Protected server interpreter differs.' }
if ((Get-BytesHash (Read-RegularBytes $sharedConfig 128KB $deployment.shared_config_sha256)) -cne $deployment.shared_config_sha256) { throw 'Shared SSH configuration differs; unchanged.' }
$null = Read-RegularBytes "$spool/review/narrator-manifest.LOCAL-USE-CANDIDATE.private.json" 1MB $deployment.manifest_sha256
$runtimeRecords = $encoding.GetString((Read-RegularBytes "$root/runtime-files.private.json" 64KB $null)) | ConvertFrom-Json
if ($runtimeRecords -isnot [array] -or $runtimeRecords.Count -ne 37 -or @(Get-ChildItem -LiteralPath "$runtime/python" -Force).Count -ne 37) { throw 'Protected interpreter inventory differs.' }
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$executionPaths = @($root,$runtime,"$runtime/python","$runtime/collector_host_exec.py")
foreach ($record in $runtimeRecords) {
    if (@($record.PSObject.Properties.Name).Count -ne 3 -or @($record.PSObject.Properties.Name | Where-Object { $_ -cnotin @('name','bytes','sha256') }).Count -or $record.name -isnot [string] -or $record.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or -not $seen.Add($record.name) -or $record.bytes -isnot [int] -or $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Protected runtime record differs.' }
    $path = Join-Path "$runtime/python" $record.name
    Assert-TrustedExecutionPath $path
    $data = Read-RegularBytes $path 32MB $record.sha256
    if ($data.Length -ne $record.bytes) { throw 'Protected runtime size differs.' }
    $executionPaths += $path
}
# Only the already pinned/protected interpreter parses untrusted staging data.
$deployment = Assert-DeploymentManifest (Convert-StrictJson $manifestBytes $python)
# Capture every original execution ACL before the narrow owner RX additions.
$aclBefore = @($executionPaths | ForEach-Object { [ordered]@{path=$_;sddl=(Get-Acl -LiteralPath $_).Sddl} })
New-ProtectedDirectory $upgrade $false
Write-NewBytes "$upgrade/dispatcher.before.py" $oldDispatcher
Write-NewBytes "$upgrade/acl-before.private.json" $encoding.GetBytes(($aclBefore | ConvertTo-Json -Depth 4))
$prepared = [ordered]@{schema_version=1;status='PREPARED';owner_sid=$ownerSid;bridge_sid=$bridgeSid;bundle_sha256=$PinnedManifestSha256;old_dispatcher_sha256=$oldDispatcherHash;dispatcher_sha256=$deployment.dispatcher_sha256;shared_config_sha256=$deployment.shared_config_sha256;publication_paused=$true}
Write-NewBytes "$upgrade/deployment.prepared.private.json" $encoding.GetBytes(($prepared | ConvertTo-Json -Depth 4))
$rollbackText = @'
$ErrorActionPreference = 'Stop'
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$upgrade = "$root/broker-upgrade-v1"
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($current.User.Value -cne '@OWNER@' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Rollback requires the original owner elevated.' }
if (Test-Path -LiteralPath "$upgrade/rollback.completed.private.json") { throw 'Rollback already recorded; do not repeat.' }
$task = Get-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName NarratorControl -ErrorAction Stop
if ($task.State -notin @('Ready','Disabled')) { throw 'Owner broker is running, queued or unverified; no task or audio was stopped.' }
if ($task.Principal.UserId -cne '@OWNER@' -or @($task.Actions).Count -ne 1 -or $task.Actions[0].Execute -cne "$root/runtime/python/python.exe" -or $task.Actions[0].Arguments -cne "-I -S -B $root/runtime/narrator-control-launch.py") { throw 'Task identity/action drift; no rollback.' }
if ((Get-FileHash -LiteralPath "$root/runtime/collector_host_exec.py" -Algorithm SHA256).Hash.ToLowerInvariant() -cne '@NEW@' -or (Get-FileHash -LiteralPath "$upgrade/dispatcher.before.py" -Algorithm SHA256).Hash.ToLowerInvariant() -cne '@OLD@') { throw 'Dispatcher/backup drift; no rollback.' }
$before = Get-Content -LiteralPath "$upgrade/acl-before.private.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$after = Get-Content -LiteralPath "$upgrade/acl-after.private.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if ($before -isnot [array] -or $after -isnot [array] -or $before.Count -ne $after.Count) { throw 'ACL receipt mismatch.' }
foreach ($entry in $after) { if ((Get-Acl -LiteralPath $entry.path).Sddl -cne $entry.sddl) { throw 'Execution ACL drift; no rollback.' } }
Disable-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName NarratorControl -ErrorAction Stop | Out-Null
$afterDisable = Get-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName NarratorControl -ErrorAction Stop
if ($afterDisable.State -cne 'Disabled') { throw 'Owner task started or state is unverified after disable; source and ACLs preserved. No task or audio was stopped.' }
$bytes = [IO.File]::ReadAllBytes("$upgrade/dispatcher.before.py")
$temp = "$root/runtime/collector_host_exec.rollback"
$stream = [IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
[IO.File]::Replace($temp,"$root/runtime/collector_host_exec.py",$null)
foreach ($entry in $before) { $acl = Get-Acl -LiteralPath $entry.path; $acl.SetSecurityDescriptorSddlForm($entry.sddl); Set-Acl -LiteralPath $entry.path -AclObject $acl }
if ((Get-FileHash -LiteralPath "$root/runtime/collector_host_exec.py" -Algorithm SHA256).Hash.ToLowerInvariant() -cne '@OLD@') { throw 'Restored source did not verify.' }
$receipt = '{"status":"SOURCE_ROLLBACK_PASS","task_disabled":true,"audio_stopped":false,"files_deleted":false}'
$stream = [IO.File]::Open("$upgrade/rollback.completed.private.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $data = [Text.Encoding]::UTF8.GetBytes($receipt); $stream.Write($data,0,$data.Length); $stream.Flush($true) } finally { $stream.Dispose() }
$receipt
'@
$rollbackText = $rollbackText.Replace('@OWNER@',$ownerSid).Replace('@NEW@',$deployment.dispatcher_sha256).Replace('@OLD@',$oldDispatcherHash)
Write-NewBytes "$upgrade/rollback-source.ps1" $encoding.GetBytes($rollbackText)
foreach ($path in $executionPaths) {
    $acl = Get-Acl -LiteralPath $path
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'ReadAndExecute','Allow'))
    Set-Acl -LiteralPath $path -AclObject $acl
    Assert-TrustedExecutionPath $path
}
New-ProtectedDirectory $package $true
foreach ($name in $files) { Write-NewBytes (Join-Path $package $name) $sources[$name]; Assert-TrustedExecutionPath (Join-Path $package $name) }
$launcher = "$runtime/narrator-control-launch.py"
Write-NewBytes $launcher $sources['narrator-control-launch.py']
$launcherAcl = Get-Acl -LiteralPath $launcher
$launcherAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'ReadAndExecute','Allow'))
Set-Acl -LiteralPath $launcher -AclObject $launcherAcl
$brokerConfig = [ordered]@{schema_version=1;owner_sid=$ownerSid;bridge_sid=$bridgeSid;server_python_sha256=$deployment.server_python_sha256;manifest_sha256=$deployment.manifest_sha256;files=$deployment.files}
Write-NewBytes "$root/narrator-broker.json" $encoding.GetBytes(($brokerConfig | ConvertTo-Json -Depth 5))
$brokerAcl = Get-Acl -LiteralPath "$root/narrator-broker.json"
$brokerAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'ReadAndExecute','Allow'))
Set-Acl -LiteralPath "$root/narrator-broker.json" -AclObject $brokerAcl
Write-NewBytes "$runtime/collector_host_exec.next" $sources['collector_host_exec.py']
Assert-TrustedExecutionPath "$runtime/collector_host_exec.next"
$null = Read-RegularBytes "$runtime/collector_host_exec.py" 128KB $oldDispatcherHash
[IO.File]::Replace("$runtime/collector_host_exec.next","$runtime/collector_host_exec.py",$null)
foreach ($path in @($launcher,"$root/narrator-broker.json","$runtime/collector_host_exec.py")) { Assert-TrustedExecutionPath $path }
$null = Read-RegularBytes "$runtime/collector_host_exec.py" 128KB $deployment.dispatcher_sha256
$taskArguments = "-I -S -B $launcher"
$action = New-ScheduledTaskAction -Execute $python -Argument $taskArguments -WorkingDirectory $runtime
$principal = New-ScheduledTaskPrincipal -UserId $ownerSid -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DisallowHardTerminate
$task = New-ScheduledTask -Action $action -Principal $principal -Settings $settings
$taskSddl = "O:${ownerSid}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${ownerSid})"
if ($null -eq $taskFolder) { $taskFolder = $scheduler.GetFolder('\').CreateFolder('KnowledgeNetworkCollector',$taskSddl) }
Assert-TaskSecurity ($taskFolder.GetSecurityDescriptor(7)) $ownerSid
Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -InputObject $task -ErrorAction Stop | Out-Null
$registered = $taskFolder.GetTask($taskName)
$registered.SetSecurityDescriptor($taskSddl,16) # TASK_DONT_ADD_PRINCIPAL_ACE preserves the explicit protected DACL.
Assert-TaskSecurity ($registered.GetSecurityDescriptor(7)) $ownerSid
$taskXml = Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
$effectivePrincipal = (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop).Principal
Assert-TaskXml $taskXml $ownerSid $python $taskArguments $runtime ($effectivePrincipal.RunLevel.ToString())
Write-NewBytes "$upgrade/task.private.xml" $encoding.GetBytes($taskXml)
$aclAfter = @($executionPaths | ForEach-Object { [ordered]@{path=$_;sddl=(Get-Acl -LiteralPath $_).Sddl} })
Write-NewBytes "$upgrade/acl-after.private.json" $encoding.GetBytes(($aclAfter | ConvertTo-Json -Depth 4))
if ((Get-FileHash -LiteralPath $sharedConfig -Algorithm SHA256).Hash.ToLowerInvariant() -cne $deployment.shared_config_sha256) { throw 'Shared SSH configuration changed during deployment; no restoration attempted.' }
Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
$completed = [ordered]@{schema_version=1;status='TASK_START_REQUESTED';owner_sid=$ownerSid;bridge_sid=$bridgeSid;task='\KnowledgeNetworkCollector\NarratorControl';task_logon='InteractiveToken';task_runlevel='LeastPrivilege';dispatcher_sha256=$deployment.dispatcher_sha256;manifest_sha256=$deployment.manifest_sha256;no_narration_submitted=$true;no_serve_change=$true;publication_paused=$true}
Write-NewBytes "$upgrade/deployment.completed.private.json" $encoding.GetBytes(($completed | ConvertTo-Json -Depth 4))
Write-Output ($completed | ConvertTo-Json -Depth 4)
