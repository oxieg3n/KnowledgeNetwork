[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
function Get-StopTrustDiagnosticFunction([byte[]]$Bytes) {
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$hash=([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
 if($hash -cne '3813b6d5655d7f9fe262a90266418b11a27032fa7cdf33a79fedac5dc5e0adfb'){throw 'Reviewed stop diagnostic source differs.'}
 $t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseInput([Text.UTF8Encoding]::new($false,$true).GetString($Bytes),[ref]$t,[ref]$e)
 $functions=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq 'Assert-StopTrustedPath')
 if($e.Count -or $functions.Count -ne 1){throw 'Reviewed trust function differs.'}
 $body=$functions[0].Extent.Text;$needle="throw 'Stop trust path is writable by another identity.'"
 if(($body.Split(@($needle),[StringSplitOptions]::None)).Count -ne 2){throw 'Diagnostic instrumentation boundary differs.'}
 $replacement=@'
$failure=[Security.SecurityException]::new('Stop trust path is writable by another identity.')
$failure.Data['checked_path']=$item.FullName
$failure.Data['principal_sid']=$ace.IdentityReference.Value
$failure.Data['rights']=[int]$ace.FileSystemRights
$failure.Data['checked_mask']=$mask
$failure.Data['effective_mask']=([int]$ace.FileSystemRights -band $mask)
$failure.Data['inherited']=$ace.IsInherited
$failure.Data['inheritance']=$ace.InheritanceFlags.ToString()
$failure.Data['propagation']=$ace.PropagationFlags.ToString()
$failure.Data['gate_sddl']=$acl.Sddl
throw $failure
'@
 return $body.Replace($needle,$replacement)
}
function Get-RepairDiagnosticIdentity([string]$Path) {
 if(-not ('KNRepairTrust.Native' -as [type])){Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
namespace KNRepairTrust {
 [StructLayout(LayoutKind.Sequential,Pack=4)] public struct Info {public uint Attributes;public long Creation,Access,Write;public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 public static class Native {
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr t);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info i);
 }
}
'@
 }
 $handle=[KNRepairTrust.Native]::CreateFile($Path,128,7,[IntPtr]::Zero,3,0x02200000,[IntPtr]::Zero)
 try{
  $info=[KNRepairTrust.Info]::new()
  if($handle.IsInvalid -or -not [KNRepairTrust.Native]::GetFileInformationByHandle($handle,[ref]$info)){throw 'Native metadata unavailable.'}
  return [ordered]@{volume=$info.Volume;file_id_high=$info.IndexHigh;file_id_low=$info.IndexLow;links=$info.Links;attributes=$info.Attributes;creation=$info.Creation;write=$info.Write;size_high=$info.SizeHigh;size_low=$info.SizeLow}
 }finally{$handle.Dispose()}
}
function Get-RepairTrustFailure([object]$Failure,[string]$Target) {
 for($depth=0;$depth -lt 8;$depth++){
  if($Failure.Data['checked_path']){break}
  if($null -eq $Failure.InnerException -or $depth -eq 7){return [ordered]@{checked_target=$Target;error='trust_failure_without_write_ace_context'}}
  $Failure=$Failure.InnerException
 }
 $path=[string]$Failure.Data['checked_path']
 if(-not $path){return [ordered]@{checked_target=$Target;error='trust_failure_without_write_ace_context'}}
 $before=Get-RepairDiagnosticIdentity $path;$acl=Get-Acl -LiteralPath $path;$after=Get-RepairDiagnosticIdentity $path
 $result=[ordered]@{checked_target=$Target;path=$path;identity_before=$before;identity_after=$after;identity_changed=(($before|ConvertTo-Json -Compress) -cne ($after|ConvertTo-Json -Compress));owner_sid=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value;sddl=$acl.Sddl;gate_acl_changed=($acl.Sddl -cne $Failure.Data['gate_sddl']);rules=@()}
 foreach($key in @('principal_sid','rights','checked_mask','effective_mask','inherited','inheritance','propagation','gate_sddl')){$result[$key]=$Failure.Data[$key]}
 foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){$result.rules+=,[ordered]@{sid=$rule.IdentityReference.Value;type=$rule.AccessControlType.ToString();rights=[int]$rule.FileSystemRights;inherited=$rule.IsInherited;inheritance=$rule.InheritanceFlags.ToString();propagation=$rule.PropagationFlags.ToString()}}
 return $result
}
$current=[Security.Principal.WindowsIdentity]::GetCurrent();$ExpectedOwnerSid=$current.User.Value
if($ExpectedOwnerSid -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Intended owner elevated, never SYSTEM required.'}
$root='C:/ProgramData/KnowledgeNetworkCollector/HostExec';$reportRoot="$root/broker-update-v1"
$kit='D:/projects/knowledgenetwork/collector-narrator-v9-004';$spool="$kit/private-service-v9-001"
$source="$kit/narrator-control-update-tools-v1/Stop-EmptyNarratorController.ps1"
$item=Get-Item -LiteralPath $source -Force;$ancestor=$item
while($null -ne $ancestor){if(($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Diagnostic source path is reparse-backed.'};$ancestor=if($ancestor -is [IO.DirectoryInfo]){$ancestor.Parent}else{$ancestor.Directory}}
$sourceBefore=Get-RepairDiagnosticIdentity $source
$stream=[IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{if($stream.Length -le 0 -or $stream.Length -gt 128KB){throw 'Diagnostic source exceeds bound.'};$reader=[IO.BinaryReader]::new($stream);$bytes=$reader.ReadBytes(131073)}finally{$stream.Dispose()}
$sourceAfter=Get-RepairDiagnosticIdentity $source
if($sourceBefore.links -ne 1 -or ($sourceBefore|ConvertTo-Json -Compress) -cne ($sourceAfter|ConvertTo-Json -Compress)){throw 'Diagnostic source identity changed.'}
. ([ScriptBlock]::Create((Get-StopTrustDiagnosticFunction $bytes)))
try{Assert-StopTrustedPath $root;Assert-StopTrustedPath $reportRoot}catch{throw 'Protected diagnostic report root failed trust; no report written.'}
$privateAcl=Get-Acl -LiteralPath $reportRoot
foreach($rule in $privateAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if($rule.AccessControlType -ne 'Allow' -or $rule.IdentityReference.Value -notin @($ExpectedOwnerSid,'S-1-5-18','S-1-5-32-544')){throw 'Diagnostic report privacy is unverified.'}}
$configPath="$root/narrator-broker.json";Assert-StopTrustedPath $configPath
if((Get-Item -LiteralPath $configPath).Length -gt 64KB -or (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne '2b38f28bc5772c069cf8a15c54b4f9ef3ac53b585e10ed572cdbed03f778304d'){throw 'Prepared broker configuration differs.'}
if((Get-Content -LiteralPath $configPath -Raw -Encoding UTF8|ConvertFrom-Json).owner_sid -cne $ExpectedOwnerSid){throw 'Intended owner differs.'}
$targets=@($root,"$root/runtime","$root/runtime/python","$root/runtime/python/python.exe","$root/runtime-files.private.json","$reportRoot/update-intent.private.json","$spool/narrator-control.sqlite")
$result=[ordered]@{schema_version=1;status='PASS_READ_ONLY_TRUST';source_sha256='3813b6d5655d7f9fe262a90266418b11a27032fa7cdf33a79fedac5dc5e0adfb';source_identity_before=$sourceBefore;source_identity_after=$sourceAfter;checked=@();failure=$null;task=$null;acl_changed=$false;stop_requested=$false;sqlite_opened=$false;python_launched=$false}
foreach($target in $targets){try{Assert-StopTrustedPath $target;$result.checked+=,$target}catch{$result.status='BLOCKED_TRUST_PATH_IDENTIFIED';$result.failure=Get-RepairTrustFailure $_.Exception $target;break}}
if($null -eq $result.failure){
 $inventoryPath="$root/runtime-files.private.json"
 if((Get-Item -LiteralPath $inventoryPath).Length -gt 64KB){throw 'Runtime inventory exceeds bound.'}
 $records=Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8|ConvertFrom-Json
 if($records -isnot [array] -or $records.Count -ne 37){throw 'Runtime inventory differs.'}
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 foreach($record in $records){if($record.name -isnot [string] -or $record.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or -not $seen.Add($record.name)){throw 'Runtime target differs.'};$target=Join-Path "$root/runtime/python" $record.name;try{Assert-StopTrustedPath $target;$result.checked+=,$target}catch{$result.status='BLOCKED_TRUST_PATH_IDENTIFIED';$result.failure=Get-RepairTrustFailure $_.Exception $target;break}}
}
try{$task=Get-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName 'NarratorControl';$info=Get-ScheduledTaskInfo -TaskPath '\KnowledgeNetworkCollector\' -TaskName 'NarratorControl';$result.task=[ordered]@{state=$task.State.ToString();last_result=$info.LastTaskResult;last_run_utc=$info.LastRunTime.ToUniversalTime().ToString('o')}}catch{$result.task=[ordered]@{status='QUERY_UNAVAILABLE';hresult=$_.Exception.HResult}}
$destination="$reportRoot/review-trust-$([guid]::NewGuid().ToString('N')).private.json"
$output=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 10))
$stream=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($output,0,$output.Length);$stream.Flush($true)}finally{$stream.Dispose()}
@{status=$result.status;evidence_path=$destination}|ConvertTo-Json -Compress
