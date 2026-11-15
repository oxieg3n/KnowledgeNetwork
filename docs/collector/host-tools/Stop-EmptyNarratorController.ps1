[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidatePattern('^S-1-5-21-(?:\d+-){3}\d+$')][string]$ExpectedOwnerSid,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedPythonSha256,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedTaskXmlSha256
)
$ErrorActionPreference='Stop'
$root='C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$python="$root/runtime/python/python.exe"
$intent="$root/broker-update-v1/update-intent.private.json"
$spool='D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001'
$current=[Security.Principal.WindowsIdentity]::GetCurrent()
if($current.User.Value -cne $ExpectedOwnerSid -or $current.User.Value -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Intended owner elevated required; nothing stopped.'}
function Assert-StopTrustedPath([string]$Path) {
 $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop;$first=$true
 $trusted=@($ExpectedOwnerSid,'S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
 while($null -ne $item){
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Stop trust path contains reparse point.'}
  $acl=Get-Acl -LiteralPath $item.FullName
  $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
  if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted){throw 'Stop trust owner/DACL differs.'}
  foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
   if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
   $mask=if($first){0x000D0156}else{0x000D0040}
   if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $trusted -and ($ace.FileSystemRights -band $mask) -ne 0){throw 'Stop trust path is writable by another identity.'}
  }
  $item=if($item -is [IO.DirectoryInfo]){$item.Parent}else{$item.Directory};$first=$false
 }
}
foreach($path in @($root,"$root/runtime","$root/runtime/python",$python,"$root/runtime-files.private.json",$intent,"$spool/narrator-control.sqlite")){Assert-StopTrustedPath $path}
if((Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedPythonSha256){throw 'Protected interpreter differs; nothing stopped.'}
$inventory=Get-Content -LiteralPath "$root/runtime-files.private.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($inventory -isnot [array] -or $inventory.Count -ne 37 -or @(Get-ChildItem -LiteralPath "$root/runtime/python" -Force).Count -ne 37){throw 'Protected interpreter inventory differs.'}
$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($record in $inventory){
 if($record.name -isnot [string] -or $record.name -cnotmatch '^[A-Za-z0-9_.-]+$' -or -not $seen.Add($record.name) -or $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $record.bytes -isnot [int]){throw 'Protected runtime record differs.'}
 $path=Join-Path "$root/runtime/python" $record.name;Assert-StopTrustedPath $path
 if((Get-Item -LiteralPath $path).Length -ne $record.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $record.sha256){throw 'Protected runtime bytes differ.'}
}
$pythonSource = @'
import ctypes
from ctypes import wintypes as w
import base64,hashlib,json,os,sqlite3,subprocess,sys,time,uuid
from pathlib import Path

ROOT=Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec')
SPOOL=Path('D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001')
PYTHON=ROOT/'runtime/python/python.exe'
LAUNCHER=ROOT/'runtime/narrator-control-launch.py'
INTENT=ROOT/'broker-update-v1/update-intent.private.json'
STAGE='intent'

class Blocked(RuntimeError): pass

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path, limit=262144):
    path=Path(path)
    for part in (path,*path.parents):
        if part.is_symlink() or getattr(part.lstat(),'st_file_attributes',0)&0x400:
            raise Blocked('stop_path_untrusted')
    if not path.is_file() or path.stat().st_nlink!=1:
        raise Blocked('stop_path_untrusted')
    with path.open('rb') as stream: raw=stream.read(limit+1)
    if len(raw)>limit: raise Blocked('stop_file_limit')
    return raw
def decode(raw):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value: raise Blocked('stop_json_invalid')
            value[key]=item
        return value
    try:
        return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError,RecursionError): raise Blocked('stop_json_invalid') from None

