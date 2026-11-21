"""Standalone bootstrap contract/native ACL checks; never installs a live task."""
from tests.fixture_retention import FixtureDirectory
import ast
import json
import os
from pathlib import Path
import subprocess
import unittest



SOURCE = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Install-KnowledgeNetworkNarratorStandalone.ps1'


class StandaloneContractTests(unittest.TestCase):
    def test_only_new_standalone_paths_are_written_and_old_recovery_is_not_invoked(self):
        source = SOURCE.read_text(encoding='utf-8')
        self.assertIn("$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'", source)
        self.assertIn("$taskName='NarratorStandaloneV1'", source)
        self.assertIn("if(Test-Path -LiteralPath $root){throw", source)
        self.assertIn("$f=[IO.File]::Open($Path,'CreateNew','Write','None')", source)
        for forbidden in ('Remove-Item', 'Stop-ScheduledTask', 'Unregister-ScheduledTask', 'Stop-EmptyNarratorController', 'Set-NetFirewall', 'serve reset', '--bg --https=443', '--bg --https=8443'):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('$null=$registered.Run($null)'), 1)
        self.assertLess(source.index('39110 occupied'), source.index('New-Item -ItemType Directory -Path $root'))
        self.assertIn('-LogonType Interactive -RunLevel Limited', source)
        self.assertIn('$settings.AllowHardTerminate=$false', source)
        self.assertEqual(source.count('$routeResult=& $tailscale serve --bg --https=9443 http://127.0.0.1:39110'), 1)
        self.assertIn('Compare-Object $actualAddresses $expectedAddresses', source)
        self.assertIn('approved_v5_typed_object_equal -ne $true', source)
        self.assertLess(source.lower().index('native9443 occupied'), source.index('$routeResult='))
        self.assertEqual(source.count('Start-Service -Name $serviceName -ErrorAction Stop'), 1)
        self.assertIn("if($initial -eq 'Stopped')", source)
        self.assertIn("$serviceName='KnowledgeNetworkHostExec'", source)
        self.assertIn("$service.StartName -cne 'LocalSystem'", source)
        self.assertIn('Dedicated SSH22230 occupied; no service start.', source)
        self.assertNotIn('Restart-Service', source)
        self.assertNotIn('Set-Service', source)

    def test_embedded_launcher_checks_owner_pins_then_reuses_the_existing_host(self):
        source = SOURCE.read_text(encoding='utf-8')
        launcher = source.split("$launcher=@'\n", 1)[1].split("\n'@", 1)[0]
        ast.parse(launcher)
        self.assertLess(launcher.index("identity!={'sid':config['owner_sid'],'elevated':False}"), launcher.index('read_secret(CREDENTIAL_TARGET)'))
        self.assertLess(launcher.index("sha(manifest)!=config['manifest_sha256']"), launcher.index('NarratorManifest(manifest)'))
        self.assertIn("NarratorStore(ROOT/'data',reviewed)", launcher)
        self.assertIn("NarratorHTTPServer(('127.0.0.1',39110),store,secret)", launcher)
        self.assertIn('absent!=401 or wrong!=401 or code!=200', launcher)
        self.assertIn("'inference_submitted':False", launcher)
        self.assertNotIn('write_secret', launcher)
        self.assertNotIn('narrate.ps1', launcher)
        tree = ast.parse(launcher)
        encrypt = [n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id=='encrypt' for t in n.targets)]
        self.assertEqual(len(encrypt), 1)
        self.assertIn('.Encrypt([Text.Encoding]::UTF8.GetBytes($r.secret),$true)', encrypt[0])
        self.assertIn('input=json.dumps', launcher)
        self.assertIn("'algorithm':'RSA2048-OAEP-SHA1'", launcher)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows RSA CSP fixture')
    def test_native_public_only_oaep_roundtrip_rejects_wrong_key_and_private_bundle(self):
        script = r'''
$ErrorActionPreference='Stop'
$key=[Security.Cryptography.RSACryptoServiceProvider]::new(2048)
$pub=[Security.Cryptography.RSACryptoServiceProvider]::new()
$wrong=[Security.Cryptography.RSACryptoServiceProvider]::new(2048)
try{
 foreach($k in @($key,$pub,$wrong)){$k.PersistKeyInCsp=$false}
 $xml=$key.ToXmlString($false);$pub.FromXmlString($xml)
 if(-not $pub.PublicOnly -or $pub.KeySize -ne 2048){throw 'Recipient key validation failed.'}
 $message=[Text.Encoding]::UTF8.GetBytes('owned synthetic envelope fixture, never a real credential')
 $cipher=$pub.Encrypt($message,$true)
 if($cipher.Length -ne 256 -or [Text.Encoding]::UTF8.GetString($key.Decrypt($cipher,$true)) -cne [Text.Encoding]::UTF8.GetString($message)){throw 'OAEP roundtrip failed.'}
 $rejected=$false;try{$null=$wrong.Decrypt($cipher,$true)}catch{$rejected=$true}
 if(-not $rejected){throw 'Wrong key accepted.'}
 if($xml -match '<(?:P|Q|D|DP|DQ|InverseQ)>'){throw 'Public XML includes private material.'}
 if($key.ToXmlString($true) -notmatch '<(?:P|Q|D|DP|DQ|InverseQ)>'){throw 'Private XML positive control failed.'}
 [Console]::Out.Write('{"roundtrip":true,"wrong_key_rejected":true,"public_only":true}')
}finally{foreach($k in @($key,$pub,$wrong)){$k.Dispose()}}
'''
        result = subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'roundtrip':True,'wrong_key_rejected':True,'public_only':True})

    @unittest.skipUnless(os.name == 'nt', 'Native Windows Task Scheduler missing-task mapping')
    def test_native_missing_task_lookup_accepts_only_file_not_found(self):
        lookup = next(line for line in SOURCE.read_text(encoding='utf-8').splitlines()
                      if line.startswith('try{$old=$folder.GetTask($taskName)}'))
        script = r'''
$ErrorActionPreference='Stop'
$lookup=[ScriptBlock]::Create(([Console]::In.ReadToEnd()|ConvertFrom-Json).lookup)
$scheduler=New-Object -ComObject Schedule.Service
$scheduler.Connect()
$folder=$scheduler.GetFolder('\')
$taskName='KnowledgeNetwork-MissingFixture-'+[Guid]::NewGuid().ToString('N')
$native=$null
try{$null=$folder.GetTask($taskName)}catch{$native=$_.Exception}
if($null -eq $native -or $native.HResult -ne -2147024894){throw 'Native missing-task control failed.'}
$old='unchanged'
. $lookup
if($null -ne $old){throw 'Missing task was not accepted.'}
$existing=[PSCustomObject]@{Name='existing-fixture'}
$folder=[PSCustomObject]@{Task=$existing}
$folder|Add-Member ScriptMethod GetTask {param($name) $this.Task}
. $lookup
if(-not [Object]::ReferenceEquals($old,$existing)){throw 'Existing task was hidden.'}
foreach($errorKind in @('access-denied','other-com')){
 $folder=[PSCustomObject]@{ErrorKind=$errorKind}
 $folder|Add-Member ScriptMethod GetTask {
  param($name)
  if($this.ErrorKind -ceq 'access-denied'){throw [UnauthorizedAccessException]::new('denied fixture')}
  throw [Runtime.InteropServices.COMException]::new('other fixture',-2147023728)
 }
 $rejected=$false
 try{. $lookup}catch{$rejected=$true}
 if(-not $rejected){throw 'Unexpected task lookup failure was accepted.'}
}
[Console]::Out.Write('{"native_missing_task":true,"existing_task_preserved":true,"other_errors_rejected":true}')
'''
        result = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                input=json.dumps({'lookup': lookup}), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'native_missing_task': True, 'existing_task_preserved': True,
                                                   'other_errors_rejected': True})

    @unittest.skipUnless(os.name == 'nt', 'Native Windows PowerShell parser/ACL fixture')
    def test_native_parser_and_protected_code_vs_owner_writable_fixture(self):
        with FixtureDirectory(prefix='kn-standalone-acl-', trusted_execution=True) as directory:
            request = json.dumps({'source': str(SOURCE), 'folder': directory})
            script = r'''
$ErrorActionPreference='Stop'
$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($r.source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Bootstrap parse failed.'}
foreach($name in @('Set-NewDirectoryAcl','Assert-AdminCode')){
 $f=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq $name)
 if($f.Count -ne 1){throw 'Function shape changed.'}
 . ([ScriptBlock]::Create($f[0].Extent.Text))
}
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$p=Join-Path $r.folder 'owner-data'
New-Item -ItemType Directory -Path $p -ErrorAction Stop|Out-Null
Set-NewDirectoryAcl $p $sid $true
$a=Get-Acl -LiteralPath $p
$rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if(-not $a.AreAccessRulesProtected -or @($rules|Where-Object IdentityReference -eq ([Security.Principal.SecurityIdentifier]::new($sid))).Count -ne 1){throw 'Owner data ACL did not apply.'}
$rejected=$false
try{Assert-AdminCode $p}catch{$rejected=$true}
if(-not $rejected){throw 'Mutable owner data accepted as protected code.'}
[Console]::Out.Write('{"parsed":true,"private_data_acl":true,"mutable_code_rejected":true}')
'''
            process = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script], input=request, text=True, capture_output=True, timeout=30, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout), {'parsed': True, 'private_data_acl': True, 'mutable_code_rejected': True})


if __name__ == '__main__':
    unittest.main()
