"""Native fixtures; FORGE task checks are opt-in and never deploy on the host."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell/file security helpers')
class NarratorBootstrapTests(unittest.TestCase):
    def helpers(self, body, prepare=None):
        source = Path(__file__).resolve().parents[1] / 'docs/collector/host-tools/Install-KnowledgeNetworkNarratorControl.ps1'
        with tempfile.TemporaryDirectory(prefix='kn-narrator-bootstrap-') as folder:
            if prepare: prepare(Path(folder))
            script = r'''
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
$tokens=$null;$parseErrors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($env:KN_BOOTSTRAP_SOURCE,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'Bootstrap syntax failed' }
foreach ($name in @('Get-BytesHash','Initialize-FileIdentity','Read-RegularBytes','Write-NewBytes','Assert-TrustedExecutionPath','Assert-RuntimeLayout','Assert-DeploymentManifest','Convert-StrictJson','Assert-TaskXml','Assert-TaskSecurity')) {
    $node=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -ceq $name)
    if ($node.Count -ne 1) { throw 'Expected one helper definition' }
    . ([ScriptBlock]::Create($node[0].Extent.Text))
}
$fixture=$env:KN_BOOTSTRAP_FIXTURE
$ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$oldDispatcherHash='637c92f13126c2ccb5a2eeb888cc4ac48a8a540cf74652f96dc268ce12600bf2'
$files=@('__init__.py','collector_narrator_pipe.py','collector_narrator_control.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
''' + body
            result = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
                                     '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                    env=dict(os.environ, KN_BOOTSTRAP_SOURCE=str(source), KN_BOOTSTRAP_FIXTURE=folder,
                                             KN_BOOTSTRAP_PYTHON=getattr(sys, '_base_executable', sys.executable),
                                             KN_BOOTSTRAP_OUTPUT=str(source.parents[3] / 'output')),
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

    def test_native_file_identity_capture_hash_limits_and_empty_marker(self):
        self.helpers(r'''
Initialize-FileIdentity
if ([Runtime.InteropServices.Marshal]::SizeOf([type][KNCollectorNarratorBootstrap.FileIdentity]) -ne 52) { throw 'Wrong native file-info layout' }
$path=Join-Path $fixture 'ordinary.py'
$data=[Text.Encoding]::UTF8.GetBytes('fixture only')
[IO.File]::WriteAllBytes($path,$data)
$captured=Read-RegularBytes $path 100 (Get-BytesHash $data)
if ([Convert]::ToBase64String($captured) -cne [Convert]::ToBase64String($data)) { throw 'Capture bytes differ' }
foreach ($case in @('limit','hash')) {
    $denied=$false
    try { if ($case -eq 'limit') { $null=Read-RegularBytes $path 1 (Get-BytesHash $data) } else { $null=Read-RegularBytes $path 100 ('0'*64) } } catch { $denied=$true }
    if (-not $denied) { throw 'Capture trust failure accepted' }
}
$empty=Join-Path $fixture '__init__.py';[IO.File]::WriteAllBytes($empty,[byte[]]@())
$emptyHash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
$captured=Read-RegularBytes $empty 100 $emptyHash
if ($captured.Length -ne 0) { throw 'Empty marker changed' }
Write-NewBytes (Join-Path $fixture 'written-empty.py') $captured
if ((Get-Item -LiteralPath (Join-Path $fixture 'written-empty.py')).Length -ne 0) { throw 'Empty marker copy failed' }
$other=Join-Path $fixture 'empty.py';[IO.File]::WriteAllBytes($other,[byte[]]@())
$denied=$false;try { $null=Read-RegularBytes $other 100 $emptyHash } catch { $denied=$true }
if (-not $denied) { throw 'Unapproved empty source accepted' }
''')

    def test_native_hardlink_is_rejected(self):
        def prepare(folder):
            source = folder / 'original.py'; source.write_text('fixture only')
            os.link(source, folder / 'linked.py')
        self.helpers(r'''
Initialize-FileIdentity
$denied=$false;try { $null=Read-RegularBytes (Join-Path $fixture 'linked.py') 100 $null } catch { $denied=$true }
if (-not $denied) { throw 'Native hardlink accepted' }
''', prepare)

    def test_execution_trust_rejects_broad_write_without_repair(self):
        self.helpers(r'''
$path=Join-Path $fixture 'untrusted-code.py';[IO.File]::WriteAllText($path,'fixture only')
$acl=Get-Acl -LiteralPath $path
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Write','Allow'))
Set-Acl -LiteralPath $path -AclObject $acl
$before=(Get-Acl -LiteralPath $path).Sddl
$denied=$false;try { Assert-TrustedExecutionPath $path } catch { $denied=$true }
if (-not $denied -or (Get-Acl -LiteralPath $path).Sddl -cne $before) { throw 'Untrusted code write permission accepted or rewritten' }
''')

    def test_native_null_dacl_is_rejected_without_repair(self):
        self.helpers(r'''
$path=Join-Path $fixture 'null-dacl.py';[IO.File]::WriteAllText($path,'fixture only')
$acl=[Security.AccessControl.FileSecurity]::new()
$acl.SetSecurityDescriptorSddlForm("O:${ownerSid}G:SYD:NO_ACCESS_CONTROL")
Set-Acl -LiteralPath $path -AclObject $acl
$before=(Get-Acl -LiteralPath $path).Sddl
$raw=[Security.AccessControl.RawSecurityDescriptor]::new((Get-Acl -LiteralPath $path).GetSecurityDescriptorBinaryForm(),0)
if ($null -ne $raw.DiscretionaryAcl) { throw 'Fixture is not an actual null DACL' }
$denied=$false;try { Assert-TrustedExecutionPath $path } catch { $denied=$true }
if (-not $denied -or (Get-Acl -LiteralPath $path).Sddl -cne $before) { throw 'Null DACL accepted or rewritten' }
''')

    def test_preexisting_runtime_shadow_module_is_rejected_not_deleted(self):
        self.helpers(r'''
$runtime=Join-Path $fixture 'runtime';New-Item -ItemType Directory -Path (Join-Path $runtime 'python') -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $runtime 'collector_host_exec.py'),'fixture only')
Assert-RuntimeLayout $runtime
$foreign=Join-Path $runtime 'ctypes.py';[IO.File]::WriteAllText($foreign,'untrusted fixture')
$denied=$false;try { Assert-RuntimeLayout $runtime } catch { $denied=$true }
if (-not $denied -or -not (Test-Path -LiteralPath $foreign)) { throw 'Runtime shadow accepted or deleted' }
''')

    def test_rollback_state_guards_recheck_after_disable_before_source_mutation(self):
        self.helpers(r"""
