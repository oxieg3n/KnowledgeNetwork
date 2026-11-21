[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BootstrapFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BootstrapSha256,
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
$launcher = "$runtime/narrator-control-launch.py"
$taskPath = '\KnowledgeNetworkCollector\'
$taskName = 'NarratorControl'
$sharedConfig = 'C:/ProgramData/ssh/sshd_config'
$oldDispatcherHash = '637c92f13126c2ccb5a2eeb888cc4ac48a8a540cf74652f96dc268ce12600bf2'
$oldRollbackHash = '21355e95e7a8969f6a6f7975f9fd006e3da174b5806c63c5b1756bb44c3f74de'
$files = @('__init__.py','collector_narrator_pipe.py','collector_narrator_control.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
$encoding = [Text.UTF8Encoding]::new($false,$true)

function Assert-ResumeBootstrapPath([string]$Path) {
    $expected = 'D:\projects\knowledgenetwork\collector-narrator-v9-004\narrator-control-resume-v1\Install-KnowledgeNetworkNarratorControl.ps1'
    if ($Path -notmatch '^[A-Za-z]:[/\\]' -or $Path -match '(^|[/\\])\.\.([/\\]|$)' -or [IO.Path]::GetFullPath($Path) -ine $expected) { throw 'Only the fixed local corrected bootstrap path is accepted.' }
    return $expected
}
function Assert-ResumeReceipt([object]$Value,[object]$Deployment,[string]$OwnerSid,[string]$BridgeSid,[string]$BundleHash) {
    $keys = @('schema_version','status','owner_sid','bridge_sid','bundle_sha256','old_dispatcher_sha256','dispatcher_sha256','shared_config_sha256','publication_paused')
    if ($null -eq $Value -or $Value -is [array] -or @($Value.PSObject.Properties.Name).Count -ne $keys.Count -or @($Value.PSObject.Properties.Name | Where-Object { $_ -cnotin $keys }).Count) { throw 'Prepared receipt fields differ.' }
    foreach ($key in @('status','owner_sid','bridge_sid','bundle_sha256','old_dispatcher_sha256','dispatcher_sha256','shared_config_sha256')) { if ($Value.$key -isnot [string]) { throw 'Prepared receipt requires scalar strings.' } }
    if ($Value.schema_version -isnot [int] -or $Value.schema_version -ne 1 -or $Value.status -cne 'PREPARED' -or $Value.owner_sid -cne $OwnerSid -or $Value.bridge_sid -cne $BridgeSid -or $Value.bundle_sha256 -cne $BundleHash -or $Value.old_dispatcher_sha256 -cne $Deployment.old_dispatcher_sha256 -or $Value.dispatcher_sha256 -cne $Deployment.dispatcher_sha256 -or $Value.shared_config_sha256 -cne $Deployment.shared_config_sha256 -or $Value.publication_paused -isnot [bool] -or $Value.publication_paused -ne $true) { throw 'Prepared receipt is not the exact pre-replacement state.' }
}
function Assert-ResumeLayout([string]$Runtime,[string]$Upgrade) {
    $runtimeNames = @('python','youtube_ops','collector_host_exec.py','collector_host_exec.next','narrator-control-launch.py')
    $members = @(Get-ChildItem -LiteralPath $Runtime -Force -ErrorAction Stop)
    if ($members.Count -ne $runtimeNames.Count) { throw 'Prepared runtime count differs; preserve all files.' }
    foreach ($item in $members) {
        if ($item.Name -cnotin $runtimeNames -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.PSIsContainer -ne ($item.Name -cin @('python','youtube_ops'))) { throw 'Prepared runtime shape differs.' }
    }
    $upgradeNames = @('acl-before.private.json','deployment.prepared.private.json','dispatcher.before.py','rollback-source.ps1')
    $members = @(Get-ChildItem -LiteralPath $Upgrade -Force -ErrorAction Stop)
    if ($members.Count -ne $upgradeNames.Count -or @($members | Where-Object { $_.Name -cnotin $upgradeNames -or $_.PSIsContainer -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count) { throw 'Upgrade state advanced or differs; no retry.' }
}
function Assert-PreparedAcls([object]$Recorded,[string[]]$Expected,[string]$OwnerReadSid) {
    if ($Recorded -isnot [array] -or $Recorded.Count -ne 41 -or $Expected.Count -ne 41) { throw 'Prepared ACL receipt count differs.' }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $Recorded) {
        if (@($entry.PSObject.Properties.Name).Count -ne 2 -or @($entry.PSObject.Properties.Name | Where-Object { $_ -cnotin @('path','sddl') }).Count -or $entry.path -isnot [string] -or $entry.sddl -isnot [string] -or $entry.path.StartsWith('\\') -or $entry.path -match '(^|[/\\])\.\.([/\\]|$)') { throw 'Prepared ACL record schema differs.' }
        $path = [IO.Path]::GetFullPath($entry.path)
        $matches = @($Expected | Where-Object { [IO.Path]::GetFullPath($_) -ieq $path })
        if ($matches.Count -ne 1 -or -not $seen.Add($path)) { throw 'Prepared ACL path differs or repeats.' }
    }
    foreach ($entry in $Recorded) {
        Assert-TrustedExecutionPath $entry.path
        $item = Get-Item -LiteralPath $entry.path -Force -ErrorAction Stop
        $expectedAcl = if ($item.PSIsContainer) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
        $expectedAcl.SetSecurityDescriptorSddlForm($entry.sddl)
        $raw = [Security.AccessControl.RawSecurityDescriptor]::new($expectedAcl.GetSecurityDescriptorBinaryForm(),0)
        if ($null -eq $raw.DiscretionaryAcl) { throw 'Original ACL receipt has a null DACL.' }
        $expectedAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($OwnerReadSid),'ReadAndExecute','Allow'))
        if ((Get-Acl -LiteralPath $entry.path).Sddl -cne $expectedAcl.Sddl) { throw 'Prepared execution ACL drift; no permissions rewritten.' }
    }
}
function Assert-BrokerConfiguration([object]$Config,[object]$Deployment,[string]$OwnerSid,[string]$BridgeSid) {
    $keys = @('schema_version','owner_sid','bridge_sid','server_python_sha256','manifest_sha256','files')
    if ($null -eq $Config -or $Config -is [array] -or @($Config.PSObject.Properties.Name).Count -ne 6 -or @($Config.PSObject.Properties.Name | Where-Object { $_ -cnotin $keys }).Count -or $Config.schema_version -isnot [int] -or $Config.schema_version -ne 1 -or $Config.owner_sid -cne $OwnerSid -or $Config.bridge_sid -cne $BridgeSid -or $Config.server_python_sha256 -cne $Deployment.server_python_sha256 -or $Config.manifest_sha256 -cne $Deployment.manifest_sha256) { throw 'Prepared broker configuration differs.' }
    foreach ($key in @('owner_sid','bridge_sid','server_python_sha256','manifest_sha256')) { if ($Config.$key -isnot [string]) { throw 'Broker configuration requires scalar strings.' } }
    $names = @($Deployment.files.PSObject.Properties.Name)
    if ($null -eq $Config.files -or $Config.files -is [array] -or @($Config.files.PSObject.Properties.Name).Count -ne $names.Count -or @($Config.files.PSObject.Properties.Name | Where-Object { $_ -cnotin $names }).Count) { throw 'Prepared broker package fields differ.' }
    foreach ($name in $names) { if ($Config.files.$name -isnot [string] -or $Config.files.$name -cne $Deployment.files.$name) { throw 'Prepared broker package digest differs.' } }
}

$current = [Security.Principal.WindowsIdentity]::GetCurrent()
$ownerSid = $current.User.Value
if ($ownerSid -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Checked continuation requires the intended owner elevated, never SYSTEM.' }
if ($BootstrapSha256 -cne 'ab682e594409f35f4650f1418a8541fe8d63b8e6e4b5981bfbe8c85ef702610c') { throw 'Corrected reviewed bootstrap revision required.' }
if ([IO.Path]::GetFullPath($BundleDirectory) -ine [IO.Path]::GetFullPath("$kit/narrator-control-deploy-v1")) { throw 'Only the original reviewed staging bundle is accepted.' }
$BundleDirectory = [IO.Path]::GetFullPath($BundleDirectory)
$BootstrapFile = Assert-ResumeBootstrapPath $BootstrapFile
if ([IO.DriveInfo]::new('D:\').DriveType -ne [IO.DriveType]::Fixed) { throw 'Bootstrap drive is not fixed local storage.' }
# Capture approved bootstrap bytes before compiling only its named helpers.
$sourceItem = Get-Item -LiteralPath $BootstrapFile -Force -ErrorAction Stop
if ($sourceItem.PSIsContainer -or ($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Regular corrected bootstrap source required.' }
$stream = [IO.File]::Open($sourceItem.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try {
    if ($stream.Length -le 0 -or $stream.Length -gt 128KB) { throw 'Corrected bootstrap exceeds bounds.' }
    $memory = [IO.MemoryStream]::new()
    try { $stream.CopyTo($memory); $sourceBytes = $memory.ToArray() } finally { $memory.Dispose() }
} finally { $stream.Dispose() }
$hasher = [Security.Cryptography.SHA256]::Create()
try { $sourceHash = ([BitConverter]::ToString($hasher.ComputeHash($sourceBytes))).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
if ($sourceHash -cne $BootstrapSha256) { throw 'Corrected bootstrap source pin mismatch.' }
$bootstrapText = $encoding.GetString($sourceBytes)
$tokens = $null; $parseErrors = $null
$tree = [Management.Automation.Language.Parser]::ParseInput($bootstrapText,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'Corrected bootstrap source syntax differs.' }
foreach ($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes','Assert-TrustedExecutionPath','Assert-DeploymentManifest','Convert-StrictJson','Write-NewBytes','Assert-TaskXml','Assert-TaskSecurity')) {
    $functions = @($tree.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -ceq $name)
    if ($functions.Count -ne 1) { throw 'Corrected bootstrap helper contract differs.' }
    . ([ScriptBlock]::Create($functions[0].Extent.Text))
}
Initialize-FileIdentity
$null = Read-RegularBytes $BootstrapFile 128KB $BootstrapSha256
foreach ($path in @($root,$runtime,"$runtime/python",$package,$upgrade,$python,"$root/config.json","$root/runtime-files.private.json","$runtime/collector_host_exec.py","$runtime/collector_host_exec.next",$launcher,"$root/narrator-broker.json",$sharedConfig)) { Assert-TrustedExecutionPath $path }
Assert-ResumeLayout $runtime $upgrade
if (@(Get-ScheduledTask -ErrorAction Stop | Where-Object { $_.TaskPath -ieq $taskPath -and $_.TaskName -ieq $taskName }).Count) { throw 'Broker task already exists; no checked continuation.' }
$scheduler = New-Object -ComObject 'Schedule.Service'; $scheduler.Connect()
$taskFolder = $null
try { $taskFolder = $scheduler.GetFolder('\KnowledgeNetworkCollector') } catch { if ($_.Exception.HResult -ne -2147024894) { throw 'Task folder query failed.' } }
if ($null -ne $taskFolder) { Assert-TaskSecurity ($taskFolder.GetSecurityDescriptor(7)) $ownerSid }
$manifestBytes = Read-RegularBytes (Join-Path $BundleDirectory 'narrator-control-deployment.json') 64KB $PinnedManifestSha256
$deployment = Assert-DeploymentManifest ($encoding.GetString($manifestBytes) | ConvertFrom-Json)
$expectedNames = @($files + @('collector_host_exec.py','narrator-control-launch.py','narrator-control-deployment.json'))
$members = @(Get-ChildItem -LiteralPath $BundleDirectory -Force -ErrorAction Stop)
if ($members.Count -ne $expectedNames.Count -or @($members | Where-Object { $_.PSIsContainer -or $_.Name -cnotin $expectedNames }).Count) { throw 'Original bundle shape differs.' }
foreach ($name in $files) {
    $null = Read-RegularBytes (Join-Path $BundleDirectory $name) 128KB $deployment.files.$name
    Assert-TrustedExecutionPath (Join-Path $package $name)
    $null = Read-RegularBytes (Join-Path $package $name) 128KB $deployment.files.$name
}
if (@(Get-ChildItem -LiteralPath $package -Force).Count -ne $files.Count) { throw 'Installed package has extra entries.' }
$null = Read-RegularBytes (Join-Path $BundleDirectory 'collector_host_exec.py') 128KB $deployment.dispatcher_sha256
$null = Read-RegularBytes (Join-Path $BundleDirectory 'narrator-control-launch.py') 4096 $deployment.launcher_sha256
$null = Read-RegularBytes $launcher 4096 $deployment.launcher_sha256
$null = Read-RegularBytes "$runtime/collector_host_exec.py" 128KB $oldDispatcherHash
$null = Read-RegularBytes "$runtime/collector_host_exec.next" 128KB $deployment.dispatcher_sha256
$null = Read-RegularBytes "$upgrade/dispatcher.before.py" 128KB $oldDispatcherHash
$null = Read-RegularBytes "$upgrade/rollback-source.ps1" 128KB $oldRollbackHash
$configBytes = Read-RegularBytes "$root/config.json" 64KB $null
$config = $encoding.GetString($configBytes) | ConvertFrom-Json
$configKeys = @('schema_version','execution_sid','forge_address','python_sha256','powershell_sha256')
if (@($config.PSObject.Properties.Name).Count -ne 5 -or @($config.PSObject.Properties.Name | Where-Object { $_ -cnotin $configKeys }).Count -or $config.schema_version -isnot [int] -or $config.schema_version -ne 1 -or $config.execution_sid -isnot [string] -or $config.execution_sid -cnotmatch '^S-1-5-21-(?:\d+-){3}\d+$' -or $config.python_sha256 -cne $deployment.server_python_sha256) { throw 'Existing execution configuration differs.' }
$bridgeSid = $config.execution_sid
if ($bridgeSid -ceq $ownerSid) { throw 'Owner and bridge identity must differ.' }
$bridge = @(Get-LocalUser -ErrorAction Stop | Where-Object { $_.Name -ceq 'kncollector_exec' -and $_.SID.Value -ceq $bridgeSid })
if ($bridge.Count -ne 1 -or -not $bridge[0].Enabled -or @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop | Where-Object { $_.SID.Value -ceq $bridgeSid }).Count) { throw 'Existing bridge account or nonadmin membership differs.' }
$runtimeBytes = Read-RegularBytes "$root/runtime-files.private.json" 64KB $null
$runtimeRecords = $encoding.GetString($runtimeBytes) | ConvertFrom-Json
if ($runtimeRecords -isnot [array] -or $runtimeRecords.Count -ne 37 -or @(Get-ChildItem -LiteralPath "$runtime/python" -Force).Count -ne 37) { throw 'Existing protected interpreter inventory differs.' }
$executionPaths = @($root,$runtime,"$runtime/python","$runtime/collector_host_exec.py")
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($record in $runtimeRecords) {
    if (@($record.PSObject.Properties.Name).Count -ne 3 -or @($record.PSObject.Properties.Name | Where-Object { $_ -cnotin @('name','bytes','sha256') }).Count -or $record.name -isnot [string] -or $record.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or -not $seen.Add($record.name) -or $record.bytes -isnot [int] -or $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Protected interpreter record differs.' }
    $path = Join-Path "$runtime/python" $record.name
    Assert-TrustedExecutionPath $path
    $bytes = Read-RegularBytes $path 32MB $record.sha256
    if ($bytes.Length -ne $record.bytes) { throw 'Protected interpreter member size differs.' }
    $executionPaths += $path
}
$null = Read-RegularBytes $python 32MB $deployment.server_python_sha256
$deployment = Assert-DeploymentManifest (Convert-StrictJson $manifestBytes $python)
$config = Convert-StrictJson $configBytes $python
$receiptBytes = Read-RegularBytes "$upgrade/deployment.prepared.private.json" 64KB $null
$receipt = Convert-StrictJson $receiptBytes $python
Assert-ResumeReceipt $receipt $deployment $ownerSid $bridgeSid $PinnedManifestSha256
$brokerBytes = Read-RegularBytes "$root/narrator-broker.json" 64KB $null
Assert-BrokerConfiguration (Convert-StrictJson $brokerBytes $python) $deployment $ownerSid $bridgeSid
$aclBytes = Read-RegularBytes "$upgrade/acl-before.private.json" 128KB $null
$aclBefore = Convert-StrictJson $aclBytes $python
Assert-PreparedAcls $aclBefore $executionPaths $ownerSid
$spoolItem = Get-Item -LiteralPath $spool -Force -ErrorAction Stop
if (-not $spoolItem.PSIsContainer -or ($spoolItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Existing private spool differs.' }
$spoolAcl = Get-Acl -LiteralPath $spool -ErrorAction Stop
$raw = [Security.AccessControl.RawSecurityDescriptor]::new($spoolAcl.GetSecurityDescriptorBinaryForm(),0)
$allowed = @($ownerSid,'S-1-5-18','S-1-5-32-544')
if ($null -eq $raw.DiscretionaryAcl -or -not $spoolAcl.AreAccessRulesProtected -or $spoolAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed) { throw 'Existing private spool DACL/owner differs.' }
$ownerFull = $false
foreach ($ace in $spoolAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
    if ($ace.AccessControlType -ne 'Allow' -or $ace.IdentityReference.Value -notin $allowed) { throw 'Existing private spool grants another identity.' }
    if ($ace.IdentityReference.Value -ceq $ownerSid -and -not $ace.IsInherited -and ($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -eq 0 -and ($ace.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -eq [Security.AccessControl.FileSystemRights]::FullControl) { $ownerFull = $true }
}
if (-not $ownerFull) { throw 'Intended owner lacks explicit existing private spool control.' }
$null = Read-RegularBytes "$spool/review/narrator-manifest.LOCAL-USE-CANDIDATE.private.json" 1MB $deployment.manifest_sha256
$null = Read-RegularBytes $sharedConfig 128KB $deployment.shared_config_sha256
# Derive both rollback revisions from the captured corrected source, never run the old one.
$literals = @($tree.FindAll({param($node) $node -is [Management.Automation.Language.StringConstantExpressionAst] -and $node.Value.StartsWith('$ErrorActionPreference') -and $node.Value.Contains('@OWNER@')},$true))
if ($literals.Count -ne 1) { throw 'Corrected rollback template boundary differs.' }
$fixedCall = '[IO.File]::Replace($temp,"$root/runtime/collector_host_exec.py",[System.Management.Automation.Language.NullString]::Value)'
$oldCall = '[IO.File]::Replace($temp,"$root/runtime/collector_host_exec.py",$null)'
if (($literals[0].Value.Split(@($fixedCall),[StringSplitOptions]::None)).Count -ne 2) { throw 'Expected exactly one corrected rollback call.' }
$newRollback = $literals[0].Value.Replace('@OWNER@',$ownerSid).Replace('@NEW@',$deployment.dispatcher_sha256).Replace('@OLD@',$oldDispatcherHash)
$derivedOld = $newRollback.Replace($fixedCall,$oldCall)
if ((Get-BytesHash $encoding.GetBytes($derivedOld)) -cne $oldRollbackHash) { throw 'Original rollback does not match the exact derived pre-replacement artifact.' }
$tailNodes = @($tree.FindAll({param($node) $node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -ceq '$taskArguments'},$true))
if ($tailNodes.Count -ne 1) { throw 'Reviewed task-registration tail boundary differs.' }
$tail = $bootstrapText.Substring($tailNodes[0].Extent.StartOffset)
# Every gate above is read-only. Preserve the original failed artifacts.
Write-NewBytes "$upgrade/rollback-source-v2.ps1" $encoding.GetBytes($newRollback)
$prepared = [ordered]@{schema_version=1;status='CHECKED_PRE_REPLACEMENT_RESUME';bootstrap_sha256=$BootstrapSha256;bundle_sha256=$PinnedManifestSha256;old_dispatcher_sha256=$oldDispatcherHash;dispatcher_sha256=$deployment.dispatcher_sha256;old_rollback_sha256=$oldRollbackHash;publication_paused=$true}
Write-NewBytes "$upgrade/resume.prepared.private.json" $encoding.GetBytes(($prepared | ConvertTo-Json -Depth 4))
$dispatcherAcl = (Get-Acl -LiteralPath "$runtime/collector_host_exec.py").Sddl
[IO.File]::Replace("$runtime/collector_host_exec.next","$runtime/collector_host_exec.py",[System.Management.Automation.Language.NullString]::Value)
$null = Read-RegularBytes "$runtime/collector_host_exec.py" 128KB $deployment.dispatcher_sha256
$null = Read-RegularBytes "$upgrade/dispatcher.before.py" 128KB $oldDispatcherHash
if (Test-Path -LiteralPath "$runtime/collector_host_exec.next") { throw 'Replacement temporary file remains; preserve state.' }
if ((Get-Acl -LiteralPath "$runtime/collector_host_exec.py").Sddl -cne $dispatcherAcl) { throw 'Dispatcher ACL changed during replacement; preserve state.' }
. ([ScriptBlock]::Create($tail))
