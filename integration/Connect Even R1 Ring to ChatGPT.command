#!/bin/bash
set -euo pipefail
umask 077

runtime="$HOME/Library/Application Support/R1 Bridge/tunnel.py"
if [[ ! -f "$runtime" ]]; then
  echo 'Open Even R1 Ring Exporter for Mac and choose Set Up This Mac first.'
  echo 'https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/'
  exit 1
fi
if [[ "$(/usr/bin/uname -m)" != arm64 ]]; then
  echo 'This version of Even R1 Ring Exporter for Mac requires a Mac with Apple silicon.'
  exit 1
fi

cat <<'GUIDE'
Connect Even R1 Ring to ChatGPT

ChatGPT receives the readings you ask for. Your archives stay on your Mac.
Setup guide: https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/#connect

1. Open https://platform.openai.com/settings/organization/tunnels and create a
   tunnel associated with your organization and personal ChatGPT workspace.
2. Open https://platform.openai.com/settings/organization/api-keys and create a
   restricted project key with Tunnels Read and Use permissions.
3. Enter the tunnel ID below, then paste the key at the hidden prompt.
   To cancel, leave the ID blank and press Return.
GUIDE

read -r -p 'Tunnel ID (tunnel_…): ' tunnel_id
[[ -n "$tunnel_id" ]] || exit 0
if [[ ! "$tunnel_id" =~ ^tunnel_[a-zA-Z0-9_-]{1,128}$ ]]; then
  echo 'Invalid tunnel ID. Copy the full value beginning with tunnel_.'
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
  echo 'The download checksum does not match this release. Installation stopped.'
  exit 1
fi
/usr/bin/unzip -p "$archive" tunnel-client > "$staging/tunnel-client"
/bin/chmod 700 "$staging/tunnel-client"
/usr/bin/python3 -B "$runtime" prepare "$tunnel_id" --client "$staging/tunnel-client"
/usr/bin/python3 -B "$runtime" store-key

cat <<'NEXT'
Open https://chatgpt.com/plugins and choose + → Add custom MCP server.
Select Tunnel, your personal tunnel, and No authentication for the local
read-only server. Create the plugin, select Connect, then Try in chat.
Ask “What are my latest ring readings?”
NEXT
