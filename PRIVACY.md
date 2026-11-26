# Politique de confidentialité — Tête-à-Clic

*© 2026 MarcDev@ · Dernière mise à jour : novembre 2026*

Tête-à-Clic a été conçu pour **protéger ta vie privée par défaut** : tout est traité sur ton ordinateur, et l'application n'utilise pas internet.

## Ce qui est traité

| Donnée | Où | Combien de temps |
|---|---|---|
| Images de la webcam | Analysées en direct, en mémoire, sur ton ordinateur | **Jamais enregistrées, jamais envoyées** |
| Orientation de la tête, scores des gestes (clignement, sourcils, bouche) | En mémoire, le temps du calcul | Effacés immédiatement |
| Texte tapé avec le clavier Tête-à-Clic | Envoyé directement à la fenêtre où tu écris | **Jamais enregistré** par Tête-à-Clic |
| Réglages (sensibilité, gestes, son, voix) | `%LOCALAPPDATA%\TeteAClic\settings.json` | Jusqu'à ce que tu les supprimes |
| Journal technique (démarrage, erreurs) | `%LOCALAPPDATA%\TeteAClic\tete_a_clic.log` | Jusqu'à ce que tu le supprimes |

## Ce qui n'est jamais fait

- Aucune image, aucune vidéo, aucun son n'est enregistré ou envoyé.
- Aucune donnée n'est envoyée sur internet : ni statistique, ni publicité, ni pistage.
- Aucun compte n'est nécessaire.

## Aperçu vidéo

L'aperçu de la webcam dans la fenêtre passe par un petit serveur **local** (`127.0.0.1`), protégé par un jeton aléatoire. Il n'est pas accessible depuis un autre ordinateur.

## Tout effacer

Désinstalle Tête-à-Clic, puis supprime le dossier `%LOCALAPPDATA%\TeteAClic`.

## Contact

MarcDev@ — [marcdevfullstack@gmail.com](mailto:marcdevfullstack@gmail.com)
