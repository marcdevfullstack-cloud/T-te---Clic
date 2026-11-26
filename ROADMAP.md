# Tête-à-Clic : feuille de route

*MarcDev@ · mise à jour le 13/11/2026 (v1.1.0)*

## Version téléphone

**Android : oui, avec une application native** (Kotlin, pas Python). Android permet à une application d'accessibilité de piloter tout le téléphone :

- **AccessibilityService** : toucher, glisser, faire défiler n'importe où, et les boutons Retour, Accueil et Applications récentes. C'est l'usage prévu par Google pour les personnes handicapées, et donc accepté sur le Play Store avec une justification.
- **MediaPipe Face Landmarker pour Android** : le même modèle que sur PC, avec les mêmes gestes.
- **Pointeur flottant** au-dessus des autres applications, avec l'anneau d'immobilité.
- **Reprise de la logique déjà testée** : filtre One Euro, gestes, clic par immobilité, disposition du clavier.
- Outils déjà présents sur ce PC : Android Studio, SDK, JDK 17. Il faudra un téléphone Android en mode développeur pour tester.

**iPhone : non.** Apple interdit aux applications de contrôler le reste du téléphone. Apple propose en revanche lui-même un suivi de la tête et des yeux dans les réglages d'accessibilité.

**Concurrence sur Android** : Google « Contacteurs caméra » (gestes du visage, sans vrai pointeur libre) et quelques souris faciales open source. Nos différences : pointeur fluide, clic à l'endroit visé, clavier français à grandes touches, voix, interface soignée.

## Améliorations proposées

### Pour écrire plus vite
1. **Prédiction de mots** au-dessus du clavier (3 suggestions qui apprennent le vocabulaire de la personne) : 2 à 3 fois moins de touches.
2. **Phrases rapides** personnalisables : « J'ai soif », « Appelle mon fils », etc.
3. **Dictée vocale** pour ceux qui peuvent parler (reconnaissance locale).

### Pour pointer plus précisément
4. **Loupe de précision** : avant de cliquer une petite cible, une loupe agrandit la zone.
5. **Barre d'actions flottante** : double-clic, glisser-déposer, copier, coller, retour, choisis par immobilité.
6. **Recentrage guidé en 5 points**, avec un réglage automatique des seuils des gestes selon le visage de la personne.

### Pour la vie quotidienne et la sécurité
7. **Bouton d'appel à l'aide** : un geste déclenche une alarme sonore et un message à l'aidant.
8. **Profils** (plusieurs utilisateurs) et **démarrage automatique** avec Windows.
9. **Mode lecture** : défilement automatique doux, page suivante par un geste.

### Commun à nos applications (Tête-à-Clic, Posture Coach)
10. **Installateur** et **mise à jour automatique**.
11. **Version anglaise** : un marché bien plus large.
12. **Site vitrine** avec démo vidéo et **licences** (plan déjà prêt pour Posture Coach).
