[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BundleDirectory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BundleSha256
)
$ErrorActionPreference='Stop'
$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'
$runtime='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python'
$work="$root/batch-update-v1"
$utf8=[Text.UTF8Encoding]::new($false,$true)
function Hash-Bytes([byte[]]$Bytes) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Capture-File([string]$Path,[string]$Pin,[long]$Limit=1048576) {
    $node=Get-Item -LiteralPath $Path -Force
    if($node.PSIsContainer){throw 'Regular file required.'}
    $parent=$node
    while($null -ne $parent){
        if(($parent.Attributes -band 0x400) -ne 0){throw 'Reparse source rejected.'}
        $parent=if($parent -is [IO.DirectoryInfo]){$parent.Parent}else{$parent.Directory}
    }
    $stream=[IO.File]::Open($node.FullName,'Open','Read','Read')
    try {
        if($stream.Length -gt $Limit){throw 'File bound exceeded.'}
        $memory=[IO.MemoryStream]::new()
        try{$stream.CopyTo($memory);$raw=$memory.ToArray()}finally{$memory.Dispose()}
    }finally{$stream.Dispose()}
    if((Hash-Bytes $raw) -cne $Pin){throw 'Captured source digest mismatch.'}
    return ,$raw
}
function Assert-Trust([string]$Path,[string]$OwnerSid,[bool]$OwnerWritable=$false) {
    $node=Get-Item -LiteralPath $Path -Force
    $first=$true
    $admins=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
    while($null -ne $node){
        if(($node.Attributes -band 0x400) -ne 0){throw 'Protected namespace reparse point.'}
        $privateRoot=[IO.Path]::GetFullPath("$root/data").TrimEnd('\')
        $privateNode=$node.FullName -ieq $privateRoot -or $node.FullName.StartsWith($privateRoot+'\',[StringComparison]::OrdinalIgnoreCase)
        $allowed=if($OwnerWritable -and $privateNode){@($admins)+$OwnerSid}else{$admins}
        $acl=Get-Acl -LiteralPath $node.FullName
        $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed){throw 'Protected namespace ownership unavailable.'}
        $mask=if($first){0x500D0156}else{0x500D0040}
        foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
            if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $allowed -and (([long]$ace.FileSystemRights -band $mask) -ne 0)){throw 'Protected namespace writable by another identity.'}
        }
        $node=if($node -is [IO.DirectoryInfo]){$node.Parent}else{$node.Directory};$first=$false
    }
}
function Write-New([string]$Path,[byte[]]$Bytes) {
    $f=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$f.Write($Bytes,0,$Bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
function New-PrivateDirectory([string]$Path,[string]$OwnerSid,[bool]$Writable) {
    New-Item -ItemType Directory -Path $Path -ErrorAction Stop | Out-Null
    $acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    foreach($sid in @('S-1-5-18','S-1-5-32-544')){
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
    }
    $rights=if($Writable){'FullControl'}else{'ReadAndExecute'}
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($OwnerSid),$rights,'ContainerInherit,ObjectInherit','None','Allow'))
    Set-Acl -LiteralPath $Path -AclObject $acl
}

