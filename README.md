# R1 Bridge

R1 Bridge est une application Mac indépendante pour les personnes qui portent une bague Even R1 et veulent retrouver leurs mesures dans ChatGPT. Le Mac déclenche l’export officiel d’Even, conserve les archives et répond aux questions via un connecteur privé en lecture seule.

**Alpha privée pour Mac Apple Silicon.** [Télécharger la version Mac](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.2) · [Installer et faire un premier essai](docs/installation.md) · [Connecter son propre ChatGPT](docs/chatgpt.md).

## Ce que vous pouvez demander

- « Combien ai-je dormi chaque nuit sur les sept dernières dates de réveil ? » Les sessions distinctes, siestes comprises, sont regroupées par date locale de réveil. Une date absente indique une absence de relevé.
- « Quelle durée Even a-t-il enregistrée en sommeil léger, profond et paradoxal ? » Le connecteur peut aussi renvoyer la durée d’éveil et signale les données ambiguës.
- « De quand datent mes dernières mesures ? » Le Mac relève les cartes de pas, calories actives, fréquence cardiaque, VFC, SpO₂ et variation de température cutanée. L’ancienneté affichée par Even accompagne chaque valeur.

## Comment les données arrivent

1. La R1 et les G2 restent appairées à l’iPhone. Even synchronise les données entre appareils du même compte lorsque la sauvegarde cloud est activée.
2. R1 Bridge utilise le bouton d’export d’Even sur le Mac. Le collecteur enregistre le ZIP, vérifie son contenu et dédoublonne les exports répétés.
3. Si vous activez la planification, R1 Bridge cherche un moment de pause à partir de **8 h 15, 12 h 15 et 18 h 15**, en heure locale. Il reporte l’export si vous utilisez le Mac ou si la session est verrouillée. Vous pouvez aussi choisir **Tester un export** quand vous voulez lancer la collecte vous-même.
4. Pour ChatGPT web, votre Mac se connecte au tunnel de votre propre compte OpenAI. Les questions interrogent l’archive locale disponible. Le tunnel doit être connecté au moment de la question.

Le prototype personnel a effectué une collecte programmée et répondu dans ChatGPT web pour le sommeil et les six cartes. La distribution alpha permet de reproduire ce parcours sur un autre Mac. La compatibilité chez un deuxième utilisateur et la remontée de deux nuits consécutives restent à valider. Le support Apple Santé nécessiterait un parcours iPhone avec HealthKit.

## Dans ce dépôt

- [Installation, matériel, permissions et dépannage](docs/installation.md)
- [Connexion à ChatGPT et commandes utiles](docs/chatgpt.md)
- [Données, accès et désinstallation](docs/confidentialite.md)
- [Guide facultatif pour les lunettes G2](evenhub/README.md)
- [Validation de l’alpha et prochaines étapes](docs/beta.md)
- Application et collecteur dans `macos/`, assistant de connexion dans `integration/`, site statique dans `site/dist/`.

## Construire depuis les sources

Sur un Mac Apple Silicon équipé des outils de développement Apple, lancez `./scripts/build-macos.sh` depuis le dépôt. Le DMG produit se trouve dans `dist/`. Les sources du guide G2 ont leur propre procédure de construction dans [evenhub/](evenhub/README.md). Le site peut être servi avec `python3 -m http.server --bind 127.0.0.1 --directory site/dist 8080`.

R1 Bridge est un projet indépendant. Les marques Even Realities, OpenAI, ChatGPT et Apple appartiennent à leurs titulaires respectifs.