$literal=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.StringConstantExpressionAst] -and $n.Value.StartsWith('$ErrorActionPreference') -and $n.Value.Contains('@OWNER@')},$true))
if ($literal.Count -ne 1) { throw 'Expected one fixed rollback template' }
$rt=$null;$re=$null;$rollback=[Management.Automation.Language.Parser]::ParseInput($literal[0].Value,[ref]$rt,[ref]$re)
if ($re.Count) { throw 'Rollback template syntax failed' }
$before=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -ceq '$task.State -notin @(''Ready'',''Disabled'')'},$true))
$after=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -ceq '$afterDisable.State -cne ''Disabled'''},$true))
$disable=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -ceq 'Disable-ScheduledTask'},$true))
$query=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$afterDisable'},$true))
$replace=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Member.Value -ceq 'Replace'},$true))
if ($before.Count -ne 1 -or $after.Count -ne 1 -or $disable.Count -ne 1 -or $query.Count -ne 1 -or $replace.Count -ne 1 -or $disable[0].Extent.EndOffset -ge $query[0].Extent.StartOffset -or $query[0].Extent.EndOffset -ge $after[0].Extent.StartOffset -or $after[0].Extent.EndOffset -ge $replace[0].Extent.StartOffset) { throw 'Rollback state guard ordering differs' }
foreach ($state in @('Ready','Disabled','Running','Queued','Unknown')) {
    $task=[pscustomobject]@{State=$state};$denied=$false
    try { . ([ScriptBlock]::Create($before[0].Extent.Text)) } catch { $denied=$true }
    if ($denied -ne ($state -notin @('Ready','Disabled'))) { throw 'Rollback pre-disable state accepted incorrectly' }
    $afterDisable=[pscustomobject]@{State=$state};$denied=$false
    try { . ([ScriptBlock]::Create($after[0].Extent.Text)) } catch { $denied=$true }
    if ($denied -ne ($state -cne 'Disabled')) { throw 'Rollback after-disable race accepted' }
}
if (@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -in @('Stop-ScheduledTask','Stop-Process','taskkill')},$true)).Count) { throw 'Rollback forcibly terminates owner work' }
""")

    def test_native_atomic_replace_uses_typed_null_in_deployment_and_rollback(self):
        self.helpers(r'''
$main=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Expression.Extent.Text -ceq '[IO.File]' -and $n.Member.Value -ceq 'Replace'},$true))
$literal=@($tree.FindAll({param($n) $n -is [Management.Automation.Language.StringConstantExpressionAst] -and $n.Value.StartsWith('$ErrorActionPreference') -and $n.Value.Contains('@OWNER@')},$true))
if ($main.Count -ne 1 -or $literal.Count -ne 1) { throw 'Expected exact deployment and rollback call sites' }
$rt=$null;$re=$null;$rollback=[Management.Automation.Language.Parser]::ParseInput($literal[0].Value,[ref]$rt,[ref]$re)
$undo=@($rollback.FindAll({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Expression.Extent.Text -ceq '[IO.File]' -and $n.Member.Value -ceq 'Replace'},$true))
if ($re.Count -or $undo.Count -ne 1) { throw 'Expected one valid rollback replacement' }
$root=$fixture;$runtime=Join-Path $root 'runtime';New-Item -ItemType Directory -Path $runtime | Out-Null
$target=Join-Path $runtime 'collector_host_exec.py';$temp=Join-Path $runtime 'collector_host_exec.rollback'
$old=[byte[]]@(1,2,3);$new=[byte[]]@(0,255,8,9)
$calls=@($main[0],$undo[0])
for ($i=0; $i -lt $calls.Count; $i++) {
    $call=$calls[$i]
    if ($call.Arguments.Count -ne 3 -or $call.Arguments[2].Extent.Text -cne '[System.Management.Automation.Language.NullString]::Value') { throw 'Replacement does not preserve an actual null backup argument' }
    $source=if ($i -eq 0) { Join-Path $runtime 'collector_host_exec.next' } else { $temp }
    [IO.File]::WriteAllBytes($target,$old);[IO.File]::WriteAllBytes($source,$new)
    $acl=Get-Acl -LiteralPath $target;$acl.SetAccessRuleProtection($true,$true);Set-Acl -LiteralPath $target -AclObject $acl
    $before=(Get-Acl -LiteralPath $target).Sddl
    if ($i -eq 0) {
        $rejected=$false
        try { [IO.File]::Replace($source,$target,$null) } catch { $rejected=$_.Exception.InnerException -is [ArgumentException] }
        if (-not $rejected -or (Get-BytesHash ([IO.File]::ReadAllBytes($target))) -cne (Get-BytesHash $old) -or -not [IO.File]::Exists($source)) { throw 'Original Windows PowerShell null binding failure did not reproduce safely' }
    }
    . ([ScriptBlock]::Create($call.Extent.Text))
    if ((Get-BytesHash ([IO.File]::ReadAllBytes($target))) -cne (Get-BytesHash $new) -or [IO.File]::Exists($source) -or (Get-Acl -LiteralPath $target).Sddl -cne $before -or @(Get-ChildItem -LiteralPath $runtime -Force).Count -ne 1) { throw 'Atomic replacement changed bytes, ACL or backup behavior' }
    [IO.File]::Delete($target)
}
''')

    def test_native_reparse_file_is_rejected(self):
        def prepare(folder):
            source = folder / 'original.py'; source.write_text('fixture only')
            try:
                os.symlink(source, folder / 'reparse.py')
            except OSError as error:
                self.skipTest('Native symlink creation unavailable: ' + str(error.winerror))
        self.helpers(r'''
Initialize-FileIdentity
$denied=$false;try { $null=Read-RegularBytes (Join-Path $fixture 'reparse.py') 100 $null } catch { $denied=$true }
if (-not $denied) { throw 'Native reparse accepted' }
''', prepare)

    def test_strict_deployment_schema_and_duplicate_fields(self):
        self.helpers(r'''
$p=[ordered]@{};foreach ($name in $files) { $p[$name]='a'*64 }
$good=[ordered]@{schema_version=1;old_dispatcher_sha256=$oldDispatcherHash;dispatcher_sha256=('b'*64);files=$p;manifest_sha256=('c'*64);server_python_sha256=('d'*64);shared_config_sha256=('e'*64);launcher_sha256=('f'*64)}
$text=$good | ConvertTo-Json -Depth 5
$value=Assert-DeploymentManifest ($text | ConvertFrom-Json)
foreach ($case in @('old','bool','extra','path','hash','file')) {
    $bad=$text | ConvertFrom-Json
    switch ($case) {
        old { $bad.old_dispatcher_sha256='0'*64 }
        bool { $bad.schema_version=$true }
        extra { $bad | Add-Member NoteProperty command 'whoami' }
        path { $bad.files | Add-Member NoteProperty '../outside.py' ('a'*64) }
        hash { $bad.dispatcher_sha256='invalid' }
        file { $bad.files.PSObject.Properties.Remove('__init__.py') }
    }
    $denied=$false;try { $null=Assert-DeploymentManifest $bad } catch { $denied=$true }
    if (-not $denied) { throw 'Malformed deployment accepted' }
}
$bytes=[Text.Encoding]::UTF8.GetBytes($text)
try { $value=Convert-StrictJson $bytes $env:KN_BOOTSTRAP_PYTHON } catch {
    # Diagnose only this synthetic fixture without printing JSON, local paths or stderr.
    $parser=@($tree.FindAll({param($a) $a -is [Management.Automation.Language.StringConstantExpressionAst] -and $a.Value.StartsWith('import json,sys')},$true))
    if($parser.Count -ne 1){throw 'Strict JSON fixture failed; validator diagnostic unavailable'}
    $diagnostic=$parser[0].Value.Replace('except Exception: sys.exit(1)','except Exception as error: print(type(error).__name__,file=sys.stderr); sys.exit(1)')
    $preference=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        $details=@([Text.UTF8Encoding]::new($false,$true).GetString($bytes) | & $env:KN_BOOTSTRAP_PYTHON -I -S -B -c $diagnostic 2>&1)
        $diagnosticExit=$LASTEXITCODE
        $version=@(& $env:KN_BOOTSTRAP_PYTHON -I -S -B -c 'import sys;print(sys.version_info.major,sys.version_info.minor,sys.version_info.micro)' 2>$null)
        $inputProbe=@'
import json,sys
b=sys.stdin.buffer.read()
s=b.decode(sys.stdin.encoding,errors='replace')
r=dict(byte_length=len(b),length=len(s),first=ord(s[0]) if s else None,codepoints=[ord(c) for c in s[:8]],prefix_hex=b[:8].hex(),encoding=sys.stdin.encoding)
try: json.loads(s)
except json.JSONDecodeError as e: r.update(error=e.msg,line=e.lineno,pos=e.pos)
print(json.dumps(r))
'@
        $observed=@([Text.UTF8Encoding]::new($false,$true).GetString($bytes) | & $env:KN_BOOTSTRAP_PYTHON -I -S -B -c $inputProbe 2>$null)
    } finally {$ErrorActionPreference=$preference}
    $kind='unclassified'
    foreach($entry in $details){foreach($candidate in @('JSONDecodeError','SyntaxError','UnicodeDecodeError','ModuleNotFoundError','ImportError','IndentationError','NameError','TypeError')){if($entry.ToString().Contains($candidate)){$kind=$candidate}}}
    $safeVersion=($version -join ' ')
    if($safeVersion -notmatch '^\d+ \d+ \d+$'){$safeVersion='unverified'}
    throw ('Strict JSON valid fixture failed: nativeExit='+$diagnosticExit+' python='+$safeVersion+' errorClass='+$kind+' syntheticInputProbe='+($observed -join ' '))
}
foreach ($text in @('{"x":1,"x":2}','{"x":NaN}')) {
    $denied=$false;try { $null=Convert-StrictJson ([Text.Encoding]::UTF8.GetBytes($text)) $env:KN_BOOTSTRAP_PYTHON } catch { $denied=$true }
    if (-not $denied) { throw 'Ambiguous JSON accepted' }
}
''')

    def test_strict_json_accepts_optional_utf8_bom_and_restores_caller_encoding(self):
        self.helpers(r'''
$good='{"schema_version":1}'
function Convert-SyntheticPositive([byte[]]$Payload,[string]$Label,[object]$Mode){
 try{return (Convert-StrictJson $Payload $env:KN_BOOTSTRAP_PYTHON)}catch{
  $decoded=[Text.UTF8Encoding]::new($false,$true).GetString($Payload)
  $summary=@{case=$Label;encoding=$Mode.WebName;codepage=$Mode.CodePage;preamble_length=$Mode.GetPreamble().Length;input_bytes=$Payload.Length;input_prefix=([BitConverter]::ToString($Payload[0..([Math]::Min(7,$Payload.Length-1))]));input_codepoints=@($decoded.ToCharArray()|Select-Object -First 8|ForEach-Object{[int]$_})}
  $probe=@'
import json,sys
b=sys.stdin.buffer.read()
r=dict(wire_prefix=b[:12].hex(),wire_length=len(b),stdin_encoding=sys.stdin.encoding)
try:
    s=b.decode('utf-8-sig')
    json.loads(s)
    r.update(parsed=True)
except Exception as e:
    r.update(error_class=type(e).__name__,error=getattr(e,'msg',None),pos=getattr(e,'pos',None))
print(json.dumps(r))
'@
  if($decoded.Length -gt 0 -and $decoded[0] -eq [char]0xFEFF){$decoded=$decoded.Substring(1)}
  try{$summary.wire_probe=($decoded|& $env:KN_BOOTSTRAP_PYTHON -I -S -B -c $probe)|ConvertFrom-Json}catch{$summary.wire_probe='unavailable'}
  throw ('Synthetic positive JSON failed: '+($summary|ConvertTo-Json -Compress -Depth 4))
 }
}
$previousEncoding=$OutputEncoding
try {
foreach($encoding in @([Text.Encoding]::ASCII,[Text.UTF8Encoding]::new($false),[Text.UTF8Encoding]::new($true))){
 $OutputEncoding=$encoding
 $body=[Text.Encoding]::UTF8.GetBytes($good)
 foreach($case in @(@{name='plain';payload=$body},@{name='one-input-signature';payload=([byte[]](@(239,187,191)+$body))})){
  $value=Convert-SyntheticPositive $case.payload $case.name $encoding
  if($value.schema_version -ne 1){throw 'Optional input/transport BOM valid JSON failed'}
 }
 $denied=$false
 try{$null=Convert-StrictJson ([byte[]](@(239,187,191,239,187,191)+$body)) $env:KN_BOOTSTRAP_PYTHON}catch{$denied=$true}
 if(-not $denied){throw 'Double input BOM accepted'}
 if($encoding.CodePage -eq 65001){
  $inside='{"x":"'+[char]0xFEFF+'"}'
  $value=Convert-SyntheticPositive ([Text.Encoding]::UTF8.GetBytes($inside)) 'quoted-embedded-FEFF' $encoding
  if($value.x.Length -ne 1 -or [int][char]$value.x[0] -ne 65279){throw 'Signature character inside quoted value changed'}
 }
 foreach($invalid in @('{"x":1,"x":2}','{"x":NaN}')){
  $denied=$false
  try{$null=Convert-StrictJson ([Text.Encoding]::UTF8.GetBytes($invalid)) $env:KN_BOOTSTRAP_PYTHON}catch{$denied=$true}
  if(-not $denied){throw 'Duplicate or nonfinite JSON accepted'}
 }
 $denied=$false
 try{$null=Convert-StrictJson ([byte[]]@(255)) $env:KN_BOOTSTRAP_PYTHON}catch{$denied=$true}
 if(-not $denied){throw 'Invalid UTF8 accepted'}
}
} finally {$OutputEncoding=$previousEncoding}
if(-not [object]::ReferenceEquals($OutputEncoding,$previousEncoding)){throw 'Caller encoding was not restored'}
''')

    def test_task_xml_rejects_elevation_other_owner_extra_actions_or_triggers(self):
        self.helpers(r'''
$sid='S-1-5-21-100-200-300-1001'
$good='<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Principals><Principal><UserId>S-1-5-21-100-200-300-1001</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Triggers/><Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><AllowHardTerminate>false</AllowHardTerminate></Settings><Actions><Exec><Command>C:/protected/python.exe</Command><Arguments>-I -S -B C:/protected/launcher.py</Arguments><WorkingDirectory>C:/protected</WorkingDirectory></Exec></Actions></Task>'
Assert-TaskXml $good $sid 'C:/protected/python.exe' '-I -S -B C:/protected/launcher.py' 'C:/protected'
Assert-TaskXml ($good.Replace('PT0S','P0D')) $sid 'C:/protected/python.exe' '-I -S -B C:/protected/launcher.py' 'C:/protected'
Assert-TaskXml ($good.Replace('<RunLevel>LeastPrivilege</RunLevel>','')) $sid 'C:/protected/python.exe' '-I -S -B C:/protected/launcher.py' 'C:/protected' 'Limited'
$denied=$false;try { Assert-TaskXml ($good.Replace('<RunLevel>LeastPrivilege</RunLevel>','')) $sid 'C:/protected/python.exe' '-I -S -B C:/protected/launcher.py' 'C:/protected' } catch { $denied=$true }
if (-not $denied) { throw 'Omitted run level accepted without native Limited evidence' }
foreach ($bad in @($good.Replace('LeastPrivilege','HighestAvailable'),$good.Replace('InteractiveToken','S4U'),$good.Replace($sid,'S-1-5-18'),$good.Replace('<Triggers/>','<Triggers><BootTrigger/></Triggers>'),$good.Replace('</Actions>','<Exec><Command>cmd.exe</Command></Exec></Actions>'),$good.Replace('C:/protected/python.exe','C:/untrusted/python.exe'),$good.Replace('PT0S','PT1H'),$good.Replace('IgnoreNew','StopExisting'),$good.Replace('<AllowHardTerminate>false','<AllowHardTerminate>true'),$good.Replace('<StopIfGoingOnBatteries>false','<StopIfGoingOnBatteries>true'),$good.Replace('<DisallowStartIfOnBatteries>false','<DisallowStartIfOnBatteries>true'),$good.Replace('</Settings>','<RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure></Settings>'))) {
    $denied=$false;try { Assert-TaskXml $bad $sid 'C:/protected/python.exe' '-I -S -B C:/protected/launcher.py' 'C:/protected' } catch { $denied=$true }
    if (-not $denied) { throw 'Unsafe task accepted' }
}
$sddl="O:${sid}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${sid})"
Assert-TaskSecurity $sddl $sid
$denied=$false;try { Assert-TaskSecurity ($sddl+'(A;;FA;;;WD)') $sid } catch { $denied=$true }
if (-not $denied) { throw 'Broad task DACL accepted' }
if (-not (Get-Command New-ScheduledTaskSettingsSet -ErrorAction Stop).Parameters.ContainsKey('DisallowHardTerminate')) { throw 'Required native task setting is unavailable' }
''')

    @unittest.skipUnless(os.environ.get('KN_NARRATOR_TASK_FIXTURE') == '1',
                         'explicit opt-in isolated FORGE Task Scheduler registration; never started')
    def test_native_isolated_task_registration_export_and_security(self):
        receipt = Path(__file__).resolve().parents[1] / 'output/narrator-control-task-fixture.json'
        if receipt.exists(): self.skipTest('One-time native fixture receipt already retained')
        output = self.helpers(r'''
$folderName='KNCollectorNarratorControlTest-'+[guid]::NewGuid().ToString('N')
if ($folderName -cnotmatch '^KNCollectorNarratorControlTest-[a-f0-9]{32}$') { throw 'Fixture path invalid' }
$path='\'+$folderName+'\';$name='NativeFixture'
$service=New-Object -ComObject Schedule.Service;$service.Connect();$top=$service.GetFolder('\')
$sddl="O:${ownerSid}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${ownerSid})"
$folder=$null;$registered=$false;$cleaned=$false
try {
    $folder=$top.CreateFolder($folderName,$sddl)
    $exe='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
    $args='-NoLogo -NoProfile -NonInteractive -Command exit 0'
    $working='C:/Windows/System32'
    $action=New-ScheduledTaskAction -Execute $exe -Argument $args -WorkingDirectory $working
    $principal=New-ScheduledTaskPrincipal -UserId $ownerSid -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DisallowHardTerminate
    $definition=New-ScheduledTask -Action $action -Principal $principal -Settings $settings
    Register-ScheduledTask -TaskPath $path -TaskName $name -InputObject $definition -ErrorAction Stop | Out-Null
    $registered=$true
    $native=$folder.GetTask($name);$native.SetSecurityDescriptor($sddl,0)
    $normalSddl=$native.GetSecurityDescriptor(7)
    $native.SetSecurityDescriptor($sddl,16)
    $withoutPrincipalSddl=$native.GetSecurityDescriptor(7)
    $probe=[ordered]@{folder=$folderName;requested=$sddl;folder_sddl=$folder.GetSecurityDescriptor(7);task_sddl_flags0=$normalSddl;task_sddl_flags16=$withoutPrincipalSddl}
    Write-NewBytes (Join-Path $env:KN_BOOTSTRAP_OUTPUT ($folderName+'.private.json')) ([Text.Encoding]::UTF8.GetBytes(($probe | ConvertTo-Json -Depth 4)))
    Assert-TaskSecurity ($native.GetSecurityDescriptor(7)) $ownerSid
    $xml=Export-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
    Write-NewBytes (Join-Path $env:KN_BOOTSTRAP_OUTPUT ($folderName+'.private.xml')) ([Text.Encoding]::UTF8.GetBytes($xml))
    $effective=(Get-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop).Principal.RunLevel.ToString()
    Assert-TaskXml $xml $ownerSid $exe $args $working $effective
    if ((Get-ScheduledTask -TaskPath $path -TaskName $name).State -notin @('Ready','Disabled')) { throw 'Never-started fixture task has unexpected state' }
} finally {
    if ($registered) { Unregister-ScheduledTask -TaskPath $path -TaskName $name -Confirm:$false -ErrorAction Stop }
    if ($null -ne $folder) { $top.DeleteFolder($folderName,0);$cleaned=$true }
}
if (@(Get-ScheduledTask -ErrorAction Stop | Where-Object { $_.TaskPath -ceq $path }).Count) { throw 'Fixture task cleanup failed' }
[ordered]@{status='PASS_FORGE_NATIVE_TASK_REGISTRATION_ONLY';folder=$folderName;task_started=$false;xml_verified=$true;dacl_verified=$true;cleaned=$cleaned} | ConvertTo-Json -Compress
''')
        receipt.parent.mkdir(exist_ok=True)
        with receipt.open('x', encoding='utf-8') as stream: stream.write(output)

    @unittest.skipUnless(os.environ.get('KN_NARRATOR_OWNER_TOKEN_FIXTURE') == '1',
                         'explicit opt-in limited-owner process/token ACL fixture on FORGE only')
    def test_native_limited_owner_process_token_query_grant(self):
        repository = Path(__file__).resolve().parents[1]
        receipt = repository / 'output/narrator-owner-token-fixture.json'
        if receipt.exists(): self.skipTest('One-time limited-owner native receipt already retained')
        helper = '''import ctypes,hashlib,json,sys
from pathlib import Path
sys.path.insert(0, REPO_SOURCE)
from youtube_ops import collector_narrator_pipe as pipe
result={'status':'BLOCKED_NATIVE_OWNER_TOKEN_FIXTURE'}
stage='identity'
try:
    sid,elevated=pipe.windows_identity()
    if elevated: raise RuntimeError('unexpected_elevated_token')
    fake='S-1-5-21-1-2-3-1002'
    stage='grant'
    pipe.allow_bridge_inspection({'owner_sid':sid,'bridge_sid':fake})
    stage='readback'
    kernel,advapi=pipe._apis()
    advapi.GetAce.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p)]
    token=pipe.wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),0x20008,ctypes.byref(token)): raise RuntimeError('token_query_failed')
    found=[]
    try:
        for handle,required in ((kernel.GetCurrentProcess(),0x1000),(token,8)):
            acl,descriptor=ctypes.c_void_p(),ctypes.c_void_p()
            if advapi.GetSecurityInfo(handle,6,4,None,None,ctypes.byref(acl),None,ctypes.byref(descriptor)): raise RuntimeError('readback_failed')
            try:
                count=ctypes.c_ushort.from_address(acl.value+4).value
                rights=[]
                for index in range(count):
                    ace=ctypes.c_void_p()
                    if not advapi.GetAce(acl,index,ctypes.byref(ace)): raise RuntimeError('ace_readback_failed')
                    if ctypes.c_ubyte.from_address(ace.value).value==0 and pipe._sid_string(ace.value+8,kernel,advapi)==fake:
                        rights.append(ctypes.c_uint32.from_address(ace.value+4).value)
                if rights!=[required]: raise RuntimeError('query_grant_not_exact')
                found.append(required)
            finally: kernel.LocalFree(descriptor)
    finally: kernel.CloseHandle(token)
    result={'status':'PASS_FORGE_LIMITED_OWNER_TOKEN_ONLY','elevated':elevated,'process_query_mask':found[0],'token_query_mask':found[1],
            'source_sha256':hashlib.sha256(Path(pipe.__file__).read_bytes()).hexdigest()}
except Exception as error:
    result['error']=getattr(error,'code','native_owner_token_unverified')
    result['stage']=stage
    result['error_class']=type(error).__name__
    result['native_error']=ctypes.get_last_error()
with Path(sys.argv[1]).open('x',encoding='utf-8') as f: json.dump(result,f)
'''.replace('REPO_SOURCE', repr(str(repository / 'src')))
        output = self.helpers(r'''
$folderName='KNCollectorNarratorControlTest-'+[guid]::NewGuid().ToString('N')
if ($folderName -cnotmatch '^KNCollectorNarratorControlTest-[a-f0-9]{32}$') { throw 'Fixture path invalid' }
$path='\'+$folderName+'\';$name='LimitedOwnerTokenFixture'
$data=Join-Path $fixture 'data';New-Item -ItemType Directory -Path $data | Out-Null
$acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetOwner([Security.Principal.SecurityIdentifier]::new($ownerSid));$acl.SetAccessRuleProtection($true,$false)
foreach ($sid in @('S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')) }
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'ReadAndExecute','ContainerInherit,ObjectInherit','None','Allow'))
Set-Acl -LiteralPath $fixture -AclObject $acl
$dataAcl=Get-Acl -LiteralPath $data;$dataAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ownerSid),'Modify','ContainerInherit,ObjectInherit','None','Allow'));Set-Acl -LiteralPath $data -AclObject $dataAcl
$script=Join-Path $fixture 'owner-token-check.py';$result=Join-Path $data 'result.json'
Write-NewBytes $script ([Convert]::FromBase64String('HELPER_BYTES'))
$service=New-Object -ComObject Schedule.Service;$service.Connect();$top=$service.GetFolder('\')
$sddl="O:${ownerSid}G:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;${ownerSid})"
$folder=$null;$registered=$false;$cleaned=$false
try {
    $folder=$top.CreateFolder($folderName,$sddl)
    $args='-I -S -B "'+$script+'" "'+$result+'"'
    $action=New-ScheduledTaskAction -Execute $env:KN_BOOTSTRAP_PYTHON -Argument $args -WorkingDirectory $fixture
    $principal=New-ScheduledTaskPrincipal -UserId $ownerSid -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DisallowHardTerminate
    Register-ScheduledTask -TaskPath $path -TaskName $name -InputObject (New-ScheduledTask -Action $action -Principal $principal -Settings $settings) -ErrorAction Stop | Out-Null
    $registered=$true;$folder.GetTask($name).SetSecurityDescriptor($sddl,16)
    Start-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
    $deadline=[DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $result) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path -LiteralPath $result)) { throw 'Limited-owner native fixture timed out' }
    $value=Get-Content -LiteralPath $result -Raw -Encoding UTF8 | ConvertFrom-Json
    while ((Get-ScheduledTask -TaskPath $path -TaskName $name).State -eq 'Running' -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if ((Get-ScheduledTask -TaskPath $path -TaskName $name).State -notin @('Ready','Disabled') -or (Get-ScheduledTaskInfo -TaskPath $path -TaskName $name).LastTaskResult -ne 0) { throw 'Limited-owner fixture did not finish cleanly' }
} finally {
    if ($registered) { Unregister-ScheduledTask -TaskPath $path -TaskName $name -Confirm:$false -ErrorAction Stop }
    if ($null -ne $folder) { $top.DeleteFolder($folderName,0);$cleaned=$true }
}
if (@(Get-ScheduledTask -ErrorAction Stop | Where-Object { $_.TaskPath -ceq $path }).Count) { throw 'Fixture cleanup failed' }
$value | Add-Member NoteProperty task_cleaned $cleaned
$value | ConvertTo-Json -Compress
'''.replace('HELPER_BYTES', __import__('base64').b64encode(helper.encode()).decode()))
        with receipt.open('x', encoding='utf-8') as stream: stream.write(output)
        self.assertEqual(json.loads(output)['status'], 'PASS_FORGE_LIMITED_OWNER_TOKEN_ONLY', output)


if __name__ == '__main__':
    unittest.main()
