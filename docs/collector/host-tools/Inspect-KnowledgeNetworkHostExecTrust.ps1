[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BootstrapFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BootstrapSha256
)
$ErrorActionPreference = 'Stop'
$bootstrap = [IO.Path]::GetFullPath($BootstrapFile)
$stream=[IO.File]::Open($bootstrap,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
$reader=[IO.BinaryReader]::new($stream)
try { $sourceBytes=$reader.ReadBytes(262145) } finally { $reader.Dispose() }
if ($sourceBytes.Length -gt 262144) { throw 'Diagnostic source exceeds its bound' }
$sha=[Security.Cryptography.SHA256]::Create()
try { $sourceHash=([BitConverter]::ToString($sha.ComputeHash($sourceBytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
if ($sourceHash -ne $BootstrapSha256) { throw 'Reviewed diagnostic source changed; stop.' }
$text=[Text.UTF8Encoding]::new($false,$true).GetString($sourceBytes)
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this read-only native ACL diagnostic in the same elevated host PowerShell session.' }
$root = 'C:/ProgramData/KnowledgeNetworkCollector/HostExec'
$python = 'D:/tools/audio/voicestudio/data/engines/voxcpm2/voxcpm2/.venv/Scripts/python.exe'
$sshd = 'C:/Windows/System32/OpenSSH/sshd.exe'
$powershell = 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
$commandShell = 'C:/Windows/System32/cmd.exe'
$hostKey = 'C:/ProgramData/ssh/ssh_host_ed25519_key'
$tokens=$null; $errors=$null
$tree=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Diagnostic source syntax failed' }
$function=@($tree.FindAll({param($a) $a -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object Name -eq 'Assert-TrustedPath')
if ($function.Count -ne 1) { throw 'Expected one reviewed trust helper' }
. ([scriptblock]::Create($function[0].Extent.Text))
$start=$text.IndexOf('# -I -S prevents')
$end=$text.IndexOf('function Protect-Directory',$start)
if ($start -lt 0 -or $end -le $start) { throw 'Read-only preflight boundaries missing' }
$preflight=$text.Substring($start,$end-$start)
$preflightTree=[Management.Automation.Language.Parser]::ParseInput($preflight,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Read-only preflight syntax failed' }
foreach ($cmd in $preflightTree.FindAll({param($a) $a -is [Management.Automation.Language.CommandAst]},$true)) {
    if ($cmd.GetCommandName() -notin @('Split-Path','Join-Path','Get-Content','Where-Object','Get-ChildItem','Assert-TrustedPath','Test-Path')) { throw 'Unexpected command in read-only trust preflight' }
}
$result=[ordered]@{status='PASS_TRUST_PREFLIGHT_ONLY';acl_changed=$false;account_created=$false;service_started=$false}
try { . ([scriptblock]::Create($preflight)) } catch {
    $exception=$_.Exception
    if (-not $exception.Data['checked_path']) { throw 'Trust diagnostic stopped without structured context; no ACL changed.' }
    $path=[string]$exception.Data['checked_path']
    $acl=Get-Acl -LiteralPath $path -ErrorAction Stop
    $result.status='BLOCKED_TRUST_PATH_IDENTIFIED'
    $result.path=$path
    $result.is_directory=(Get-Item -LiteralPath $path -Force).PSIsContainer
    $result.owner_sid=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    $result.blocked_principal_sid=$exception.Data['principal_sid']
    $result.blocked_rights=$exception.Data['rights']
    $result.checked_mask=$exception.Data['checked_mask']
    $result.sddl=$acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]'Access,Owner,Group')
    $result.rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | ForEach-Object {
        [ordered]@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString();rights=[int]$_.FileSystemRights;inherited=$_.IsInherited;inheritance=$_.InheritanceFlags.ToString();propagation=$_.PropagationFlags.ToString()}
    })
}
$evidence=Join-Path 'D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001/review' ('trust-check-'+[guid]::NewGuid().ToString('N')+'.private.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result | ConvertTo-Json -Depth 8))
$stream=[IO.File]::Open($evidence,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
@{status=$result.status;evidence_path=$evidence;acl_changed=$false;service_started=$false} | ConvertTo-Json
