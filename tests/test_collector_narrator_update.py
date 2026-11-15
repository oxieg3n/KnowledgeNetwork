"""Bounded native tests for protected postdeployment repair helpers."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'docs/collector/host-tools/Update-KnowledgeNetworkNarratorControl.ps1'
INSTALL = ROOT / 'docs/collector/host-tools/Install-KnowledgeNetworkNarratorControl.ps1'


@unittest.skipUnless(os.name == 'nt', 'PowerShell5 native helper tests')
class NarratorUpdateTests(unittest.TestCase):
    def run_ps(self, body):
        header = r'''
$ErrorActionPreference='Stop'
function Import-Helper([string]$Path,[string]$Name){
 $tokens=$null;$errors=$null
 $tree=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
 if($errors.Count){throw 'Script parse failed.'}
 $matches=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq $Name)
 if($matches.Count -ne 1){throw 'Helper missing.'}
 . ([ScriptBlock]::Create($matches[0].Extent.Text))
 Set-Item ('Function:script:'+$Name) (Get-Item ('Function:'+$Name)).ScriptBlock
}
'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', header + body], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_entire_script_parses_and_has_no_direct_stop_or_acl_repair(self):
        path = str(SCRIPT).replace("'", "''")
        self.run_ps(f'''
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$t,[ref]$e)
if($e.Count){{throw 'Parser error'}}
$bad=@($tree.FindAll({{param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -in @('Stop-ScheduledTask','Register-ScheduledTask')}},$true))
if($bad.Count){{throw 'Updater must not force-stop/re-register task or rewrite existing data ACLs.'}}
$aclCalls=@($tree.FindAll({{param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Set-Acl'}},$true))
if($aclCalls.Count -ne 1){{throw 'Only the new replacement security helper may set an ACL'}}
$parent=$aclCalls[0].Parent
while($null -ne $parent -and $parent -isnot [Management.Automation.Language.FunctionDefinitionAst]){{$parent=$parent.Parent}}
if($null -eq $parent -or $parent.Name -cne 'Set-NewReplacementSecurity' -or $aclCalls[0].Extent.Text -notmatch '-LiteralPath \\$Temporary'){{throw 'Existing target ACL rewrite forbidden'}}
''')

    def test_running_ready_disabled_states_only(self):
        self.run_ps(f"Import-Helper '{SCRIPT}' 'Assert-DiagnosticTaskState'\n" + r'''
foreach($state in @('Ready','Disabled','Running')) {if((Assert-DiagnosticTaskState ([pscustomobject]@{State=$state})) -cne $state){throw 'State changed'}}
foreach($state in @('Queued','Unknown','')) {$denied=$false;try{$null=Assert-DiagnosticTaskState ([pscustomobject]@{State=$state})}catch{$denied=$true};if(-not $denied){throw 'Unsafe state accepted'}}
''')

    def test_file_repair_rollback_rejects_running_and_queued_tasks(self):
        self.run_ps(f"Import-Helper '{SCRIPT}' 'Assert-InactiveRepairTask'\n" + r'''
foreach($state in @('Ready','Disabled')) {if((Assert-InactiveRepairTask ([pscustomobject]@{State=$state})) -cne $state){throw 'State changed'}}
foreach($state in @('Running','Queued','Unknown')) {$denied=$false;try{$null=Assert-InactiveRepairTask ([pscustomobject]@{State=$state})}catch{$denied=$true};if(-not $denied){throw 'Live task accepted for file replacement'}}
''')

    def test_disabled_zero_instances_gate_and_only_enabled_xml_change(self):
        self.run_ps(f"Import-Helper '{SCRIPT}' 'Assert-DisabledIdleTask'\nImport-Helper '{SCRIPT}' 'Assert-OnlyTaskEnabledChanged'\n" + r'''
Assert-DisabledIdleTask ([pscustomobject]@{State='Disabled'}) 0
foreach($case in @(@('Running',0),@('Ready',0),@('Disabled',1))) {$denied=$false;try{Assert-DisabledIdleTask ([pscustomobject]@{State=$case[0]}) $case[1]}catch{$denied=$true};if(-not $denied){throw 'Nonidle/active enabled task accepted'}}
$before='<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Settings><Enabled>true</Enabled><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy></Settings><Actions><Exec><Command>fixed.exe</Command></Exec></Actions></Task>'
$disabled=$before.Replace('<Enabled>true</Enabled>','<Enabled>false</Enabled>')
Assert-OnlyTaskEnabledChanged $before $disabled
$denied=$false;try{Assert-OnlyTaskEnabledChanged $before ($disabled.Replace('fixed.exe','arbitrary.exe'))}catch{$denied=$true};if(-not $denied){throw 'Changed task action accepted'}
''')

    def test_bridge_only_read_execute_added_original_aces_preserved(self):
        self.run_ps(f"Import-Helper '{INSTALL}' 'Assert-TaskSecurity'\nImport-Helper '{SCRIPT}' 'Add-TaskBridgeRead'\n" + r'''
$owner='S-1-5-21-1-2-3-1001';$bridge='S-1-5-21-1-2-3-1002'
$before="O:${owner}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${owner})"
$after=Add-TaskBridgeRead $before $owner $bridge
$a=[Security.AccessControl.RawSecurityDescriptor]::new($before)
$b=[Security.AccessControl.RawSecurityDescriptor]::new($after)
if($b.Owner.Value -cne $owner -or $b.DiscretionaryAcl.Count -ne 4){throw 'Security owner/count changed'}
for($i=0;$i -lt 3;$i++){
 $x=New-Object byte[] $a.DiscretionaryAcl[$i].BinaryLength;$a.DiscretionaryAcl[$i].GetBinaryForm($x,0)
 $y=New-Object byte[] $b.DiscretionaryAcl[$i].BinaryLength;$b.DiscretionaryAcl[$i].GetBinaryForm($y,0)
 if([Convert]::ToBase64String($x) -cne [Convert]::ToBase64String($y)){throw 'Original ACE changed'}
}
$ace=$b.DiscretionaryAcl[3]
if($ace.SecurityIdentifier.Value -cne $bridge -or $ace.AccessMask -ne 0x1200a9 -or $ace.AceFlags -ne 0){throw 'Bridge rights broader than exact RX'}
$denied=$false;try{$null=Add-TaskBridgeRead $after $owner $bridge}catch{$denied=$true};if(-not $denied){throw 'Duplicate bridge grant accepted'}
''')

    def test_rollback_accepts_only_recorded_bytes_and_unchanged_acl(self):
        self.run_ps(f"Import-Helper '{SCRIPT}' 'Assert-UpdateFileState'\n" + r'''
$e=[pscustomobject]@{old_sha256=('a'*64);new_sha256=('b'*64);sddl='recorded'}
Assert-UpdateFileState $e ('a'*64) 'recorded'
Assert-UpdateFileState $e ('b'*64) 'recorded'
foreach($v in @(@(('c'*64),'recorded'),@(('b'*64),'changed'))) {$denied=$false;try{Assert-UpdateFileState $e $v[0] $v[1]}catch{$denied=$true};if(-not $denied){throw 'Drift accepted'}}
''')

    def test_generated_rollback_functions_parse_without_lifecycle_actions(self):
        self.run_ps(f"$installer='{INSTALL}';$updater='{SCRIPT}'\n" + r'''
$text=''
foreach($source in @(@($installer,@('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes','Assert-TrustedExecutionPath','Assert-DeploymentManifest','Convert-StrictJson','Write-NewBytes','New-ProtectedDirectory','Assert-TaskXml','Assert-TaskSecurity')),@($updater,@('Assert-InactiveRepairTask','Assert-DisabledIdleTask','Assert-OnlyTaskEnabledChanged','Assert-UpdateFileState','Set-NewReplacementSecurity','Invoke-CheckedRollback')))){
 $t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($source[0],[ref]$t,[ref]$e)
 foreach($name in $source[1]){
  $function=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq $name)
  if($function.Count -ne 1){throw 'Missing rollback helper'}
  $text+=$function[0].Extent.Text+"`n"
 }
}
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseInput($text+"`nInitialize-FileIdentity`nInvoke-CheckedRollback",[ref]$t,[ref]$e)
if($e.Count){throw 'Generated rollback parse failed'}
$bad=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -in @('Start-ScheduledTask','Stop-ScheduledTask')},$true))
if($bad.Count){throw 'Rollback lifecycle mutation forbidden'}
''')

    def test_native_empty_marker_preflight_skipped_and_changed_file_rollback(self):
        self.run_ps(f"$installer='{INSTALL}';$updater='{SCRIPT}'\n" + r'''
foreach($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes')){Import-Helper $installer $name}
foreach($name in @('New-ChangedEntry','Assert-UpdateFileState','Set-NewReplacementSecurity')){Import-Helper $updater $name}
Initialize-FileIdentity
$folder=Join-Path $env:TEMP ('kn-empty-marker-update-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder|Out-Null
try {
 $marker=Join-Path $folder '__init__.py';[IO.File]::WriteAllBytes($marker,[byte[]]@())
 $empty='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
 $data=Read-RegularBytes $marker 128KB $empty
 if($data.Length -ne 0){throw 'Empty marker preflight failed'}
 $entry=New-ChangedEntry $marker '__init__.py' $empty $empty ((Get-Acl -LiteralPath $marker).Sddl)
 if($null -ne $entry){throw 'Unchanged empty marker must not enter rollback set'}
 $path=Join-Path $folder 'control.py';[IO.File]::WriteAllText($path,'new-control')
 $before=[Text.Encoding]::UTF8.GetBytes('old-control')
 $old=Get-BytesHash $before;$new=Get-BytesHash ([IO.File]::ReadAllBytes($path));$sddl=(Get-Acl -LiteralPath $path).Sddl
 $entry=New-ChangedEntry $path 'control.py' $old $new $sddl
 Assert-UpdateFileState $entry (Get-BytesHash (Read-RegularBytes $entry.path 128KB $null)) ((Get-Acl -LiteralPath $entry.path).Sddl)
 $temporary=$path+'.rollback-next';[IO.File]::WriteAllBytes($temporary,$before)
 Set-NewReplacementSecurity $temporary $entry
 [IO.File]::Replace($temporary,$path,[System.Management.Automation.Language.NullString]::Value)
 $null=Read-RegularBytes $path 128KB $old
 if((Get-Item -LiteralPath $marker).Length -ne 0){throw 'Rollback changed the untouched empty marker'}
 $afterSddl=(Get-Acl -LiteralPath $path).Sddl
 if($afterSddl -cne $sddl){throw ('Rollback destination security descriptor changed; before='+$sddl+'; after='+$afterSddl)}
}finally{
 $resolved=[IO.Path]::GetFullPath($folder);$allowed=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
 if(-not $resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup escaped TEMP'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
}
''')

    def test_actual_stamp_replace_preserves_owner_group_protected_and_inherited_acl(self):
        self.run_ps(f"$updater='{SCRIPT}';$installer='{INSTALL}'\n" + r'''
foreach($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes')){Import-Helper $installer $name}
Import-Helper $updater 'Set-NewReplacementSecurity'
Initialize-FileIdentity
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($updater,[ref]$t,[ref]$e)
$calls=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Extent.Text.StartsWith('[IO.File]::Replace(')},$true))
$folder=Join-Path $env:TEMP ('kn-security-replace-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder|Out-Null
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
try {
 foreach($call in $calls){foreach($kind in @('Owner','Group')){foreach($protected in @($false,$true)){
  $entry=[pscustomobject]@{path=(Join-Path $folder ([guid]::NewGuid().ToString('N')))}
  [IO.File]::WriteAllText($entry.path,'old')
  $temporary=$entry.path+'.update-next';[IO.File]::WriteAllText($temporary,'new')
  $security=Get-Acl -LiteralPath $entry.path
  if($kind -eq 'Owner'){
   $originalOwner=$security.GetOwner([Security.Principal.SecurityIdentifier])
   $alternate=if($originalOwner.Value -ceq $sid.Value){[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')}else{$sid}
   $security.SetOwner($alternate)
  }else{
   $originalGroup=$security.GetGroup([Security.Principal.SecurityIdentifier]).Value
   $alternate=if($originalGroup -ceq 'S-1-5-32-544'){'S-1-5-32-545'}else{'S-1-5-32-544'}
   $security.SetGroup([Security.Principal.SecurityIdentifier]::new($alternate))
  }
  if($protected){$security.SetAccessRuleProtection($true,$true)}
  Set-Acl -LiteralPath $entry.path -AclObject $security
  $before=(Get-Acl -LiteralPath $entry.path).Sddl
  $entry|Add-Member -NotePropertyName sddl -NotePropertyValue $before
  # Negative control: the actual unstamped production Replace loses metadata.
  . ([ScriptBlock]::Create($call.Extent.Text))
  if((Get-Acl -LiteralPath $entry.path).Sddl -ceq $before){throw 'Unstamped negative control did not expose owner/group loss'}
  # Recreate the same owned fixture, then exercise production stamp + Replace.
  $restore=[Security.AccessControl.FileSecurity]::new();$restore.SetSecurityDescriptorSddlForm($before)
  Set-Acl -LiteralPath $entry.path -AclObject $restore
  [IO.File]::WriteAllText($temporary,'reviewed-new')
  $denied=$false;try{Set-NewReplacementSecurity $entry.path $entry}catch{$denied=$true}
  if(-not $denied -or (Get-Acl -LiteralPath $entry.path).Sddl -cne $before){throw 'Stamp helper accepted existing target or rewrote it'}
  Set-NewReplacementSecurity $temporary $entry
  if((Get-Acl -LiteralPath $temporary).Sddl -cne $before -or (Get-Acl -LiteralPath $entry.path).Sddl -cne $before){throw 'Pre-replace exact-security gate failed'}
  . ([ScriptBlock]::Create($call.Extent.Text))
  if([IO.File]::ReadAllText($entry.path) -cne 'reviewed-new' -or (Get-Acl -LiteralPath $entry.path).Sddl -cne $before){throw 'Stamped production replacement lost bytes or owner/group/DACL'}
 }}}
}finally{
 $resolved=[IO.Path]::GetFullPath($folder);$allowed=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
 if(-not $resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup escaped TEMP'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
}
''')

    def test_actual_production_atomic_replace_preserves_destination_acl(self):
        self.run_ps(f"$path='{SCRIPT}';$installer='{INSTALL}'\n" + r'''
foreach($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes')){Import-Helper $installer $name}
Import-Helper $path 'Set-NewReplacementSecurity'
Initialize-FileIdentity
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$t,[ref]$e)
$calls=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Extent.Text.StartsWith('[IO.File]::Replace(')},$true))
if($calls.Count -ne 2){throw 'Expected update and rollback atomic call'}
$folder=Join-Path $env:TEMP ('kn-narrator-update-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder|Out-Null
try {
 foreach($call in $calls){
  $entry=[pscustomobject]@{path=(Join-Path $folder ([guid]::NewGuid().ToString('N')))}
  [IO.File]::WriteAllText($entry.path,'old');$temporary=$entry.path+'.update-next';[IO.File]::WriteAllText($temporary,'new')
  $acl=(Get-Acl -LiteralPath $entry.path).Sddl
  $entry|Add-Member -NotePropertyName sddl -NotePropertyValue $acl
  Set-NewReplacementSecurity $temporary $entry
  . ([ScriptBlock]::Create($call.Extent.Text))
  if([IO.File]::ReadAllText($entry.path) -cne 'new'){throw 'Atomic replacement bytes differ'}
  if(Test-Path -LiteralPath $temporary){throw 'Atomic replacement did not consume temporary source'}
  $afterSddl=(Get-Acl -LiteralPath $entry.path).Sddl
  if($afterSddl -cne $acl){throw ('Atomic replacement destination security descriptor changed; before='+$acl+'; after='+$afterSddl)}
 }
}finally{
 $resolved=[IO.Path]::GetFullPath($folder);$allowed=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
 if(-not $resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Fixture cleanup path escaped TEMP'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
}
''')


if __name__ == '__main__':
    unittest.main()
