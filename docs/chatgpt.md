# Set up Even R1 Ring Data for ChatGPT

This read-only connector lets your ChatGPT account ask your Mac about ring readings. First complete a [local export](installation.md).

## What you need

- A ChatGPT workspace that supports custom MCP servers. In a managed workspace, check that you can add one.
- An OpenAI Platform organization with access to secure tunnels.
- Your Mac awake and online when you ask ChatGPT a question. [OpenAI’s tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

## Create your tunnel and key

1. Open [OpenAI Platform tunnels](https://platform.openai.com/settings/organization/tunnels) and select your organization.
2. Create a tunnel and associate it with your organization and personal ChatGPT workspace. Creating it requires **Tunnels Read + Manage**.
3. Copy the identifier beginning with `tunnel_`.
4. Create a [project API key](https://platform.openai.com/settings/organization/api-keys) dedicated to this Mac. Select **Restricted** and grant **Tunnels Read and Use**.

## Connect your Mac

1. In the Mac app, choose **ChatGPT Connection → Connect Even R1 Ring to ChatGPT…**. You can also open **Connect Even R1 Ring to ChatGPT.command** from the DMG.
2. Enter your tunnel identifier. The assistant downloads the official Apple silicon tunnel client and verifies its SHA-256 checksum.
3. Paste the complete API key at the hidden Terminal prompt and press Return. It will be stored in your Mac’s Keychain.
4. Wait for confirmation that the tunnel has connected to OpenAI.

## Add the connector in ChatGPT

1. In the [ChatGPT plugin directory](https://chatgpt.com/plugins), select **+ → Add custom MCP server**.
2. Name it **Even R1 Ring Data for ChatGPT**. Choose **Tunnel** and select your tunnel.
3. Choose **No authentication** for the local MCP server. The tunnel key and workspace association authenticate the connection. Limit access to your own workspace.
4. Create the plugin, click **Connect**, then **Try in chat**.
5. Ask “How much did I sleep each night over the last seven days?” Compare a wake-up date with Even on your iPhone.

If an older alpha shows different tool names, refresh or reconnect the plugin. Your API key stays in Keychain.

## What you can ask

- **Sleep duration** (`sleep_durations`). Get total sleep minutes for each local wake-up date, including recorded naps.
- **Sleep stages** (`sleep_stages`). Get awake, light, deep and REM minutes. A missing date means Even supplied no session. A `null` value indicates ambiguous data.
- **Latest measurements** (`latest_readings`). Read Even’s six health cards and their displayed age. A matching export can also establish the batch date.
- **Changes over time** (`reading_history`). See when the Mac observed a card’s value or unit change. Steps and active calories may be running totals.

## Check the connection

- Run the commands below after setting up the Mac. Scheduled collection and the tunnel can be stopped independently.
- **HTTP 401** means OpenAI declined the key. Enter the complete key again at the assistant’s hidden prompt.
- **HTTP 403** means you should check the organization, project, tunnel permissions and workspace association. [OpenAI troubleshooting](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels/#troubleshooting)

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" status
/usr/bin/python3 -B "$runtime/tunnel.py" status
```