TASK_SCRIPT=r'''
$ErrorActionPreference='Stop'
$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$root='C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$python="$root/runtime/python/python.exe";$launcher="$root/runtime/narrator-control-launch.py"
$path='\KnowledgeNetworkCollector\';$name='NarratorControl'
$s=New-Object -ComObject 'Schedule.Service';$s.Connect();$f=$s.GetFolder('\KnowledgeNetworkCollector');$t=$f.GetTask($name)
$xml=Export-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
$h=[Security.Cryptography.SHA256]::Create()
try{$digest=([BitConverter]::ToString($h.ComputeHash([Text.UTF8Encoding]::new($false,$true).GetBytes($xml)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
[xml]$definition=$xml;$ns=[Xml.XmlNamespaceManager]::new($definition.NameTable);$ns.AddNamespace('t',$definition.DocumentElement.NamespaceURI)
$principals=@($definition.SelectNodes('/t:Task/t:Principals/t:Principal',$ns))
$ownerMatches=$principals.Count -eq 1 -and $principals[0].UserId -ceq $r.owner_sid
# COM may return an account name; the pinned XML retains the canonical owner SID.
$identityChecks=@{xml_match=($digest -ceq $r.xml_sha256);owner_match=$ownerMatches;limited=($t.Definition.Principal.RunLevel -eq 0);interactive=($t.Definition.Principal.LogonType -eq 3)}
if(@($identityChecks.Values|Where-Object{-not $_}).Count){[Console]::Out.Write(($identityChecks|ConvertTo-Json -Compress));exit 1}
$instances=@($t.GetInstances(0));$state=[int]$t.State
if($r.action -ceq 'ready'){
 if($state -ne 3 -or $instances.Count -ne 0){throw 'Task not Ready.'}
 [Console]::Out.Write('{"state":3,"instances":0}');exit 0
}
if($r.action -cnotin @('query','stop') -or $state -ne 4 -or $instances.Count -ne 1){throw 'Exactly one Running task instance required.'}
$instance=[string]$instances[0].InstanceGuid
$engine=[int]$instances[0].EnginePID
if($r.action -ceq 'stop'){
 if($instance -cne $r.instance_id -or $engine -ne $r.engine_pid){throw 'Task instance changed.'}
 $null=$t.Stop(0)
 [Console]::Out.Write('{"stop_requested_once":true}');exit 0
}
$items=@(Get-CimInstance -ClassName Win32_Process -Filter "Name = 'python.exe'" -ErrorAction Stop | Where-Object {$_.ProcessId -ne $r.helper_pid -and $_.ExecutablePath -and $_.ExecutablePath.Replace('\','/') -ieq $python})
if($items.Count -gt 8){throw 'Process inventory bound.'}
$records=@()
foreach($p in $items){
 if(-not $p.CommandLine -or $p.CommandLine.Length -gt 1024){throw 'Process command unavailable.'}
 $o=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
 if($o.ReturnValue -ne 0){throw 'Process owner unavailable.'}
 $parents=@();$next=[int]$p.ParentProcessId
 if($engine -ne $p.ProcessId){
  for($i=0;$i -lt 8 -and $next -gt 0;$i++){
   $parent=Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $next" -ErrorAction Stop
   if($null -eq $parent){throw 'Task parent unavailable.'}
   $parents+=@{pid=[int]$parent.ProcessId;parent_pid=[int]$parent.ParentProcessId;creation_filetime=[string]$parent.CreationDate.ToUniversalTime().ToFileTimeUtc()}
   if($parent.ProcessId -eq $engine){break};$next=[int]$parent.ParentProcessId
  }
 }
 $records+=@{pid=[int]$p.ProcessId;image=[string]$p.ExecutablePath;command_line=[string]$p.CommandLine;owner_sid=[string]$o.Sid;creation_filetime=[string]$p.CreationDate.ToUniversalTime().ToFileTimeUtc();parent_pid=[int]$p.ParentProcessId;parents=$parents}
}
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq 39110 | ForEach-Object {[int]$_.OwningProcess})
[Console]::Out.Write((@{state=$state;instance_id=$instance;engine_pid=$engine;processes=$records;listener_pids=$listeners}|ConvertTo-Json -Depth 6 -Compress))
'''

def task_call(action, expected, timeout=10, instance=None, engine=None):
    if action not in ('query','stop','ready'): raise Blocked('stop_action_denied')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes=[w.LPWSTR,w.UINT]
    buffer=ctypes.create_unicode_buffer(32768)
    if not 0<kernel.GetSystemDirectoryW(buffer,len(buffer))<len(buffer):
        raise Blocked('system_powershell_unverified')
    executable=Path(buffer.value)/'WindowsPowerShell/v1.0/powershell.exe'
    request={'action':action,'owner_sid':expected['owner_sid'],'xml_sha256':expected['task_xml_sha256'],
        'helper_pid':os.getpid(),'instance_id':instance,'engine_pid':engine}
    try:
        result=subprocess.run([str(executable),'-NoLogo','-NoProfile','-NonInteractive','-Command',TASK_SCRIPT],
            input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=timeout,check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired): raise Blocked('task_stop_outcome_unverified' if action=='stop' else 'task_query_unverified') from None
    if result.returncode or len(result.stdout)>65536: raise Blocked('task_operation_unverified')
    return decode(result.stdout)

