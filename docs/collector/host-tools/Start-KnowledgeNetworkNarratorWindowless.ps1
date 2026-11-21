$ErrorActionPreference='Stop'
$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'
$work="$root/batch-update-v1"
$python='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/python.exe'
$helperPin='1ec820f1123aab4d12d8719efc0a462f89e9db18e80d52b09523743542129ca6'
$utf8=[Text.UTF8Encoding]::new($false,$true)
function Hash-Bytes([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Assert-ReadTrust([string]$Path,[string]$OwnerSid=$null,[bool]$OwnerWritable=$false){
    $node=Get-Item -LiteralPath $Path -Force;$first=$true
    $allowed=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
    while($null -ne $node){
        if(($node.Attributes -band 0x400) -ne 0){throw 'Offline recovery reparse path rejected.'}
        $privateRoot=[IO.Path]::GetFullPath("$root/data").TrimEnd('\')
        $inPrivate=$node.FullName -ieq $privateRoot -or $node.FullName.StartsWith($privateRoot+'\',[StringComparison]::OrdinalIgnoreCase)
        $permitted=if($OwnerWritable -and $inPrivate){@($allowed)+$OwnerSid}else{$allowed}
        $acl=Get-Acl -LiteralPath $node.FullName
        $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $permitted){throw 'Offline recovery trust unavailable.'}
        $mask=if($first){0x500D0156}else{0x500D0040}
        foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
            if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $permitted -and (([long]$ace.FileSystemRights -band $mask) -ne 0)){throw 'Offline recovery code writable by another identity.'}
        }
        $node=if($node -is [IO.DirectoryInfo]){$node.Parent}else{$node.Directory};$first=$false
    }
}
function Capture-Read([string]$Path,[long]$Limit){
    Assert-ReadTrust $Path
    $stream=[IO.File]::Open($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt $Limit){throw 'Offline recovery input bound exceeded.'}
        $memory=[IO.MemoryStream]::new()
        try{$stream.CopyTo($memory);return ,$memory.ToArray()}finally{$memory.Dispose()}
    }finally{$stream.Dispose()}
}
function Write-New([string]$Path,[byte[]]$Bytes){
    $stream=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$stream.Write($Bytes,0,[Math]::Min($Bytes.Length,65536));$stream.Flush($true)}finally{$stream.Dispose()}
}
if($env:COMPUTERNAME -ine 'BLACKHAT-BASE'){throw 'Offline recovery requires BLACKHAT-BASE.'}
$owner=[Security.Principal.WindowsIdentity]::GetCurrent()
if($owner.User.Value -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($owner)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Elevated recorded owner required; never SYSTEM.'}
$config=$utf8.GetString((Capture-Read "$root/code/config.json" 65536))|ConvertFrom-Json
if($config.owner_sid -cne $owner.User.Value){throw 'Recorded recovery owner mismatch.'}
foreach($path in @("$root/data","$root/data/remote-voice.lock","$root/data/host-narrations.sqlite")){
    Assert-ReadTrust $path $owner.User.Value $true
    $acl=Get-Acl -LiteralPath $path
    foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
        if($ace.AccessControlType -ne 'Allow' -or $ace.IdentityReference.Value -notin @($owner.User.Value,'S-1-5-18','S-1-5-32-544')){throw 'Existing private narrator data ACL changed.'}
    }
}
$helper=Capture-Read "$work/update-helper.py" 1048576
if((Hash-Bytes $helper) -cne $helperPin){throw 'Original captured helper changed; do not execute.'}
if((Hash-Bytes (Capture-Read $python 33554432)) -cne $config.server_python_sha256){throw 'Protected Python changed.'}
$prepared=$utf8.GetString((Capture-Read "$work/prepared-only.private.json" 65536))|ConvertFrom-Json
$bundle=Capture-Read "$work/batch-update-bundle.private.json" 65536
if((Hash-Bytes $bundle) -cne $prepared.bundle_sha256 -or $prepared.helper_sha256 -cne $helperPin){throw 'Original prepared capture changed.'}
$package=$utf8.GetString($bundle)|ConvertFrom-Json
$inputPins=@{'batch-update-bundle.private.json'=(Hash-Bytes $bundle)}
foreach($name in @('__init__.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')){
    $bytes=Capture-Read "$work/new-$name" 1048576
    if((Hash-Bytes $bytes) -cne $package.files.$name){throw 'Captured prepared source changed.'}
    $inputPins["new-$name"]=(Hash-Bytes $bytes)
    if($name -ceq 'collector_narration_common.py'){$common=$bytes}
}
$probe=Capture-Read "$work/collector_narrator_recovery_probe.py" 1048576
if((Hash-Bytes $probe) -cne $package.probe_sha256){throw 'Captured namespace probe changed.'}
$inputPins['collector_narrator_recovery_probe.py']=(Hash-Bytes $probe)
$validator=Capture-Read "$work/assert-code.ps1" 65536
$inputPins['assert-code.ps1']=(Hash-Bytes $validator)
$pythonw='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/pythonw.exe'
$pythonwPin='36392dade900489423a15686340bf5f95a64d661d9322bb4c0e0f1d4e6a84cb7'
$inventory=$utf8.GetString((Capture-Read 'C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime-files.private.json' 65536))|ConvertFrom-Json
$windowlessRecords=@($inventory|Where-Object name -ceq 'pythonw.exe')
if(@($inventory).Count -ne 37 -or $windowlessRecords.Count -ne 1 -or $windowlessRecords[0].sha256 -cne $pythonwPin -or (Hash-Bytes (Capture-Read $pythonw 33554432)) -cne $pythonwPin){throw 'Existing protected windowless interpreter changed.'}
$stem='windowless-start-'+[Guid]::NewGuid().ToString('N')
$driver=@'
import ast,base64,hashlib,json,os,socket,sys,time,uuid
from contextlib import contextmanager
from pathlib import Path
RAW=base64.b64decode('__CAPTURED_HELPER__',validate=True)
COMMON=base64.b64decode('__CAPTURED_COMMON__',validate=True)
INPUT_PINS=json.loads(base64.b64decode('__INPUT_PINS__',validate=True))
PIN='1ec820f1123aab4d12d8719efc0a462f89e9db18e80d52b09523743542129ca6'
WORK=Path('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1')
ROOT=WORK.parent;DATA=ROOT/'data';NEW=WORK/'code-windowless-v1'
PYTHONW=Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/pythonw.exe')
PYTHONW_PIN='36392dade900489423a15686340bf5f95a64d661d9322bb4c0e0f1d4e6a84cb7'
STEM='__START_STEM__';CHECKPOINT='batch-offline-recovery-ae91f12ecf584634b0173831305c6bc6-review'
PINS={
 'code/config.json':'a2b219a49d677b5edef6477d0c3a53c0dad05a6e7e13ee1b3e6b6fea03218c4e',
 'code/narrator-standalone.py':'26895777336f7fcbfa91350c35898ec948773e8b7038dfbe6edd8a4dbca68c50',
 'code/standalone-bundle.json':'a8cf6b5ab1bbbf8623cb96c36450349670aabba3baf7a80fa97db0cbbe45352c',
 CHECKPOINT+'/blocked.private.json':'c1243dc891598735fd66fc90c8910352474fdea5e7c8aa7015374aa2f44702fc',
 CHECKPOINT+'/start-requested.private.json':'2a745e19bac160a22c4a86bcf2749961354a3e0bb5e3aca11ace51c5fcc67046',
 CHECKPOINT+'/one-start-intent.private.json':'9bbdfdea4b5209d568b9eaf9ff9b8d5628e5418401ca94228e78fbd7ce3a18a9',
 CHECKPOINT+'/post-start-task-raw.private.json':'1310346a7d06cf1c190e50ac76478bb2afe1b3737f7d76f7a0bed08afd61f107'}
