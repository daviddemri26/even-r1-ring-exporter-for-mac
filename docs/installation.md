# Installer R1 Bridge sur un Mac

## Avant de télécharger

- **Matériel** — La configuration du pilote comprend une bague Even R1, des lunettes Even G2 et un iPhone avec l’app **Even Realities**. Conservez l’appairage sur l’iPhone. Pour une nuit de sommeil, portez la bague pendant la nuit, puis vérifiez la date dans **Health** sur l’iPhone.
- **Mac** — Utilisez un Mac Apple Silicon (M1 ou ultérieur). L’app R1 Bridge cible macOS 14 ou ultérieur. La version d’Even disponible pour votre Mac doit également pouvoir s’y exécuter. Le poste de référence utilisait macOS 26.5.1 et Even 2.4.1. Apple présente Even comme une app conçue pour iPhone. [Fiche App Store](https://apps.apple.com/us/app/even-realities/id6747017725)
- **Python Apple** — L’alpha utilise `/usr/bin/python3` (3.9 ou ultérieur). Vérifiez avec `/usr/bin/python3 --version` dans Terminal. Si macOS propose les outils en ligne de commande Apple, terminez leur installation. On peut aussi lancer `xcode-select --install`.
- **Compte Even** — Connectez l’app sur le Mac au même compte que sur l’iPhone. Pour la synchronisation utilisée ici, activez **Health → réglages → Cloud processing & backup** si vous acceptez que vos mesures soient sauvegardées chez Even. Comparez la date d’un relevé sur les deux appareils. [Aide Even](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- **ChatGPT web, en option** — Il vous faudra un compte permettant l’ajout d’un serveur MCP personnalisé et une organisation OpenAI Platform avec l’accès aux tunnels. Vous pouvez commencer par vérifier la collecte locale. [Configuration ChatGPT](chatgpt.md)

## Installer l’alpha

1. Ouvrez la [release GitHub](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.2) avec le compte invité au dépôt privé. Téléchargez le **DMG arm64**, puis ouvrez-le.
2. Glissez **R1 Bridge.app** dans **Applications**. Éjectez le DMG et ouvrez l’app depuis Applications.
3. Ce build de test est signé localement. La distribution avec Developer ID et notarisation Apple reste une étape avant l’ouverture publique. Si Gatekeeper bloque l’ouverture, vérifiez la provenance et l’empreinte publiée. Vous pouvez également construire l’app depuis les sources. [Aide Apple sur l’ouverture des apps](https://support.apple.com/fr-fr/102445)

Pour mettre à jour depuis l’alpha 1, quittez l’ancienne app, remplacez-la dans Applications puis ouvrez la nouvelle. Cliquez sur **Préparer ce Mac**. Vérifiez l’accès du nouveau collecteur comme indiqué ci-dessous. Si vous aviez déjà activé la collecte automatique, cliquez de nouveau sur **Programmer la collecte** pour installer les nouveaux horaires de vérification.

## Faire le premier essai

1. Ouvrez Even sur le Mac. Dans **Health**, vérifiez qu’une mesure connue y est visible. Le chemin manuel de référence est **Health → réglages → Export Health data**. [Guide d’export Even](https://support.evenrealities.com/hc/en-us/articles/17995748835599-Export-Your-Health-Data)
2. Dans **R1 Bridge**, préparez le moteur local. La session doit être déverrouillée pendant l’essai. Le collecteur lance Even en arrière-plan si nécessaire. Even peut afficher brièvement une fenêtre pendant l’export.
3. Dans **Réglages Système → Confidentialité et sécurité → Accessibilité**, autorisez **R1 Bridge Collector**. Le collecteur vérifie cet accès silencieusement. Si le test signale un refus après une mise à jour alors que l’interrupteur est bleu, retirez l’ancienne entrée puis ajoutez la nouvelle app avec **+**, puis **⌘⇧G** et le chemin `~/Library/Application Support/R1 Bridge/Export.workflow/Contents/Resources/R1 Bridge Collector.app`. Si macOS demande l’accès aux données d’une autre app pendant le premier essai, cette permission permet de lire le ZIP qu’Even vient de créer dans son cache.
4. Relancez l’essai après toute demande de permission. Vérifiez dans l’état local la dernière tentative et la dernière date de réveil enregistrée. Un export réussi peut contenir exactement les mêmes nuits que le précédent.
5. Cliquez sur **Programmer la collecte**. À partir de 8 h 15, 12 h 15 et 18 h 15, R1 Bridge vérifie toutes les dix minutes pendant une heure si le Mac est disponible. L’export démarre après deux minutes sans activité du clavier ou de la souris, dans une session déverrouillée. Si vous utilisez le Mac pendant toute l’heure, la collecte attend le créneau suivant. **Tester un export** permet de la lancer vous-même. L’heure de collecte indique quand le Mac a lu Even. La date de réveil provient des sessions de l’export.

## Si une fenêtre demande où enregistrer un ZIP

Even peut proposer d’enregistrer le fichier `Even_health_data_…zip` dans Documents pendant l’export. R1 Bridge récupère sa propre copie dans le cache d’Even. Si cette fenêtre reste ouverte, choisissez **Annuler** dans la fenêtre portant ce nom de fichier. L’état de la collecte dans R1 Bridge permet de vérifier si le ZIP a été reçu. Les demandes d’autorisation de macOS se traitent séparément lors du premier essai.

## Si une nuit manque

- **Absente aussi sur l’iPhone** — Vérifiez le port de la bague, le suivi santé et sa synchronisation avec Even. R1 Bridge reçoit uniquement les sessions fournies par Even. [Aide Even sur les mesures manquantes](https://support.evenrealities.com/hc/en-us/articles/17144131645327-Detected-Health-Data-Is-Missing)
- **Visible sur l’iPhone uniquement** — Vérifiez le compte et la sauvegarde cloud sur les deux appareils, puis ouvrez la vue Health sur le Mac.
- **Visible sur le Mac, export en échec** — Vérifiez la session déverrouillée, le collecteur autorisé dans Accessibilité et l’absence de fenêtre modale dans Even. Une mise à jour d’Even ou une localisation différente peut modifier son interface. Conservez le message technique de l’app pour le signalement.
- **Export réussi, ancienneté inchangée** — Les pas et calories peuvent être des cumuls partiels et une température ancienne peut rester affichée. Un nouveau passage du collecteur ne constitue pas une nouvelle mesure.
