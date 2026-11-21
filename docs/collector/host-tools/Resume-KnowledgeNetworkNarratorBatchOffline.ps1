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
$gpu='C:/Windows/System32/nvidia-smi.exe'
# NVIDIA inventory is optional evidence; never execute an unverified tool.
$gpuPin=''
$gpuEvidence=@{status='UNAVAILABLE';reason='tool_verification_unavailable';tool_executed=$false}
try {
    $gpuBytes=Capture-Read $gpu 33554432
    $version=[Diagnostics.FileVersionInfo]::GetVersionInfo($gpu)
    $signature=Get-AuthenticodeSignature -FilePath $gpu
    $gpuEvidence.file_version=$version.FileVersion
    $gpuEvidence.company=$version.CompanyName
    $gpuEvidence.signature_status=[string]$signature.Status
    $gpuEvidence.signer=if($signature.SignerCertificate){$signature.SignerCertificate.Subject}else{$null}
    if($version.FileVersion -ceq '8.17.16.1714' -and $version.CompanyName -match 'NVIDIA' -and $signature.Status -eq 'Valid' -and $gpuEvidence.signer -match 'NVIDIA'){
        $gpuPin=Hash-Bytes $gpuBytes
        $gpuEvidence.status='VERIFIED';$gpuEvidence.reason='verified_before_query'
    }else{$gpuEvidence.reason='tool_identity_not_verified'}
}catch{$gpuEvidence.reason='tool_read_or_trust_unavailable';$gpuEvidence.error=$_.Exception.Message}
$stem='batch-offline-recovery-'+[Guid]::NewGuid().ToString('N')
$driver=@'
import ast,base64,ctypes,hashlib,json,os,socket,subprocess,sys,time,traceback,uuid
from contextlib import contextmanager
from pathlib import Path
RAW=base64.b64decode('__CAPTURED_HELPER__',validate=True)
COMMON=base64.b64decode('__CAPTURED_COMMON__',validate=True)
INPUT_PINS=json.loads(base64.b64decode('__INPUT_PINS__',validate=True))
PIN='1ec820f1123aab4d12d8719efc0a462f89e9db18e80d52b09523743542129ca6'
WORK=Path('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1')
GPU=Path('C:/Windows/System32/nvidia-smi.exe');GPU_PIN='__GPU_PIN__'
GPU_EVIDENCE=json.loads(base64.b64decode('__GPU_EVIDENCE__',validate=True))
STEM='__RECOVERY_STEM__'
CHECKPOINT='batch-offline-recovery-f22619166b424f5a86e8963de5dd1bb0'
CHECKPOINT_PINS={
    CHECKPOINT+'-review/blocked.private.json':'6646531ee62bf9f249d39cc2de828c5aa80a507af74334946f231be22aadc78f',
    CHECKPOINT+'-review/initial-offline.private.json':'c287da2cd2fac5f6591344ef57dd43347368bfd6e03f2e36f2b0f5610dc97695',
    CHECKPOINT+'-task-18c7f1c550784e7386e4a99dc39966fe.private.json':'35a8ba2fe2995e5b89fb6e1d500da53525a4a587762d606ef0bdaebcd366d1dc',
    'task-before.private.json':'c287da2cd2fac5f6591344ef57dd43347368bfd6e03f2e36f2b0f5610dc97695',
    'task-before.private.xml':'7cd415ccfb470f3134bb02e44527a3342fedabbcb4377f1a81474e3a53b79e53',
    'original-code-descriptors.private.json':'cde34a3575e0f20ce46fd10e4f762d942a00cef8838f006bba6beb4eefdf0f0c'}