DATA_PINS={
 'schema2-migration.private.json':'a36b70dc88b6225de78a5ea278d8966f59f128393f10e69dd7053afb8770bcb3',
 'schema2-migration-completed.private.json':'f00d10a4576f639f05a50be3cc6560da4e8770ecef8ce0d4d8ceb52ef1bb3ddc',
 'host-narrations.schema1.backup.sqlite':'0adb7158513d5129284b7fb7dc2aa309f8e2d24412ab2b39d119de6c9f54fafb',
 'batch-update-v1/parity-review/c67fe3af962d4ff89d1303839b4ba7c5/parity-completed.private.json':'79e95941df37c5ad495ae72370d6dfdbf3ecd2a80ee529ea3b8211c795385960',
 'batch-update-v1/parity/narration.wav':'950a708ebb736d65c6596dce6ba3677f7a574e6f83b4723548c513e363005e36',
 'batch-update-v1/startup/d6ab17d2c9e14e00a8a6173542b412b4/startup-ready.private.json':'646ead8f38d19f12e41097db3e1c3d86ff134db3456d198c2e2e0e60c7048110'}
TASK_READ=r'''
$ErrorActionPreference='Stop';$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\KnowledgeNetworkCollector').GetTask('NarratorStandaloneV1');$d=$t.Definition;$a=$d.Actions.Item(1)
$owner=if($d.Principal.UserId -match '^S-1-'){$d.Principal.UserId}else{([Security.Principal.NTAccount]::new($d.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object LocalPort -eq 39110|Select-Object LocalAddress,LocalPort,OwningProcess)
$scripts=@('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/code/narrator-standalone.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/narrator-standalone.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/parity.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/update-helper.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code-windowless-v1/narrator-standalone.py')
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop|Where-Object {$cmd=([string]$_.CommandLine).Replace('\','/');@($scripts|Where-Object {$cmd.IndexOf($_,[StringComparison]::OrdinalIgnoreCase) -ge 0}).Count}|Select-Object ProcessId,ExecutablePath,CommandLine)
$pidValue=if($listeners.Count -eq 1){$listeners[0].OwningProcess}else{0};$p=if($pidValue){Get-CimInstance Win32_Process -Filter ('ProcessId='+$pidValue) -ErrorAction Stop}else{$null}
$sid=if($p){Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop}else{$null}
@{xml=$t.Xml;sddl=$t.GetSecurityDescriptor(7);state=$t.State;enabled=$t.Enabled;instances=$t.GetInstances(0).Count;owner_sid=$owner;logon=$d.Principal.LogonType;runlevel=$d.Principal.RunLevel;actions=$d.Actions.Count;triggers=$d.Triggers.Count;multiple=$d.Settings.MultipleInstances;hard_terminate=$d.Settings.AllowHardTerminate;execution_limit=$d.Settings.ExecutionTimeLimit;execute=$a.Path;arguments=$a.Arguments;working_directory=$a.WorkingDirectory;listeners=$listeners;canonical_processes=$processes;pid=$pidValue;image=if($p){$p.ExecutablePath}else{''};command_line=if($p){$p.CommandLine}else{''};process_owner=if($sid -and $sid.ReturnValue -eq 0){$sid.Sid}else{''};children=@(if($p){Get-CimInstance Win32_Process -Filter ('ParentProcessId='+$pidValue)|Select-Object ProcessId,CreationDate})}|ConvertTo-Json -Depth 5 -Compress
'''

