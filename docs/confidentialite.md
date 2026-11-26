# Où vont mes données ?

R1 Bridge est un outil indépendant. Chaque personne prépare son propre Mac et choisit si elle souhaite relier ses mesures à son compte ChatGPT.

- **Dans Even** — Le parcours testé utilise la sauvegarde cloud du compte Even pour retrouver les mesures de l’iPhone dans Even sur le Mac. Le réglage se trouve dans l’app Even. [Sauvegarde des données de santé chez Even](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- **Sur le Mac** — Le collecteur accède à l’interface Even, récupère le ZIP créé par la fonction officielle d’export et conserve les archives, l’état des essais et les cartes observées dans `~/Library/Application Support/R1 Bridge/`. Les ZIP contiennent des données personnelles. Tenez-en compte si vous sauvegardez ce dossier.
- **Dans ChatGPT** — Si vous activez le tunnel, les personnes autorisées à appeler le connecteur peuvent obtenir les résultats de ses quatre outils, par exemple les durées des nuits demandées. Utilisez votre espace personnel. Les résultats retournés entrent dans la conversation. La clé dédiée est enregistrée dans le Trousseau du Mac.
- **Sur le site et dans les lunettes** — Le site de présentation explique le projet. Le guide G2 embarque cinq fiches de texte. Leur consultation ne demande aucune mesure personnelle.

## Arrêter ou désinstaller

1. Depuis R1 Bridge, arrêtez la planification. Si vous avez activé le tunnel, arrêtez aussi son service depuis l’onglet ChatGPT. Les commandes ci-dessous permettent également d’arrêter les deux services depuis Terminal.
2. Pour retirer l’accès web, déconnectez le plugin dans ChatGPT puis révoquez la clé dédiée et retirez l’association du tunnel sur OpenAI Platform. L’élément du Trousseau s’appelle **R1 Bridge - OpenAI Tunnel**.
3. Pour désinstaller, quittez R1 Bridge, placez l’app dans la Corbeille et retirez **R1 Bridge Collector** des permissions d’accessibilité dans Réglages Système. Vous pouvez conserver vos archives ou en faire une copie avant de supprimer vous-même le dossier `R1 Bridge` dans la bibliothèque de votre compte. Les copies déjà sauvegardées, les données chez Even et les conversations ChatGPT se gèrent séparément.

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" arreter
/usr/bin/python3 -B "$runtime/tunnel_r1.py" arreter
```

Pour signaler un problème, communiquez les versions de R1 Bridge, d’Even et de macOS, la langue de l’interface, l’étape et le message d’erreur expurgé. Gardez vos ZIP, clés, identifiants de tunnel et captures de mesures dans votre espace privé.