ORIGINAL_XML='7cd415ccfb470f3134bb02e44527a3342fedabbcb4377f1a81474e3a53b79e53'
DISABLED_XML='2713e2f07981df12c2ec5f29ecbbf019505c1d49a87a804b454d09b8e4fc1119'
TASK_OPERATION_CODE='f1605941ac9b6211cac1d552d3be14738707a09243161b5da90ad0bd0b16e338'
OFFLINE_TASK=r'''
$ErrorActionPreference='Stop';$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\KnowledgeNetworkCollector').GetTask('NarratorStandaloneV1')
$d=$t.Definition;$a=$d.Actions.Item(1);$owner=if($d.Principal.UserId -match '^S-1-'){$d.Principal.UserId}else{([Security.Principal.NTAccount]::new($d.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object LocalPort -eq 39110|Select-Object LocalAddress,LocalPort,OwningProcess)
$scripts=@('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/code/narrator-standalone.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/narrator-standalone.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/parity.py','C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/update-helper.py')
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop|Where-Object { $cmd=([string]$_.CommandLine).Replace('\','/');@($scripts|Where-Object {$cmd.IndexOf($_,[StringComparison]::OrdinalIgnoreCase) -ge 0}).Count }|Select-Object ProcessId,ExecutablePath,CommandLine)
@{xml=$t.Xml;sddl=$t.GetSecurityDescriptor(7);state=$t.State;enabled=$t.Enabled;instances=$t.GetInstances(0).Count;last_result=$t.LastTaskResult;last_run=$t.LastRunTime.ToUniversalTime().ToString('O');owner_sid=$owner;logon=$d.Principal.LogonType;runlevel=$d.Principal.RunLevel;actions=$d.Actions.Count;triggers=$d.Triggers.Count;multiple=$d.Settings.MultipleInstances;hard_terminate=$d.Settings.AllowHardTerminate;execution_limit=$d.Settings.ExecutionTimeLimit;execute=$a.Path;arguments=$a.Arguments;working_directory=$a.WorkingDirectory;listeners=$listeners;canonical_processes=$processes}|ConvertTo-Json -Depth 5 -Compress
'''

def checked_prefix(raw,pin):
    if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('captured_helper_changed')
    text=raw.decode('utf-8',errors='strict');tree=ast.parse(text)
    main=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main']
    if len(main)!=1 or text.count('\ndef main():\n')!=1:raise ValueError('main_boundary_changed')
    return ''.join(text.splitlines(keepends=True)[:main[0].lineno-1])

def capture_only(ns):
    forbidden=['old-code','code','update-review','schema1-before-update.backup.sqlite','task-before.private.xml','task-before.private.json','original-code-descriptors.private.json','parity-task.private.xml','config-parity-disabled.retained.json']
    for path in [*(ns['WORK']/name for name in forbidden),ns['DATA']/'batch-update-v1']:
        try:path.lstat()
        except FileNotFoundError:continue
        raise RuntimeError('prepared_capture_has_prior_activity')

def install_task_refresh(ns,prefix):
    function=next(node for node in ast.parse(prefix).body if isinstance(node,ast.FunctionDef) and node.name=='task_operation')
    codes=[node.args[0].value for node in ast.walk(function) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='ps' and isinstance(node.args[0],ast.Constant)]
    if len(codes)!=1 or hashlib.sha256(codes[0].encode()).hexdigest()!=TASK_OPERATION_CODE:raise RuntimeError('captured_task_operation_changed')
    original=codes[0];marker='\n@{xml=$t.Xml;enabled=$t.Enabled;state=$t.State}|ConvertTo-Json -Compress'
    if original.count(marker)!=1:raise RuntimeError('task_metadata_return_changed')
    refreshed=original.replace(marker,"\n$t=$f.GetTask('NarratorStandaloneV1')"+marker)
    original_ps=ns['ps']
    def ps(code,value=None,timeout=20):return original_ps(refreshed if code==original else code,value,timeout)
    ns['ps']=ps

