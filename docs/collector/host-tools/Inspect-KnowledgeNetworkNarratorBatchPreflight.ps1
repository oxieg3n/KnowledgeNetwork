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
function Assert-ReadTrust([string]$Path){
    $node=Get-Item -LiteralPath $Path -Force;$first=$true
    $allowed=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
    while($null -ne $node){
        if(($node.Attributes -band 0x400) -ne 0){throw 'Read-only diagnostic reparse path rejected.'}
        $acl=Get-Acl -LiteralPath $node.FullName
        $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed){throw 'Read-only diagnostic trust unavailable.'}
        $mask=if($first){0x500D0156}else{0x500D0040}
        foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
            if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $allowed -and (([long]$ace.FileSystemRights -band $mask) -ne 0)){throw 'Read-only diagnostic path is writable by another identity.'}
        }
        $node=if($node -is [IO.DirectoryInfo]){$node.Parent}else{$node.Directory};$first=$false
    }
}
function Capture-Read([string]$Path,[long]$Limit){
    Assert-ReadTrust $Path
    $stream=[IO.File]::Open($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt $Limit){throw 'Diagnostic read bound exceeded.'}
        $memory=[IO.MemoryStream]::new()
        try{$stream.CopyTo($memory);return ,$memory.ToArray()}finally{$memory.Dispose()}
    }finally{$stream.Dispose()}
}
function Write-New([string]$Path,[byte[]]$Bytes){
    $stream=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$stream.Write($Bytes,0,[Math]::Min($Bytes.Length,65536));$stream.Flush($true)}finally{$stream.Dispose()}
}
if($env:COMPUTERNAME -ine 'BLACKHAT-BASE'){throw 'Read-only diagnostic requires BLACKHAT-BASE.'}
$owner=[Security.Principal.WindowsIdentity]::GetCurrent()
if($owner.User.Value -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($owner)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Elevated recorded owner required; never SYSTEM.'}
$config=$utf8.GetString((Capture-Read "$root/code/config.json" 65536))|ConvertFrom-Json
if($config.owner_sid -cne $owner.User.Value){throw 'Recorded diagnostic owner mismatch.'}
$helper=Capture-Read "$work/update-helper.py" 1048576
if((Hash-Bytes $helper) -cne $helperPin){throw 'Exact failed helper changed; no Python execution.'}
if((Hash-Bytes (Capture-Read $python 33554432)) -cne $config.server_python_sha256){throw 'Protected Python changed.'}
Assert-ReadTrust $work
$stem='batch-preflight-'+[Guid]::NewGuid().ToString('N')
$diagnostic=@'
import ast,base64,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
RAW=base64.b64decode('__CAPTURED_HELPER__',validate=True)
PIN='1ec820f1123aab4d12d8719efc0a462f89e9db18e80d52b09523743542129ca6'
WORK=Path('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1/batch-update-v1')
STEM='__DIAGNOSTIC_STEM__'
OWNER_CODE="$i=[Security.Principal.WindowsIdentity]::GetCurrent();@{sid=$i.User.Value;elevated=([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}|ConvertTo-Json -Compress"

def checked_prefix(raw,pin):
    if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('diagnostic_helper_hash_changed')
    text=raw.decode('utf-8',errors='strict');tree=ast.parse(text)
    main=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main']
    if len(main)!=1 or text.count('\ndef main():\n')!=1:raise ValueError('diagnostic_main_boundary_changed')
    prefix=''.join(text.splitlines(keepends=True)[:main[0].lineno-1])
    compile(prefix,'captured-readonly-helper-prefix','exec')
    return prefix

def save(name,data):
    with (WORK/(STEM+name)).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())

def denied(*args,**kwargs):raise RuntimeError('diagnostic_mutation_or_database_open_denied')