def prefix(raw):
    if hashlib.sha256(raw).hexdigest()!=PIN:raise RuntimeError('captured_helper_changed')
    text=raw.decode('utf-8');tree=ast.parse(text);main=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main']
    if len(main)!=1 or text.count('\ndef main():\n')!=1:raise RuntimeError('captured_main_boundary_changed')
    return ''.join(text.splitlines(keepends=True)[:main[0].lineno-1])

def checkpoint(ns):
    for base,pins in ((WORK,PINS),(DATA,DATA_PINS)):
        for relative,pin in pins.items():
            if ns['sha'](base/relative)!=pin:raise RuntimeError('completed_parity_checkpoint_changed')
    config=json.loads((WORK/'code/config.json').read_text());bundle=json.loads((WORK/'code/standalone-bundle.json').read_text())
    if set(bundle['files'])!=set(ns['NAMES']) or config['bundle_sha256']!=PINS['code/standalone-bundle.json'] or config['segment_batches'] is not True:raise RuntimeError('batch_configuration_changed')
    for name,pin in bundle['files'].items():
        if ns['sha'](WORK/'code/youtube_ops'/name)!=pin:raise RuntimeError('reviewed_host_module_changed')
    parity_path=DATA/'batch-update-v1/parity-review/c67fe3af962d4ff89d1303839b4ba7c5/parity-completed.private.json'
    if Path(config['parity_receipt']).resolve()!=parity_path.resolve() or config['parity_receipt_sha256']!=DATA_PINS[str(parity_path.relative_to(DATA)).replace('\\','/')]:raise RuntimeError('existing_parity_binding_changed')
    parity=json.loads(parity_path.read_text());ready=json.loads((DATA/'batch-update-v1/startup/d6ab17d2c9e14e00a8a6173542b412b4/startup-ready.private.json').read_text())
    if parity['status']!='PASS_TECHNICAL_BATCH_ONLY' or parity['elevated'] is not False or parity['owner_sid']!=config['owner_sid'] or parity['process']['exit_code']!=0 or parity['process']['owned_active_processes']!=0 or parity['provenance']!=ready['provenance'] or parity['audio']['sha256']!=DATA_PINS['batch-update-v1/parity/narration.wav']:raise RuntimeError('completed_parity_unverified')
    for path in (NEW,WORK/'windowless-v1.schema2.backup.sqlite',DATA/'batch-update-v1/windowless-startup-v1'):
        try:path.lstat()
        except FileNotFoundError:continue
        raise RuntimeError('windowless_revision_already_exists')
    return config,json.loads((WORK/CHECKPOINT/'post-start-task-raw.private.json').read_text()),json.loads((WORK/CHECKPOINT/'start-requested.private.json').read_text())['xml']

