; Inno Setup Script for Premiere AI Editor
; Compiles a single-file graphical installer for Windows 11 x64

#define MyAppName "Premiere AI Editor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Tlab Video Tools"
#define MyAppURL "https://github.com/pouraminam/Pr-Pro"
#define MyAppExeName "start_engine.bat"

[Setup]
AppId={{D81938D2-4874-4C59-BCDF-211756472401}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=PremiereAIEditor_Setup_v1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\plugin\*"; DestDir: "{userappdata}\Adobe\UXP\Plugins\External\com.premiere.ai.editor"; Flags: recursesubdirs createallsubdirs
Source: "..\..\engine\*"; DestDir: "{app}\engine"; Flags: recursesubdirs createallsubdirs
Source: "start_engine.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "start_engine.vbs"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} Engine"; Filename: "{app}\start_engine.vbs"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName} Engine"; Filename: "{app}\start_engine.vbs"; WorkingDir: "{app}"

[Run]
Filename: "{app}\start_engine.vbs"; Description: "Launch Premiere AI Editor Engine"; Flags: postinstall nowait skipifsilent
