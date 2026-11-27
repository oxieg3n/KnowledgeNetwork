"""Read-only native ancestor observations; no BLACKHAT-BASE execution."""
import os
import hashlib
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Inspect-NarratorRecoveryAncestors.ps1'


class RecoveryInspectorBytesTests(unittest.TestCase):
    def test_reviewed_source_preserves_exact_bytes_across_checkout(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '6b5a48514c0691cb46a637c7310af34c95ee3e79c1c08f6a36277501de482f8b')


@unittest.skipUnless(os.name == 'nt', 'Native Windows handles and ACLs')
class RecoveryAncestorTests(unittest.TestCase):
    def run_ps(self, body):
        header = f"$source='{SOURCE}'\n" + r'''
$ErrorActionPreference='Stop'
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$t,[ref]$e)
if($e.Count){throw 'Inspector parse failed'}
foreach($fn in $tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)){. ([ScriptBlock]::Create($fn.Extent.Text))}
$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', header + body],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_complete_chain_reports_multiple_untrusted_ancestors_without_acl_changes(self):
        self.run_ps(self.fixture(r'''
$upper=Join-Path $folder 'upper';$lower=Join-Path $upper 'lower'
New-Item -ItemType Directory -Path $lower -Force|Out-Null
$leaf=Join-Path $lower 'ledger.sqlite';[IO.File]::WriteAllText($leaf,'not a database')
foreach($p in @($upper,$lower)){$a=Get-Acl -LiteralPath $p;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','Allow'));Set-Acl -LiteralPath $p -AclObject $a}
$before=@{};foreach($p in @($upper,$lower,$leaf)){$before[$p]=(Get-Acl -LiteralPath $p).Sddl}
$chain=Get-RecoveryAncestorChain $leaf $owner
foreach($p in @($upper,$lower)){
 $expected=Get-RecoveryPathRecord $p $owner 0xD0040
 $matches=@($chain|Where-Object {$_.identity_before -and (Test-RecoveryIdentity $_.identity_before $expected.identity_before)})
 if($matches.Count -ne 1 -or $matches[0].strict_gate_pass -or $matches[0].untrusted_write_rules.Count -ne 1 -or $matches[0].checked_mask -ne 0xD0040){throw 'Full chain missed an unsafe ancestor'}
 if(-not $matches[0].handle_identity_stable -or -not $matches[0].path_binding_stable -or -not $matches[0].acl_stable){throw 'Native observation not stable'}
}
$expectedLeaf=Get-RecoveryPathRecord $leaf $owner 0xD0156
$expectedRoot=Get-RecoveryPathRecord ([IO.Path]::GetPathRoot($leaf)) $owner 0xD0040
if($chain[-1].checked_mask -ne 0xD0156 -or -not (Test-RecoveryIdentity $chain[-1].identity_before $expectedLeaf.identity_before) -or -not (Test-RecoveryIdentity $chain[0].identity_before $expectedRoot.identity_before)){throw 'Physical root/leaf chain coverage differs'}
foreach($p in @($upper,$lower,$leaf)){if((Get-Acl -LiteralPath $p).Sddl -cne $before[$p]){throw 'Observation changed an ACL'}}
if([Runtime.InteropServices.Marshal]::SizeOf([KNRecoveryAncestors.Info]::new()) -ne 52){throw 'Native file metadata packing differs'}
'''))

    def test_handle_security_remains_bound_to_original_after_path_replacement(self):
        self.run_ps(self.fixture(r'''
$path=Join-Path $folder 'original';New-Item -ItemType Directory -Path $path|Out-Null
Initialize-RecoveryAncestorNative;$h=[KNRecoveryAncestors.Native]::Open($path)
try{
 $before=[KNRecoveryAncestors.Native]::Read($h)
 Move-Item -LiteralPath $path -Destination (Join-Path $folder 'renamed')
 New-Item -ItemType Directory -Path $path|Out-Null
 $replacement=Get-RecoveryPathRecord $path $owner 0xD0156
 $after=[KNRecoveryAncestors.Native]::Read($h)
 if(-not (Test-RecoveryIdentity (Convert-RecoveryObservation $before) (Convert-RecoveryObservation $after))){throw 'Held handle identity changed'}
 if(Test-RecoveryIdentity (Convert-RecoveryObservation $before) $replacement.identity_before){throw 'Replacement was confused with original object'}
 if([Convert]::ToBase64String($before.Security) -cne [Convert]::ToBase64String($after.Security)){throw 'Held descriptor changed unexpectedly'}
 if($replacement.namespace_protected){throw 'Metadata observation claimed namespace protection'}
}finally{$h.Dispose()}
'''))

    def test_private_report_root_rejects_untrusted_read_permission(self):
        self.run_ps(self.fixture(r'''
$report=Join-Path $folder 'review';New-Item -ItemType Directory -Path $report|Out-Null
$a=Get-Acl -LiteralPath $report;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'ReadAndExecute','Allow'));Set-Acl -LiteralPath $report -AclObject $a
$record=Get-RecoveryPathRecord $report $owner 0xD0156
if(-not $record.strict_gate_pass){throw 'Read-only ACL fixture failed write gate unexpectedly'}
$records=@($record)
$denied=$false;try{Assert-RecoveryReportRoot $records $report $owner}catch{$denied=$true}
if(-not $denied){throw 'Private report root accepted readable descriptor'}
if(@(Get-ChildItem -LiteralPath $report -Force).Count){throw 'Rejected report wrote an artifact'}
'''))

    def test_unavailable_report_root_fails_closed_without_creation(self):
        self.run_ps(self.fixture(r'''
