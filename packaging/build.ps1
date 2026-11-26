# Construit l'application Windows puis, si Inno Setup est installé, l'installateur.
# Usage (depuis la racine du projet, environnement virtuel activé) :  .\packaging\build.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Une application lancée depuis dist\ verrouille ses fichiers : la reconstruction échouerait.
$running = Get-Process TeteAClic -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*\dist\TeteAClic\*" }
if ($running) {
    Write-Host "Tête-à-Clic tourne depuis dist\ : ferme-le puis relance ce script." -ForegroundColor Yellow
    exit 1
}

function Invoke-Step($label, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "Échec : $label (code $LASTEXITCODE)" }
}

$version = (python main.py --version).Split(" ")[-1]
Invoke-Step "installation de PyInstaller" { python -m pip install --quiet pyinstaller }
Invoke-Step "tests" { python -m unittest -q }
Invoke-Step "icône" { python packaging\make_icon.py }
Invoke-Step "PyInstaller" { pyinstaller --noconfirm --log-level WARN --distpath dist --workpath build packaging\tete_a_clic.spec }

# L'exécutable construit doit charger le modèle d'IA et trouver son interface.
$test = Start-Process dist\TeteAClic\TeteAClic.exe -ArgumentList "--selftest" -Wait -PassThru
if ($test.ExitCode -ne 0) { throw "Autotest de l'exécutable échoué (voir %LOCALAPPDATA%\TeteAClic\tete_a_clic.log)" }
Write-Host "Application : dist\TeteAClic\TeteAClic.exe (version $version, autotest réussi)"

# Signature de code (Authenticode) : évite l'avertissement SmartScreen « éditeur inconnu ».
# Fournir le certificat de MarcDev@ :  $env:CODESIGN_PFX = "C:\chemin\certificat.pfx" ; $env:CODESIGN_PASSWORD = "..."
function Sign-File($path) {
    if (-not $env:CODESIGN_PFX) { return }
    $signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName | Select-Object -Last 1
    if (-not $signtool) { Write-Host "signtool introuvable (installe le SDK Windows) : signature ignorée." -ForegroundColor Yellow; return }
    Invoke-Step "signature de $path" { & $signtool.FullName sign /f $env:CODESIGN_PFX /p $env:CODESIGN_PASSWORD /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "Tête-à-Clic" $path }
}
Sign-File "dist\TeteAClic\TeteAClic.exe"
if (-not $env:CODESIGN_PFX) { Write-Host "Pas de certificat (CODESIGN_PFX) : application non signée." -ForegroundColor Yellow }

$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    Invoke-Step "Inno Setup" { & $iscc /Q "/DAppVersion=$version" packaging\installer.iss }
    $setup = Get-Item "dist\TeteAClic-Setup-$version.exe"
    Sign-File $setup.FullName
    Write-Host ("Installateur : {0} ({1:N0} Mo)" -f $setup.FullName, ($setup.Length / 1MB))
} else {
    Write-Host "Inno Setup 6 introuvable : installe-le (https://jrsoftware.org/isdl.php) pour produire l'installateur."
}