def run_diagnostic():
    report={'schema_version':1,'helper_sha256':PIN,'stages':[],'powershell':[],'mutation_performed':False,'database_opened':False,'inference_submitted':False,'publication_paused':True}
    stage='imports';namespace={'__name__':'knowledge_network_readonly_preflight'}
    try:
        exec(compile(checked_prefix(RAW,PIN),'captured-readonly-helper-prefix','exec'),namespace)
        # Only these two existing read-only fixed commands are permitted. No
        # original ps(), failure writer, task mutator or SQLite opener is called.
        def diagnostic_ps(code,value=None,timeout=20):
            if code not in (OWNER_CODE,namespace['TASK_PROOF']) or value is not None:denied()
            index=len(report['powershell']);timed_out=False
            try:
                result=subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=min(timeout,20),creationflags=subprocess.CREATE_NO_WINDOW)
                out,err,exit_code=result.stdout,result.stderr,result.returncode
            except subprocess.TimeoutExpired as error:
                out,err,exit_code,timed_out=error.stdout or b'',error.stderr or b'',None,True
            save('.ps-%d.stdout.private.log'%index,out[:65536]);save('.ps-%d.stderr.private.log'%index,err[:65536])
            report['powershell'].append({'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'exit_code':exit_code,'timed_out':timed_out,'stdout_bytes':len(out),'stderr_bytes':len(err),'truncated':len(out)>65536 or len(err)>65536})
            if timed_out or exit_code!=0 or len(out)>65536 or len(err)>65536:raise RuntimeError('readonly_powershell_failed_see_private_capture')
            return json.loads(out.decode('utf-8-sig'))
        namespace['ps']=diagnostic_ps
        for name in ('Sqlite','prepare_fence','clear_own_fence','preserve_old_code','task_operation','parity_task','make_private_data','prepare_code','assert_new_code','write','raw_write','retain_ps_failure','backup_locked','bind_running'):
            namespace[name]=denied
        namespace['sqlite3']=None
        report['stages'].append('PASS_IMPORTS')
        stage='owner_and_flags'
        config=json.loads((namespace['ROOT']/'code/config.json').read_text())
        identity=diagnostic_ps(OWNER_CODE)
        report['identity']=identity
        actual_image=Path(sys.executable)
        actual_sha=namespace['sha'](actual_image)
        report['runtime']={'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,'dont_write_bytecode':sys.flags.dont_write_bytecode,'actual_executable':str(actual_image),'actual_image_sha256':actual_sha,'image_matches_expected':actual_image.resolve()==namespace['PYTHON'].resolve() and actual_sha==config['server_python_sha256']}
        if identity!={'sid':config['owner_sid'],'elevated':True} or identity['sid']=='S-1-5-18':raise ValueError('diagnostic_owner_mismatch')
        if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or not report['runtime']['image_matches_expected']:raise ValueError('diagnostic_runtime_flags_or_image_mismatch')
        report['stages'].append('PASS_OWNER_FLAGS_IMAGE')
        stage='bundle_validation'
        package=json.loads((WORK/'batch-update-bundle.private.json').read_text())
        namespace['verify_bundle'](package,config)
        report['stages'].append('PASS_ACTUAL_BUNDLE_VALIDATION')
        stage='task_process_proof'
        task=namespace['task_proof'](config)
        report['task_process']={'pid':task['pid'],'creation_filetime':task['creation_filetime']}
        report['stages'].append('PASS_ACTUAL_TASK_PROCESS_PROOF')
        stage='startup_pid_binding'
        old_ready=json.loads((namespace['DATA']/'review/startup-ready.private.json').read_text())
        report['startup_pid_binding']={'actual_pid':task['pid'],'recorded_pid':old_ready['pid']}
        if task['pid']!=old_ready['pid']:raise ValueError('old_startup_pid_changed')
        report['stages'].append('PASS_STARTUP_PID_BINDING')
        report['status']='PASS_READ_ONLY_PREFLIGHT'
    except BaseException as error:
        report.update(status='BLOCKED_READ_ONLY_PREFLIGHT',stage=stage,error_class=type(error).__name__,error=str(error),winerror=getattr(error,'winerror',None))
        traceback.print_exc(file=sys.stderr)
    report_path=WORK/(STEM+'.report.private.json')
    save('.report.private.json',json.dumps(report,sort_keys=True,indent=2).encode())
    print(json.dumps({'status':report['status'],'stage':stage,'report_path':str(report_path),'mutation_performed':False,'database_opened':False,'publication_paused':True}))
    return 0 if report['status']=='PASS_READ_ONLY_PREFLIGHT' else 1

if __name__=='__main__':raise SystemExit(run_diagnostic())
'@
$diagnostic=$diagnostic.Replace('__CAPTURED_HELPER__',[Convert]::ToBase64String($helper)).Replace('__DIAGNOSTIC_STEM__',$stem)
if($diagnostic -match '[^\x00-\x7f]'){throw 'Captured diagnostic transport must be ASCII.'}
# BEGIN CAPTURED PROCESS: no native-command error-stream conversion in PS5.1.
$start=[Diagnostics.ProcessStartInfo]::new()
$start.FileName=$python;$start.Arguments='-I -S -B -';$start.WorkingDirectory=$work
$start.UseShellExecute=$false;$start.CreateNoWindow=$true
$start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
$process=[Diagnostics.Process]::new();$process.StartInfo=$start
$null=$process.Start();$stdoutTask=$process.StandardOutput.ReadToEndAsync();$stderrTask=$process.StandardError.ReadToEndAsync()
$process.StandardInput.Write($diagnostic);$process.StandardInput.Close()
$timedOut=-not $process.WaitForExit(90000)
if($timedOut){$process.Kill();$null=$process.WaitForExit(5000)}
if(-not $stdoutTask.Wait(5000) -or -not $stderrTask.Wait(5000)){throw 'Owned diagnostic streams remain uncertain; preserve evidence and do not retry updater.'}
$stdout=$stdoutTask.Result;$stderr=$stderrTask.Result
$outBytes=$utf8.GetBytes($stdout);$errBytes=$utf8.GetBytes($stderr)
Write-New "$work/$stem.stdout.private.log" $outBytes
Write-New "$work/$stem.stderr.private.log" $errBytes
$capture=@{schema_version=1;pid=$process.Id;exit_code=$process.ExitCode;timed_out=$timedOut;helper_sha256=$helperPin;stdout_truncated=($outBytes.Length -gt 65536);stderr_truncated=($errBytes.Length -gt 65536);publication_paused=$true}
Write-New "$work/$stem.process.private.json" $utf8.GetBytes(($capture|ConvertTo-Json))
$process.Dispose()
# END CAPTURED PROCESS
if($stdout.Length -gt 0){[Console]::Out.Write($stdout)}else{(@{status='BLOCKED_DIAGNOSTIC_STARTUP';process_evidence="$work/$stem.process.private.json";mutation_performed=$false;publication_paused=$true}|ConvertTo-Json -Compress)}