$missing=Join-Path $folder 'does-not-exist'
$record=Get-RecoveryPathRecord $missing $owner 0xD0156
if($record.status -cne 'UNAVAILABLE' -or $record.strict_gate_pass){throw 'Unavailable path was trusted'}
$denied=$false;try{Assert-RecoveryReportRoot @($record) $missing $owner}catch{$denied=$true}
if(-not $denied -or (Test-Path -LiteralPath $missing)){throw 'Unavailable report root was accepted or created'}
'''))

    def test_reparse_ancestor_stops_descendant_observations(self):
        self.run_ps(self.fixture(r'''
$actual=Join-Path $folder 'actual';New-Item -ItemType Directory -Path $actual|Out-Null
[IO.File]::WriteAllText((Join-Path $actual 'ledger.sqlite'),'fixture only')
$junction=Join-Path $folder 'junction';New-Item -ItemType Junction -Path $junction -Target $actual|Out-Null
$chain=Get-RecoveryAncestorChain (Join-Path $junction 'ledger.sqlite') $owner
if(-not $chain[-2].reparse_point -or $chain[-2].strict_gate_pass -or $chain[-1].status -cne 'NOT_INSPECTED_REPARSE_ANCESTOR'){throw 'Reparse-backed descendant was inspected'}
'''))

    def test_unavailable_ancestor_keeps_descendants_unknown_without_opening_them(self):
        self.run_ps(self.fixture(r'''
$unobserved=Join-Path $folder 'unobserved';$child=Join-Path $unobserved 'child'
New-Item -ItemType Directory -Path $child -Force|Out-Null
$leaf=Join-Path $child 'ledger.sqlite';[IO.File]::WriteAllText($leaf,'fixture only')
$real=(Get-Command Get-RecoveryPathRecord -CommandType Function).ScriptBlock
$calls=[Collections.Generic.List[string]]::new()
function Get-RecoveryPathRecord([string]$Path,[string]$OwnerSid,[int]$Mask){
 $calls.Add($Path)
 if([IO.Path]::GetFileName($Path) -ceq 'unobserved'){return [ordered]@{path=$Path;status='UNAVAILABLE';strict_gate_pass=$false}}
 return & $real $Path $OwnerSid $Mask
}
$chain=Get-RecoveryAncestorChain $leaf $owner
if($chain[-3].status -cne 'UNAVAILABLE' -or $chain[-2].status -cne 'NOT_INSPECTED_UNVERIFIED_ANCESTOR' -or $chain[-1].status -cne 'NOT_INSPECTED_UNVERIFIED_ANCESTOR'){throw 'Missing ancestor proof became trusted'}
if($calls.Contains($child) -or $calls.Contains($leaf)){throw 'Native descendant opened after an unobserved ancestor'}
'''))

    def test_inspector_contains_no_host_mutation_or_original_stop_execution(self):
        self.run_ps(r'''
$bad=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -in @('Set-Acl','Start-ScheduledTask','Stop-ScheduledTask','Register-ScheduledTask','Remove-Item','Start-Process','Invoke-Expression')},$true))
if($bad.Count){throw 'Inspector contains mutating execution command'}
$text=[IO.File]::ReadAllText($source)
foreach($needle in @('TerminateProcess','SetSecurityInfo','SetFileInformationByHandle','SQLiteConnection','Stop-EmptyNarratorController')){if($text.Contains($needle)){throw 'Inspector contains forbidden host action'}}
''')

    @staticmethod
    def fixture(body):
        return r'''
$folder=Join-Path $env:TEMP ('kn-recovery-ancestors-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder|Out-Null
try{
 $safe=[Security.AccessControl.DirectorySecurity]::new();$safe.SetOwner([Security.Principal.SecurityIdentifier]::new($owner));$safe.SetAccessRuleProtection($true,$false)
 foreach($sid in @($owner,'S-1-5-18','S-1-5-32-544')){$safe.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 Set-Acl -LiteralPath $folder -AclObject $safe
''' + body + r'''
}finally{
 $resolved=[IO.Path]::GetFullPath($folder);$allowed=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
 if(-not $resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup escaped TEMP'}
 [IO.File]::WriteAllText((Join-Path $resolved 'fixture-retained.private.json'),('{"status":"RETAINED_NATIVE_FIXTURE","deletion_performed":false}'))
}
'''


if __name__ == '__main__':
    unittest.main()
