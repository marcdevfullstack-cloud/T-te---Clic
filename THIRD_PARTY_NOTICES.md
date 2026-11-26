# Logiciels tiers — Tête-à-Clic

Tête-à-Clic (© 2026 MarcDev@) s'appuie sur les composants open source suivants. Chacun reste soumis à sa propre licence. Les textes complets sont fournis avec chaque paquet (dossier `_internal` de l'application, fichiers `*.dist-info/LICENSE*`).

| Composant | Version | Licence | Usage |
|---|---|---|---|
| Python | 3.14 | PSF License | Environnement d'exécution |
| MediaPipe (Google) | 1.2 | Apache-2.0 | Détection du visage et des expressions |
| Modèle MediaPipe Face Landmarker | — | Apache-2.0 | Modèle d'IA embarqué |
| OpenCV (opencv-python) | 5.0 | Apache-2.0 | Caméra et traitement d'image |
| NumPy | 2.5 | BSD-3-Clause et licences associées | Calcul numérique |
| Pillow | 13.0 | MIT-CMU (HPND) | Dessin de l'anneau du curseur et du clavier |
| pywebview | 6.2 | BSD-3-Clause | Fenêtre de l'application |
| pythonnet / clr_loader | 3.2 / 0.3 | MIT | Pont vers Microsoft Edge WebView2 |
| Microsoft Edge WebView2 (SDK et runtime) | — | Licence Microsoft (composant redistribuable) | Moteur d'affichage de l'interface |
| bottle, proxy_tools | — | MIT | Serveur interne de l'interface |
| Matplotlib | 3.11 | Matplotlib License (type PSF) | Dépendance de MediaPipe |
| protobuf | — | BSD-3-Clause | Dépendance de MediaPipe |
| flatbuffers, absl-py | — | Apache-2.0 | Dépendances de MediaPipe |
| sounddevice | 0.5 | MIT | Dépendance de MediaPipe |

## Polices

Le clavier utilise les polices Segoe UI de Windows, déjà présentes sur l'ordinateur. Elles ne sont pas distribuées avec Tête-à-Clic.

## Outils de fabrication (non distribués)

- **PyInstaller** (GPL-2.0 avec exception d'amorçage) : construit l'exécutable. L'exception autorise la distribution d'applications propriétaires.
- **Inno Setup** : construit l'installateur. **Son usage commercial nécessite une licence commerciale** (voir https://jrsoftware.org/isorder.php).