if($env:COMPUTERNAME -ine 'BLACKHAT-BASE'){throw 'BLACKHAT-BASE required.'}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if($identity.User.Value -eq 'S-1-5-18' -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Elevated recorded owner required; never SYSTEM.'}
$ownerSid=$identity.User.Value
Assert-Trust "$root/code/config.json" $ownerSid
$originalConfig=Get-Content -LiteralPath "$root/code/config.json" -Raw -Encoding UTF8|ConvertFrom-Json
if($originalConfig.owner_sid -cne $ownerSid){throw 'Recorded owner mismatch.'}
Assert-Trust $root $ownerSid
Assert-Trust "$root/data" $ownerSid $true
Assert-Trust "$root/data/host-narrations.sqlite" $ownerSid $true
Assert-Trust "$runtime/python.exe" $ownerSid
$null=Capture-File "$runtime/python.exe" $originalConfig.server_python_sha256 33554432
$inventoryPath='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime-files.private.json'
Assert-Trust $inventoryPath $ownerSid
$inventory=Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8|ConvertFrom-Json
if(@($inventory).Count -ne 37 -or @(Get-ChildItem -LiteralPath $runtime -Force).Count -ne 37 -or @($inventory.name|Sort-Object -Unique).Count -ne 37){throw 'Protected runtime inventory changed.'}
foreach($item in $inventory){
    if($item.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or $item.sha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Runtime inventory shape.'}
    Assert-Trust "$runtime/$($item.name)" $ownerSid
    $null=Capture-File "$runtime/$($item.name)" $item.sha256 33554432
}
$bundlePath=[IO.Path]::GetFullPath($BundleDirectory)
$bundle=Capture-File (Join-Path $bundlePath 'batch-update-bundle.private.json') $BundleSha256 65536
$package=$utf8.GetString($bundle)|ConvertFrom-Json
$names=@('__init__.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
if($package.schema_version -ne 1 -or @($package.files.PSObject.Properties).Count -ne 4 -or @($package.expected_job_ids).Count -ne 9 -or @($package.canonical_audio).Count -ne 8){throw 'Batch update bundle shape.'}
$captured=@{}
foreach($name in @($names)+@('collector_narrator_recovery_probe.py')){
    $pin=if($name -ceq 'collector_narrator_recovery_probe.py'){$package.probe_sha256}else{$package.files.$name}
    if($pin -cnotmatch '^[a-f0-9]{64}$'){throw 'Bundle source pin unavailable.'}
    $captured[$name]=Capture-File (Join-Path $bundlePath $name) $pin
}
# All input is captured before creating project children. Existing code is untouched.
if(Test-Path -LiteralPath $work){throw 'Batch update already prepared; preserve and reconcile, never retry.'}
New-PrivateDirectory $work $ownerSid $false
Write-New "$work/batch-update-bundle.private.json" $bundle
Write-New "$work/collector_narrator_recovery_probe.py" $captured['collector_narrator_recovery_probe.py']
foreach($name in $names){Write-New "$work/new-$name" $captured[$name]}
$trustFunction=(Get-Command Assert-Trust -CommandType Function).Definition
$codeValidator="param([string]`$OwnerSid)`n`$ErrorActionPreference='Stop'`n`$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'`nfunction Assert-Trust {`n$trustFunction`n}`n"
$codeValidator+=@'
foreach($relative in @('code','code/youtube_ops','code/config.json','code/standalone-bundle.json','code/narrator-standalone.py','code/parity.py','code/youtube_ops/__init__.py','code/youtube_ops/collector_narrator_host.py','code/youtube_ops/collector_narration_common.py','code/youtube_ops/collector_credentials.py')){
    Assert-Trust (Join-Path "$root/batch-update-v1" $relative) $OwnerSid
}
'@
Write-New "$work/assert-code.ps1" $utf8.GetBytes($codeValidator)
Assert-Trust "$work/assert-code.ps1" $ownerSid
$helper=@'
"""One fixed owner bootstrap, not an RPC endpoint or a legacy controller repair."""
import ctypes as c
from contextlib import closing
import hashlib,json,os,re,sqlite3,subprocess,sys,time,uuid
from pathlib import Path

ROOT=Path('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1')
WORK=ROOT/'batch-update-v1'
DATA=ROOT/'data'
DB=DATA/'host-narrations.sqlite'
PYTHON=Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/python.exe')
TASK=r'\KnowledgeNetworkCollector\NarratorStandaloneV1'
FENCE='batch_update_v1_'+uuid.uuid4().hex
NAMES=('__init__.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
if hashlib.sha256((WORK/'collector_narrator_recovery_probe.py').read_bytes()).hexdigest()!=json.loads((WORK/'batch-update-bundle.private.json').read_text())['probe_sha256']:raise RuntimeError('probe_source_changed')
sys.path.insert(0,str(WORK))
import collector_narrator_recovery_probe as probe

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())
def raw_write(path,value):
    with path.open('xb') as f:f.write(value);f.flush();os.fsync(f.fileno())
def ps(code,value=None,timeout=20):
    p=subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],input=None if value is None else json.dumps(value).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('fixed_powershell_operation_failed')
    return json.loads(p.stdout.decode('utf-8-sig')) if p.stdout.strip() else None

def backup_locked(path,destination):
    with destination.open('xb'):pass
    deadline=time.monotonic()+20
    def progress(status,remaining,total):
        if time.monotonic()>deadline:raise RuntimeError('backup_deadline')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1)) as source,closing(sqlite3.connect(destination)) as target:
        source.backup(target,pages=128,progress=progress,sleep=.01)
        if target.execute('PRAGMA quick_check').fetchone()!=('ok',):raise RuntimeError('backup_invalid')

class Sqlite:
    """A public C-API connection whose borrowed Windows HANDLE is verified."""
    def __init__(self,path,guard):
        self.guard,self.db=guard,c.c_void_p()
        import _sqlite3
        self.dll=c.CDLL(str(Path(_sqlite3.__file__).with_name('sqlite3.dll')))
        signatures={'sqlite3_open_v2':([c.c_char_p,c.POINTER(c.c_void_p),c.c_int,c.c_char_p],c.c_int),
            'sqlite3_file_control':([c.c_void_p,c.c_char_p,c.c_int,c.c_void_p],c.c_int),
            'sqlite3_exec':([c.c_void_p,c.c_char_p,c.c_void_p,c.c_void_p,c.c_void_p],c.c_int),
            'sqlite3_close_v2':([c.c_void_p],c.c_int),'sqlite3_busy_timeout':([c.c_void_p,c.c_int],c.c_int)}
        for name,(args,result) in signatures.items():
            fn=getattr(self.dll,name);fn.argtypes,fn.restype=args,result
        guard.verify()
        if self.dll.sqlite3_open_v2(str(path).encode(),c.byref(self.db),2,None):self.close();raise RuntimeError('sqlite_open_failed')
        if self.dll.sqlite3_busy_timeout(self.db,2000):self.close();raise RuntimeError('sqlite_busy_timeout_failed')
        try:self.verify()
        except BaseException:self.close();raise
    def verify(self):
        self.guard.verify();handle=probe.HANDLE()
        if self.dll.sqlite3_file_control(self.db,b'main',29,c.byref(handle)) or not handle.value:raise RuntimeError('sqlite_handle_unverified')
        if probe.identity(self.guard.native.metadata(handle))!=probe.identity(self.guard.ledger):raise RuntimeError('sqlite_ledger_mismatch')
    def execute(self,sql):
        self.verify();rows=[]
        def row(_,count,values,names):
            if count>8 or len(rows)>128:return 1
            rows.append(tuple(None if not values[i] else c.string_at(values[i]).decode('utf-8') for i in range(count)));return 0
        callback=c.CFUNCTYPE(c.c_int,c.c_void_p,c.c_int,c.POINTER(c.c_void_p),c.POINTER(c.c_void_p))(row)
        if self.dll.sqlite3_exec(self.db,sql.encode('ascii'),callback,None,None):raise RuntimeError('sqlite_busy_or_failed')
        self.verify()
        return rows
    def close(self):
        if self.db:
            if self.dll.sqlite3_close_v2(self.db):raise RuntimeError('sqlite_close_failed')
            self.db=c.c_void_p()

