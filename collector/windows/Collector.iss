#ifndef PackageDir
  #error PackageDir must name the verified self-contained release directory
#endif
#ifndef OutputDir
  #error OutputDir must name a local installer output directory
#endif
[Setup]
AppId={{19CF91E1-6D57-45C3-9ED9-19ACDE2BC814}
AppName=The Knowledge Network Collector
AppVersion=0.1.0
AppPublisher=KnowledgeNetwork contributors
DefaultDirName={autopf}\The Knowledge Network Collector
DisableDirPage=yes
DefaultGroupName=The Knowledge Network Collector
OutputDir={#OutputDir}
OutputBaseFilename=The-Knowledge-Network-Collector-0.1.0-setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\kn-collector-dashboard.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\The Knowledge Network Collector"; Filename: "{app}\kn-collector-dashboard.exe"

[Code]
var
  CompanionWasEnabled: Boolean;

function GetFileAttributesW(Name: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function RunWorker(const Verb: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if CompareText(ExpandConstant('{app}'), ExpandConstant('{autopf}\The Knowledge Network Collector')) <> 0 then Exit;
  if (GetFileAttributesW(ExpandConstant('{app}')) and $400) <> 0 then Exit;
  if (GetFileAttributesW(ExpandConstant('{app}\kn-collector.exe')) and $400) <> 0 then Exit;
  Result := Exec(ExpandConstant('{app}\kn-collector.exe'), Verb,
    ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := Result and (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ServiceImage: String;
begin
  Result := '';
  if CompareText(WizardDirValue, ExpandConstant('{autopf}\The Knowledge Network Collector')) <> 0 then begin
    Result := 'Collector installation requires its fixed Program Files directory.';
    Exit;
  end;
  { remove-service deletes the registration; remember its opt-in before that. }
  if RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Services\KnowledgeNetworkCollector',
    'ImagePath', ServiceImage) then
    if Pos(' --enable-companion ', ' ' + ServiceImage + ' ') > 0 then begin
      CompanionWasEnabled := True;
      Log('Preserving configured user-session companion mode during upgrade.');
    end;
  if FileExists(ExpandConstant('{app}\kn-collector.exe')) then
    if not RunWorker('remove-service') then
      Result := 'Could not stop the existing Collector service. Installation was not continued.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  InstallCommand: String;
begin
  if CurStep = ssPostInstall then begin
    InstallCommand := 'install-service';
    if CompanionWasEnabled then InstallCommand := InstallCommand + ' --enable-companion';
    if not RunWorker(InstallCommand) then
      RaiseException('Collector files were installed, but service setup failed. Keep the installer log and run kn-collector.exe install-service elevated to repair.');
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := RunWorker('remove-service');
  if not Result then
    MsgBox('Could not stop the Collector service. Uninstall was not continued; private data is retained.', mbError, MB_OK);
end;
