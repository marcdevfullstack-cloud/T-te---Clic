; Installateur Windows (Inno Setup 6) : produit dist\TeteAClic-Setup-<version>.exe
; S'installe pour l'utilisateur courant, sans droits administrateur.

#define AppName "Tête-à-Clic"
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif
#define AppExe "TeteAClic.exe"
#ifndef AppSource
  #define AppSource "..\dist\TeteAClic"
#endif

[Setup]
AppId={{E169EC40-1B1A-416F-9A4C-637B337CE9C9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=MarcDev@
AppCopyright=© 2026 MarcDev@. Tous droits réservés.
AppPublisherURL=mailto:marcdevfullstack@gmail.com
AppSupportURL=mailto:marcdevfullstack@gmail.com
AppContact=marcdevfullstack@gmail.com
VersionInfoCompany=MarcDev@
VersionInfoCopyright=© 2026 MarcDev@
VersionInfoDescription=Installation de Tête-à-Clic
VersionInfoProductName={#AppName}
VersionInfoVersion={#AppVersion}
LicenseFile=..\LICENSE.txt
DefaultDirName={localappdata}\Programs\TeteAClic
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=TeteAClic-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le bureau (recommandé)"; GroupDescription: "Options :"
Name: "autostart"; Description: "Démarrer {#AppName} avec Windows"; GroupDescription: "Options :"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "TeteAClic"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart; \
  Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName} maintenant"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "StopApp"

[UninstallDelete]
; Les réglages (%LOCALAPPDATA%\TeteAClic) sont conservés volontairement.
Type: filesandordirs; Name: "{app}"
