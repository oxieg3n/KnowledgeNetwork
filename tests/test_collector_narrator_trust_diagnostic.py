"""Read-only trust diagnostics exercise the unchanged pinned native gate."""
import os
import hashlib
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / 'docs/collector/host-tools/Inspect-NarratorRepairTrust.ps1'
STOP = ROOT / 'docs/collector/host-tools/Stop-EmptyNarratorController.ps1'


class PinnedTrustDiagnosticSourceTests(unittest.TestCase):
    def test_source_bytes_match_pins_without_checkout_newline_conversion(self):
        self.assertEqual(hashlib.sha256(STOP.read_bytes()).hexdigest(),
                         '3813b6d5655d7f9fe262a90266418b11a27032fa7cdf33a79fedac5dc5e0adfb')
        self.assertEqual(hashlib.sha256(DIAGNOSTIC.read_bytes()).hexdigest(),
                         '3cc1713813ecf49028d129adb92a711242027ab1bd2881ab4354fe74692b78c2')


@unittest.skipUnless(os.name == 'nt', 'Native Windows ACLs')
class NarratorTrustDiagnosticTests(unittest.TestCase):
    def run_ps(self, body):
        header = f"$diagnostic='{DIAGNOSTIC}';$stop='{STOP}'\n" + r'''
$ErrorActionPreference='Stop'
$t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($diagnostic,[ref]$t,[ref]$e)
if($e.Count){throw 'Diagnostic parse failure'}
foreach($name in @('Get-StopTrustDiagnosticFunction','Get-RepairDiagnosticIdentity','Get-RepairTrustFailure')){
 $fn=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq $name)
 if($fn.Count -ne 1){throw 'Missing diagnostic function'}
 . ([ScriptBlock]::Create($fn[0].Extent.Text))
}
$ExpectedOwnerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
. ([ScriptBlock]::Create((Get-StopTrustDiagnosticFunction ([IO.File]::ReadAllBytes($stop)))))
'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', header + body],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_diagnostic_cannot_execute_mutating_commands_or_original_main(self):
        self.run_ps(r'''
$bad=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -in @('Set-Acl','Start-ScheduledTask','Stop-ScheduledTask','Register-ScheduledTask','Remove-Item')},$true))
if($bad.Count){throw 'Read-only diagnostic contains a mutating command'}
$methods=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and ($n.Member.Extent.Text -in @('Stop','Delete') -or ($n.Member.Extent.Text -ceq 'Replace' -and $n.Expression.Extent.Text -in @('[IO.File]','[System.IO.File]')))},$true))
if($methods.Count){throw 'Read-only diagnostic contains a stop/replace/delete method'}
$denied=$false;try{$null=Get-StopTrustDiagnosticFunction ([Text.Encoding]::UTF8.GetBytes('unreviewed'))}catch{$denied=$true}
if(-not $denied){throw 'Unpinned source accepted'}
''')

    def test_native_ancestor_modify_is_identified_despite_tight_leaf_without_acl_repair(self):
        self.run_ps(self.fixture(r'''
$acl=Get-Acl -LiteralPath $ancestor
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','Allow'))
Set-Acl -LiteralPath $ancestor -AclObject $acl
$before=(Get-Acl -LiteralPath $ancestor).Sddl;$failure=$null
try{Assert-StopTrustedPath $leaf}catch{$failure=$_.Exception}
if($null -eq $failure){throw 'Writable ancestor accepted'}
$report=Get-RepairTrustFailure $failure $leaf
if($report.path -ine $ancestor -or $report.principal_sid -cne 'S-1-1-0' -or $report.checked_mask -ne 0xD0040 -or $report.effective_mask -ne 0x10000){throw 'Incorrect original gate context'}
if($report.identity_changed -or $report.gate_acl_changed -or $report.identity_before.links -ne 1){throw 'Native identity/ACL snapshot mismatch'}
if([Runtime.InteropServices.Marshal]::SizeOf([KNRepairTrust.Info]::new()) -ne 52){throw 'Native file identity packing differs'}
$wrapped=[Management.Automation.MethodInvocationException]::new('fixture wrapper',[Management.Automation.RuntimeException]::new('fixture inner',$failure))
$unwrapped=Get-RepairTrustFailure $wrapped $leaf
if($unwrapped.path -ine $ancestor -or $unwrapped.effective_mask -ne 0x10000){throw 'Wrapped native gate context was lost'}
$tooDeep=$failure;for($i=0;$i -lt 8;$i++){$tooDeep=[Management.Automation.RuntimeException]::new('bounded fixture',$tooDeep)}
if((Get-RepairTrustFailure $tooDeep $leaf).error -cne 'trust_failure_without_write_ace_context'){throw 'Exception walk exceeded bound'}
if((Get-Acl -LiteralPath $ancestor).Sddl -cne $before){throw 'Diagnostic repaired the broad ACL'}
'''))

    def test_native_inherit_only_write_rule_is_ignored_by_original_gate(self):
        self.run_ps(self.fixture(r'''
$acl=Get-Acl -LiteralPath $ancestor
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow'))
Set-Acl -LiteralPath $ancestor -AclObject $acl
$before=(Get-Acl -LiteralPath $ancestor).Sddl
Assert-StopTrustedPath $leaf
if((Get-Acl -LiteralPath $ancestor).Sddl -cne $before){throw 'Diagnostic changed inherit-only ACL'}
'''))

    @staticmethod
    def fixture(body):
        return r'''
$folder=Join-Path $env:TEMP ('kn-trust-diagnostic-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder|Out-Null
try{
 $safe=[Security.AccessControl.DirectorySecurity]::new();$safe.SetOwner([Security.Principal.SecurityIdentifier]::new($ExpectedOwnerSid));$safe.SetAccessRuleProtection($true,$false)
 foreach($sid in @($ExpectedOwnerSid,'S-1-5-18','S-1-5-32-544')){$safe.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 Set-Acl -LiteralPath $folder -AclObject $safe
 $ancestor=Join-Path $folder 'ancestor';New-Item -ItemType Directory -Path $ancestor|Out-Null
 $leaf=Join-Path $ancestor 'private.sqlite';[IO.File]::WriteAllText($leaf,'fixture-only')
 $tight=Get-Acl -LiteralPath $leaf;$tight.SetAccessRuleProtection($true,$true);Set-Acl -LiteralPath $leaf -AclObject $tight
''' + body + r'''
}finally{
 $resolved=[IO.Path]::GetFullPath($folder);$allowed=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
 if(-not $resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup escaped TEMP'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
}
'''


if __name__ == '__main__':
    unittest.main()
