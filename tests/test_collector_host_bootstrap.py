"""Native checks of bootstrap helpers only; never install an account or service."""
import os
import re
import zipfile
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows ACL/PowerShell acceptance only')
class HostBootstrapTests(unittest.TestCase):
    def run_helpers(self, body, archives=None):
        source = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Install-KnowledgeNetworkHostExec.ps1'
        with tempfile.TemporaryDirectory(prefix='kn-bootstrap-check-') as folder:
            for name, data in (archives or {}).items():
                (Path(folder) / name).write_bytes(data)
            # Load only named function ASTs. Top-level privileged bootstrap is never evaluated.
            script = r"""
$ErrorActionPreference = 'Stop'
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
$tokens=$null; $errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($env:KN_TEST_SOURCE,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Bootstrap syntax error' }
foreach ($name in @('Assert-TrustedPath','Protect-Directory','Ipv4-Text','Expand-DispatcherRuntime')) {
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
try { Assert-TrustedPath $bad } catch {
    $denied=$true
    if ($_.Exception.Data['checked_path'] -ne $bad -or $_.Exception.Data['principal_sid'] -ne 'S-1-1-0') { throw 'Private trust diagnostic context missing' }
}
if (-not $denied) { throw 'Untrusted write was accepted' }
Protect-Directory $bad $current.User.Value $true
$acl=Get-Acl -LiteralPath $bad
$inherit=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow')
$acl.AddAccessRule($inherit); Set-Acl -LiteralPath $bad -AclObject $acl
Assert-TrustedPath $bad
$loader=Join-Path $fixture 'loader'
New-Item -ItemType Directory -Path $loader | Out-Null
$acl=Get-Acl -LiteralPath $loader
$create=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'CreateFiles','Allow')
$acl.AddAccessRule($create); Set-Acl -LiteralPath $loader -AclObject $acl
$denied=$false
try { Assert-TrustedPath $loader } catch { $denied=$true }
if (-not $denied) { throw 'Loader directory create-file rights were accepted' }
""")

    def test_runtime_archive_validation_and_no_overwrite(self):
        import io
        source = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Install-KnowledgeNetworkHostExec.ps1'
        allowed = re.search(r"\$allowed = @\(([^\n]+)\)", source.read_text()).group(1)
        names = re.findall(r"'([^']+)'", allowed)
        self.assertEqual(len(names), 37)
        def archive(kind):
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as z:
                for index, name in enumerate(names):
                    if index == 0:
                        name = {'traversal': '../python.exe', 'duplicate': names[1],
                                'case': 'PYTHON.EXE', 'directory': 'python.exe/'}.get(kind, name)
                    item = zipfile.ZipInfo(name)
                    if index == 0 and kind == 'symlink':
                        item.create_system = 3
                        item.external_attr = 0o120777 << 16
                    z.writestr(item, b'x')
            return data.getvalue()
        fixtures = {kind+'.zip': archive(kind) for kind in ('valid','traversal','duplicate','case','directory','symlink')}
        self.run_helpers(r"""
foreach ($kind in @('valid','traversal','duplicate','case','directory','symlink')) {
    $target=Join-Path $fixture $kind
    New-Item -ItemType Directory -Path $target | Out-Null
    $bytes=[IO.File]::ReadAllBytes((Join-Path $fixture ($kind+'.zip')))
    $denied=$false
    try { $records=@(Expand-DispatcherRuntime $bytes $target) } catch { $denied=$true }
    if ($kind -eq 'valid') {
        if ($denied -or $records.Count -ne 37) { throw 'Expected valid bounded extraction' }
        foreach ($record in $records) { if ($record.sha256 -ne '2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881') { throw 'Extracted hash differs' } }
        $denied=$false
        try { Expand-DispatcherRuntime $bytes $target | Out-Null } catch { $denied=$true }
        if (-not $denied) { throw 'Existing runtime was overwritten' }
    } elseif (-not $denied -or @(Get-ChildItem -LiteralPath $target -Force).Count) { throw 'Unsafe archive was not rejected before extraction' }
}
""", fixtures)

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

    def test_diagnostic_uses_bounded_hash_verified_captured_text(self):
        self.run_helpers(r"""
$diagnostic=Join-Path (Split-Path -Parent $env:KN_TEST_SOURCE) 'Inspect-KnowledgeNetworkHostExecTrust.ps1'
$source=[IO.File]::ReadAllText($diagnostic)
$begin=$source.IndexOf('$stream=')
$end=$source.IndexOf('$current =',$begin)
if ($begin -lt 0 -or $end -le $begin) { throw 'Expected source capture block' }
$capture=[scriptblock]::Create($source.Substring($begin,$end-$begin))
$bootstrap=Join-Path $fixture 'captured-source.ps1'
[IO.File]::WriteAllText($bootstrap,'# reviewed source',[Text.UTF8Encoding]::new($false))
$BootstrapSha256=(Get-FileHash -LiteralPath $bootstrap -Algorithm SHA256).Hash.ToLowerInvariant()
. $capture
[IO.File]::WriteAllText($bootstrap,'# replaced source')
if ($text -cne '# reviewed source') { throw 'Captured source was reread' }
$denied=$false
try { . $capture } catch { $denied=$true }
if (-not $denied) { throw 'Source pin mismatch was accepted' }
[IO.File]::WriteAllBytes($bootstrap,(New-Object byte[] 262145))
$denied=$false
try { . $capture } catch { $denied=$true }
if (-not $denied) { throw 'Oversized source was accepted' }
""")


if __name__ == '__main__':
    unittest.main()