def argv(command):
    shell=ctypes.WinDLL('shell32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    shell.CommandLineToArgvW.argtypes=[w.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype=ctypes.POINTER(w.LPWSTR);kernel.LocalFree.argtypes=[ctypes.c_void_p]
    count=ctypes.c_int();value=shell.CommandLineToArgvW(command,ctypes.byref(count))
    if not value: raise Blocked('process_command_unverified')
    try:return [value[i] for i in range(count.value)]
    finally:kernel.LocalFree(value)

class HeldProcess:
    def __init__(self, process, expected):
        self.handle=None;self.pid=process['pid'];self.parents=[]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.api=ctypes.WinDLL('advapi32',use_last_error=True)
        k,a=self.kernel,self.api
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.CloseHandle.argtypes=[w.HANDLE];k.LocalFree.argtypes=[ctypes.c_void_p]
        k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
        k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
        k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
        a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
        a.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
        a.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.LPWSTR)]
        self.handle=k.OpenProcess(0x1000|0x100000,False,self.pid)
        if not self.handle: raise Blocked('process_handle_unverified')
        token=w.HANDLE()
        try:
            size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value)
            if not k.QueryFullProcessImageNameW(self.handle,0,image,ctypes.byref(size)) or Path(image.value)!=PYTHON:
                raise Blocked('process_image_unverified')
            if not a.OpenProcessToken(self.handle,8,ctypes.byref(token)): raise Blocked('process_token_unverified')
            size=w.DWORD();a.GetTokenInformation(token,1,None,0,ctypes.byref(size))
            if not 0<size.value<=65536: raise Blocked('process_token_unverified')
            data=ctypes.create_string_buffer(size.value)
            if not a.GetTokenInformation(token,1,data,size,ctypes.byref(size)): raise Blocked('process_token_unverified')
            sid=w.LPWSTR()
            if not a.ConvertSidToStringSidW(ctypes.cast(data,ctypes.POINTER(ctypes.c_void_p))[0],ctypes.byref(sid)):
                raise Blocked('process_token_unverified')
            try: identity=sid.value
            finally:k.LocalFree(sid)
            elevation=w.DWORD()
            if not a.GetTokenInformation(token,20,ctypes.byref(elevation),ctypes.sizeof(elevation),ctypes.byref(size)) or identity!=expected['owner_sid'] or elevation.value:
                raise Blocked('owner_limited_process_required')
            self.created=self.creation()
            if not 0<=self.created-int(process['creation_filetime'])<10 or sha(read(PYTHON,32*1024*1024))!=expected['python_sha256']:
                raise Blocked('process_creation_or_python_changed')
            if k.WaitForSingleObject(self.handle,0)!=258: raise Blocked('controller_not_running')
        except BaseException:
            self.close();raise
        finally:
            if token:k.CloseHandle(token)
    def creation(self):
        values=[w.FILETIME() for _ in range(4)]
        if not self.kernel.GetProcessTimes(self.handle,*[ctypes.byref(v) for v in values]): raise Blocked('process_creation_unverified')
        return (values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
    def wait(self,seconds):
        if self.kernel.WaitForSingleObject(self.handle,max(0,int(seconds*1000)))!=0: raise Blocked('controller_stop_outcome_unknown')
        if self.creation()!=self.created: raise Blocked('process_identity_changed')
    def close(self):
        for parent in self.parents:self.kernel.CloseHandle(parent)
        self.parents=[]
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None

def associate(held,process,snapshot):
    engine=snapshot.get('engine_pid')
    if type(engine) is not int or engine<=0: raise Blocked('task_engine_unverified')
    if engine==held.pid:return
    next_pid=process['parent_pid'];child_time=held.created
    parents=process.get('parents')
    if not isinstance(parents,list) or not 1<=len(parents)<=8: raise Blocked('task_association_unverified')
    for parent in parents:
        if parent['pid']!=next_pid: raise Blocked('task_association_unverified')
        handle=held.kernel.OpenProcess(0x1000|0x100000,False,next_pid)
        if not handle: raise Blocked('task_parent_handle_unverified')
        held.parents.append(handle)
        times=[w.FILETIME() for _ in range(4)]
        if not held.kernel.GetProcessTimes(handle,*[ctypes.byref(v) for v in times]): raise Blocked('task_parent_creation_unverified')
        created=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        if not 0<=created-int(parent['creation_filetime'])<10 or created>child_time:
            raise Blocked('task_parent_identity_changed')
        if next_pid==engine:return
        child_time=created;next_pid=parent['parent_pid']
    raise Blocked('task_association_unverified')

def stop_empty(expected):
    global STAGE
    STAGE='intent'
    intent=decode(read(INTENT))
    if (not isinstance(intent,dict) or type(intent.get('schema_version')) is not int or intent['schema_version']!=1 or intent.get('status')!='FULL_REPAIR_PREPARED'
        or intent.get('owner_sid')!=expected['owner_sid'] or intent.get('task_state')!='Running'
        or intent.get('publication_paused') is not True or not isinstance(intent.get('task_xml'),str)
        or sha(intent['task_xml'].encode())!=expected['task_xml_sha256']):
        raise Blocked('prepared_update_intent_unverified')
    STAGE='database_guard'
    dbpath=SPOOL/'narrator-control.sqlite';read(dbpath,1024*1024)
    if any(Path(str(dbpath)+suffix).exists() for suffix in ('-journal','-wal','-shm')):
        raise Blocked('control_database_journal_uncertain')
    db=sqlite3.connect(dbpath.as_uri()+'?mode=rw',uri=True,timeout=2)
    held=None
    try:
        STAGE='database_lock'
        db.execute('BEGIN IMMEDIATE')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables!={'requests','audit'} or db.execute('PRAGMA journal_mode').fetchone()!=('delete',) or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1").fetchone():
            raise Blocked('control_database_schema_unverified')
        shapes={'requests':[('id','TEXT',0,None,1),('operation','TEXT',1,None,0),('state','TEXT',1,None,0),('response','TEXT',0,None,0)],
            'audit':[('request_id','TEXT',0,None,1),('owner_sid','TEXT',1,None,0),('operation','TEXT',1,None,0),('outcome','TEXT',1,None,0),('duration_ms','INTEGER',1,None,0),('result_sha256','TEXT',1,None,0)]}
        for table,shape in shapes.items():
            if [row[1:] for row in db.execute('PRAGMA table_info('+table+')')]!=shape:
                raise Blocked('control_database_schema_unverified')
        if db.execute('SELECT count(*) FROM requests').fetchone()!=(0,) or db.execute('SELECT count(*) FROM audit').fetchone()!=(0,):
            raise Blocked('controller_not_empty')
        STAGE='task_query'
        snapshot=task_call('query',expected)
        if (not isinstance(snapshot,dict) or set(snapshot)!={'state','instance_id','engine_pid','processes','listener_pids'}
            or type(snapshot['state']) is not int or snapshot['state']!=4 or not isinstance(snapshot['instance_id'],str)
            or type(snapshot['engine_pid']) is not int or snapshot['engine_pid']<=0
            or not isinstance(snapshot['processes'],list) or not 1<=len(snapshot['processes'])<=8
            or not isinstance(snapshot['listener_pids'],list) or any(type(p) is not int or p<=0 for p in snapshot['listener_pids'])):
            raise Blocked('running_task_unverified')
        try:uuid.UUID(snapshot['instance_id'].strip('{}'))
        except ValueError:raise Blocked('running_task_unverified') from None
        candidates=[]
        for process in snapshot.get('processes',[]):
            words=argv(process['command_line'])
            if (len(words)==5 and Path(words[0])==PYTHON and words[1:4]==['-I','-S','-B'] and Path(words[4])==LAUNCHER):
                candidates.append(process)
        if len(candidates)!=1 or candidates[0].get('owner_sid')!=expected['owner_sid']:
            raise Blocked('unique_owner_controller_unverified')
        process=candidates[0]
        if process['pid'] in snapshot.get('listener_pids',[]): raise Blocked('controller_owns_api_listener')
        STAGE='process_hold'
        held=HeldProcess(process,expected)
        associate(held,process,snapshot)
        stop_intent={'status':'EMPTY_CONTROLLER_STOP_INTENT','pid':process['pid'],'creation_filetime':held.created,
            'task_instance':snapshot['instance_id'],'ledger_rows':0,'audit_rows':0,'stop_attempts':1,'created_ns':time.time_ns()}
        STAGE='stop_intent'
        with (INTENT.parent/'empty-stop-intent.private.json').open('xb') as stream:
            stream.write(json.dumps(stop_intent).encode());stream.flush();os.fsync(stream.fileno())
        deadline=time.monotonic()+8
        STAGE='task_stop'
        result=task_call('stop',expected,timeout=4,instance=snapshot['instance_id'],engine=snapshot['engine_pid'])
        if result!={'stop_requested_once':True}: raise Blocked('task_stop_outcome_unverified')
        STAGE='process_exit_wait'
        held.wait(deadline-time.monotonic())
        remaining=deadline-time.monotonic()
        if remaining<=0: raise Blocked('task_stop_outcome_unverified')
        STAGE='task_ready'
        if task_call('ready',expected,timeout=remaining)!={'state':3,'instances':0}: raise Blocked('task_not_ready_after_stop')
        STAGE='complete'
        return {'status':'STOPPED_EMPTY_CONTROLLER','held_process_signaled':True,'task_state':'Ready'}
    finally:
        if held:held.close()
        db.rollback();db.close()

if __name__=='__main__':
    try:
        expected=decode(base64.b64decode(sys.argv[1],validate=True))
        result=stop_empty(expected)
    except Exception as error:
        allowed={'stop_path_untrusted','stop_file_limit','stop_json_invalid','system_powershell_unverified',
            'task_stop_outcome_unverified','task_query_unverified','task_operation_unverified',
            'process_command_unverified','process_handle_unverified','process_image_unverified',
            'process_token_unverified','owner_limited_process_required','process_creation_or_python_changed',
            'controller_not_running','process_creation_unverified','controller_stop_outcome_unknown',
            'process_identity_changed','task_engine_unverified','task_association_unverified',
            'task_parent_handle_unverified','task_parent_creation_unverified','task_parent_identity_changed',
            'prepared_update_intent_unverified','control_database_journal_uncertain','control_database_schema_unverified',
            'controller_not_empty','running_task_unverified','unique_owner_controller_unverified',
            'controller_owns_api_listener','task_not_ready_after_stop'}
        code=str(error) if isinstance(error,Blocked) and str(error) in allowed else 'empty_controller_stop_unverified'
        result={'status':'BLOCKED','stage':STAGE,'error':code}
        if type(getattr(error,'winerror',None)) is int:result['winerror']=error.winerror
    try:
        private={**result,'stage':STAGE,'recorded_ns':time.time_ns()}
        with (INTENT.parent/'empty-stop-result.private.json').open('xb') as stream:
            stream.write(json.dumps(private).encode());stream.flush();os.fsync(stream.fileno())
    except Exception:
        result={'status':'BLOCKED','stage':STAGE,'error':'empty_stop_result_unavailable'}
    print(json.dumps(result))
    sys.exit(0 if result['status']=='STOPPED_EMPTY_CONTROLLER' else 1)
'@
$payload=@{owner_sid=$ExpectedOwnerSid;python_sha256=$ExpectedPythonSha256;task_xml_sha256=$ExpectedTaskXmlSha256}|ConvertTo-Json -Compress
if(Test-Path -LiteralPath "$root/broker-update-v1/empty-stop-result.private.json"){throw 'Previous empty-controller result exists; reconcile without retry.'}
$encodedPayload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
$previousOutputEncoding=$OutputEncoding
try{
 $OutputEncoding=[Text.UTF8Encoding]::new($false)
 $output=$pythonSource | & $python -I -S -B - $encodedPayload 2>$null
 $nativeExit=$LASTEXITCODE
}finally{$OutputEncoding=$previousOutputEncoding}
$result=$output|ConvertFrom-Json
if($nativeExit -ne 0){
 $stage=if($result.stage -cmatch '^[a-z_]{1,48}$'){$result.stage}else{'unverified'}
 $code=if($result.error -cmatch '^[a-z_]{1,80}$'){$result.error}else{'unverified'}
 throw "Empty controller stop BLOCKED at $stage ($code); preserve evidence, never force or retry."
}
if($result.status -cne 'STOPPED_EMPTY_CONTROLLER' -or $result.held_process_signaled -isnot [bool] -or -not $result.held_process_signaled -or $result.task_state -cne 'Ready'){throw 'Controller stop result unverified; no file updates.'}
$result
