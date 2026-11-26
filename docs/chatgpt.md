# Relier son Mac à son propre ChatGPT

Terminez d’abord un [essai local](installation.md). Chaque utilisateur crée son tunnel dans son organisation OpenAI et le relie à son espace ChatGPT personnel. Sur un espace administré, il faut aussi pouvoir y ajouter des serveurs MCP personnalisés. [Documentation OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

## Première connexion

1. Dans les [tunnels OpenAI Platform](https://platform.openai.com/settings/organization/tunnels), vérifiez l’organisation active, créez un tunnel et associez votre organisation et votre espace ChatGPT. Conservez son identifiant `tunnel_…`. La création requiert **Tunnels Read + Manage**.
2. Créez une [clé de projet](https://platform.openai.com/settings/organization/api-keys) dédiée à ce Mac. Choisissez **Restricted → Tunnels → Use**, puis vérifiez que **Read** et **Use** sont sélectionnés. La clé sera conservée dans le Trousseau du Mac.
3. Ouvrez **Connecter ChatGPT.command** depuis le DMG ou l’assistant de l’app. Donnez l’identifiant du tunnel. L’assistant télécharge le client OpenAI pour Mac arm64 depuis sa release officielle et en vérifie le SHA-256 avant l’installation. [Client OpenAI utilisé par l’alpha](https://github.com/openai/tunnel-client/releases/tag/v0.0.21)
4. À l’invite **Clé OpenAI**, collez la clé entière dans Terminal et validez. La saisie est masquée. L’assistant vérifie la clé pour ce tunnel, la conserve dans le Trousseau puis démarre le service. Attendez la confirmation d’un **échange avec OpenAI**.
5. Dans le [répertoire de plugins ChatGPT](https://chatgpt.com/plugins), cliquez sur **+ → Add custom MCP server**. Donnez-lui un nom, par exemple **Ma bague R1**, puis choisissez **Tunnel** et votre tunnel. Pour le serveur local fourni, sélectionnez **No authentication** au niveau MCP. Le transport est authentifié par la clé du tunnel et son association à votre espace. Limitez l’installation à votre espace personnel.
6. Vérifiez l’avertissement, créez le plugin, cliquez sur **Connect**, puis sur **Try in chat**. Demandez par exemple « Combien ai-je dormi chaque nuit sur les sept dernières dates de réveil ? » ou « Quelles sont mes dernières mesures et de quand datent-elles ? »

## Ce que peut lire le connecteur

- `durees_sommeil` renvoie les minutes de sommeil par date locale de réveil. Les siestes d’une même date peuvent faire partie du total.
- `phases_sommeil` renvoie les durées enregistrées par stade. Une date vide signifie qu’aucune session n’a été fournie. Une valeur `null` signale une ambiguïté.
- `dernier_releve_even` lit les six cartes selon la sélection demandée. Une date de lot est ajoutée quand les cartes concordent avec l’export.
- `evolution_cartes_even` présente les changements de valeur observés depuis l’installation. Une valeur inchangée ne donne pas lieu à un nouvel échantillon. Additionner des cumuls successifs de pas ou de calories compterait certaines activités plusieurs fois.

Le Mac doit être en ligne pour que ChatGPT atteigne le connecteur. La planification de collecte et le service de tunnel sont indépendants. Vous pouvez garder les archives locales et arrêter uniquement l’accès web.

## Diagnostic local

Depuis Terminal, après préparation du moteur dans l’app :

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" etat
/usr/bin/python3 -B "$runtime/tunnel_r1.py" etat
```

Un **401** signifie qu’OpenAI a refusé la clé. Utilisez l’invite masquée de l’assistant pour enregistrer une clé valide et complète. Un **403** invite à vérifier le compte, le projet, les droits Tunnels et les associations du tunnel. Si la création du plugin échoue, vérifiez d’abord le premier échange du client avec OpenAI. [Dépannage OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels/#troubleshooting)
