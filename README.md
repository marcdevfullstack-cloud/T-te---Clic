# HeadPilot

*par **MarcDev@** · © 2026 MarcDev@. Tous droits réservés. · Contact : [marcdevfullstack@gmail.com](mailto:marcdevfullstack@gmail.com)*

**Contrôler son ordinateur avec la tête et le regard**, avec une simple webcam. Pour les personnes paralysées, à mobilité réduite, ou temporairement privées de leurs mains. Aucun matériel spécial n'est nécessaire, et tout est traité sur l'ordinateur : aucune image n'est enregistrée ni envoyée.

## Comment ça marche

| Geste | Action |
|---|---|
| Tourner la tête | Le curseur suit (pointage absolu, lissé contre les tremblements) |
| **Clignement long** (environ ½ seconde) | Clic gauche. Les clignements naturels sont ignorés |
| Garder le curseur **immobile** 1,2 s | Clic. Un anneau se remplit autour du curseur |
| **Lever les sourcils** | Clic droit |
| **Ouvrir la bouche**, puis lever ou baisser la tête | Défilement (molette) |
| **Fermer les yeux 2,5 s** | Pause, puis reprise, sans les mains |
| Bouton **Clavier** | Ouvre le clavier visuel de Windows, utilisable avec le clic par immobilité |

**Pour l'aidant :**
- **Ctrl + Alt + P** met en pause ou reprend, même hors de la fenêtre.
- **Toucher la vraie souris** suspend aussitôt le contrôle par la tête pendant 2,5 s.

**Précision du clic :** quand on cligne ou qu'on lève les sourcils, la tête bouge souvent un peu. HeadPilot clique donc là où était le curseur **juste avant** le geste.

## Démarrage

```powershell
cd head_pilot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Au démarrage, **regarde le centre de l'écran 2 secondes** : c'est le recentrage. Tu peux le refaire avec le bouton **Recentrer**, par exemple après avoir changé de position.

## Réglages (dans la fenêtre, enregistrés automatiquement)

- **Sensibilité horizontale et verticale** : plus haut = petits mouvements de tête suffisent.
- **Stabilité** : plus haut = curseur plus stable, plus bas = plus réactif.
- **Gestes** : chacun s'active ou se désactive. Une jauge en direct montre l'intensité du geste et son seuil de déclenchement : utile pour apprendre.
- **Clic par immobilité** : durée de 0,6 à 2,5 s.
- **Son des clics** et **voix** (annonces de pause, de reprise et de recentrage).

## Technique

- **MediaPipe Face Landmarker** : 478 points du visage et scores des expressions (clignement, sourcils, bouche).
- **Orientation de la tête** : décalage du nez par rapport au milieu des yeux, divisé par l'écart des yeux. On suit ainsi la rotation, pas la position dans l'image.
- **Filtre « One Euro »** (Casiez et al., 2012), la référence pour le pointage : stable à l'arrêt, réactif en mouvement.
- **Anneau du curseur** : fenêtre Windows superposée, transparente pixel par pixel, que les clics traversent, rafraîchie à 60 images/s.
- **Souris** : API Windows via ctypes, en vrais pixels (compatible avec un affichage à 125 % ou 150 %).

```
headpilot/
  tracker.py   visage → orientation de la tête + scores des gestes
  gestures.py  reconnaissance des gestes (logique pure, testée)
  pointer.py   tête → position du curseur, clic par immobilité (logique pure, testée)
  filters.py   filtre One Euro
  engine.py    boucle principale : caméra → gestes → souris
  mouse.py     souris Windows, clavier visuel
  overlay.py   anneau transparent autour du curseur
  hotkey.py    raccourci Ctrl+Alt+P
  config.py    réglages enregistrés
  ui/          fenêtre (pywebview), flux vidéo local, interface web
main.py        point d'entrée
tests/         tests de la logique
```

Tests : `python -m unittest`