def task_proof(ns,config,expected_xml,expected_sddl,live=False,enabled=True):
    value=ns['ps'](TASK_READ);ns['write'](WORK/(STEM+'-task-'+uuid.uuid4().hex+'.private.json'),value)
    if live:
        value=ns['capture_task_process'](value['pid'],lambda:ns['ps'](TASK_READ))
        ns['write'](WORK/(STEM+'-task-held-'+uuid.uuid4().hex+'.private.json'),value)
    code=NEW if live else WORK/'code';image=PYTHONW if live else ns['PYTHON'];normalize=lambda path:str(path).replace('\\','/').casefold()
    if (value['xml']!=expected_xml or value['sddl']!=expected_sddl or value['owner_sid']!=config['owner_sid'] or value['enabled'] is not enabled
        or value['state']!=(4 if live else 3 if enabled else 1) or value['logon']!=3 or value['runlevel']!=0 or value['actions']!=1 or value['triggers']!=0
        or value['multiple']!=2 or value['hard_terminate'] is not False or value['execution_limit']!='PT0S'
        or normalize(value['execute'])!=normalize(image) or value['arguments']!='-I -S -B '+str(code/'narrator-standalone.py').replace('\\','/') or normalize(value['working_directory'])!=normalize(code)):raise RuntimeError('exact_task_definition_unverified')
    if not live:
        if value['instances']!=0 or value['listeners'] or value['canonical_processes']:raise RuntimeError('supervisor_not_confirmed_offline')
    elif (value['instances']!=1 or len(value['listeners'])!=1 or value['listeners'][0]['LocalAddress']!='127.0.0.1' or value['process_owner']!=config['owner_sid'] or normalize(value['image'])!=normalize(PYTHONW) or value['children']):raise RuntimeError('windowless_process_unverified')
    if live:
        expected=ns['subprocess'].list2cmdline([str(PYTHONW),'-I','-S','-B',str(NEW/'narrator-standalone.py')])
        if value['command_line'].replace('\\','/').replace('"','')!=expected.replace('\\','/').replace('"',''):raise RuntimeError('windowless_command_changed')
    return value

