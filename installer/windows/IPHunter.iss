#define MyAppName "IPHunter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ParkSmart"
#define MyAppExeName "IPHunter.exe"

[Setup]
AppId={{B629D199-2C17-4F72-A3E0-677A45F45DBE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\installer-output
OutputBaseFilename=IPHunter-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\IPHunter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\IPHunter"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\IPHunter"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch IPHunter"; Flags: nowait postinstall skipifsilent
