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
foreach ($name in @('Assert-TrustedPath','Protect-Directory','Ipv4-Text','Expand-DispatcherRuntime','Assert-PreparedRuntimeReceipt')) {
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

    def test_account_description_matches_native_parameter_limit(self):
        self.run_helpers(r"""
$calls=@($tree.FindAll({param($a) $a -is [Management.Automation.Language.CommandAst] -and $a.GetCommandName() -eq 'New-LocalUser'},$true))
if ($calls.Count -ne 1) { throw 'Expected one fixed account creation site' }
$elements=$calls[0].CommandElements
$description=$null
for ($i=0; $i -lt $elements.Count-1; $i++) {
    if ($elements[$i] -is [Management.Automation.Language.CommandParameterAst] -and $elements[$i].ParameterName -eq 'Description') { $description=$elements[$i+1].SafeGetValue() }
}
$limits=@((Get-Command New-LocalUser -ErrorAction Stop).Parameters['Description'].Attributes | Where-Object { $_ -is [Management.Automation.ValidateLengthAttribute] })
if ($limits.Count -ne 1 -or -not $description -or $description.Length -gt $limits[0].MaxLength -or $description.Length -lt $limits[0].MinLength) { throw 'Account description exceeds native cmdlet limit' }
""")

    def test_resume_accepts_only_exact_pre_account_receipt(self):
        self.run_helpers(r"""
$valid=[ordered]@{schema_version=1;status='BOOTSTRAP_IN_PROGRESS';service='KnowledgeNetworkHostExec';execution_sid=$null;account='kncollector_exec';port=22230;host_address='100.100.100.20';forge_address='100.100.100.10';dispatcher_sha256=('a'*64);runtime_version='3.14.10';runtime_archive_sha256='90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159';shared_config_sha256=('b'*64);created_at='2026-11-15T00:00:00Z';gateway_service_restarted=$false;publication_paused=$true}
function Check-Receipt($value) { Assert-PreparedRuntimeReceipt $value '100.100.100.20' '100.100.100.10' ('a'*64) ('b'*64) }
$accepted=Check-Receipt ($valid | ConvertTo-Json | ConvertFrom-Json)
$accepted.block_sources=@('one','two')
if ($accepted.block_sources.Count -ne 2) { throw 'Resumed receipt cannot retain new fields' }
foreach ($field in @('status','execution_sid','account','port','host_address','forge_address','dispatcher_sha256','runtime_version','runtime_archive_sha256','shared_config_sha256','created_at','gateway_service_restarted','publication_paused','schema_version','extra')) {
    $bad=$valid | ConvertTo-Json | ConvertFrom-Json
    if ($field -eq 'extra') { $bad | Add-Member -NotePropertyName extra -NotePropertyValue 'untrusted' }
    elseif ($field -eq 'gateway_service_restarted') { $bad.$field=$true }
    elseif ($field -eq 'publication_paused') { $bad.$field=$false }
    elseif ($field -eq 'schema_version') { $bad.$field=$true }
    else { $bad.$field='wrong' }
    $denied=$false
    try { Check-Receipt $bad | Out-Null } catch { $denied=$true }
    if (-not $denied) { throw ('Invalid prepared field accepted: '+$field) }
}
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
        if (@(Expand-DispatcherRuntime $bytes $target -VerifyExisting).Count -ne 37) { throw 'Existing prepared runtime did not verify' }
        $denied=$false
        try { Expand-DispatcherRuntime $bytes $target | Out-Null } catch { $denied=$true }
        if (-not $denied) { throw 'Existing runtime was overwritten' }
        [IO.File]::WriteAllText((Join-Path $target 'python.exe'),'changed')
        $denied=$false
        try { Expand-DispatcherRuntime $bytes $target -VerifyExisting | Out-Null } catch { $denied=$true }
        if (-not $denied -or [IO.File]::ReadAllText((Join-Path $target 'python.exe')) -ne 'changed') { throw 'Changed prepared runtime was accepted or repaired' }
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