def schema2_idle(db,expected,hold=None):
    if [row[1] for row in db.execute('PRAGMA table_info(jobs)')]!=['id','request_sha','text','text_sha','state','provenance','audio','error','cancel_requested','segments','cues']:raise RuntimeError('schema2_columns_changed')
    if db.execute("SELECT value FROM metadata WHERE key='schema_version'")!=[('2',)] or db.execute('SELECT id,state FROM jobs ORDER BY id')!=[(key,'completed') for key in sorted(expected)]:raise RuntimeError('schema2_jobs_not_exactly_completed')
    if db.execute("SELECT value FROM metadata WHERE key='execution_hold'")!=([] if hold is None else [(hold,)]):raise RuntimeError('schema2_hold_changed')
    return {'jobs':sorted(expected),'event_count':db.execute('SELECT count(*) FROM events')}

def supervisor_launcher(raw):
    text=raw.decode('utf-8')
    changes={"CODE=ROOT/'batch-update-v1/code'":"CODE=ROOT/'batch-update-v1/code-windowless-v1'","REVIEW=ROOT/'data/batch-update-v1/startup'/uuid.uuid4().hex":"REVIEW=ROOT/'data/batch-update-v1/windowless-startup-v1'/uuid.uuid4().hex","sha(Path(sys.executable))!=config['server_python_sha256']":"sha(Path(sys.executable))!=config['supervisor_python_sha256']"}
    for before,after in changes.items():
        if text.count(before)!=1:raise RuntimeError('reviewed_launcher_changed')
        text=text.replace(before,after)
    compile(text,'windowless-supervisor','exec');return text.encode()

