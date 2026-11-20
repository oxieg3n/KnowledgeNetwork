[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BundleDirectory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BundleSha256
)
$ErrorActionPreference='Stop'
$root='C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1'
$existing='C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$python="$existing/runtime/python/python.exe"
$manifest='D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001/review/narrator-manifest.LOCAL-USE-CANDIDATE.private.json'
$manifestPin='42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84'
$taskPath='\KnowledgeNetworkCollector\'
$taskName='NarratorStandaloneV1'
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
function Assert-AdminCode([string]$Path) {
    $node=Get-Item -LiteralPath $Path -Force
    $first=$true
    $allowed=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
    while($null -ne $node){
        if(($node.Attributes -band 0x400) -ne 0){throw 'Protected execution reparse point.'}
        $acl=Get-Acl -LiteralPath $node.FullName
        $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed){throw 'Protected execution ownership unavailable.'}
        $mask=if($first){0x500D0156}else{0x500D0040}
        foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
            if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $allowed -and (([long]$ace.FileSystemRights -band $mask) -ne 0)){throw 'Protected execution writable by another identity.'}
        }
        $node=if($node -is [IO.DirectoryInfo]){$node.Parent}else{$node.Directory};$first=$false
    }
}
function Set-NewDirectoryAcl([string]$Path,[string]$OwnerSid,[bool]$Writable) {
    # Only newly created project children are changed; existing ancestors stay intact.
    $acl=[Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    foreach($sid in @('S-1-5-18','S-1-5-32-544')){
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
    }
    $rights=if($Writable){'FullControl'}else{'ReadAndExecute'}
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($OwnerSid),$rights,'ContainerInherit,ObjectInherit','None','Allow'))
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function Write-New([string]$Path,[byte[]]$Bytes) {
    $f=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$f.Write($Bytes,0,$Bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
function Start-KnownHostExec([object]$Pins) {
    $serviceName='KnowledgeNetworkHostExec'
    $image='"C:/Windows/System32/OpenSSH/sshd.exe" -f "C:/ProgramData/KnowledgeNetworkCollector/HostExec/sshd_config"'
    $paths=@{sshd_binary='C:/Windows/System32/OpenSSH/sshd.exe';sshd_config="$existing/sshd_config";dispatcher="$existing/runtime/collector_host_exec.py";authorized_keys="$existing/authorized_keys";bridge_config="$existing/config.json";broker_config="$existing/narrator-broker.json"}
    if(@($Pins.PSObject.Properties).Count -ne $paths.Count){throw 'Dedicated SSH pin set unavailable.'}
    foreach($name in $paths.Keys){
        if([string]$Pins.$name -cnotmatch '^[a-f0-9]{64}$'){throw 'Dedicated SSH pin unavailable.'}
        Assert-AdminCode $paths[$name]
        $null=Capture-File $paths[$name] $Pins.$name 33554432
    }
    $service=Get-CimInstance Win32_Service -Filter "Name='KnowledgeNetworkHostExec'" -ErrorAction Stop
    if($null -eq $service -or $service.Name -cne $serviceName -or $service.StartName -cne 'LocalSystem' -or $service.PathName.Replace('\','/') -ine $image -or $service.State -notin @('Running','Stopped') -or $service.StartMode -eq 'Disabled'){throw 'Dedicated SSH service identity/state mismatch.'}
    $initial=$service.State
    Write-New "$root/code/ssh-service-before.private.json" $utf8.GetBytes((@{name=$serviceName;state=$initial;image=$service.PathName;start_name=$service.StartName}|ConvertTo-Json))
    if($initial -eq 'Stopped'){
        if(@(Get-NetTCPConnection -State Listen -LocalPort 22230 -ErrorAction SilentlyContinue).Count){throw 'Dedicated SSH22230 occupied; no service start.'}
        # Configuration validation only; never edit shared SSH/Gateway/firewall.
        $null=& $paths.sshd_binary -t -f $paths.sshd_config 2>&1
        if($LASTEXITCODE -ne 0){throw 'Dedicated SSH configuration validation failed.'}
        Write-New "$root/code/ssh-service-start-intent.private.json" $utf8.GetBytes('{"service":"KnowledgeNetworkHostExec","attempts_max":1,"operation":"Start only if stopped","no_config_change":true}')
        Start-Service -Name $serviceName -ErrorAction Stop
        (Get-Service -Name $serviceName).WaitForStatus('Running',[TimeSpan]::FromSeconds(10))
    }
    $after=Get-CimInstance Win32_Service -Filter "Name='KnowledgeNetworkHostExec'" -ErrorAction Stop
    $listeners=@(Get-NetTCPConnection -State Listen -LocalPort 22230 -ErrorAction Stop)
    if($after.State -cne 'Running' -or $after.PathName.Replace('\','/') -ine $image -or $after.StartName -cne 'LocalSystem' -or $listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $after.ProcessId){throw 'Dedicated SSH start/listener outcome unverified; preserve, do not retry.'}
    $bindLines=@(Get-Content -LiteralPath $paths.sshd_config -Encoding UTF8|Where-Object {$_ -match '^\s*ListenAddress\s+'})
    if($bindLines.Count -ne 1){throw 'Dedicated SSH ListenAddress shape changed.'}
    $address=($bindLines[0].Trim() -split '\s+')[1]
    $parsed=$null
    if(-not [Net.IPAddress]::TryParse($address,[ref]$parsed) -or $address -in @('0.0.0.0','::') -or $listeners[0].LocalAddress -cne $address){throw 'Dedicated SSH bound address differs; preserve state and reconcile.'}
    Write-New "$root/code/ssh-service-after.private.json" $utf8.GetBytes((@{status='PASS_SERVICE_IDENTITY_ONLY';name=$serviceName;before=$initial;state=$after.State;pid=$after.ProcessId;port=22230;gateway_changed=$false;authentication_not_tested=$true}|ConvertTo-Json))
}

# The bootstrap itself must be captured and hashed by the owner's reviewed command.
if($env:COMPUTERNAME -ine 'BLACKHAT-BASE'){throw 'BLACKHAT-BASE required.'}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or $identity.User.Value -eq 'S-1-5-18'){throw 'Elevated owner context required; never SYSTEM.'}
Assert-AdminCode "$existing/narrator-broker.json"
$broker=Get-Content -LiteralPath "$existing/narrator-broker.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$ownerSid=[string]$broker.owner_sid
if($ownerSid -cne $identity.User.Value -or $broker.manifest_sha256 -cne $manifestPin){throw 'Recorded owner or manifest mismatch.'}
Assert-AdminCode $python
Assert-AdminCode "$existing/runtime/python"
Assert-AdminCode "$existing/runtime-files.private.json"
$inventory=Get-Content -LiteralPath "$existing/runtime-files.private.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if(@($inventory).Count -ne 37 -or @(Get-ChildItem -LiteralPath "$existing/runtime/python" -Force).Count -ne 37){throw 'Runtime inventory changed.'}
$runtimeNames=@($inventory|ForEach-Object {[string]$_.name})
if(@($runtimeNames|Sort-Object -Unique).Count -ne 37){throw 'Duplicate runtime names.'}
foreach($member in @(Get-ChildItem -LiteralPath "$existing/runtime/python" -Force)){if($member.PSIsContainer -or $member.Name -cnotin $runtimeNames){throw 'Unexpected runtime member.'}}
foreach($item in $inventory){
    if($item.name -notmatch '^[A-Za-z0-9_.-]+$' -or $item.sha256 -notmatch '^[a-f0-9]{64}$'){throw 'Runtime inventory shape.'}
    $file="$existing/runtime/python/$($item.name)";Assert-AdminCode $file
    $null=Capture-File $file $item.sha256 33554432
}
foreach($name in $broker.files.PSObject.Properties.Name){
    if($name -notin @('__init__.py','collector_narrator_pipe.py','collector_narrator_control.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')){throw 'Existing broker source list changed.'}
    $file="$existing/runtime/youtube_ops/$name";Assert-AdminCode $file
    $null=Capture-File $file $broker.files.$name
}
if(@($broker.files.PSObject.Properties).Count -ne 6){throw 'Existing broker source list changed.'}
$null=Capture-File $manifest $manifestPin
$bundlePath=[IO.Path]::GetFullPath($BundleDirectory)
$bundle=Capture-File (Join-Path $bundlePath 'standalone-bundle.json') $BundleSha256 16384
$package=$utf8.GetString($bundle) | ConvertFrom-Json
$names=@('__init__.py','collector_narrator_host.py','collector_narration_common.py','collector_credentials.py')
if($package.schema_version -ne 1 -or @($package.files.PSObject.Properties).Count -ne $names.Count -or $package.client_public_key_xml -isnot [string] -or $package.tailscale_exe_sha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Bundle shape mismatch.'}
$publicKey=[Security.Cryptography.RSACryptoServiceProvider]::new()
try {
    $publicKey.PersistKeyInCsp=$false
    if($package.client_public_key_xml.Length -gt 1024 -or $package.client_public_key_xml -match '<(?:P|Q|D|DP|DQ|InverseQ)>'){throw 'Public recipient key required.'}
    $publicKey.FromXmlString($package.client_public_key_xml)
    if($publicKey.KeySize -ne 2048 -or -not $publicKey.PublicOnly){throw 'RSA2048 public recipient required.'}
} finally {$publicKey.Dispose()}
$transport=$null
if($null -ne $package.transport_review_sha256){
    if($package.transport_review_sha256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Transport review pin invalid.'}
    $transportBytes=Capture-File (Join-Path $bundlePath 'policy-proof.private.json') $package.transport_review_sha256 65536
    $transport=$utf8.GetString($transportBytes)|ConvertFrom-Json
    if($transport.schema_version -ne 1 -or $transport.status -cne 'PASS_FRESH_REVIEW' -or $transport.intended_target_identity -cne 'BLACKHAT-BASE' -or $transport.policy_sha256 -cnotmatch '^[a-f0-9]{64}$' -or $transport.approved_v5_typed_object_equal -ne $true -or $transport.inventory_id_addresses_equal -ne $true -or $transport.all_advertised_enabled_routes_explicit_empty -ne $true -or $transport.official_validation -cne 'PASS' -or $transport.preview_byte_matches -ne 10){throw 'Reviewed transport proof unavailable.'}
    $reviewed=[DateTime]::Parse($transport.reviewed_at).ToUniversalTime();$valid=[DateTime]::Parse($transport.valid_until).ToUniversalTime()
    if([DateTime]::UtcNow -lt $reviewed -or [DateTime]::UtcNow -gt $valid -or ($valid-$reviewed).TotalSeconds -gt 7200){throw 'Transport proof is stale; obtain fresh read-only review before bootstrap.'}
}
$sources=@{}
foreach($name in $names){
    $pin=[string]$package.files.$name
    if($pin -cnotmatch '^[a-f0-9]{64}$'){throw 'Bundle member pin missing.'}
    $sources[$name]=Capture-File (Join-Path $bundlePath $name) $pin
}
if(Test-Path -LiteralPath $root){throw 'Standalone root exists; reconcile it, do not retry or choose a new path.'}
$scheduler=New-Object -ComObject 'Schedule.Service';$scheduler.Connect()
$folder=$scheduler.GetFolder('\KnowledgeNetworkCollector')
try{$old=$folder.GetTask($taskName)}catch [Runtime.InteropServices.COMException]{if($_.Exception.HResult -ne -2147024894){throw};$old=$null}
if($null -ne $old){throw 'Standalone task already exists; preserve and reconcile.'}
$existingNarratorListeners=@(Get-NetTCPConnection -State Listen -LocalPort 39110 -ErrorAction SilentlyContinue)
if($existingNarratorListeners.Count){
    Write-Output ((@{status='BLOCKED_EXISTING_LISTENER';port=39110;listeners=@($existingNarratorListeners|Select-Object LocalAddress,LocalPort,OwningProcess);mutation_performed=$false})|ConvertTo-Json -Depth 4)
    throw '39110 occupied; preserve the listener and identify its owner.'
}
$probe=[Net.Sockets.Socket]::new([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.SocketType]::Stream,[Net.Sockets.ProtocolType]::Tcp)
try{$probe.ExclusiveAddressUse=$true;$probe.Bind([Net.IPEndPoint]::new([Net.IPAddress]::Loopback,39110))}finally{$probe.Dispose()}
Assert-AdminCode (Split-Path -Parent $root)
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
Set-NewDirectoryAcl $root $ownerSid $false
foreach($name in @('code','code/youtube_ops','data','data/review')){New-Item -ItemType Directory -Path "$root/$name" -ErrorAction Stop | Out-Null}
Set-NewDirectoryAcl "$root/data" $ownerSid $true
Set-NewDirectoryAcl "$root/data/review" $ownerSid $true
foreach($name in $names){Write-New "$root/code/youtube_ops/$name" $sources[$name]}
Write-New "$root/code/standalone-bundle.json" $bundle
$config=@{schema_version=1;owner_sid=$ownerSid;manifest=$manifest;manifest_sha256=$manifestPin;bundle_sha256=$BundleSha256;server_python_sha256=$broker.server_python_sha256;client_public_key_xml=$package.client_public_key_xml}
Write-New "$root/code/config.json" $utf8.GetBytes(($config|ConvertTo-Json -Depth 4))
$launcher=@'
import hashlib,json,os,sys,threading,http.client
from pathlib import Path
ROOT=Path('C:/ProgramData/KnowledgeNetworkCollector/NarratorStandaloneV1')
sys.path.insert(0,str(ROOT/'code'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    with (ROOT/'data/review'/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,sort_keys=True);f.flush();os.fsync(f.fileno())
try:
    config=json.loads((ROOT/'code/config.json').read_text(encoding='utf-8-sig'))
    import subprocess
    command="$i=[Security.Principal.WindowsIdentity]::GetCurrent();@{sid=$i.User.Value;elevated=([Security.Principal.WindowsPrincipal]::new($i)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}|ConvertTo-Json -Compress"
    raw=subprocess.check_output([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',command],timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    identity=json.loads(raw)
    if identity!={'sid':config['owner_sid'],'elevated':False}:raise ValueError('limited_owner_required')
    if sha(Path(sys.executable))!=config['server_python_sha256']:raise ValueError('python_changed')
    bundle=ROOT/'code/standalone-bundle.json'
    if sha(bundle)!=config['bundle_sha256']:raise ValueError('bundle_changed')
    for name,pin in json.loads(bundle.read_text())['files'].items():
        if sha(ROOT/'code/youtube_ops'/name)!=pin:raise ValueError('source_changed')
    manifest=Path(config['manifest'])
    if sha(manifest)!=config['manifest_sha256']:raise ValueError('manifest_changed')
    from youtube_ops.collector_narrator_host import NarratorManifest,NarratorStore,NarratorHTTPServer,verify_spool_acl,CREDENTIAL_TARGET
    from youtube_ops.collector_credentials import read_secret
    verify_spool_acl(ROOT/'data')
    reviewed=NarratorManifest(manifest)
    secret,_=read_secret(CREDENTIAL_TARGET)
    if len(secret.encode('utf-8'))>190:raise ValueError('credential_envelope_bound')
    encrypt="$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;$rsa=[Security.Cryptography.RSACryptoServiceProvider]::new();try{$rsa.PersistKeyInCsp=$false;$rsa.FromXmlString($r.public_key);[Console]::Out.Write([Convert]::ToBase64String($rsa.Encrypt([Text.Encoding]::UTF8.GetBytes($r.secret),$true)))}finally{$rsa.Dispose()}"
    wrapped=subprocess.check_output([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',encrypt],input=json.dumps({'public_key':config['client_public_key_xml'],'secret':secret}).encode('utf-8'),timeout=10,creationflags=subprocess.CREATE_NO_WINDOW).decode('ascii')
    import base64
    if len(base64.b64decode(wrapped,validate=True))!=256:raise ValueError('credential_envelope_invalid')
    write('forge-bearer-envelope.private.json',{'schema_version':1,'algorithm':'RSA2048-OAEP-SHA1','recipient_public_key_sha256':hashlib.sha256(config['client_public_key_xml'].encode('utf-8')).hexdigest(),'ciphertext_base64':wrapped,'credential_target':'KnowledgeNetworkCollector/OxiegenNarrator/Host'})
    store=NarratorStore(ROOT/'data',reviewed)
    server=NarratorHTTPServer(('127.0.0.1',39110),store,secret)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},daemon=True)
    thread.start();store.start()
    def request(auth):
        c=http.client.HTTPConnection('127.0.0.1',39110,timeout=10)
        try:
            c.request('GET','/health',headers={} if auth is None else {'Authorization':'Bearer '+auth})
            r=c.getresponse();b=r.read(65537)
            return r.status,json.loads(b) if r.status==200 else None
        finally:c.close()
    absent=request(None)[0];wrong=request(secret+'-invalid')[0];code,health=request(secret)
    if absent!=401 or wrong!=401 or code!=200 or health['provenance']!=reviewed.provenance or health['execution_hold']:raise ValueError('local_auth_unverified')
    write('startup-ready.private.json',{'status':'PASS_LOOPBACK_AUTH_ONLY','pid':os.getpid(),'owner_sid':identity['sid'],'elevated':False,'missing_bearer':absent,'wrong_bearer':wrong,'authenticated_health':code,'provenance':reviewed.provenance,'inference_submitted':False,'publication_paused':True})
    thread.join()
except BaseException as error:
    write('startup-failed.private.json',{'status':'BLOCKED_STARTUP','error_class':type(error).__name__,'error':str(error) if isinstance(error,ValueError) and str(error).replace('_','').isalpha() else 'private_startup_error','publication_paused':True})
    raise SystemExit(1)
'@
Write-New "$root/code/narrator-standalone.py" $utf8.GetBytes($launcher)
Assert-AdminCode "$root/code/narrator-standalone.py"
$action=New-ScheduledTaskAction -Execute $python -Argument "-I -S -B $root/code/narrator-standalone.py" -WorkingDirectory "$root/code"
$taskPrincipal=New-ScheduledTaskPrincipal -UserId $ownerSid -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$settings.AllowHardTerminate=$false
$task=New-ScheduledTask -Action $action -Principal $taskPrincipal -Settings $settings -Description 'KnowledgeNetwork limited private narrator'
Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -InputObject $task -ErrorAction Stop | Out-Null
$registered=$folder.GetTask($taskName)
$sddl="O:$ownerSid"+"G:$ownerSid"+"D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;$ownerSid)"
$registered.SetSecurityDescriptor($sddl,16)
Write-New "$root/code/task.private.xml" $utf8.GetBytes($registered.Xml)
Write-New "$root/code/rollback.private.txt" $utf8.GetBytes('Do not stop during queued/running/unknown narration. Reconcile exact task/process/job state first. Once confirmed idle, stop and disable only NarratorStandaloneV1; preserve all files/data. No original NarratorControl, Gateway or Serve route was changed by this bootstrap.')
if($null -ne $package.host_exec_service_pins){Start-KnownHostExec $package.host_exec_service_pins}
# Exactly one start attempt. Any timeout/unknown outcome requires reconciliation.
$null=$registered.Run($null)
$deadline=[DateTime]::UtcNow.AddSeconds(180)
$ready=$false
while([DateTime]::UtcNow -lt $deadline){
    if(Test-Path -LiteralPath "$root/data/review/startup-failed.private.json"){throw 'Owner task startup failed; preserve report and reconcile, do not retry.'}
    if(Test-Path -LiteralPath "$root/data/review/startup-ready.private.json"){
        $result=Get-Content -LiteralPath "$root/data/review/startup-ready.private.json" -Raw | ConvertFrom-Json
        if($result.status -cne 'PASS_LOOPBACK_AUTH_ONLY' -or $result.owner_sid -cne $ownerSid -or $result.elevated -ne $false){throw 'Owner startup receipt unavailable.'}
        $ready=$true;break
    }
    Start-Sleep -Milliseconds 500
}
if(-not $ready){throw 'Task startup outcome uncertain; retain task/root and reconcile. No retry or alternate spool.'}
if($null -ne $transport){
    # This fixed route is allowed only by the independently pinned, fresh FORGE review.
    if([DateTime]::UtcNow -gt $valid){throw 'Transport review expired during startup; loopback stays private.'}
    $tailscale='C:/Program Files/Tailscale/tailscale.exe'
    Assert-AdminCode $tailscale
    $null=Capture-File $tailscale $package.tailscale_exe_sha256 67108864
    $selfRaw=& $tailscale status --json
    if($LASTEXITCODE -ne 0){throw 'Host Tailscale identity unavailable; route unchanged.'}
    $status=$selfRaw|ConvertFrom-Json
    $actualAddresses=@($status.Self.TailscaleIPs|Sort-Object)
    $expectedAddresses=@($transport.intended_target_addresses|Sort-Object)
    if($status.BackendState -cne 'Running' -or $status.Self.Online -ne $true -or $status.Self.HostName -ine 'BLACKHAT-BASE' -or $status.Self.DNSName.TrimEnd('.') -ine $transport.intended_target_dns.TrimEnd('.') -or (Compare-Object $actualAddresses $expectedAddresses)){throw 'Host Tailscale identity/address drift; route unchanged.'}
    $beforeRaw=& $tailscale serve status --json
    if($LASTEXITCODE -ne 0){throw 'Serve configuration unavailable; route unchanged.'}
    $before=$beforeRaw|ConvertFrom-Json
    if($null -ne $before.TCP.'9443' -or @($before.Web.PSObject.Properties|Where-Object Name -Like '*:9443').Count){throw '9443 Serve route already exists; preserve it.'}
    if($null -ne $before.AllowFunnel -and @($before.AllowFunnel.PSObject.Properties|Where-Object Value -eq $true).Count){throw 'Unexpected Funnel state; route unchanged.'}
    if(@(Get-NetTCPConnection -State Listen -LocalPort 9443 -ErrorAction SilentlyContinue).Count){throw 'Native9443 occupied; route unchanged.'}
    $sockets=@()
    try{
        foreach($family in @([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.AddressFamily]::InterNetworkV6)){
            $s=[Net.Sockets.Socket]::new($family,[Net.Sockets.SocketType]::Stream,[Net.Sockets.ProtocolType]::Tcp);$sockets+=,$s;$s.ExclusiveAddressUse=$true
            $address=if($family -eq [Net.Sockets.AddressFamily]::InterNetworkV6){$s.DualMode=$false;[Net.IPAddress]::IPv6Any}else{[Net.IPAddress]::Any}
            $s.Bind([Net.IPEndPoint]::new($address,9443))
        }
    }finally{foreach($s in $sockets){$s.Dispose()}}
    Write-New "$root/code/serve-before.private.json" $utf8.GetBytes(($before|ConvertTo-Json -Depth 20))
    Write-New "$root/code/transport-review.private.json" $utf8.GetBytes(($transport|ConvertTo-Json -Depth 8))
    Write-New "$root/code/route-intent.private.json" $utf8.GetBytes('{"port":9443,"target":"http://127.0.0.1:39110","attempts_max":1,"publication_paused":true}')
    $routeResult=& $tailscale serve --bg --https=9443 http://127.0.0.1:39110 2>&1
    $routeExit=$LASTEXITCODE
    $afterRaw=& $tailscale serve status --json
    if($LASTEXITCODE -ne 0){throw 'Route outcome unknown; preserve route intent and reconcile without retry.'}
    $after=$afterRaw|ConvertFrom-Json
    Write-New "$root/code/serve-after.private.json" $utf8.GetBytes(($after|ConvertTo-Json -Depth 20))
    $newWeb=@($after.Web.PSObject.Properties|Where-Object Name -Like '*:9443')
    if($routeExit -ne 0 -or $newWeb.Count -ne 1 -or $newWeb[0].Value.Handlers.'/'.Proxy -cne 'http://127.0.0.1:39110' -or $after.TCP.'9443'.HTTPS -ne $true){throw 'Route result uncertain; reconcile retained before/after evidence, do not retry.'}
    $after.TCP.PSObject.Properties.Remove('9443');$after.Web.PSObject.Properties.Remove($newWeb[0].Name)
    if(($before|ConvertTo-Json -Depth 20 -Compress) -cne ($after|ConvertTo-Json -Depth 20 -Compress)){throw 'Unrelated Serve configuration differs; preserve evidence and reconcile.'}
    Write-New "$root/code/route-rollback.private.txt" $utf8.GetBytes('After verifying current9443 is still exactly the owned narrator route: tailscale serve --https=9443 off. Preserve original443/8443. Do not reset Serve or delete task/data. Reconcile unknown outcomes before another mutation.')
    $result|Add-Member NoteProperty private_https_9443 'CONFIGURED_PENDING_FORGE_TLS_ACCEPTANCE'
}
Write-Output ($result|ConvertTo-Json -Depth 5)