def disabled_checkpoint(ns,package):
    for relative,pin in CHECKPOINT_PINS.items():
        if ns['sha'](WORK/relative)!=pin:raise RuntimeError('disabled_checkpoint_evidence_changed')
    review=WORK/(CHECKPOINT+'-review')
    if {path.name for path in review.iterdir()}!={'initial-offline.private.json','blocked.private.json'}:raise RuntimeError('checkpoint_has_later_activity')
    blocked=json.loads((review/'blocked.private.json').read_text())
    if blocked.get('fence_committed') is not False or blocked.get('no_process_stopped') is not True or blocked.get('error')!='exact_offline_task_proof_failed':raise RuntimeError('disabled_checkpoint_not_pre_database')
    for path in [*(WORK/name for name in ('code','update-review','schema1-before-update.backup.sqlite','parity-task.private.xml','config-parity-disabled.retained.json')),ns['DATA']/'batch-update-v1']:
        try:path.lstat()
        except FileNotFoundError:continue
        raise RuntimeError('checkpoint_has_later_activity')
    disabled=json.loads((WORK/(CHECKPOINT+'-task-18c7f1c550784e7386e4a99dc39966fe.private.json')).read_text())
    before=json.loads((WORK/'task-before.private.json').read_text())
    if hashlib.sha256(disabled['xml'].encode()).hexdigest()!=DISABLED_XML or hashlib.sha256(before['xml'].encode()).hexdigest()!=ORIGINAL_XML or disabled['sddl']!=before['sddl']:raise RuntimeError('checkpoint_task_identity_changed')
    sources={'config.json':package['old_config_sha256'],'narrator-standalone.py':package['old_launcher_sha256'],'standalone-bundle.json':package['old_bundle_sha256'],'task.private.xml':ORIGINAL_XML}
    old_bundle=json.loads((ns['ROOT']/'code/standalone-bundle.json').read_text())
    sources.update({'youtube_ops/'+name:pin for name,pin in old_bundle['files'].items()})
    if {path.relative_to(WORK/'old-code').as_posix() for path in (WORK/'old-code').rglob('*') if path.is_file()}!=set(sources):raise RuntimeError('checkpoint_backup_set_changed')
    for relative,pin in sources.items():
        for path in (ns['ROOT']/'code'/relative,WORK/'old-code'/relative):
            if path.is_symlink() or getattr(path.stat(),'st_file_attributes',0)&0x400 or path.stat().st_nlink!=1 or ns['sha'](path)!=pin:raise RuntimeError('checkpoint_original_or_backup_changed')
    expected=json.loads((WORK/'original-code-descriptors.private.json').read_text())
    normalize=lambda path:str(path).replace('\\','/').casefold()
    if {normalize(item['path']) for item in expected}!={normalize(ns['ROOT']/'code'/relative) for relative in sources}:raise RuntimeError('checkpoint_descriptor_set_changed')
    actual=ns['ps']("$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;@($r.paths|ForEach-Object{@{path=$_;sddl=(Get-Acl -LiteralPath $_).Sddl}})|ConvertTo-Json -Compress",{'paths':[item['path'] for item in expected]})
    ns['write'](WORK/(STEM+'-code-descriptors-'+uuid.uuid4().hex+'.private.json'),actual)
    if {normalize(item['path']):item['sddl'] for item in actual}!={normalize(item['path']):item['sddl'] for item in expected}:raise RuntimeError('checkpoint_source_descriptors_changed')
    return disabled

def verify_disabled_live(value,checkpoint):
    if any(value.get(key)!=checkpoint.get(key) for key in ('xml','sddl','owner_sid','last_result','last_run')):raise RuntimeError('disabled_checkpoint_live_task_changed')

def offline_proof(ns,config,enabled=True,expected_xml=None):
    value=ns['ps'](OFFLINE_TASK)
    ns['write'](WORK/(STEM+'-task-'+uuid.uuid4().hex+'.private.json'),value)
    if expected_xml is None:
        if not enabled:raise RuntimeError('disabled_task_xml_required')
        expected_xml=(ns['ROOT']/'code/task.private.xml').read_bytes().decode('utf-8')
    normalized=lambda path:str(path).replace('\\','/').casefold()
    if (value['xml']!=expected_xml or value['owner_sid']!=config['owner_sid'] or value['state']!=(3 if enabled else 1) or value['enabled'] is not enabled
        or value['instances']!=0 or value['listeners'] or value['canonical_processes'] or value['logon']!=3 or value['runlevel']!=0
        or value['actions']!=1 or value['triggers']!=0 or value['multiple']!=2 or value['hard_terminate'] is not False or value['execution_limit']!='PT0S'
        or normalized(value['execute'])!=normalized(ns['PYTHON']) or normalized(value['working_directory'])!=normalized(ns['ROOT']/'code')
        or value['arguments']!='-I -S -B '+str(ns['ROOT']/'code/narrator-standalone.py').replace('\\','/')):raise RuntimeError('exact_offline_task_proof_failed')
    return value