TASK_CHANGE=r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$s=New-Object -ComObject Schedule.Service;$s.Connect();$f=$s.GetFolder('\KnowledgeNetworkCollector');$t=$f.GetTask('NarratorStandaloneV1')
$sha=[Security.Cryptography.SHA256]::Create();try{$actual=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($t.Xml)))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
if($actual -cne $r.xml_sha256){throw 'Task changed.'}
if($r.operation -ceq 'disable'){$t.Enabled=$false}
elseif($r.operation -ceq 'switch'){
 $sddl=$t.GetSecurityDescriptor(7);[xml]$x=$t.Xml;$n=[Xml.XmlNamespaceManager]::new($x.NameTable);$n.AddNamespace('t',$x.DocumentElement.NamespaceURI);$e=$x.SelectSingleNode('/t:Task/t:Actions/t:Exec',$n)
 $e.Command='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/pythonw.exe';$e.Arguments='-I -S -B C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code-windowless-v1/narrator-standalone.py';$e.WorkingDirectory='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code-windowless-v1'
 $t=$f.RegisterTask('NarratorStandaloneV1',$x.OuterXml,4,$r.owner,$null,3,$null);$t.SetSecurityDescriptor($sddl,16)
}elseif($r.operation -ceq 'start'){$t.Enabled=$true;$null=$t.Run($null)}else{throw 'Fixed task operation denied.'}
$t=$f.GetTask('NarratorStandaloneV1');@{xml=$t.Xml;sddl=$t.GetSecurityDescriptor(7);state=$t.State;enabled=$t.Enabled}|ConvertTo-Json -Compress
'''

def change_task(ns,operation,xml,owner):
    if operation not in ('disable','switch','start'):raise RuntimeError('task_operation_denied')
    return ns['ps'](TASK_CHANGE,{'operation':operation,'xml_sha256':hashlib.sha256(xml.encode()).hexdigest(),'owner':owner})

def check_new_code(ns,owner):
    ns['ps'](r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'
$b=[IO.File]::ReadAllBytes($root+'/batch-update-v1/assert-code.ps1');$h=[Security.Cryptography.SHA256]::Create();try{$pin=([BitConverter]::ToString($h.ComputeHash($b))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()};if($pin -cne $r.pin){throw 'Validator changed.'}
$tokens=$null;$errors=$null;$a=[Management.Automation.Language.Parser]::ParseInput([Text.UTF8Encoding]::new($false,$true).GetString($b),[ref]$tokens,[ref]$errors);$f=@($a.FindAll({param($x)$x -is [Management.Automation.Language.FunctionDefinitionAst] -and $x.Name -ceq 'Assert-Trust'},$false));if($errors.Count -or $f.Count -ne 1){throw 'Validator shape changed.'};. ([ScriptBlock]::Create($f[0].Extent.Text))
foreach($name in @('','youtube_ops','config.json','standalone-bundle.json','narrator-standalone.py','youtube_ops/__init__.py','youtube_ops/collector_narrator_host.py','youtube_ops/collector_narration_common.py','youtube_ops/collector_credentials.py')){Assert-Trust ($root+'/batch-update-v1/code-windowless-v1/'+$name) $r.owner}
''',{'owner':owner,'pin':ns['VALIDATOR_SHA256']})

def await_ready(base,timeout=180):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        paths=list(base.glob('*/startup-ready.private.json'));failed=list(base.glob('*/startup-failed.private.json'))
        if failed or len(paths)>1:raise RuntimeError('windowless_start_failed_or_ambiguous')
        if paths:
            try:return paths[0],json.loads(paths[0].read_text())
            except (json.JSONDecodeError,OSError):pass
        time.sleep(.25)
    raise RuntimeError('windowless_start_outcome_unknown_no_retry')

