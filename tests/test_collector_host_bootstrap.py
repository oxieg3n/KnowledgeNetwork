"""Native checks of bootstrap helpers only; never install an account or service."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows ACL/PowerShell acceptance only')
class HostBootstrapTests(unittest.TestCase):
    def run_helpers(self, body):
        source = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Install-KnowledgeNetworkHostExec.ps1'
        with tempfile.TemporaryDirectory(prefix='kn-bootstrap-check-') as folder:
            # Load only named function ASTs. Top-level privileged bootstrap is never evaluated.
            script = r"""
$ErrorActionPreference = 'Stop'
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
$tokens=$null; $errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($env:KN_TEST_SOURCE,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Bootstrap syntax error' }
foreach ($name in @('Assert-TrustedPath','Protect-Directory','Ipv4-Text')) {
    $fn=@($tree.FindAll({param($a) $a -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -eq $name)
    if ($fn.Count -ne 1) { throw 'Expected one reviewed helper' }
    . ([scriptblock]::Create($fn[0].Extent.Text))
}
$fixture=$env:KN_TEST_FOLDER
""" + body
            result = subprocess.run(
                ['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
                 '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                env=dict(os.environ, KN_TEST_SOURCE=str(source), KN_TEST_FOLDER=folder),
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_acl_trust_and_inherit_only(self):
        self.run_helpers(r"""
Protect-Directory $fixture $current.User.Value $true
Assert-TrustedPath $fixture
$bad=Join-Path $fixture 'unsafe'
New-Item -ItemType Directory -Path $bad | Out-Null
$acl=Get-Acl -LiteralPath $bad
$rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','ContainerInherit,ObjectInherit','None','Allow')
$acl.AddAccessRule($rule); Set-Acl -LiteralPath $bad -AclObject $acl
$denied=$false
try { Assert-TrustedPath $bad } catch { $denied=$true }
if (-not $denied) { throw 'Untrusted write was accepted' }
Protect-Directory $bad $current.User.Value $true
$acl=Get-Acl -LiteralPath $bad
$inherit=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow')
$acl.AddAccessRule($inherit); Set-Acl -LiteralPath $bad -AclObject $acl
Assert-TrustedPath $bad
""")

    def test_ipv4_complement_ranges_exclude_only_forge(self):
        self.run_helpers(r"""
foreach ($number in @([uint64]1677721601,[uint64]1681915903,[uint64]1686109950)) {
    $ranges=@(('0.0.0.0-'+(Ipv4-Text ($number-1))),((Ipv4-Text ($number+1))+'-255.255.255.255'))
    if ($ranges.Count -ne 2) { throw 'Expected exactly two block ranges' }
    foreach ($entry in @(@($ranges[0].Split('-')[1],($number-1)),@($ranges[1].Split('-')[0],($number+1)))) {
        $b=([Net.IPAddress]::Parse($entry[0])).GetAddressBytes()
        $actual=[uint64]$b[0]*16777216+[uint64]$b[1]*65536+[uint64]$b[2]*256+[uint64]$b[3]
        if ($actual -ne [uint64]$entry[1]) { throw 'Complement endpoint differs' }
    }
}
""")


if __name__ == '__main__':
    unittest.main()
