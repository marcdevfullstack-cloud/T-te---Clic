# Recette PyInstaller : construit dist/TeteAClic/TeteAClic.exe
# Lancer depuis la racine du projet :  pyinstaller --noconfirm packaging/tete_a_clic.spec
from pathlib import Path

import re

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                  VarFileInfo, VarStruct, VSVersionInfo)

ROOT = Path(SPECPATH).parent
_config = (ROOT / "tete_a_clic" / "config.py").read_text(encoding="utf-8")
VERSION = re.search(r'VERSION = "([^"]+)"', _config).group(1)
AUTHOR = re.search(r'AUTHOR = "([^"]+)"', _config).group(1)
_v = tuple(int(x) for x in VERSION.split(".")) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_v, prodvers=_v),
    kids=[
        StringFileInfo([StringTable("040C04B0", [
            StringStruct("CompanyName", AUTHOR),
            StringStruct("FileDescription", "Tête-à-Clic - contrôle de l'ordinateur par la tête"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "TeteAClic"),
            StringStruct("LegalCopyright", f"© 2026 {AUTHOR}. Tous droits réservés."),
            StringStruct("OriginalFilename", "TeteAClic.exe"),
            StringStruct("ProductName", "Tête-à-Clic"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x040C, 1200])]),
    ],
)

# MediaPipe charge libmediapipe.dll depuis son propre dossier : on embarque le paquet complet.
mp_datas, mp_binaries, mp_hidden = collect_all("mediapipe")
# Interface : pywebview (Edge WebView2) et pythonnet, avec leurs DLL .NET.
wv_datas, wv_binaries, wv_hidden = collect_all("webview")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=mp_binaries + wv_binaries,
    datas=mp_datas + wv_datas + [
        (str(ROOT / "models" / "*.task"), "models"),
        (str(ROOT / "tete_a_clic" / "ui" / "web"), "tete_a_clic/ui/web"),
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
        (str(ROOT / "LICENSE.txt"), "."),
        (str(ROOT / "PRIVACY.md"), "."),
        (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    ],
    hiddenimports=mp_hidden + wv_hidden + ["clr", "clr_loader"],
    excludes=["pandas", "IPython", "pytest", "tkinter"],  # matplotlib reste : MediaPipe l'importe
    noarchive=False,
)
# Le module vidéo FFmpeg d'OpenCV (30 Mo) ne sert qu'à lire des fichiers vidéo : la webcam passe par DirectShow.
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0]]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TeteAClic",
    icon=str(ROOT / "assets" / "icon.ico"),
    console=False,  # pas de fenêtre noire : les messages vont dans le journal
    version=version_info,
)
coll = COLLECT(exe, a.binaries, a.datas, name="TeteAClic")
