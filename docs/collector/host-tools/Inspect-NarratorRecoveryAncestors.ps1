[CmdletBinding()]
param()
$ErrorActionPreference='Stop'

function Initialize-RecoveryAncestorNative {
 if('KNRecoveryAncestors.Native' -as [type]){return}
 Add-Type -TypeDefinition @'
using System;using System.ComponentModel;using System.Runtime.InteropServices;using System.Text;using Microsoft.Win32.SafeHandles;
namespace KNRecoveryAncestors {
 [StructLayout(LayoutKind.Sequential,Pack=4)] public struct Info {public uint Attributes;public long Creation,Access,Write;public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 public sealed class Observation {public Info Identity;public byte[] Security;public string FileSystem;}
 public static class Native {
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr t);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info i);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool GetVolumeInformationByHandleW(SafeFileHandle h,IntPtr name,uint namesize,out uint serial,out uint max,out uint flags,StringBuilder filesystem,uint size);
  [DllImport("advapi32.dll")] static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint requested,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr descriptor);
  [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
  [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
  public static SafeFileHandle Open(string path) {
   var h=CreateFile(path,0x20080,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
   if(h.IsInvalid){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}return h;
  }
  public static Observation Read(SafeFileHandle handle) {
   Info info;if(!GetFileInformationByHandle(handle,out info))throw new Win32Exception(Marshal.GetLastWin32Error());
   uint serial,max,flags;var fs=new StringBuilder(32);if(!GetVolumeInformationByHandleW(handle,IntPtr.Zero,0,out serial,out max,out flags,fs,32))throw new Win32Exception(Marshal.GetLastWin32Error());
   IntPtr o,g,d,s,sd;uint error=GetSecurityInfo(handle,1,7,out o,out g,out d,out s,out sd);
   if(error!=0)throw new Win32Exception((int)error);
   try {if(sd==IntPtr.Zero)throw new InvalidOperationException("Security descriptor required.");uint size=GetSecurityDescriptorLength(sd);if(size==0||size>65536)throw new InvalidOperationException("Bounded security descriptor required.");
    byte[] data=new byte[size];Marshal.Copy(sd,data,0,(int)size);return new Observation {Identity=info,Security=data,FileSystem=fs.ToString()};
   }finally{LocalFree(sd);}
  }
 }
}
'@
}
function Convert-RecoveryObservation([object]$Observation) {
 $i=$Observation.Identity
 return [ordered]@{filesystem=$Observation.FileSystem;volume=$i.Volume;file_id_high=$i.IndexHigh;file_id_low=$i.IndexLow;creation=$i.Creation;attributes=$i.Attributes;links=$i.Links;write=$i.Write;size_high=$i.SizeHigh;size_low=$i.SizeLow}
}
function Test-RecoveryIdentity([object]$Before,[object]$After) {
 foreach($key in @('filesystem','volume','file_id_high','file_id_low','creation')){if($Before[$key] -ne $After[$key]){return $false}}
 return $true
}
function Get-RecoveryPathRecord([string]$Path,[string]$OwnerSid,[int]$Mask) {
 Initialize-RecoveryAncestorNative
 $record=[ordered]@{path=[IO.Path]::GetFullPath($Path);checked_mask=$Mask;status='UNAVAILABLE';strict_gate_pass=$false;namespace_protected=$false}
 $handle=$null;$reopened=$null
 try{
  $handle=[KNRecoveryAncestors.Native]::Open($record.path)
  $before=[KNRecoveryAncestors.Native]::Read($handle)
  $raw=[Security.AccessControl.RawSecurityDescriptor]::new($before.Security,0)
  $record.owner_sid=if($null -eq $raw.Owner){$null}else{$raw.Owner.Value}
  $record.sddl_before=$raw.GetSddlForm([Security.AccessControl.AccessControlSections]::All)
  $record.identity_before=Convert-RecoveryObservation $before
  $record.supported_local_filesystem=($before.FileSystem -ceq 'NTFS')
  $record.reparse_point=(($before.Identity.Attributes -band 0x400) -ne 0)
  $record.regular_single_link=(($before.Identity.Attributes -band 16) -ne 0 -or $before.Identity.Links -eq 1)
  $record.null_dacl=($null -eq $raw.DiscretionaryAcl)
  $trusted=@($OwnerSid,'S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
  $security=[Security.AccessControl.FileSecurity]::new();$security.SetSecurityDescriptorBinaryForm($before.Security)
  $record.rules=@();$record.untrusted_write_rules=@()
  foreach($rule in $security.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
   $rights=[int]$rule.FileSystemRights;$inheritOnly=(($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0)
   $entry=[ordered]@{sid=$rule.IdentityReference.Value;type=$rule.AccessControlType.ToString();rights=$rights;inherited=$rule.IsInherited;inheritance=$rule.InheritanceFlags.ToString();propagation=$rule.PropagationFlags.ToString();checked_mask_match=($rights -band $Mask);generic_write_or_all=((([long]$rights -band 0x50000000) -ne 0))}
   $record.rules+=,$entry
   if($rule.AccessControlType -eq 'Allow' -and -not $inheritOnly -and $entry.sid -notin $trusted -and ($entry.checked_mask_match -ne 0 -or $entry.generic_write_or_all)){$record.untrusted_write_rules+=,$entry}
  }
  $after=[KNRecoveryAncestors.Native]::Read($handle)
  $record.identity_after=Convert-RecoveryObservation $after
  $record.sddl_after=([Security.AccessControl.RawSecurityDescriptor]::new($after.Security,0)).GetSddlForm([Security.AccessControl.AccessControlSections]::All)
  $record.handle_identity_stable=Test-RecoveryIdentity $record.identity_before $record.identity_after
  $record.acl_stable=($record.sddl_before -ceq $record.sddl_after)
  $record.metadata_changed=(($record.identity_before|ConvertTo-Json -Compress) -cne ($record.identity_after|ConvertTo-Json -Compress))
  $reopened=[KNRecoveryAncestors.Native]::Open($record.path)
  $current=[KNRecoveryAncestors.Native]::Read($reopened)
  $record.pathname_identity=Convert-RecoveryObservation $current
  $record.path_binding_stable=Test-RecoveryIdentity $record.identity_before $record.pathname_identity
  $record.pathname_acl_stable=($record.sddl_after -ceq ([Security.AccessControl.RawSecurityDescriptor]::new($current.Security,0)).GetSddlForm([Security.AccessControl.AccessControlSections]::All))
  $record.strict_gate_pass=($record.supported_local_filesystem -and $record.handle_identity_stable -and $record.path_binding_stable -and $record.acl_stable -and $record.pathname_acl_stable -and -not $record.reparse_point -and $record.regular_single_link -and -not $record.null_dacl -and $record.owner_sid -in $trusted -and $record.untrusted_write_rules.Count -eq 0)
  $record.status='OBSERVED'
 }catch{
  $record.error='native_identity_or_acl_unavailable';$record.hresult=$_.Exception.HResult
 }finally{if($null -ne $reopened){$reopened.Dispose()};if($null -ne $handle){$handle.Dispose()}}
 return $record
}
function Get-RecoveryAncestorChain([string]$Target,[string]$OwnerSid) {
 $paths=[Collections.Generic.List[string]]::new();$path=[IO.Path]::GetFullPath($Target)
 if($path.StartsWith('\\') -or $path -cnotmatch '^[A-Za-z]:\\'){throw 'Fixed local path required.'}
 while($null -ne $path){if($paths.Count -ge 32){throw 'Ancestor bound exceeded.'};$paths.Add($path);$parent=[IO.Directory]::GetParent($path);$path=if($null -eq $parent){$null}else{$parent.FullName}}
 $paths.Reverse();$records=@();$skipReason=$null
 foreach($path in $paths){
  if($null -ne $skipReason){$records+=,[ordered]@{path=$path;status=$skipReason;strict_gate_pass=$false};continue}
  $mask=if($path -ieq [IO.Path]::GetFullPath($Target)){0x000D0156}else{0x000D0040}
  $record=Get-RecoveryPathRecord $path $OwnerSid $mask;$records+=,$record
  if($record.status -cne 'OBSERVED'){$skipReason='NOT_INSPECTED_UNVERIFIED_ANCESTOR'}elseif($record.reparse_point){$skipReason='NOT_INSPECTED_REPARSE_ANCESTOR'}
 }
 return ,$records
}
function Assert-RecoveryReportRoot([object[]]$Records,[string]$ReportRoot,[string]$OwnerSid) {
 foreach($record in $Records){if(-not $record.strict_gate_pass){throw 'Protected report chain failed native trust; no report written.'}}
 $leaf=@($Records|Where-Object {$_.path -ieq [IO.Path]::GetFullPath($ReportRoot)})
 if($leaf.Count -ne 1){throw 'Protected report root differs.'}
 foreach($rule in $leaf[0].rules){if($rule.type -ne 'Allow' -or $rule.sid -notin @($OwnerSid,'S-1-5-18','S-1-5-32-544')){throw 'Protected report privacy differs; no report written.'}}
}

$current=[Security.Principal.WindowsIdentity]::GetCurrent();$owner=$current.User.Value
if($env:COMPUTERNAME -ine 'BLACKHAT-BASE' -or [IntPtr]::Size -ne 8 -or $owner -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'BLACKHAT-BASE intended owner elevated 64-bit, never SYSTEM required.'}
$root='C:/ProgramData/KnowledgeNetworkCollector/HostExec';$reportRoot="$root/broker-update-v1"
$reportChain=Get-RecoveryAncestorChain $reportRoot $owner
Assert-RecoveryReportRoot $reportChain $reportRoot $owner
$configPath="$root/narrator-broker.json";$configRecord=Get-RecoveryPathRecord $configPath $owner 0x000D0156
if(-not $configRecord.strict_gate_pass -or (Get-Item -LiteralPath $configPath).Length -gt 64KB){throw 'Protected broker configuration trust differs.'}
$configBytes=[IO.File]::ReadAllBytes($configPath);$sha=[Security.Cryptography.SHA256]::Create()
try{$configHash=([BitConverter]::ToString($sha.ComputeHash($configBytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
$configAfter=Get-RecoveryPathRecord $configPath $owner 0x000D0156
if($configHash -cne '2b38f28bc5772c069cf8a15c54b4f9ef3ac53b585e10ed572cdbed03f778304d' -or -not $configAfter.strict_gate_pass -or $configRecord.sddl_before -cne $configAfter.sddl_before -or -not (Test-RecoveryIdentity $configRecord.identity_before $configAfter.identity_before) -or ([Text.UTF8Encoding]::new($false,$true).GetString($configBytes)|ConvertFrom-Json).owner_sid -cne $owner){throw 'Pinned owner broker configuration differs.'}
$target='D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001/narrator-control.sqlite'
$dataChain=Get-RecoveryAncestorChain $target $owner
$executionChain=Get-RecoveryAncestorChain "$root/runtime/python/python.exe" $owner
$result=[ordered]@{schema_version=1;status='OBSERVED_READ_ONLY_ANCESTOR_CHAIN';runtime=[ordered]@{powershell_version=$PSVersionTable.PSVersion.ToString();process_bits=([IntPtr]::Size*8);clr_version=[Environment]::Version.ToString()};data_chain=$dataChain;execution_chain=$executionChain;report_chain=$reportChain;broker_configuration=$configRecord;broker_configuration_after=$configAfter;task=$null;namespace_protected=$false;live_ledger_binding_proven=$false;acl_changed=$false;stop_requested=$false;sqlite_opened=$false;python_launched=$false;publication_paused=$true}
if(@($dataChain+$executionChain|Where-Object {-not $_.strict_gate_pass}).Count){$result.status='BLOCKED_NATIVE_ANCESTOR_TRUST'}
try{$task=Get-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName NarratorControl;$info=Get-ScheduledTaskInfo -TaskPath '\KnowledgeNetworkCollector\' -TaskName NarratorControl;$result.task=[ordered]@{state=$task.State.ToString();last_result=$info.LastTaskResult;last_run_utc=$info.LastRunTime.ToUniversalTime().ToString('o')}}catch{$result.task=[ordered]@{status='QUERY_UNAVAILABLE';hresult=$_.Exception.HResult}}
$reportChainAfter=Get-RecoveryAncestorChain $reportRoot $owner
Assert-RecoveryReportRoot $reportChainAfter $reportRoot $owner
for($index=0;$index -lt $reportChain.Count;$index++){if(-not (Test-RecoveryIdentity $reportChain[$index].identity_before $reportChainAfter[$index].identity_before) -or $reportChain[$index].sddl_before -cne $reportChainAfter[$index].sddl_before){throw 'Report namespace changed; no report written.'}}
$destination="$reportRoot/recovery-ancestors-$([guid]::NewGuid().ToString('N')).private.json"
$output=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 12));if($output.Length -gt 256KB){throw 'Private report exceeds bound.'}
$stream=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($output,0,$output.Length);$stream.Flush($true)}finally{$stream.Dispose()}
@{status=$result.status;evidence_path=$destination}|ConvertTo-Json -Compress