def main():
    ns={'__name__':'completed_parity_windowless_start'};exec(compile(prefix(RAW),'captured-helper-definitions-only','exec'),ns)
    for name,pin in INPUT_PINS.items():
        if ns['sha'](WORK/name)!=pin:raise RuntimeError('captured_input_changed')
    if INPUT_PINS['assert-code.ps1']!=ns['VALIDATOR_SHA256'] or hashlib.sha256(COMMON).hexdigest()!=INPUT_PINS['new-collector_narration_common.py']:raise RuntimeError('captured_common_or_validator_changed')
    common={'__name__':'captured_narration_common'};exec(compile(COMMON,'captured-common','exec'),common)
    config,prior,xml=checkpoint(ns);package=json.loads((WORK/'batch-update-bundle.private.json').read_text())
    identity=ns['ps']("$i=[Security.Principal.WindowsIdentity]::GetCurrent();@{sid=$i.User.Value;elevated=([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}|ConvertTo-Json -Compress")
    if identity!={'sid':config['owner_sid'],'elevated':True} or identity['sid']=='S-1-5-18' or not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or Path(sys.executable).resolve()!=ns['PYTHON'].resolve() or ns['sha'](ns['PYTHON'])!=config['server_python_sha256'] or ns['sha'](PYTHONW)!=PYTHONW_PIN:raise RuntimeError('separate_helper_supervisor_identity_unverified')
    ns['verify_bundle'](package,json.loads((ROOT/'code/config.json').read_text()));task=task_proof(ns,config,xml,prior['sddl'])
    review=WORK/(STEM+'-review');review.mkdir();ns['write'](review/'task-before.private.json',task);ns['raw_write'](review/'task-before.private.xml',task['xml'].encode())
    ns['idle_native']=schema2_idle;ns['FENCE']='windowless_v1_'+uuid.uuid4().hex
    lock_guard=db_guard=connection=reservation=None;fenced=False
    try:
        lock_guard=ns['probe'].NamespaceGuard(DATA/'remote-voice.lock')
        if (DATA/'remote-voice.lock').stat().st_size!=1:raise RuntimeError('existing_lease_shape_changed')
        with common['voice_lease'](DATA):
            lock_guard.verify();reservation=socket.socket(socket.AF_INET,socket.SOCK_STREAM);reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);reservation.bind(('127.0.0.1',39110))
            task_proof(ns,config,xml,prior['sddl']);disabled=change_task(ns,'disable',xml,config['owner_sid']);task_proof(ns,config,disabled['xml'],prior['sddl'],enabled=False)
            db_guard=ns['probe'].NamespaceGuard(ns['DB']);connection=ns['Sqlite'](ns['DB'],db_guard)
            def on_fenced():
                nonlocal fenced
                fenced=True;ns['write'](review/'fence-committed.private.json',{'fence':ns['FENCE'],'schema_version':2,'no_process_stopped':True})
            ns['prepare_fence'](connection,package['expected_job_ids'],lambda:ns['backup_locked'](ns['DB'],WORK/'windowless-v1.schema2.backup.sqlite'),on_fenced);connection.execute('COMMIT')
            ns['write'](review/'prepared.private.json',{'schema_version':2,'ledger_identity':db_guard.ledger,'lock_identity':lock_guard.ledger,'database_backup_sha256':ns['sha'](WORK/'windowless-v1.schema2.backup.sqlite'),'parity_reused_without_inference':True,'old_code_preserved':True,'automatic_database_restore':False})
            NEW.mkdir();(NEW/'youtube_ops').mkdir()
            for name in ns['NAMES']:ns['raw_write'](NEW/'youtube_ops'/name,(WORK/'code/youtube_ops'/name).read_bytes())
            ns['raw_write'](NEW/'standalone-bundle.json',(WORK/'code/standalone-bundle.json').read_bytes());ns['raw_write'](NEW/'narrator-standalone.py',supervisor_launcher((WORK/'code/narrator-standalone.py').read_bytes()))
            updated=dict(config,supervisor_python_sha256=PYTHONW_PIN);ns['raw_write'](NEW/'config.json',json.dumps(updated,sort_keys=True).encode());check_new_code(ns,config['owner_sid'])
            ns['write'](review/'rollback-prepared.private.json',{'status':'PREPARED_MANUAL_NOT_TESTED','old_code':str(WORK/'code'),'old_task':str(review/'task-before.private.xml'),'consistent_schema2_backup':str(WORK/'windowless-v1.schema2.backup.sqlite'),'never_restore_schema1':True,'no_automatic_retry':True})
            switched=change_task(ns,'switch',disabled['xml'],config['owner_sid']);ns['write'](review/'switched-disabled.private.json',switched)
            connection.execute('BEGIN IMMEDIATE');ns['clear_own_fence'](connection,package['expected_job_ids']);connection.execute('COMMIT')
            ns['write'](review/'one-start-intent.private.json',{'supervisor_pythonw_sha256':PYTHONW_PIN,'helper_python_sha256':config['server_python_sha256'],'parity_retry':False,'inference_submitted':False})
            reservation.close();reservation=None
        started=change_task(ns,'start',switched['xml'],config['owner_sid']);ns['write'](review/'start-requested.private.json',started)
        ready_path,ready=await_ready(DATA/'batch-update-v1/windowless-startup-v1')
        if ready['status']!='PASS_LOOPBACK_AUTH_ONLY' or ready['provenance']!=json.loads(Path(config['parity_receipt']).read_text())['provenance'] or ready['owner_sid']!=config['owner_sid'] or ready['elevated'] is not False or ready['segment_batches'] is not True or (ready['missing_bearer'],ready['wrong_bearer'],ready['authenticated_health'])!=(401,401,200):raise RuntimeError('windowless_auth_unverified')
        current=task_proof(ns,config,started['xml'],prior['sddl'],live=True)
        if current['pid']!=ready['pid']:raise RuntimeError('windowless_ready_pid_changed')
        process=ns['bind_running'](db_guard.native,current,db_guard,config['owner_sid']);db_guard.native.k.CloseHandle(process)
        ns['write'](review/'completed.private.json',{'status':'PASS_WINDOWLESS_LOOPBACK_START','ready_path':str(ready_path),'supervisor_pythonw_sha256':PYTHONW_PIN,'helper_python_sha256':config['server_python_sha256'],'parity_reused':True,'inference_submitted':False,'remote_batch_request':'NOT_TESTED','publication_paused':True})
        print(json.dumps({'status':'PASS_WINDOWLESS_LOOPBACK_START','review_directory':str(review),'inference_submitted':False,'publication_paused':True}))
    except BaseException as error:
        if connection:
            try:connection.execute('ROLLBACK')
            except BaseException:pass
        ns['write'](review/'blocked.private.json',{'status':'BLOCKED_PRESERVE_ALL_STATE','error_class':type(error).__name__,'error':str(error),'winerror':getattr(error,'winerror',None),'fence_committed':fenced,'automatic_retry':False,'no_process_stopped':True,'inference_submitted':False})
        raise
    finally:
        if connection:connection.close()
        if db_guard:db_guard.close()
        if lock_guard:lock_guard.close()
        if reservation:reservation.close()

