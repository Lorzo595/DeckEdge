#ifndef AppVersion
#define AppVersion "0.1.0"
#endif
#ifndef Payload
#error Payload required
#endif
#ifndef Output
#error Output required
#endif
[Setup]
AppId={{4A8E0309-846A-4E17-827B-8154D77C4060}
AppName=DeckEdge
AppVersion={#AppVersion}
AppPublisher=Lorzo595
DefaultDirName={localappdata}\Programs\DeckEdge
DefaultGroupName=DeckEdge
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#Output}
OutputBaseFilename=DeckEdge-{#AppVersion}-Setup-x64
SetupIconFile=..\desktop\DeckEdge.ico
UninstallDisplayIcon={app}\DeckEdge.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=DeckEdge
[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked
[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Excludes: "portable.flag,data\*"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\DeckEdge"; Filename: "{app}\DeckEdge.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\DeckEdge"; Filename: "{app}\DeckEdge.exe"; Tasks: desktopicon; WorkingDir: "{app}"
[Run]
Filename: "{app}\prerequisites\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installation du composant Microsoft WebView2…"; Flags: waituntilterminated; Check: NeedsWebView2
Filename: "{app}\DeckEdge.exe"; Description: "Ouvrir DeckEdge"; Flags: nowait postinstall skipifsilent
[Code]
function NeedsWebView2: Boolean;
var Version: String;
begin
  Result := not ((RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM32, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')));
end;
function InitializeSetup(): Boolean;
var Code: Integer;
begin
  Result := True;
  if FileExists(ExpandConstant('{localappdata}\Programs\DeckEdge\DeckEdge.exe')) then
    Exec(ExpandConstant('{localappdata}\Programs\DeckEdge\DeckEdge.exe'), '--quit', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Command: String; Code: Integer; Shell, Shortcut: Variant;
begin
  if CurUninstallStep = usUninstall then begin
    Exec(ExpandConstant('{app}\DeckEdge.exe'), '--quit', '', SW_HIDE, ewWaitUntilTerminated, Code);
    if FileExists(ExpandConstant('{userstartup}\DeckEdge.lnk')) then begin
      try
        Shell := CreateOleObject('WScript.Shell');
        Shortcut := Shell.CreateShortcut(ExpandConstant('{userstartup}\DeckEdge.lnk'));
        if (CompareText(Shortcut.TargetPath, ExpandConstant('{app}\DeckEdge.exe')) = 0) and (Shortcut.Arguments = '--startup') then
          DeleteFile(ExpandConstant('{userstartup}\DeckEdge.lnk'));
      except
        Log('Impossible de vérifier le raccourci de démarrage DeckEdge.');
      end;
    end;
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DeckEdge', Command) then
      if CompareText(Command, '"' + ExpandConstant('{app}\DeckEdge.exe') + '" --startup') = 0 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DeckEdge');
  end;
end;
