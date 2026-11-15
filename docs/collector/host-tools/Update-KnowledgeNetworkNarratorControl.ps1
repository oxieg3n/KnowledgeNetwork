[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PinnedManifestSha256,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PinnedStopHelperSha256
)
$ErrorActionPreference='Stop'
$root='C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$kit='D:/projects/knowledgenetwork/collector-narrator-v9-004'
$runtime="$root/runtime"; $python="$runtime/python/python.exe"; $package="$runtime/youtube_ops"
$launcher="$runtime/narrator-control-launch.py"; $sharedConfig='C:/ProgramData/ssh/sshd_config'
$upgrade="$root/broker-update-v1"; $taskPath='\KnowledgeNetworkCollector\'; $taskName='NarratorControl'
$oldDispatcherHash='86b94ada8cc7097fee5b8d0a095826bfb4932526d8a2ab5ea4da7b70ee68c3ef'
$oldConfigHash='2b38f28bc5772c069cf8a15c54b4f9ef3ac53b585e10ed572cdbed03f778304d'
$fixedManifestHash='42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84'
$files=@('__init__.py','collector_narrator_pipe.py','collector_narrator_control.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
$encoding=[Text.UTF8Encoding]::new($false,$true)

function Assert-DiagnosticTaskState([object]$Task) {
 if ($Task.State.ToString() -cnotin @('Ready','Disabled','Running')) {throw 'Broker task must be Ready, Disabled or Running; nothing stopped.'}
 return $Task.State.ToString()
}
function Assert-InactiveRepairTask([object]$Task) {
 if ($Task.State.ToString() -cnotin @('Ready','Disabled')) {throw 'Repair/rollback requires inactive Ready or Disabled task; no force stop.'}
 return $Task.State.ToString()
}
function Assert-DisabledIdleTask([object]$Task,[int]$Instances) {
 if($Task.State.ToString() -cne 'Disabled' -or $Instances -ne 0){throw 'Disabled task with zero instances required before execution-file replacement.'}
}
function Assert-OnlyTaskEnabledChanged([string]$Before,[string]$After) {
 $normalized=@()
 foreach($text in @($Before,$After)){
  $xml=[Xml.XmlDocument]::new();$xml.XmlResolver=$null;$xml.LoadXml($text)
  $ns=[Xml.XmlNamespaceManager]::new($xml.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
  $settings=@($xml.SelectNodes('/t:Task/t:Settings',$ns));$enabled=@($xml.SelectNodes('/t:Task/t:Settings/t:Enabled',$ns))
  if($settings.Count -ne 1 -or $enabled.Count -gt 1){throw 'Task settings shape differs.'}
  if($enabled.Count){if($enabled[0].InnerText -cnotin @('true','false')){throw 'Task Enabled value differs.'};$null=$settings[0].RemoveChild($enabled[0])}
  $normalized+=,$xml.OuterXml
 }
 if($normalized[0] -cne $normalized[1]){throw 'Task definition changed beyond Enabled; no repair.'}
}
function Add-TaskBridgeRead([string]$Sddl,[string]$Owner,[string]$Bridge) {
 Assert-TaskSecurity $Sddl $Owner
 $descriptor=[Security.AccessControl.RawSecurityDescriptor]::new($Sddl)
 $ace=[Security.AccessControl.CommonAce]::new([Security.AccessControl.AceFlags]::None,[Security.AccessControl.AceQualifier]::AccessAllowed,0x1200a9,[Security.Principal.SecurityIdentifier]::new($Bridge),$false,$null)
 $descriptor.DiscretionaryAcl.InsertAce($descriptor.DiscretionaryAcl.Count,$ace)
 return $descriptor.GetSddlForm([Security.AccessControl.AccessControlSections]::All)
}
function Assert-UpdateFileState([object]$Entry,[string]$ActualHash,[string]$ActualSddl) {
 if ($ActualHash -cne $Entry.old_sha256 -and $ActualHash -cne $Entry.new_sha256) {throw 'Updated file drift; no rollback.'}
 if ($ActualSddl -cne $Entry.sddl) {throw 'Updated file ACL drift; no rollback.'}
}
function New-ChangedEntry([string]$Path,[string]$Backup,[string]$OldHash,[string]$NewHash,[string]$Sddl) {
 if($OldHash -ceq $NewHash){return $null}
 return [ordered]@{path=$Path;backup=$Backup;old_sha256=$OldHash;new_sha256=$NewHash;sddl=$Sddl}
}
function Set-NewReplacementSecurity([string]$Temporary,[object]$Entry) {
 $actual=[IO.Path]::GetFullPath($Temporary)
 if($actual -ine [IO.Path]::GetFullPath($Entry.path+'.update-next') -and $actual -ine [IO.Path]::GetFullPath($Entry.path+'.rollback-next')){throw 'Only the new replacement temporary may receive recorded security.'}
 $null=Read-RegularBytes $Temporary 256KB $null
 if((Get-Acl -LiteralPath $Entry.path).Sddl -cne $Entry.sddl){throw 'Existing target security changed; no replacement.'}
 # ReplaceFile does not retain owner/group reliably. Stamp only the new file.
 $security=[Security.AccessControl.FileSecurity]::new()
 $security.SetSecurityDescriptorSddlForm($Entry.sddl)
 Set-Acl -LiteralPath $Temporary -AclObject $security -ErrorAction Stop
 if((Get-Acl -LiteralPath $Temporary).Sddl -cne $Entry.sddl -or (Get-Acl -LiteralPath $Entry.path).Sddl -cne $Entry.sddl){throw 'Replacement security differs; existing target was not rewritten.'}
}
function Invoke-CheckedRollback {
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 if ($identity.User.Value -cne $ownerSid -or -not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'Original owner elevated required.'}
 Assert-TrustedExecutionPath $upgrade
 $state=[Text.UTF8Encoding]::new($false,$true).GetString((Read-RegularBytes "$upgrade/update-intent.private.json" 128KB $null)) | ConvertFrom-Json
 if ($state.owner_sid -cne $ownerSid -or $state.bridge_sid -cne $bridgeSid) {throw 'Rollback identity differs.'}
 foreach($record in $state.runtime_records){
  $path=Join-Path "$runtime/python" $record.name;Assert-TrustedExecutionPath $path
  if((Read-RegularBytes $path 32MB $record.sha256).Length -ne $record.bytes){throw 'Protected runtime drift; no rollback.'}
 }
 $task=Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
 $null=Assert-InactiveRepairTask $task
 $service=New-Object -ComObject 'Schedule.Service';$service.Connect()
 $folder=$service.GetFolder('\KnowledgeNetworkCollector');$registered=$folder.GetTask($taskName)
 if ($folder.GetTasks(1).Count -ne 1) {throw 'Task folder membership differs.'}
 $currentFolder=$folder.GetSecurityDescriptor(7);$currentTask=$registered.GetSecurityDescriptor(7)
 if (($currentFolder -cne $state.folder_before -and $currentFolder -cne $state.folder_after) -or ($currentTask -cne $state.task_before -and $currentTask -cne $state.task_after)) {throw 'Task security drift; no rollback.'}
 if ((Get-BytesHash (Read-RegularBytes $sharedConfig 128KB $state.shared_config_sha256)) -cne $state.shared_config_sha256) {throw 'Shared configuration drift; no rollback.'}
 foreach($entry in $state.entries) {
  Assert-TrustedExecutionPath $entry.path
  Assert-UpdateFileState $entry (Get-BytesHash (Read-RegularBytes $entry.path 256KB $null)) ((Get-Acl -LiteralPath $entry.path).Sddl)
  $null=Read-RegularBytes (Join-Path $upgrade $entry.backup) 256KB $entry.old_sha256
 }
 Assert-OnlyTaskEnabledChanged $state.task_xml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
 $null=Assert-InactiveRepairTask (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
 Disable-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop | Out-Null
 Assert-DisabledIdleTask (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop) ($registered.GetInstances(0).Count)
 Assert-OnlyTaskEnabledChanged $state.task_xml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
 foreach($entry in $state.entries) {
  $bytes=Read-RegularBytes (Join-Path $upgrade $entry.backup) 256KB $entry.old_sha256
  $temporary=$entry.path+'.rollback-next'
  Write-NewBytes $temporary $bytes
  Assert-UpdateFileState $entry (Get-BytesHash (Read-RegularBytes $entry.path 256KB $null)) ((Get-Acl -LiteralPath $entry.path).Sddl)
  Set-NewReplacementSecurity $temporary $entry
  [IO.File]::Replace($temporary,$entry.path,[System.Management.Automation.Language.NullString]::Value)
  if ((Get-BytesHash (Read-RegularBytes $entry.path 256KB $entry.old_sha256)) -cne $entry.old_sha256 -or (Get-Acl -LiteralPath $entry.path).Sddl -cne $entry.sddl) {throw 'Rollback verification failed; preserve evidence.'}
 }
 $registered.SetSecurityDescriptor($state.task_before,16)
 $folder.SetSecurityDescriptor($state.folder_before,0)
 if ($registered.GetSecurityDescriptor(7) -cne $state.task_before -or $folder.GetSecurityDescriptor(7) -cne $state.folder_before) {throw 'Rollback task security readback differs.'}
 if($state.task_state -cne 'Disabled'){Enable-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop | Out-Null}
 Assert-OnlyTaskEnabledChanged $state.task_xml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
 Write-Output '{"status":"PASS_INACTIVE_REPAIR_ROLLBACK","task_started":false,"publication_paused":true}'
}

$current=[Security.Principal.WindowsIdentity]::GetCurrent();$ownerSid=$current.User.Value
if ($ownerSid -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'Intended owner elevated, never SYSTEM required.'}
$bootstrap="$kit/narrator-control-resume-v1/Install-KnowledgeNetworkNarratorControl.ps1"
if ([IO.DriveInfo]::new('D:\').DriveType -ne [IO.DriveType]::Fixed) {throw 'Fixed local staging drive required.'}
$item=Get-Item -LiteralPath $bootstrap -Force -ErrorAction Stop
$ancestor=$item
while($null -ne $ancestor){
 if(($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path denied.'}
 $ancestor=if($ancestor -is [IO.DirectoryInfo]){$ancestor.Parent}else{$ancestor.Directory}
}
if($item.PSIsContainer -or $item.Length -gt 128KB){throw 'Regular bounded bootstrap source required.'}
$source=[IO.File]::ReadAllBytes($bootstrap)
$hasher=[Security.Cryptography.SHA256]::Create()
try {$hash=([BitConverter]::ToString($hasher.ComputeHash($source))).Replace('-','').ToLowerInvariant()}finally{$hasher.Dispose()}
if($hash -cne 'ab682e594409f35f4650f1418a8541fe8d63b8e6e4b5981bfbe8c85ef702610c'){throw 'Pinned bootstrap differs.'}
$tokens=$null;$errors=$null;$tree=[Management.Automation.Language.Parser]::ParseInput($encoding.GetString($source),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Pinned helper syntax differs.'}
$helperText=''
foreach($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes','Assert-TrustedExecutionPath','Assert-DeploymentManifest','Convert-StrictJson','Write-NewBytes','New-ProtectedDirectory','Assert-TaskXml','Assert-TaskSecurity')){
 $matches=@($tree.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq $name)
 if($matches.Count -ne 1){throw 'Pinned helper contract differs.'}
 $helperText+=$matches[0].Extent.Text+"`n"
 . ([ScriptBlock]::Create($matches[0].Extent.Text))
}
Initialize-FileIdentity
$null=Read-RegularBytes $bootstrap 128KB 'ab682e594409f35f4650f1418a8541fe8d63b8e6e4b5981bfbe8c85ef702610c'
if(Test-Path -LiteralPath $upgrade){throw 'Update evidence already exists; preserve and reconcile.'}
foreach($path in @($root,$runtime,$package,$python,$launcher,"$root/narrator-broker.json","$root/config.json","$root/runtime-files.private.json",$sharedConfig)){Assert-TrustedExecutionPath $path}
$oldConfigBytes=Read-RegularBytes "$root/narrator-broker.json" 64KB $oldConfigHash
$oldConfig=$encoding.GetString($oldConfigBytes) | ConvertFrom-Json
if($oldConfig.owner_sid -cne $ownerSid -or $oldConfig.manifest_sha256 -cne $fixedManifestHash){throw 'Current owner or private manifest differs.'}
$bridgeSid=$oldConfig.bridge_sid
$executionConfig=$encoding.GetString((Read-RegularBytes "$root/config.json" 64KB $null)) | ConvertFrom-Json
if($executionConfig.execution_sid -cne $bridgeSid){throw 'Dedicated bridge identity differs.'}
$null=Read-RegularBytes "$kit/private-service-v9-001/review/narrator-manifest.LOCAL-USE-CANDIDATE.private.json" 1MB $fixedManifestHash
$inventory=$encoding.GetString((Read-RegularBytes "$root/runtime-files.private.json" 64KB $null)) | ConvertFrom-Json
if($inventory -isnot [array] -or $inventory.Count -ne 37 -or @(Get-ChildItem -LiteralPath "$runtime/python" -Force -ErrorAction Stop).Count -ne 37){throw 'Protected runtime inventory differs.'}
$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach($record in $inventory){
 if($record.name -isnot [string] -or $record.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or -not $seen.Add($record.name) -or $record.bytes -isnot [int] -or $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Runtime inventory record differs.'}
 $path=Join-Path "$runtime/python" $record.name;Assert-TrustedExecutionPath $path
 if((Read-RegularBytes $path 32MB $record.sha256).Length -ne $record.bytes){throw 'Runtime inventory bytes differ.'}
}
$null=Read-RegularBytes $python 32MB $oldConfig.server_python_sha256
$packageMembers=@(Get-ChildItem -LiteralPath $package -Force -ErrorAction Stop)
if($packageMembers.Count -ne 6 -or @($packageMembers|Where-Object{$_.PSIsContainer -or $_.Name -cnotin $files}).Count){throw 'Existing package shape differs.'}
$bundle="$kit/narrator-control-update-v1"
$manifestBytes=Read-RegularBytes "$bundle/narrator-control-deployment.json" 64KB $PinnedManifestSha256
$deployment=Assert-DeploymentManifest (Convert-StrictJson $manifestBytes $python)
if($deployment.manifest_sha256 -cne $fixedManifestHash -or $deployment.server_python_sha256 -cne $oldConfig.server_python_sha256){throw 'Update cannot change runtime or narrator identity.'}
$null=Read-RegularBytes $python 32MB $deployment.server_python_sha256
$null=Read-RegularBytes $launcher 4KB $deployment.launcher_sha256
$null=Read-RegularBytes $sharedConfig 128KB $deployment.shared_config_sha256
$names=@($files+@('collector_host_exec.py','narrator-control-launch.py','narrator-control-deployment.json'))
$members=@(Get-ChildItem -LiteralPath $bundle -Force -ErrorAction Stop)
if($members.Count -ne 9 -or @($members|Where-Object{$_.PSIsContainer -or $_.Name -cnotin $names}).Count){throw 'Exact nine-file update bundle required.'}
$entries=@();$newBytes=@{}
foreach($name in $files){
 $path=Join-Path $package $name;Assert-TrustedExecutionPath $path
 $old=Read-RegularBytes $path 128KB $oldConfig.files.$name
 $new=Read-RegularBytes (Join-Path $bundle $name) 128KB $deployment.files.$name
 # Unchanged markers still pass byte gates, but need no rollback or replacement.
 $entry=New-ChangedEntry $path $name (Get-BytesHash $old) (Get-BytesHash $new) ((Get-Acl -LiteralPath $path).Sddl)
 if($null -ne $entry){$entries+=,$entry;$newBytes[$path]=$new}
}
$path="$runtime/collector_host_exec.py";Assert-TrustedExecutionPath $path
$old=Read-RegularBytes $path 128KB $oldDispatcherHash
$new=Read-RegularBytes "$bundle/collector_host_exec.py" 128KB $deployment.dispatcher_sha256
$entry=New-ChangedEntry $path 'dispatcher.before' $oldDispatcherHash $deployment.dispatcher_sha256 ((Get-Acl -LiteralPath $path).Sddl)
if($null -ne $entry){$entries+=,$entry;$newBytes[$path]=$new}
$null=Read-RegularBytes "$bundle/narrator-control-launch.py" 4KB $deployment.launcher_sha256
$newConfig=[ordered]@{schema_version=1;owner_sid=$ownerSid;bridge_sid=$bridgeSid;server_python_sha256=$deployment.server_python_sha256;manifest_sha256=$fixedManifestHash;files=$deployment.files}
$new=$encoding.GetBytes(($newConfig|ConvertTo-Json -Depth 5));$path="$root/narrator-broker.json"
$entry=New-ChangedEntry $path 'broker-config.before' $oldConfigHash (Get-BytesHash $new) ((Get-Acl -LiteralPath $path).Sddl)
if($null -ne $entry){$entries+=,$entry;$newBytes[$path]=$new}
foreach($entry in $entries){foreach($suffix in @('.update-next','.rollback-next')){if(Test-Path -LiteralPath ($entry.path+$suffix)){throw 'Unreconciled temporary update artifact exists.'}}}
$task=Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
$taskState=Assert-DiagnosticTaskState $task
$taskInfo=Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
$taskXml=Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
Assert-TaskXml $taskXml $ownerSid $python "-I -S -B $launcher" $runtime ($task.Principal.RunLevel.ToString())
$scheduler=New-Object -ComObject 'Schedule.Service';$scheduler.Connect();$folder=$scheduler.GetFolder('\KnowledgeNetworkCollector');$registered=$folder.GetTask($taskName)
if($folder.GetTasks(1).Count -ne 1){throw 'Task folder must contain only the dedicated task.'}
$folderBefore=$folder.GetSecurityDescriptor(7);$taskBefore=$registered.GetSecurityDescriptor(7)
$folderAfter=Add-TaskBridgeRead $folderBefore $ownerSid $bridgeSid
$taskAfter=Add-TaskBridgeRead $taskBefore $ownerSid $bridgeSid
$stopHelperBytes=Read-RegularBytes "$kit/narrator-control-update-tools-v1/Stop-EmptyNarratorController.ps1" 128KB $PinnedStopHelperSha256
# Nonconnecting native availability probe; never disturb a running broker.
$pipeProbe = @'
import json,ctypes
from ctypes import wintypes
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.WaitNamedPipeW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD]
kernel.WaitNamedPipeW.restype=wintypes.BOOL
available=bool(kernel.WaitNamedPipeW(r'\\.\pipe\KnowledgeNetworkCollectorNarratorControlV1',1))
print(json.dumps({'available':available,'winerror':0 if available else ctypes.get_last_error(),'connected':False}))
'@
$ownerPipeProbeJson = & $python -I -S -B -c $pipeProbe
if ($LASTEXITCODE -ne 0) {throw 'Native owner pipe diagnostic failed.'}
$ownerPipeProbe = $ownerPipeProbeJson | ConvertFrom-Json
# Durable backup and rollback precede any stop or execution-file replacement.
New-ProtectedDirectory $upgrade $false
foreach($entry in $entries){Write-NewBytes (Join-Path $upgrade $entry.backup) (Read-RegularBytes $entry.path 256KB $entry.old_sha256)}
$intent=[ordered]@{schema_version=1;status='FULL_REPAIR_PREPARED';owner_sid=$ownerSid;bridge_sid=$bridgeSid;bundle_sha256=$PinnedManifestSha256;stop_helper_sha256=$PinnedStopHelperSha256;entries=$entries;runtime_records=$inventory;task_state=$taskState;last_task_result=$taskInfo.LastTaskResult;owner_pipe_probe=$ownerPipeProbe;task_xml=$taskXml;folder_before=$folderBefore;task_before=$taskBefore;folder_after=$folderAfter;task_after=$taskAfter;shared_config_sha256=$deployment.shared_config_sha256;publication_paused=$true}
Write-NewBytes "$upgrade/update-intent.private.json" $encoding.GetBytes(($intent|ConvertTo-Json -Depth 7))
$rollbackVariables=@"
`$ErrorActionPreference='Stop'
`$root='$root';`$runtime='$runtime';`$python='$python';`$upgrade='$upgrade';`$sharedConfig='$sharedConfig'
`$ownerSid='$ownerSid';`$bridgeSid='$bridgeSid';`$taskPath='$taskPath';`$taskName='$taskName'
"@
$rollbackFunctions=''
foreach($name in @('Assert-InactiveRepairTask','Assert-DisabledIdleTask','Assert-OnlyTaskEnabledChanged','Assert-UpdateFileState','Set-NewReplacementSecurity','Invoke-CheckedRollback')){$rollbackFunctions+="function $name {`n"+(Get-Command $name -CommandType Function).Definition+"`n}`n"}
Write-NewBytes "$upgrade/rollback-update.ps1" $encoding.GetBytes($rollbackVariables+"`n"+$helperText+"`n"+$rollbackFunctions+"`nInitialize-FileIdentity`nInvoke-CheckedRollback`n")
if($taskState -ceq 'Running') {
 # The reviewed helper owns the zero-row SQLite lock and held process handle.
 # No forced termination, fallback stop or uncertain-stop retry is permitted.
 $stopped=& ([ScriptBlock]::Create($encoding.GetString($stopHelperBytes))) -ExpectedOwnerSid $ownerSid -ExpectedPythonSha256 $oldConfig.server_python_sha256 -ExpectedTaskXmlSha256 (Get-BytesHash $encoding.GetBytes($taskXml))
 if($null -eq $stopped -or $stopped -is [array] -or $stopped.status -isnot [string] -or $stopped.status -cne 'STOPPED_EMPTY_CONTROLLER' -or $stopped.held_process_signaled -isnot [bool] -or $stopped.held_process_signaled -ne $true -or $stopped.task_state -isnot [string] -or $stopped.task_state -cne 'Ready'){throw 'Empty-controller shutdown unverified; no execution files replaced.'}
 Write-NewBytes "$upgrade/empty-stop.private.json" $encoding.GetBytes(($stopped|ConvertTo-Json -Depth 4))
}
$inactiveState=Assert-InactiveRepairTask (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
if(($taskState -ceq 'Disabled') -ne ($inactiveState -ceq 'Disabled')){throw 'Task enabled state changed before replacement.'}
Disable-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop | Out-Null
Assert-DisabledIdleTask (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop) ($registered.GetInstances(0).Count)
Assert-OnlyTaskEnabledChanged $taskXml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
foreach($entry in $entries){
 $null=Read-RegularBytes $entry.path 256KB $entry.old_sha256
 if((Get-Acl -LiteralPath $entry.path).Sddl -cne $entry.sddl){throw 'Execution ACL changed before replacement.'}
 if($entry.old_sha256 -cne $entry.new_sha256){
  $temporary=$entry.path+'.update-next';Write-NewBytes $temporary $newBytes[$entry.path]
  Set-NewReplacementSecurity $temporary $entry
  [IO.File]::Replace($temporary,$entry.path,[System.Management.Automation.Language.NullString]::Value)
 }
 $null=Read-RegularBytes $entry.path 256KB $entry.new_sha256
 if((Get-Acl -LiteralPath $entry.path).Sddl -cne $entry.sddl){throw 'Replacement ACL differs; preserve rollback.'}
}
if($folder.GetSecurityDescriptor(7) -cne $folderBefore -or $registered.GetSecurityDescriptor(7) -cne $taskBefore){throw 'Task security changed before update.'}
$registered.SetSecurityDescriptor($taskAfter,16);$folder.SetSecurityDescriptor($folderAfter,0)
if($registered.GetSecurityDescriptor(7) -cne $taskAfter -or $folder.GetSecurityDescriptor(7) -cne $folderAfter){throw 'Narrow task read/execute ACL readback differs.'}
$null=Read-RegularBytes $sharedConfig 128KB $deployment.shared_config_sha256
Assert-DisabledIdleTask (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop) ($registered.GetInstances(0).Count)
Assert-OnlyTaskEnabledChanged $taskXml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
if($taskState -cne 'Disabled'){
 Enable-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop | Out-Null
 Assert-OnlyTaskEnabledChanged $taskXml (Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop)
 Write-NewBytes "$upgrade/start-intent.private.json" $encoding.GetBytes('{"start_requested_once":true,"inference_submitted":false}')
 Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
}
$completed=[ordered]@{schema_version=1;status=$(if($taskState -ceq 'Disabled'){'REPAIRED_DISABLED_NOT_STARTED'}else{'REPAIRED_START_REQUESTED'});task_started=($taskState -cne 'Disabled');bundle_sha256=$PinnedManifestSha256;previous_task_state=$taskState;previous_last_task_result=$taskInfo.LastTaskResult;owner_pipe_probe=$ownerPipeProbe;inference_submitted=$false;route_changed=$false;publication_paused=$true}
Write-NewBytes "$upgrade/update-completed.private.json" $encoding.GetBytes(($completed|ConvertTo-Json -Depth 4))
Write-Output ($completed|ConvertTo-Json -Depth 4)
