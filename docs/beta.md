# Tester l’alpha sur un autre Mac

La première question à trancher est simple. Une personne qui possède déjà une R1 peut-elle obtenir dans son ChatGPT les mêmes informations que dans Even, en suivant le guide seule ? Le dépôt et la première release sont privés, pour pouvoir ajuster ce parcours avant une diffusion plus large.

## Essai avec une personne invitée

1. **Avant l’installation** — Notez les versions de macOS et d’Even, la langue de l’interface et le modèle de Mac. Choisissez sur votre iPhone une nuit identifiable. Comparez sa date de réveil et sa durée avec Even sur le Mac de test.
2. **Installation vierge** — Téléchargez le DMG de la release et suivez le [guide Mac](installation.md). Notez les étapes auxquelles vous avez dû demander de l’aide, notamment les outils Apple et les autorisations. La personne qui porte la bague effectue elle-même les comparaisons.
3. **Première collecte et second passage** — Lancez une collecte, puis une deuxième sur le même export. Vérifiez que la durée ne double pas. Un utilisateur sans nuit enregistrée doit pouvoir lire un état compréhensible et commencer la collecte.
4. **Deux nuits portées** — Portez la bague deux nuits de suite, avec la collecte planifiée et le Mac disponible aux heures prévues. Comparez chaque nouvelle date avec l’iPhone. Notez l’heure de l’essai si un passage a échoué.
5. **Question dans ChatGPT web** — Sur le compte du testeur, configurez son propre tunnel. Ouvrez une nouvelle conversation, sélectionnez le connecteur et demandez les sept dernières dates de réveil, puis une carte et son ancienneté. Vérifiez les réponses sans joindre de fichier.
6. **Arrêt** — Essayez d’arrêter la planification et le tunnel séparément. Vérifiez l’état depuis le Mac. [Désinstallation et données](confidentialite.md)

Un retour utile précise l’étape, le résultat attendu, le résultat observé et les versions utilisées. Pour les valeurs personnelles, indiquez simplement « correspond », « manque » ou « diffère ».

## Avant la diffusion publique

- Valider ce parcours sur un deuxième compte Even et un deuxième Mac, puis documenter les versions et langues réellement testées.
- Finaliser la signature Developer ID et la notarisation Apple pour simplifier la première ouverture. Évaluer l’embarquement du runtime Python selon les difficultés rencontrées à l’installation.
- Tester la navigation et la sortie du guide sur de vraies G2 et avec la R1, préparer les visuels de sa fiche, puis décider d’une soumission à Even Hub. [Critères de soumission Even](https://hub.evenrealities.com/docs/ship/app-submission)
- Choisir la licence, les modalités de support et la visibilité avant de rendre le dépôt ou les téléchargements publics.