def prepare_fence(connection,expected,backup,on_fenced=lambda:None):
    # Fixed validated IDs only; the helper never accepts caller-supplied SQL.
    connection.execute('BEGIN IMMEDIATE')
    try:
        snapshot=idle_native(connection,expected)
        backup()
        connection.execute("INSERT INTO metadata(key,value) VALUES('execution_hold','"+FENCE+"')")
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK');raise
    on_fenced()
    connection.execute('BEGIN IMMEDIATE')
    # Keep this second writer lock through exact-process exit. A pre-fence POST
    # could otherwise insert after checking held() but before acquiring its lock.
    if idle_native(connection,expected,FENCE)!=snapshot:raise RuntimeError('ledger_changed_after_fence')
    return snapshot

def idle_native(db,expected,hold=None):
    columns=[row[1] for row in db.execute('PRAGMA table_info(jobs)')]
    if columns!=['id','request_sha','text','text_sha','state','provenance','audio','error','cancel_requested']:raise RuntimeError('expected_schema1_columns_required')
    if db.execute('SELECT id,state FROM jobs ORDER BY id')!=[(job,'completed') for job in sorted(expected)]:raise RuntimeError('ledger_not_exactly_completed')
    rows=db.execute("SELECT value FROM metadata WHERE key='execution_hold'")
    if rows!=([] if hold is None else [(hold,)]):raise RuntimeError('ledger_hold_changed')
    if db.execute("SELECT value FROM metadata WHERE key='schema_version'")!=[('1',)]:raise RuntimeError('expected_schema1_required')
    return {'jobs':sorted(expected),'event_count':db.execute('SELECT count(*) FROM events')}

def clear_own_fence(connection,expected):
    idle_native(connection,expected,FENCE)
    connection.execute("DELETE FROM metadata WHERE key='execution_hold' AND value='"+FENCE+"'")

TASK_PROOF=r'''
$ErrorActionPreference='Stop'
$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\KnowledgeNetworkCollector').GetTask('NarratorStandaloneV1')
$d=$t.Definition;$a=$d.Actions.Item(1)
$owner=if($d.Principal.UserId -match '^S-1-'){$d.Principal.UserId}else{([Security.Principal.NTAccount]::new($d.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}
$l=@(Get-NetTCPConnection -State Listen -LocalPort 39110 -ErrorAction Stop)
if($l.Count -ne 1 -or $l[0].LocalAddress -cne '127.0.0.1'){throw 'loopback'}
$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$l[0].OwningProcess) -ErrorAction Stop
$sid=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
if($sid.ReturnValue -ne 0){throw 'owner'}
@{xml=$t.Xml;sddl=$t.GetSecurityDescriptor(7);state=$t.State;enabled=$t.Enabled;owner_sid=$owner;logon=$d.Principal.LogonType;runlevel=$d.Principal.RunLevel;actions=$d.Actions.Count;triggers=$d.Triggers.Count;multiple=$d.Settings.MultipleInstances;hard_terminate=$d.Settings.AllowHardTerminate;execution_limit=$d.Settings.ExecutionTimeLimit;execute=$a.Path;arguments=$a.Arguments;working_directory=$a.WorkingDirectory;pid=$p.ProcessId;creation_filetime=$p.CreationDate.ToFileTimeUtc();process_owner=$sid.Sid;image=$p.ExecutablePath;command_line=$p.CommandLine;children=@(Get-CimInstance Win32_Process -Filter ('ParentProcessId='+$p.ProcessId)|Select-Object ProcessId,CreationDate)}|ConvertTo-Json -Depth 5 -Compress
'''

def task_proof(config,code=None):
    code=ROOT/'code' if code is None else code
    if code not in (ROOT/'code',WORK/'code'):raise RuntimeError('fixed_code_directory_required')
    value=ps(TASK_PROOF)
    normalized=lambda path:str(path).replace('\\','/').casefold()
    if (value['owner_sid']!=config['owner_sid'] or value['process_owner']!=config['owner_sid']
        or value['state']!=4 or value['enabled'] is not True or value['logon']!=3 or value['runlevel']!=0
        or value['actions']!=1 or value['triggers']!=0 or value['multiple']!=2
        or value['hard_terminate'] is not False or value['execution_limit']!='PT0S'
        or normalized(value['execute'])!=normalized(PYTHON) or normalized(value['image'])!=normalized(PYTHON)
        or value['arguments']!='-I -S -B '+str(code/'narrator-standalone.py').replace('\\','/')
        or normalized(value['working_directory'])!=normalized(code) or value['children']):
        raise RuntimeError('fixed_task_process_binding_failed')
    # CIM's command line is independently bound to the fixed action, not merely PID.
    tokens=subprocess.list2cmdline([str(PYTHON),'-I','-S','-B',str(code/'narrator-standalone.py')])
    if value['command_line'].replace('\\','/').replace('"','')!=tokens.replace('\\','/').replace('"',''):
        raise RuntimeError('fixed_process_command_line_changed')
    return value

