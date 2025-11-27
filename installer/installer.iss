#define MyAppName "CS FiveM Management Tool"
#define MyAppExeName "csservers.exe"
#define MyAppPublisher "Covex Studios"
#define MyAppVersion "1.0.0"
#define MyAppDirName "CSFiveMTool"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=CSFiveMToolSetup
Compression=lzma
SolidCompression=yes

; run as admin
PrivilegesRequired=admin

; tell Windows env vars (PATH) changed
ChangesEnvironment=yes

SetupIconFile=..\icons\csfivem.ico

[Files]
Source: "..\dist\csservers.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; \
    GroupDescription: "Additional icons:"; Flags: unchecked

Name: "addtopath"; Description: "Add &csservers to PATH (command-line)"; \
    GroupDescription: "Command-line integration:"; Flags: checkedonce

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Run {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[Registry]
; add install dir to *user* PATH
Root: HKCU; \
    Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; \
    Tasks: addtopath; Flags: preservestringtype
