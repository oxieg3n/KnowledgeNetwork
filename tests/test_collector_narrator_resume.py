"""Checked continuation helpers only; no task, service, host or deployment run."""
from tests.fixture_retention import FixtureDirectory
import os
from pathlib import Path
import subprocess
import unittest


@unittest.skipUnless(os.name == 'nt', 'native Windows ACL and PowerShell preflight helpers')
class NarratorResumeTests(unittest.TestCase):
    def helpers(self, body):
        root = Path(__file__).resolve().parents[1]
        with FixtureDirectory(prefix='kn-narrator-resume-', trusted_execution=True, dir='C:/ProgramData') as folder:
            script = r'''
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($env:KN_RESUME_SOURCE,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Resume syntax failed' }
$bt=$null;$be=$null
$bootstrap=[Management.Automation.Language.Parser]::ParseFile($env:KN_BOOTSTRAP_SOURCE,[ref]$bt,[ref]$be)
if ($be.Count) { throw 'Bootstrap syntax failed' }
foreach ($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes','Assert-TrustedExecutionPath')) {
    $node=@($bootstrap.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -ceq $name)
    if ($node.Count -ne 1) { throw 'Expected fixed bootstrap helper' }
    . ([ScriptBlock]::Create($node[0].Extent.Text))
}
foreach ($name in @('Assert-ResumeBootstrapPath','Assert-ResumeReceipt','Assert-ResumeLayout','Assert-PreparedAcls','Assert-BrokerConfiguration')) {
    $node=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -ceq $name)
    if ($node.Count -ne 1) { throw 'Expected fixed resume helper' }
    . ([ScriptBlock]::Create($node[0].Extent.Text))
}
$fixture=$env:KN_RESUME_FIXTURE
$ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
''' + body
            result = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
                                     '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                    env=dict(os.environ, KN_RESUME_SOURCE=str(root / 'docs/collector/host-tools/Resume-KnowledgeNetworkNarratorControl.ps1'),
                                             KN_BOOTSTRAP_SOURCE=str(root / 'docs/collector/host-tools/Install-KnowledgeNetworkNarratorControl.ps1'),
                                             KN_RESUME_FIXTURE=folder),
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prepared_receipt_and_broker_configuration_are_closed_and_exact(self):
        self.helpers(r'''
$bridge='S-1-5-21-1-2-3-1002';$bundle='a'*64
$files=[pscustomobject]@{'__init__.py'=('1'*64);'collector_narrator_pipe.py'=('2'*64);'collector_narrator_control.py'=('3'*64);'collector_narrator_host.py'=('4'*64);'collector_narration_common.py'=('5'*64);'collector_credentials.py'=('6'*64)}
$deployment=[pscustomobject]@{old_dispatcher_sha256=('b'*64);dispatcher_sha256=('c'*64);shared_config_sha256=('d'*64);server_python_sha256=('e'*64);manifest_sha256=('f'*64);files=$files}
$good=[pscustomobject]@{schema_version=1;status='PREPARED';owner_sid=$ownerSid;bridge_sid=$bridge;bundle_sha256=$bundle;old_dispatcher_sha256=$deployment.old_dispatcher_sha256;dispatcher_sha256=$deployment.dispatcher_sha256;shared_config_sha256=$deployment.shared_config_sha256;publication_paused=$true}
Assert-ResumeReceipt $good $deployment $ownerSid $bridge $bundle
foreach ($case in @('version','status','owner','bridge','bundle','pending','publication','extra')) {
    $bad=$good | ConvertTo-Json | ConvertFrom-Json
    switch ($case) {
        version { $bad.schema_version=$true }
        status { $bad.status='TASK_START_REQUESTED' }
        owner { $bad.owner_sid=$bridge }
        bridge { $bad.bridge_sid=$ownerSid }
        bundle { $bad.bundle_sha256='0'*64 }
        pending { $bad.dispatcher_sha256='0'*64 }
        publication { $bad.publication_paused='true' }
        extra { $bad | Add-Member NoteProperty recovery 'clear-state' }
    }
    $denied=$false;try { Assert-ResumeReceipt $bad $deployment $ownerSid $bridge $bundle } catch { $denied=$true }
    if (-not $denied) { throw 'Changed/advanced receipt accepted' }
}
$broker=[pscustomobject]@{schema_version=1;owner_sid=$ownerSid;bridge_sid=$bridge;server_python_sha256=$deployment.server_python_sha256;manifest_sha256=$deployment.manifest_sha256;files=$files}
Assert-BrokerConfiguration $broker $deployment $ownerSid $bridge
foreach ($key in @('status','owner_sid','bridge_sid','bundle_sha256','old_dispatcher_sha256','dispatcher_sha256','shared_config_sha256')) { $bad=$good | ConvertTo-Json | ConvertFrom-Json;$bad.$key=@($bad.$key);$denied=$false;try { Assert-ResumeReceipt $bad $deployment $ownerSid $bridge $bundle } catch { $denied=$true };if (-not $denied) { throw 'Receipt array accepted' } }
foreach ($case in @('identity','file','extra','version','arrayowner','arrayfile')) {
    $bad=$broker | ConvertTo-Json -Depth 5 | ConvertFrom-Json
    switch ($case) {
        arrayowner { $bad.owner_sid=@($bad.owner_sid) }
        arrayfile { $bad.files.'collector_narrator_control.py'=@($bad.files.'collector_narrator_control.py') }
        identity { $bad.owner_sid=$bridge }
        file { $bad.files.'collector_narrator_control.py'='0'*64 }
        extra { $bad | Add-Member NoteProperty command 'whoami' }
        version { $bad.schema_version='1' }
    }
    $denied=$false;try { Assert-BrokerConfiguration $bad $deployment $ownerSid $bridge } catch { $denied=$true }
    if (-not $denied) { throw 'Changed broker accepted' }
}
''')

    def test_bootstrap_path_rejects_nonlocal_and_wrong_paths_before_io(self):
        self.helpers(r'''
$good='D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-control-resume-v1/Install-KnowledgeNetworkNarratorControl.ps1'
$null=Assert-ResumeBootstrapPath $good
foreach ($bad in @('\\server/share/Install-KnowledgeNetworkNarratorControl.ps1','\\?\D:\file.ps1','relative.ps1','D:/projects/../file.ps1','C:/projects/file.ps1','D:/wrong/Install-KnowledgeNetworkNarratorControl.ps1')) {
    $denied=$false;try { $null=Assert-ResumeBootstrapPath $bad } catch { $denied=$true };if (-not $denied) { throw 'Noncanonical bootstrap path accepted' }
}
$commands=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Get-Item' -and $n.Extent.Text.Contains('$BootstrapFile')},$true))
$guard=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Assert-ResumeBootstrapPath'},$true))
if ($commands.Count -ne 1 -or $guard.Count -ne 1 -or $guard[0].Extent.StartOffset -ge $commands[0].Extent.StartOffset) { throw 'Path guard must precede bootstrap filesystem access' }
''')

    def test_runtime_and_upgrade_refuse_advanced_or_extra_state_without_deletion(self):
        self.helpers(r'''
$runtime=Join-Path $fixture 'runtime';$upgrade=Join-Path $fixture 'upgrade'
New-Item -ItemType Directory -Path $runtime,$upgrade | Out-Null
foreach ($name in @('python','youtube_ops')) { New-Item -ItemType Directory -Path (Join-Path $runtime $name) | Out-Null }
foreach ($name in @('collector_host_exec.py','collector_host_exec.next','narrator-control-launch.py')) { [IO.File]::WriteAllText((Join-Path $runtime $name),'fixture only') }
foreach ($name in @('acl-before.private.json','deployment.prepared.private.json','dispatcher.before.py','rollback-source.ps1')) { [IO.File]::WriteAllText((Join-Path $upgrade $name),'fixture only') }
Assert-ResumeLayout $runtime $upgrade
$extra=Join-Path $upgrade 'resume.prepared.private.json';[IO.File]::WriteAllText($extra,'advanced')
$denied=$false;try { Assert-ResumeLayout $runtime $upgrade } catch { $denied=$true }
if (-not $denied -or -not (Test-Path -LiteralPath $extra)) { throw 'Advanced state accepted or deleted' }
[IO.File]::Move($extra,(Join-Path $fixture 'retained-resume.prepared.private.json'))
$extra=Join-Path $runtime 'ctypes.py';[IO.File]::WriteAllText($extra,'untrusted')
$denied=$false;try { Assert-ResumeLayout $runtime $upgrade } catch { $denied=$true }
if (-not $denied -or -not (Test-Path -LiteralPath $extra)) { throw 'Shadow module accepted or deleted' }
''')

    def test_native_prepared_acl_derivation_accepts_only_recorded_plus_owner_rx(self):
        self.helpers(r'''
$paths=@();$before=@();$readSid='S-1-5-21-1-2-3-1001'
# Protected fixture mirrors the accepted runtime; never weaken the production path check.
$base=Get-Acl -LiteralPath $fixture;$base.SetAccessRuleProtection($true,$false)
foreach ($rule in @($base.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))) { $base.RemoveAccessRuleSpecific($rule) }
foreach ($sid in @($ownerSid,'S-1-5-18','S-1-5-32-544')) { $base.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')) };Set-Acl -LiteralPath $fixture -AclObject $base
for ($i=0;$i -lt 41;$i++) {
    $path=Join-Path $fixture ('file-'+$i+'.py');[IO.File]::WriteAllText($path,'fixture only')
    $acl=Get-Acl -LiteralPath $path;$acl.SetAccessRuleProtection($true,$false)
    foreach ($rule in @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))) { $acl.RemoveAccessRuleSpecific($rule) }
    foreach ($sid in @($ownerSid,'S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','Allow')) };Set-Acl -LiteralPath $path -AclObject $acl
    $acl=Get-Acl -LiteralPath $path
    $paths+=$path;$before+=[pscustomobject]@{path=$path;sddl=$acl.Sddl}
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($readSid),'ReadAndExecute','Allow'))
    Set-Acl -LiteralPath $path -AclObject $acl
}
Assert-PreparedAcls $before $paths $readSid
foreach ($case in @('missing','duplicate','extra','outside')) {
    $bad=$before | ConvertTo-Json -Depth 4 | ConvertFrom-Json
    switch ($case) {
        missing { $bad=@($bad | Select-Object -Skip 1) }
        duplicate { $bad[1].path=$bad[0].path }
        extra { $bad[0] | Add-Member NoteProperty writable $true }
        outside { $bad[0].path='C:/Windows/System32/cmd.exe' }
    }
    $denied=$false;try { Assert-PreparedAcls $bad $paths $readSid } catch { $denied=$true }
    if (-not $denied) { throw 'Changed ACL record accepted' }
}
$acl=Get-Acl -LiteralPath $paths[0];$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'Delete','Deny'));Set-Acl -LiteralPath $paths[0] -AclObject $acl
$drift=(Get-Acl -LiteralPath $paths[0]).Sddl
$denied=$false;try { Assert-PreparedAcls $before $paths $readSid } catch { $denied=$true }
if (-not $denied -or (Get-Acl -LiteralPath $paths[0]).Sddl -cne $drift) { throw 'ACL drift accepted or rewritten' }
''')

    def test_actual_pending_hash_guard_and_typed_null_replacement_preserve_acl(self):
        self.helpers(r'''
Initialize-FileIdentity
$runtime=Join-Path $fixture 'runtime';New-Item -ItemType Directory -Path $runtime | Out-Null
$target=Join-Path $runtime 'collector_host_exec.py';$pending=Join-Path $runtime 'collector_host_exec.next'
$old=[byte[]]@(1,2,3);$new=[byte[]]@(0,255,8,9)
[IO.File]::WriteAllBytes($target,$old);[IO.File]::WriteAllBytes($pending,[byte[]]@(9,9))
$acl=Get-Acl -LiteralPath $target;$acl.SetAccessRuleProtection($true,$true);Set-Acl -LiteralPath $target -AclObject $acl
$deployment=[pscustomobject]@{dispatcher_sha256=(Get-BytesHash $new)}
$commands=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Read-RegularBytes' -and $n.CommandElements[1].Extent.Text -ceq '"$runtime/collector_host_exec.next"'},$true))
if ($commands.Count -ne 1) { throw 'Expected one fixed pre-replacement pending-file pin gate' }
$denied=$false;try { . ([ScriptBlock]::Create('$null = '+$commands[0].Extent.Text)) } catch { $denied=$true }
if (-not $denied -or (Get-BytesHash ([IO.File]::ReadAllBytes($target))) -cne (Get-BytesHash $old) -or -not [IO.File]::Exists($pending)) { throw 'Pending-byte drift accepted or state changed' }
[IO.File]::WriteAllBytes($pending,$new)
. ([ScriptBlock]::Create('$null = '+$commands[0].Extent.Text))
$calls=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Expression.Extent.Text -ceq '[IO.File]' -and $n.Member.Value -ceq 'Replace'},$true))
if ($calls.Count -ne 1 -or $calls[0].Arguments[2].Extent.Text -cne '[System.Management.Automation.Language.NullString]::Value') { throw 'Expected exact corrected atomic replacement' }
$acl=(Get-Acl -LiteralPath $target).Sddl
. ([ScriptBlock]::Create($calls[0].Extent.Text))
if ([IO.File]::Exists($pending) -or (Get-BytesHash ([IO.File]::ReadAllBytes($target))) -cne (Get-BytesHash $new) -or (Get-Acl -LiteralPath $target).Sddl -cne $acl -or @(Get-ChildItem -LiteralPath $runtime).Count -ne 1) { throw 'Replacement bytes/ACL/source consumption differs' }
if (@($tree.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -cin @('Set-Acl','New-LocalUser','New-Service','New-NetFirewallRule','Stop-Process','Stop-ScheduledTask')},$true)).Count) { throw 'Resume contains forbidden account/permission/network/process mutation' }
''')


if __name__ == '__main__':
    unittest.main()