if __name__=='__main__':main()
'@
$driver=$driver.Replace('__CAPTURED_HELPER__',[Convert]::ToBase64String($helper)).Replace('__CAPTURED_COMMON__',[Convert]::ToBase64String($common)).Replace('__INPUT_PINS__',[Convert]::ToBase64String($utf8.GetBytes(($inputPins|ConvertTo-Json -Compress)))).Replace('__START_STEM__',$stem)
if($driver -match '[^\x00-\x7f]'){throw 'Captured windowless transport must be ASCII.'}
$start=[Diagnostics.ProcessStartInfo]::new();$start.FileName=$python;$start.Arguments='-I -S -B -';$start.WorkingDirectory=$work
$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
$process=[Diagnostics.Process]::new();$process.StartInfo=$start;$null=$process.Start();$out=$process.StandardOutput.ReadToEndAsync();$err=$process.StandardError.ReadToEndAsync();$process.StandardInput.Write($driver);$process.StandardInput.Close()
$timedOut=-not $process.WaitForExit(360000)
if($timedOut){$process.Kill();$null=$process.WaitForExit(5000)}
if(-not $out.Wait(5000) -or -not $err.Wait(5000)){throw 'Owned recovery streams uncertain; preserve state and do not retry.'}
$outBytes=$utf8.GetBytes($out.Result);$errBytes=$utf8.GetBytes($err.Result)
Write-New "$work/$stem.stdout.private.log" $outBytes;Write-New "$work/$stem.stderr.private.log" $errBytes
Write-New "$work/$stem.process.private.json" $utf8.GetBytes((@{schema_version=1;pid=$process.Id;exit_code=$process.ExitCode;timed_out=$timedOut;helper_sha256=$helperPin;stdout_bytes=$outBytes.Length;stderr_bytes=$errBytes.Length;stdout_truncated=($outBytes.Length -gt 65536);stderr_truncated=($errBytes.Length -gt 65536);publication_paused=$true}|ConvertTo-Json))
$exitCode=$process.ExitCode;$process.Dispose()
if($exitCode -ne 0){throw 'Windowless start blocked; inspect retained private recovery logs. Do not retry.'}
[Console]::Out.Write($out.Result)