@contextmanager
def existing_lease(ns,common,guard):
    path=ns['DATA']/'remote-voice.lock'
    guard.verify()
    if path.stat().st_size!=1:raise RuntimeError('existing_lease_shape_changed')
    with common['voice_lease'](ns['DATA']):
        guard.verify();yield guard
        guard.verify()

def reserve_port(port=39110):
    reservation=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        reservation.bind(('127.0.0.1',port));return reservation
    except BaseException:reservation.close();raise

def gpu_baseline(ns,review):
    evidence=dict(GPU_EVIDENCE,facts_only=True,unrelated_workloads_changed=False,tool_executed=False)
    if evidence['status']!='VERIFIED':
        ns['write'](review/'gpu-before.private.json',evidence);return
    try:
        if ns['sha'](GPU)!=GPU_PIN:raise ValueError('tool_digest_changed_before_query')
    except (OSError,ValueError) as error:
        evidence.update(status='UNAVAILABLE',reason=str(error))
        ns['write'](review/'gpu-before.private.json',evidence);return
    try:
        result=subprocess.run([str(GPU),'-q'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        out,err,code=result.stdout,result.stderr,result.returncode
        evidence.update(status='AVAILABLE' if code==0 and len(out)<=65536 and len(err)<=65536 else 'UNAVAILABLE',reason='query_completed',exit_code=code,tool_executed=True)
    except (OSError,subprocess.TimeoutExpired) as error:
        out,err=getattr(error,'stdout',None) or b'',getattr(error,'stderr',None) or b''
        evidence.update(status='UNAVAILABLE',reason='optional_query_failed',error_class=type(error).__name__,tool_executed=isinstance(error,subprocess.TimeoutExpired))
    ns['raw_write'](review/'gpu-before.stdout.private.log',out[:65536]);ns['raw_write'](review/'gpu-before.stderr.private.log',err[:65536])
    evidence.update(tool_sha256=GPU_PIN,stdout_bytes=len(out),stderr_bytes=len(err),truncated=len(out)>65536 or len(err)>65536)
    ns['write'](review/'gpu-before.private.json',evidence)


def main():
    ns={'__name__':'knowledge_network_offline_continuation'}
    prefix=checked_prefix(RAW,PIN);exec(compile(prefix,'captured-helper-definitions-only','exec'),ns);install_task_refresh(ns,prefix)
    for name,pin in INPUT_PINS.items():
        if ns['sha'](WORK/name)!=pin:raise RuntimeError('captured_input_changed')
    if INPUT_PINS['assert-code.ps1']!=ns['VALIDATOR_SHA256']:raise RuntimeError('captured_validator_changed')
    if hashlib.sha256(COMMON).hexdigest()!=INPUT_PINS['new-collector_narration_common.py']:raise RuntimeError('captured_common_changed')
    common={'__name__':'captured_narration_common'};exec(compile(COMMON,'captured-narration-common','exec'),common)
    config=json.loads((ns['ROOT']/'code/config.json').read_text());package=json.loads((WORK/'batch-update-bundle.private.json').read_text())
    identity=ns['ps']("$i=[Security.Principal.WindowsIdentity]::GetCurrent();@{sid=$i.User.Value;elevated=([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}|ConvertTo-Json -Compress")
    if identity!={'sid':config['owner_sid'],'elevated':True} or identity['sid']=='S-1-5-18' or not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or Path(sys.executable).resolve()!=ns['PYTHON'].resolve() or ns['sha'](ns['PYTHON'])!=config['server_python_sha256']:raise RuntimeError('owner_or_runtime_unverified')
    ns['verify_bundle'](package,config);checkpoint=disabled_checkpoint(ns,package)
    task=offline_proof(ns,config,False,checkpoint['xml']);verify_disabled_live(task,checkpoint)
    review=WORK/(STEM+'-review');review.mkdir();ns['write'](review/'initial-offline.private.json',task)
    reservation=None;connection=None;db_guard=None;lock_guard=None;fenced=False
    try:
        lock_guard=ns['probe'].NamespaceGuard(ns['DATA']/'remote-voice.lock')
        with existing_lease(ns,common,lock_guard):
            reservation=reserve_port();fresh=offline_proof(ns,config,False,checkpoint['xml']);verify_disabled_live(fresh,checkpoint)
            disabled_checkpoint(ns,package);disabled=fresh
            ns['write'](review/'disabled-offline.private.json',fresh)
            db_guard=ns['probe'].NamespaceGuard(ns['DB'])
            connection=ns['Sqlite'](ns['DB'],db_guard)
            def on_fenced():
                nonlocal fenced
                fenced=True;ns['write'](review/'fence-committed.private.json',{'fence':ns['FENCE'],'no_process_stopped':True})
            snapshot=ns['prepare_fence'](connection,package['expected_job_ids'],lambda:ns['backup_locked'](ns['DB'],WORK/'schema1-before-update.backup.sqlite'),on_fenced)
            connection.execute('COMMIT')
            ns['write'](review/'offline-prepared.private.json',{'status':'OFFLINE_LEDGER_VERIFIED','snapshot':snapshot,'ledger_identity':db_guard.ledger,'lock_identity':lock_guard.ledger,'database_backup_sha256':ns['sha'](WORK/'schema1-before-update.backup.sqlite'),'previous_exit_cause':'UNKNOWN','no_process_stopped':True})
            ns['make_private_data'](config['owner_sid']);code,new_config=ns['prepare_code'](package,config,review);ns['assert_new_code'](config['owner_sid'])
            ns['write'](review/'rollback-prepared.private.json',{'status':'PREPARED_MANUAL_ROLLBACK_NOT_TESTED','original_task_xml':str(WORK/'task-before.private.xml'),'original_code_backup':str(WORK/'old-code'),'consistent_database_backup':str(WORK/'schema1-before-update.backup.sqlite'),'rollback_code':str(code),'rollback_mode':'Reviewed new source with segment_batches false and a fresh startup UUID; preserve current database.','preconditions':['Parity process confirmed exited; no uncertain jobs or unknown hold.','Exact protected namespace, task, owner and current process identity verified.','Clear only this continuation fence under a held writer transaction.'],'never_restore_schema1_over_schema2_activity':True,'automatic_rollback':False,'publication_paused':True})
            gpu_baseline(ns,review)
            parity_path,parity=ns['parity_task'](config)
            old_ready=json.loads((ns['DATA']/'review/startup-ready.private.json').read_text())
            if parity['provenance']!=old_ready['provenance']:raise RuntimeError('batch_parity_provenance_changed')
            previous=(code/'config.json').read_bytes();(code/'config.json').rename(WORK/'config-parity-disabled.retained.json')
            ns['write'](review/'config-revision-retained.private.json',{'original_path':str(code/'config.json'),'retained_path':str(WORK/'config-parity-disabled.retained.json'),'sha256':hashlib.sha256(previous).hexdigest(),'size':len(previous),'recorded_at':time.time(),'reason':'Preserve referenced disabled configuration revision','deletion_performed':False})
            new_config.update(segment_batches=True,parity_receipt=str(parity_path),parity_receipt_sha256=ns['sha'](parity_path));ns['raw_write'](code/'config.json',json.dumps(new_config,sort_keys=True).encode());ns['assert_new_code'](config['owner_sid'])
            switched=ns['task_operation']('switch',disabled['xml'],config['owner_sid']);ns['write'](review/'switched-disabled.private.json',switched)
            connection.execute('BEGIN IMMEDIATE');ns['clear_own_fence'](connection,package['expected_job_ids']);connection.execute('COMMIT')
            ns['write'](review/'one-start-intent.private.json',{'status':'ONE_LIMITED_OWNER_START_AUTHORIZED','parity_receipt':str(parity_path),'parity_sha256':ns['sha'](parity_path),'no_process_stopped':True,'no_database_restore':True})
            reservation.close();reservation=None
            # Release the same singleton lease before the new store acquires it.
        started=ns['task_operation']('start',switched['xml'],config['owner_sid']);ns['write'](review/'start-requested.private.json',started)
        ready_path,ready=ns['wait_startup'](config)
        ns['write'](review/'post-start-task-raw.private.json',ns['ps'](ns['TASK_PROOF']))
        current=ns['task_proof'](config,code);ns['write'](review/'post-start-task.private.json',current)
        if current['pid']!=ready['pid']:raise RuntimeError('new_startup_pid_changed')
        process=ns['bind_running'](db_guard.native,current,db_guard,config['owner_sid']);db_guard.native.k.CloseHandle(process)
        ns['write'](review/'completed.private.json',{'status':'PASS_OFFLINE_BATCH_LOOPBACK_RECOVERY','ready_receipt':str(ready_path),'remote_batch_request':'NOT_TESTED','listening':'NOT_TESTED','route_changed':False,'publication_paused':True})
        print(json.dumps({'status':'PASS_OFFLINE_BATCH_LOOPBACK_RECOVERY','review_directory':str(review),'publication_paused':True}))
    except BaseException as error:
        if connection:
            try:connection.execute('ROLLBACK')
            except BaseException:pass
        ns['write'](review/'blocked.private.json',{'status':'BLOCKED_PRESERVE_ALL_STATE','error_class':type(error).__name__,'error':str(error),'winerror':getattr(error,'winerror',None),'fence_committed':fenced,'no_process_stopped':True,'automatic_retry':False,'automatic_database_restore':False,'publication_paused':True})
        raise
    finally:
        if connection:connection.close()
        if db_guard:db_guard.close()
        if lock_guard:lock_guard.close()
        if reservation:reservation.close()

if __name__=='__main__':main()
'@
$driver=$driver.Replace('__CAPTURED_HELPER__',[Convert]::ToBase64String($helper)).Replace('__CAPTURED_COMMON__',[Convert]::ToBase64String($common)).Replace('__INPUT_PINS__',[Convert]::ToBase64String($utf8.GetBytes(($inputPins|ConvertTo-Json -Compress)))).Replace('__GPU_PIN__',$gpuPin).Replace('__GPU_EVIDENCE__',[Convert]::ToBase64String($utf8.GetBytes(($gpuEvidence|ConvertTo-Json -Compress)))).Replace('__RECOVERY_STEM__',$stem)
if($driver -match '[^\x00-\x7f]'){throw 'Captured recovery transport must be ASCII.'}
$start=[Diagnostics.ProcessStartInfo]::new();$start.FileName=$python;$start.Arguments='-I -S -B -';$start.WorkingDirectory=$work
$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
$process=[Diagnostics.Process]::new();$process.StartInfo=$start;$null=$process.Start();$out=$process.StandardOutput.ReadToEndAsync();$err=$process.StandardError.ReadToEndAsync();$process.StandardInput.Write($driver);$process.StandardInput.Close()
$timedOut=-not $process.WaitForExit(1500000)
if($timedOut){$process.Kill();$null=$process.WaitForExit(5000)}
if(-not $out.Wait(5000) -or -not $err.Wait(5000)){throw 'Owned recovery streams uncertain; preserve state and do not retry.'}
$outBytes=$utf8.GetBytes($out.Result);$errBytes=$utf8.GetBytes($err.Result)
Write-New "$work/$stem.stdout.private.log" $outBytes;Write-New "$work/$stem.stderr.private.log" $errBytes
Write-New "$work/$stem.process.private.json" $utf8.GetBytes((@{schema_version=1;pid=$process.Id;exit_code=$process.ExitCode;timed_out=$timedOut;helper_sha256=$helperPin;stdout_bytes=$outBytes.Length;stderr_bytes=$errBytes.Length;stdout_truncated=($outBytes.Length -gt 65536);stderr_truncated=($errBytes.Length -gt 65536);publication_paused=$true}|ConvertTo-Json))
$exitCode=$process.ExitCode;$process.Dispose()
if($exitCode -ne 0){throw 'Offline continuation blocked; inspect retained private recovery logs. Do not retry.'}
[Console]::Out.Write($out.Result)