def live_ledger_handles(native,process,created,ledger):
    """Read only the held PID's handle snapshot; no process memory or arbitrary paths."""
    native.running(process,created)
    count,snapshot,marker=probe.U32(),probe.HANDLE(),probe.HANDLE()
    found=[]
    if not native.k.GetProcessHandleCount(process,c.byref(count)) or count.value>512:raise RuntimeError('process_handle_bound')
    try:
        if native.k.PssCaptureSnapshot(process,4,0,c.byref(snapshot)):raise RuntimeError('handle_snapshot_unavailable')
        if native.k.PssQuerySnapshot(snapshot,4,c.byref(count),c.sizeof(count)) or count.value>512:raise RuntimeError('snapshot_bound')
        if native.k.PssWalkMarkerCreate(None,c.byref(marker)):raise RuntimeError('snapshot_marker_unavailable')
        seen=0;deadline=time.monotonic()+5
        while True:
            if seen>=512 or time.monotonic()>deadline:raise RuntimeError('snapshot_deadline')
            entry=probe.HandleEntry();status=native.k.PssWalkSnapshot(snapshot,2,marker,c.byref(entry),c.sizeof(entry))
            if status==259:break
            if status:raise RuntimeError('snapshot_walk_failed')
            seen+=1
            duplicate=probe.HANDLE()
            if not native.k.DuplicateHandle(process,entry.handle,native.k.GetCurrentProcess(),c.byref(duplicate),0,False,2):
                # Non-file unsupported objects may not duplicate. Matching disk
                # identity, never type names or arbitrary paths, is the proof.
                if c.get_last_error()==50:continue
                raise RuntimeError('snapshot_handle_changed')
            try:
                if native.k.GetFileType(duplicate)!=1:continue
                if Path(native.final_path(duplicate)).name.casefold()!='host-narrations.sqlite':continue
                info=native.metadata(duplicate)
                if probe.identity(info)==probe.identity(ledger):
                    if info['links']!=1 or info['attributes']&16:raise RuntimeError('live_ledger_invalid')
                    found.append(entry.handle)
            finally:native.k.CloseHandle(duplicate)
        if seen!=count.value:raise RuntimeError('snapshot_handle_count_changed')
        if len(found)!=1:raise RuntimeError('live_ledger_not_unique_'+str(len(found)))
        native.running(process,created)
        return found
    finally:
        bad=bool(marker and native.k.PssWalkMarkerFree(marker))
        bad|=bool(snapshot and native.k.PssFreeSnapshot(native.k.GetCurrentProcess(),snapshot))
        if bad:raise RuntimeError('snapshot_cleanup_unverified')

def held_process_owner(native,process,expected_sid):
    adv=c.WinDLL('advapi32',use_last_error=True);token=probe.HANDLE()
    adv.OpenProcessToken.argtypes=[probe.HANDLE,probe.U32,c.POINTER(probe.HANDLE)];adv.OpenProcessToken.restype=c.c_int
    adv.GetTokenInformation.argtypes=[probe.HANDLE,c.c_int,c.c_void_p,probe.U32,c.POINTER(probe.U32)];adv.GetTokenInformation.restype=c.c_int
    adv.ConvertSidToStringSidW.argtypes=[c.c_void_p,c.POINTER(c.c_wchar_p)];adv.ConvertSidToStringSidW.restype=c.c_int
    native.k.LocalFree.argtypes=[c.c_void_p];native.k.LocalFree.restype=c.c_void_p
    if not adv.OpenProcessToken(process,8,c.byref(token)):raise RuntimeError('process_token_unverified')
    try:
        needed,elevated=probe.U32(),probe.U32()
        if not adv.GetTokenInformation(token,20,c.byref(elevated),c.sizeof(elevated),c.byref(needed)) or elevated.value!=0:raise RuntimeError('running_owner_not_limited')
        adv.GetTokenInformation(token,1,None,0,c.byref(needed))
        if not 8<=needed.value<=65536:raise RuntimeError('process_owner_bound')
        raw=c.create_string_buffer(needed.value)
        if not adv.GetTokenInformation(token,1,raw,len(raw),c.byref(needed)):raise RuntimeError('process_owner_unverified')
        sid=c.c_wchar_p()
        if not adv.ConvertSidToStringSidW(c.cast(raw,c.POINTER(c.c_void_p))[0],c.byref(sid)):raise RuntimeError('process_owner_unverified')
        try:
            if sid.value!=expected_sid:raise RuntimeError('process_owner_changed')
        finally:native.k.LocalFree(c.cast(sid,c.c_void_p))
    finally:native.k.CloseHandle(token)

def bind_running(native,value,guard,owner):
    native.k.OpenProcess.argtypes=[probe.U32,c.c_int,probe.U32];native.k.OpenProcess.restype=probe.HANDLE
    native.k.TerminateProcess.argtypes=[probe.HANDLE,probe.U32];native.k.TerminateProcess.restype=c.c_int
    process=native.k.OpenProcess(0x100441,False,value['pid'])
    if not process:raise RuntimeError('fixed_process_access_unavailable')
    try:
        held_process_owner(native,process,owner)
        first=live_ledger_handles(native,process,value['creation_filetime'],guard.ledger)
        if live_ledger_handles(native,process,value['creation_filetime'],guard.ledger)!=first:raise RuntimeError('live_ledger_handle_changed')
        guard.verify()
        return process
    except BaseException:native.k.CloseHandle(process);raise

