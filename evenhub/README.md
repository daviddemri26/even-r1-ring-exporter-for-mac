# R1 Bridge Guide pour Even G2

Cinq fiches courtes pour vérifier ce qui se passe entre le port de la bague, l’export sur Mac et la réponse dans ChatGPT. Le guide fonctionne hors ligne après chargement, utilise du texte embarqué et ne demande aucune permission de santé ou de réseau. L’app Mac s’installe séparément. [Parcours d’installation Mac](../docs/installation.md)

## Dans les lunettes

- Un appui ou un défilement vers le bas avance d’une fiche. Un défilement vers le haut revient à la précédente.
- Un double appui demande la sortie système. Sur le téléphone, les boutons **Précédent** et **Suivant** permettent aussi de parcourir le guide.
- Le paquet `r1-bridge-guide.ehpk` est disponible dans la [release privée](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.1). Le test de lisibilité, de gestes et de sortie sur de vraies G2 fait partie de la préparation à une soumission au catalogue.

## Construire le paquet

Depuis le dossier `evenhub/` avec Node.js 22 et npm, exécutez les commandes suivantes. Le CLI officiel empaquette le résultat pour le SDK `0.0.16`.

```sh
npm ci
npm test
npm run pack
```

`dist/` contient l’interface web embarquée et la licence du SDK. `r1-bridge-guide.ehpk` est le paquet à tester. Le manifeste et les textes sont modifiables dans `app.json` et `src/guide.js`.

## Brouillon de fiche pour Even Hub

**R1 Bridge Guide** aide les porteurs d’une R1 à retrouver une nuit depuis leurs lunettes. Parcourez cinq fiches pour vérifier la date dans Even, lancer la collecte sur un Mac et choisir une question à poser à votre connecteur ChatGPT. Disponible en français. Projet indépendant développé pour les G2.

Le SDK public décrit les gestes utilisés par ce guide. Le parcours santé du projet utilise l’export officiel de l’app Even sur le Mac. [API des appareils](https://hub.evenrealities.com/docs/build/device-apis) · [Démarrer avec Even Hub](https://hub.evenrealities.com/docs/get-started/quickstart/first-app) · [Soumettre une app](https://hub.evenrealities.com/docs/ship/app-submission)
