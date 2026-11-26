# Tête-à-Clic

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
| Bouton **Clavier** | Affiche le clavier Tête-à-Clic (voir ci-dessous) |

## Écrire avec la tête : le clavier Tête-à-Clic

1. **Clique d'abord dans le texte où écrire** (Word, Bloc-notes, navigateur…), par clignement ou immobilité.
2. Affiche le clavier (bouton **Clavier**). Son bandeau indique **où le texte va s'écrire**.
3. Pointe une touche et **reste immobile** (ou cligne longuement) : la lettre est tapée.
   Rester sur la même touche la **retape** après un nouveau délai : pratique pour « ll », « ss ».

- Grandes touches AZERTY, accents en accès direct (é è à ç, ê ù en mode 123), **⇧** majuscule, **Entrée**, **⌫** effacer, flèches **← →**, **123** chiffres et symboles.
- **⇅** passe le clavier en haut ou en bas de l'écran ; **✕** le masque.
- Le clavier **ne prend jamais le focus** : le texte arrive dans ta fenêtre, et non dans Tête-à-Clic. Le clavier visuel de Windows (osk.exe), lui, ignore souvent les clics simulés : c'est pourquoi Tête-à-Clic a le sien.

**Pour l'aidant :**
- **Ctrl + Alt + P** met en pause ou reprend, même hors de la fenêtre.
- **Toucher la vraie souris** suspend aussitôt le contrôle par la tête pendant 2,5 s.

**Précision du clic :** quand on cligne ou qu'on lève les sourcils, la tête bouge souvent un peu. Tête-à-Clic clique donc là où était le curseur **juste avant** le geste.

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
tete_a_clic/
  tracker.py   visage → orientation de la tête + scores des gestes
  gestures.py  reconnaissance des gestes (logique pure, testée)
  pointer.py   tête → position du curseur, clic par immobilité (logique pure, testée)
  filters.py   filtre One Euro
  engine.py    boucle principale : caméra → gestes → souris
  mouse.py     souris et frappes clavier Windows (SendInput)
  keyboard.py  clavier Tête-à-Clic (fenêtre qui ne prend jamais le focus)
  keyboard_layout.py  disposition des touches (logique pure, testée)
  overlay.py   anneau transparent autour du curseur
  hotkey.py    raccourci Ctrl+Alt+P
  config.py    réglages enregistrés
  ui/          fenêtre (pywebview), flux vidéo local, interface web
main.py        point d'entrée
tests/         tests de la logique
```

Tests : `python -m unittest`

Ce que fera la version de ce soir :

La souris suit la tête : la position du nez par rapport aux yeux donne la direction, et un filtre anti-tremblement rend le curseur précis.
Clic gauche : un clignement long (environ une demi-seconde). Les clignements naturels, plus courts, sont ignorés.
Clic par immobilité : garder le curseur immobile une seconde clique. C'est le mode standard des logiciels d'accessibilité, avec un anneau de progression autour du curseur.
Clic droit : lever les sourcils.
Défilement : ouvrir la bouche, puis lever ou baisser la tête.
Pause et reprise sans les mains : fermer les yeux 2,5 secondes.
Recentrage : un bouton, ou automatique au démarrage.
Clavier visuel de Windows : un bouton, pour écrire avec la tête.
Sécurité : si quelqu'un touche la vraie souris, le contrôle par la tête s'efface aussitôt.
Panneau de contrôle dans le style de Posture Coach : vidéo, jauges des gestes, réglages de sensibilité.