def task_operation(operation,expected_xml,owner):
    if operation not in ('disable','switch','start'):raise RuntimeError('fixed_task_operation_denied')
    return ps(r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$s=New-Object -ComObject Schedule.Service;$s.Connect();$f=$s.GetFolder('\KnowledgeNetworkCollector');$t=$f.GetTask('NarratorStandaloneV1')
$h=[Security.Cryptography.SHA256]::Create();try{$actual=([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($t.Xml)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
if($actual -cne $r.expected_xml){throw 'task_changed'}
if($r.operation -ceq 'disable'){$t.Enabled=$false}
elseif($r.operation -ceq 'switch'){
 $sddl=$t.GetSecurityDescriptor(7);[xml]$x=$t.Xml;$ns=[Xml.XmlNamespaceManager]::new($x.NameTable);$ns.AddNamespace('t',$x.DocumentElement.NamespaceURI)
 $e=$x.SelectSingleNode('/t:Task/t:Actions/t:Exec',$ns);if($null -eq $e){throw 'action'}
 $e.Command='C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/python.exe'
 $e.Arguments='-I -S -B C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/narrator-standalone.py'
 $e.WorkingDirectory='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code'
 $t=$f.RegisterTask('NarratorStandaloneV1',$x.OuterXml,4,$r.owner,$null,3,$null);$t.SetSecurityDescriptor($sddl,16)
}elseif($r.operation -ceq 'start'){$t.Enabled=$true;$null=$t.Run($null)}else{throw 'operation'}
@{xml=$t.Xml;enabled=$t.Enabled;state=$t.State}|ConvertTo-Json -Compress
''',{'operation':operation,'expected_xml':hashlib.sha256(expected_xml.encode()).hexdigest(),'owner':owner})

def verify_bundle(package,config):
    if (set(package)!= {'schema_version','files','probe_sha256','old_config_sha256','old_launcher_sha256','old_bundle_sha256','old_ready_sha256','expected_job_ids','canonical_audio','parity_segments'}
        or package['schema_version']!=1 or set(package['files'])!=set(NAMES)
        or len(package['expected_job_ids'])!=9 or len(set(package['expected_job_ids']))!=9
        or any(not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key) for key in package['expected_job_ids'])
        or len(package['parity_segments'])!=2
        or any(not isinstance(text,str) or not 1<=len(text)<=160 or text!=text.strip() or any(ord(ch)<32 or ord(ch)==127 for ch in text) for text in package['parity_segments'])
        or len(package['canonical_audio'])!=8):raise RuntimeError('batch_bundle_invalid')
    for name in ('probe_sha256','old_config_sha256','old_launcher_sha256','old_bundle_sha256','old_ready_sha256'):
        if not isinstance(package[name],str) or not re.fullmatch('[a-f0-9]{64}',package[name]):raise RuntimeError('batch_bundle_pin_invalid')
    for name in NAMES:
        if not isinstance(package['files'][name],str) or not re.fullmatch('[a-f0-9]{64}',package['files'][name]):raise RuntimeError('batch_bundle_pin_invalid')
        if sha(WORK/('new-'+name))!=package['files'][name]:raise RuntimeError('captured_batch_source_changed')
    for path,key in ((ROOT/'code/config.json','old_config_sha256'),(ROOT/'code/narrator-standalone.py','old_launcher_sha256'),(ROOT/'code/standalone-bundle.json','old_bundle_sha256'),(DATA/'review/startup-ready.private.json','old_ready_sha256')):
        if sha(path)!=package[key]:raise RuntimeError('old_standalone_source_changed')
    old=json.loads((ROOT/'code/standalone-bundle.json').read_text())
    if old['files'].keys()!=package['files'].keys():raise RuntimeError('old_source_shape_changed')
    for name,pin in old['files'].items():
        if sha(ROOT/'code/youtube_ops'/name)!=pin:raise RuntimeError('old_standalone_source_changed')
    ready=json.loads((DATA/'review/startup-ready.private.json').read_text())
    if ready['owner_sid']!=config['owner_sid'] or ready['elevated'] is not False or ready['status']!='PASS_LOOPBACK_AUTH_ONLY':raise RuntimeError('old_startup_identity_changed')
    if config['bundle_sha256']!=package['old_bundle_sha256'] or sha(Path(config['manifest']))!=config['manifest_sha256']:raise RuntimeError('original_manifest_changed')
    canonical=[]
    for item in package['canonical_audio']:
        if set(item)!={'job_id','sha256'} or item['job_id'] not in package['expected_job_ids'] or not re.fullmatch('[a-f0-9]{64}',item['sha256']):raise RuntimeError('canonical_audio_evidence_invalid')
        path=DATA/item['job_id']/'narration.wav'
        with probe.NamespaceGuard(path) as audio_guard:
            if sha(path)!=item['sha256']:raise RuntimeError('canonical_audio_evidence_changed')
            audio_guard.verify()
        canonical.append(item['job_id'])
    if len(set(canonical))!=8:raise RuntimeError('canonical_audio_evidence_invalid')

def new_launcher(old):
    replacements={
        'import hashlib,json,os,sys,threading,http.client':'import hashlib,json,os,sys,threading,http.client,uuid',
        "sys.path.insert(0,str(ROOT/'code'))":"CODE=ROOT/'batch-update-v1/code'\nREVIEW=ROOT/'data/batch-update-v1/startup'/uuid.uuid4().hex\nsys.path.insert(0,str(CODE))",
        "ROOT/'data/review'/name":"REVIEW/name",
        "ROOT/'code/config.json'":"CODE/'config.json'",
        "ROOT/'code/standalone-bundle.json'":"CODE/'standalone-bundle.json'",
        "ROOT/'code/youtube_ops'/name":"CODE/'youtube_ops'/name",
        "if identity!={'sid':config['owner_sid'],'elevated':False}:raise ValueError('limited_owner_required')":"if identity!={'sid':config['owner_sid'],'elevated':False}:raise ValueError('limited_owner_required')\n    REVIEW.mkdir(parents=True)",
        "store=NarratorStore(ROOT/'data',reviewed)":"parity=Path(config['parity_receipt'])\n    if config['segment_batches'] and (sha(parity)!=config['parity_receipt_sha256'] or json.loads(parity.read_text())['status']!='PASS_TECHNICAL_BATCH_ONLY'):raise ValueError('batch_parity_unverified')\n    store=NarratorStore(ROOT/'data',reviewed,segment_batches=config['segment_batches'])",
        "'inference_submitted':False,'publication_paused':True":"'inference_submitted':False,'segment_batches':health['segment_batches'],'publication_paused':True",
    }
    for before,after in replacements.items():
        if old.count(before)!=1:raise RuntimeError('known_launcher_template_changed')
        old=old.replace(before,after)
    compile(old,'new-standalone','exec')
    return old

def parity_source(launcher,parts):
    marker='    secret,_=read_secret(CREDENTIAL_TARGET)'
    if launcher.count(marker)!=1:raise RuntimeError('known_launcher_template_changed')
    prefix=launcher.split(marker)[0].replace("ROOT/'data/batch-update-v1/startup'","ROOT/'data/batch-update-v1/parity-review'")
    return prefix+'''    from youtube_ops.collector_narrator_host import WindowsScriptRunner,SCRIPT,REFERENCE,validate_cues
    from youtube_ops.collector_narration_common import inspect_wav
    before={'script':sha(SCRIPT),'reference':sha(REFERENCE)}
    output=ROOT/'data/batch-update-v1/parity/narration.wav'
    parts='''+repr(parts)+'''
    cues=WindowsScriptRunner().batch(parts,output,threading.Event())
    audio=inspect_wav(output);validate_cues(cues,parts,audio['frames'],audio['sample_rate'])
    if before!={'script':sha(SCRIPT),'reference':sha(REFERENCE)}:raise ValueError('narrator_identity_changed')
    process=json.loads((output.parent/'batch-process.private.json').read_text())
    if process['exit_code']!=0 or process['owned_active_processes']!=0:raise ValueError('batch_process_exit_unverified')
    write('parity-completed.private.json',{'status':'PASS_TECHNICAL_BATCH_ONLY','pid':os.getpid(),'owner_sid':identity['sid'],'elevated':False,'execution_mode':'cli_segment_batch_v1','audio':audio,'cues':cues,'process':process,'provenance':reviewed.provenance,'identity_before_after':before,'model_loads_verified_by_cli_log':1,'listening':'NOT_TESTED','publication_paused':True})
except BaseException as error:
    if REVIEW.exists():write('parity-failed.private.json',{'status':'BLOCKED_PARITY','error_class':type(error).__name__,'publication_paused':True})
    raise SystemExit(1)
'''

def prepare_code(package,config,review):
    code=WORK/'code';code.mkdir();(code/'youtube_ops').mkdir()
    for name in NAMES:raw_write(code/'youtube_ops'/name,(WORK/('new-'+name)).read_bytes())
    bundle={'files':package['files']}
    raw_write(code/'standalone-bundle.json',json.dumps(bundle,sort_keys=True).encode())
    original=(ROOT/'code/narrator-standalone.py').read_text()
    launcher=new_launcher(original)
    raw_write(code/'narrator-standalone.py',launcher.encode())
    raw_write(code/'parity.py',parity_source(launcher,package['parity_segments']).encode())
    configuration=dict(config,bundle_sha256=sha(code/'standalone-bundle.json'),segment_batches=False,parity_receipt='',parity_receipt_sha256='')
    raw_write(code/'config.json',json.dumps(configuration,sort_keys=True).encode())
    # Code inherits the administrator-owned read-only owner ACL from WORK.
    return code,configuration

def assert_new_code(owner):
    ps(r'''$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;& 'C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/assert-code.ps1' -OwnerSid $r.owner''',{'owner':owner})

def parity_task(config):
    result=ps(r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$s=New-Object -ComObject Schedule.Service;$s.Connect();$f=$s.GetFolder('\KnowledgeNetworkCollector')
try{$existing=$f.GetTask('NarratorBatchParityV1')}catch{if($_.Exception.HResult -ne -2147024894){throw};$existing=$null}
if($null -ne $existing){throw 'parity_task_exists'}
$a=New-ScheduledTaskAction -Execute 'C:/ProgramData/KnowledgeNetworkCollector/HostExec/runtime/python/python.exe' -Argument '-I -S -B C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code/parity.py' -WorkingDirectory 'C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1/code'
$p=New-ScheduledTaskPrincipal -UserId $r.owner -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$settings.AllowHardTerminate=$false
Register-ScheduledTask -TaskPath '\KnowledgeNetworkCollector\' -TaskName 'NarratorBatchParityV1' -InputObject (New-ScheduledTask -Action $a -Principal $p -Settings $settings) -ErrorAction Stop|Out-Null
$t=$f.GetTask('NarratorBatchParityV1');$t.SetSecurityDescriptor(('O:'+$r.owner+'G:'+$r.owner+'D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;'+$r.owner+')'),16)
$xml=$t.Xml;$null=$t.Run($null);@{xml=$xml;start_attempts=1}|ConvertTo-Json -Compress
''',{'owner':config['owner_sid']})
    raw_write(WORK/'parity-task.private.xml',result['xml'].encode())
    deadline=time.monotonic()+1140
    while time.monotonic()<deadline:
        reports=list((DATA/'batch-update-v1/parity-review').glob('*/parity-*.private.json'))
        if len(reports)>1:raise RuntimeError('parity_outcome_ambiguous')
        if reports:
            value=json.loads(reports[0].read_text())
            if value.get('status')!='PASS_TECHNICAL_BATCH_ONLY' or value.get('elevated') is not False or value.get('owner_sid')!=config['owner_sid']:raise RuntimeError('parity_failed_preserve_fence')
            # A receipt alone is insufficient: the limited task must really finish.
            ended=ps("$s=New-Object -ComObject Schedule.Service;$s.Connect();$t=$s.GetFolder('\\KnowledgeNetworkCollector').GetTask('NarratorBatchParityV1');@{state=$t.State;result=$t.LastTaskResult;instances=$t.GetInstances(0).Count}|ConvertTo-Json -Compress")
            if ended['state']==3 and ended['result']==0 and ended['instances']==0:return reports[0],value
        time.sleep(.25)
    raise RuntimeError('parity_outcome_unknown_no_retry')

def make_private_data(owner):
    ps(r'''
$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$base='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/data/batch-update-v1'
New-Item -ItemType Directory -Path $base -ErrorAction Stop|Out-Null
$acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetAccessRuleProtection($true,$false);$acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
foreach($sid in @('S-1-5-18','S-1-5-32-544',$r.owner)){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
Set-Acl -LiteralPath $base -AclObject $acl
foreach($child in @('parity','parity-review','startup')){New-Item -ItemType Directory -Path ($base+'/'+$child) -ErrorAction Stop|Out-Null}
''',{'owner':owner})

def preserve_old_code(config,task):
    backup=WORK/'old-code';backup.mkdir()
    for name in ('config.json','standalone-bundle.json','narrator-standalone.py','task.private.xml'):
        raw_write(backup/name,(ROOT/'code'/name).read_bytes())
    (backup/'youtube_ops').mkdir()
    for name in NAMES:raw_write(backup/'youtube_ops'/name,(ROOT/'code/youtube_ops'/name).read_bytes())
    raw_write(WORK/'task-before.private.xml',task['xml'].encode())
    write(WORK/'task-before.private.json',task)
    paths=[ROOT/'code'/name for name in ('config.json','standalone-bundle.json','narrator-standalone.py','task.private.xml')]
    paths.extend(ROOT/'code/youtube_ops'/name for name in NAMES)
    records=ps(r'''$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;@($r.paths|ForEach-Object{@{path=$_;sddl=(Get-Acl -LiteralPath $_).Sddl}})|ConvertTo-Json -Compress''',{'paths':[str(path) for path in paths]})
    write(WORK/'original-code-descriptors.private.json',records)

def wait_startup(config):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        ready=list((DATA/'batch-update-v1/startup').glob('*/startup-ready.private.json'))
        failed=list((DATA/'batch-update-v1/startup').glob('*/startup-failed.private.json'))
        if failed or len(ready)>1:raise RuntimeError('new_startup_failed_or_ambiguous')
        if ready:
            value=json.loads(ready[0].read_text())
            if (value.get('status')!='PASS_LOOPBACK_AUTH_ONLY' or value.get('owner_sid')!=config['owner_sid'] or value.get('elevated') is not False
                or value.get('segment_batches') is not True or (value.get('missing_bearer'),value.get('wrong_bearer'),value.get('authenticated_health'))!=(401,401,200)):
                raise RuntimeError('new_startup_identity_unverified')
            return ready[0],value
        time.sleep(.25)
    raise RuntimeError('new_startup_outcome_unknown_no_retry')

def main():
    package=json.loads((WORK/'batch-update-bundle.private.json').read_text())
    config=json.loads((ROOT/'code/config.json').read_text())
    identity=ps("$i=[Security.Principal.WindowsIdentity]::GetCurrent();@{sid=$i.User.Value;elevated=([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}|ConvertTo-Json -Compress")
    if (identity!={'sid':config['owner_sid'],'elevated':True} or identity['sid']=='S-1-5-18'
        or not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)
        or Path(sys.executable).resolve()!=PYTHON.resolve() or sha(PYTHON)!=config['server_python_sha256']):raise RuntimeError('elevated_recorded_owner_helper_required')
    verify_bundle(package,config)
    task=task_proof(config)
    old_ready=json.loads((DATA/'review/startup-ready.private.json').read_text())
    if task['pid']!=old_ready['pid']:raise RuntimeError('old_startup_pid_changed')
    preserve_old_code(config,task)
    process=None;connection=None;fence_state={'committed':False};exited=False
    review=WORK/'update-review';review.mkdir()
    with probe.NamespaceGuard(DB) as guard:
        try:
            process=bind_running(guard.native,task,guard,config['owner_sid'])
            # Every namespace guard precedes the helper's physical C-API open.
            connection=Sqlite(DB,guard)
            expected=package['expected_job_ids']
            def on_fenced():
                fence_state['committed']=True
                write(review/'fence-committed.private.json',{'status':'MAINTENANCE_FENCE_COMMITTED','fence':FENCE,'schema1_backup_sha256':sha(WORK/'schema1-before-update.backup.sqlite')})
            before=prepare_fence(connection,expected,lambda:backup_locked(DB,WORK/'schema1-before-update.backup.sqlite'),on_fenced)
            fresh=task_proof(config)
            if (fresh['pid'],fresh['creation_filetime'],fresh['xml'])!=(task['pid'],task['creation_filetime'],task['xml']):raise RuntimeError('fixed_task_changed_while_fenced')
            guard.native.running(process,task['creation_filetime'])
            write(review/'prepared.private.json',{'status':'PREPARED_IDLE_FENCE_WRITER_LOCK_HELD','fence':FENCE,'pid':task['pid'],'creation_filetime':task['creation_filetime'],'ledger_identity':guard.ledger,'snapshot':before,'schema1_backup_sha256':sha(WORK/'schema1-before-update.backup.sqlite'),'original_code_retained':True,'publication_paused':True})
            disabled=task_operation('disable',task['xml'],config['owner_sid'])
            write(review/'task-disabled.private.json',disabled)
            # The writer lock remains held: no previously checked POST can commit.
            idle_native(connection,expected,FENCE);guard.native.running(process,task['creation_filetime'])
            held_process_owner(guard.native,process,config['owner_sid'])
            if not guard.native.k.TerminateProcess(process,0):raise RuntimeError('exact_held_process_stop_failed')
            if guard.native.k.WaitForSingleObject(process,10000)!=0:raise RuntimeError('exact_process_exit_unknown')
            exited=True
            idle_native(connection,expected,FENCE)
            connection.execute('COMMIT')
            write(review/'exit-confirmed.private.json',{'status':'EXACT_HELD_PROCESS_EXIT_CONFIRMED','pid':task['pid'],'creation_filetime':task['creation_filetime'],'ledger_identity':guard.ledger,'writer_lock_held_through_exit':True,'no_runtime_code_replaced':True})
            make_private_data(config['owner_sid'])
            code,new_config=prepare_code(package,config,review)
            assert_new_code(config['owner_sid'])
            write(review/'rollback-prepared.private.json',{'status':'PREPARED_REQUIRES_EXACT_STATE_REVIEW','original_task_xml':str(WORK/'task-before.private.xml'),'original_code_backup':str(WORK/'old-code'),'original_database_backup':str(WORK/'schema1-before-update.backup.sqlite'),'rollback_code':str(code),'rollback_mode':'Reviewed new source with segment_batches false; preserve current database and all schema2 records.','preconditions':['Parity task and owned model process both confirmed exited.','No queued/running jobs or unknown hold.','Bind current task/PID/source and physical database under protected namespace.','Use a new unique startup review directory and preserve every configuration revision.','Clear only this exact maintenance fence inside held writer transaction.'],'never_restore_schema1_over_schema2':True,'automatic_rollback':False,'publication_paused':True})
            parity_path,parity=parity_task(config)
            if parity['provenance']!=old_ready['provenance']:raise RuntimeError('batch_parity_provenance_changed')
            write(review/'parity-verified.private.json',{'status':'PASS_TECHNICAL_PARITY_ONLY','receipt':str(parity_path),'sha256':sha(parity_path),'canonical_eight_wavs_reused':package['canonical_audio'],'listening':'NOT_TESTED','no_canonical_audio_overwritten':True})
            # Preserve even the intermediate configuration; no overwritten artifact.
            previous_config=(code/'config.json').read_bytes()
            (code/'config.json').rename(WORK/'config-parity-disabled.retained.json')
            write(review/'config-revision-retained.private.json',{'original_path':str(code/'config.json'),'retained_path':str(WORK/'config-parity-disabled.retained.json'),'sha256':hashlib.sha256(previous_config).hexdigest(),'size':len(previous_config),'reason':'Parity task completed; preserve the disabled configuration as a referenced rollback revision.','recorded_at':time.time(),'archive_performed':False,'deletion_performed':False})
            new_config.update(segment_batches=True,parity_receipt=str(parity_path),parity_receipt_sha256=sha(parity_path))
            raw_write(code/'config.json',json.dumps(new_config,sort_keys=True).encode())
            assert_new_code(config['owner_sid'])
            switched=task_operation('switch',disabled['xml'],config['owner_sid'])
            write(review/'task-switched-disabled.private.json',switched)
            # There is no listener and the exact old process is dead. Clear ONLY
            # our own fence; any unknown/changed hold blocks this operation.
            connection.execute('BEGIN IMMEDIATE');clear_own_fence(connection,expected);connection.execute('COMMIT')
            write(review/'activation-intent.private.json',{'status':'READY_FOR_ONE_LIMITED_OWNER_START','task_xml_sha256':hashlib.sha256(switched['xml'].encode()).hexdigest(),'new_launcher_sha256':sha(code/'narrator-standalone.py'),'new_config_sha256':sha(code/'config.json'),'old_schema1_backup_restore_permitted':False})
            started=task_operation('start',switched['xml'],config['owner_sid'])
            write(review/'task-start-requested.private.json',started)
            ready_path,ready=wait_startup(config)
            current=task_proof(config,code)
            if current['pid']!=ready['pid']:raise RuntimeError('new_process_binding_unverified')
            new_process=bind_running(guard.native,current,guard,config['owner_sid'])
            guard.native.k.CloseHandle(new_process)
            write(review/'completed.private.json',{'status':'PASS_BATCH_LOOPBACK_ACTIVATION_ONLY','ready_receipt':str(ready_path),'ready_sha256':sha(ready_path),'parity_receipt':str(parity_path),'remote_batch_request':'NOT_TESTED','listening':'NOT_TESTED','route_changed':False,'publication_paused':True})
            print(json.dumps({'status':'PASS_BATCH_LOOPBACK_ACTIVATION_ONLY','review_directory':str(review),'remote_batch_request':'NOT_TESTED','publication_paused':True}))
        except BaseException as error:
            if connection:
                try:connection.execute('ROLLBACK')
                except BaseException:pass
            write(review/'blocked.private.json',{'status':'BLOCKED_PRESERVE_ALL_STATE','error_class':type(error).__name__,'error':str(error) if isinstance(error,RuntimeError) and re.fullmatch('[a-z_]+',str(error)) else 'private_update_error','fence_committed':fence_state['committed'],'old_process_exit_confirmed':exited,'automatic_retry':False,'automatic_database_restore':False,'publication_paused':True})
            raise
        finally:
            if connection:connection.close()
            if process:guard.native.k.CloseHandle(process)

if __name__=='__main__':main()
'@
Write-New "$work/update-helper.py" $utf8.GetBytes($helper)
Assert-Trust "$work/update-helper.py" $ownerSid
Write-New "$work/prepared-only.private.json" $utf8.GetBytes((@{status='BUNDLE_CAPTURED_BEFORE_ACTIVATION';bundle_sha256=$BundleSha256;helper_sha256=(Hash-Bytes $utf8.GetBytes($helper));publication_paused=$true;host_runtime_changed=$false;database_opened=$false;task_changed=$false;network_changed=$false}|ConvertTo-Json))
# Root must review and native-test these exact bytes before staging an owner command.
& "$runtime/python.exe" -I -S -B "$work/update-helper.py" 1>"$work/owner-update.stdout.private.log" 2>"$work/owner-update.stderr.private.log"
if($LASTEXITCODE -ne 0){throw 'Batch update blocked; preserve batch-update-v1 and inspect its private update-review receipt. Do not retry.'}
Get-Content -LiteralPath "$work/owner-update.stdout.private.log" -Raw
