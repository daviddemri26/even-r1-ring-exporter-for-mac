#!/bin/bash
set -euo pipefail
umask 077

runtime="$HOME/Library/Application Support/R1 Bridge/tunnel_r1.py"
if [[ ! -f "$runtime" ]]; then
  echo 'Ouvrez d’abord R1 Bridge et préparez la collecte sur ce Mac.'
  exit 1
fi
if [[ "$(/usr/bin/uname -m)" != arm64 ]]; then
  echo 'Cette version de R1 Bridge cible les Mac Apple Silicon.'
  exit 1
fi

cat <<'GUIDE'
Connecter R1 Bridge à votre ChatGPT personnel

Votre Mac enverra à OpenAI les résultats demandés par votre connecteur privé.
Les archives ZIP sont conservées sur ce Mac.

1. Dans https://platform.openai.com/settings/organization/tunnels, créez un
   tunnel associé à votre organisation et à votre espace ChatGPT personnel.
2. Dans https://platform.openai.com/settings/organization/api-keys, créez une
   clé restreinte au projet voulu, avec les droits Tunnels Read et Use.
3. Indiquez ci-dessous l’identifiant du tunnel. L’assistant téléchargera le
   client officiel OpenAI (v0.0.21) et vérifiera son empreinte. Une seconde
   invite masquée vous demandera la clé. Entrée sur un identifiant vide quitte.
GUIDE

read -r -p 'Identifiant du tunnel (tunnel_…) : ' tunnel_id
[[ -n "$tunnel_id" ]] || exit 0
if [[ ! "$tunnel_id" =~ ^tunnel_[a-zA-Z0-9_-]{1,128}$ ]]; then
  echo 'Identifiant invalide. Recopiez la valeur commençant par tunnel_.'
  exit 1
fi

staging=$(/usr/bin/mktemp -d)
trap '/bin/rm -rf "$staging"' EXIT
archive="$staging/tunnel.zip"
/usr/bin/curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  'https://github.com/openai/tunnel-client/releases/download/v0.0.21/tunnel-client-v0.0.21-darwin-arm64.zip' -o "$archive"
expected='353a535d2513f599f9fe7897606e89b3248611453b30203ebddfb6e62fd4f58b'
digest=$(/usr/bin/shasum -a 256 < "$archive")
if [[ "${digest%% *}" != "$expected" ]]; then
  echo 'L’empreinte du téléchargement ne correspond pas à la version attendue. Installation interrompue.'
  exit 1
fi
/usr/bin/unzip -p "$archive" tunnel-client > "$staging/tunnel-client"
/bin/chmod 700 "$staging/tunnel-client"
/usr/bin/python3 -B "$runtime" preparer "$tunnel_id" --client "$staging/tunnel-client"
/usr/bin/python3 -B "$runtime" enregistrer-trousseau

cat <<'NEXT'
Dans https://chatgpt.com/plugins, ouvrez + → Add custom MCP server.
Choisissez Tunnel, votre tunnel personnel et No authentication pour le serveur
local en lecture seule. Créez le plugin et sélectionnez Connect, puis Try in chat.
Essayez « Combien ai-je dormi chaque nuit ces sept derniers jours ? »
NEXT
