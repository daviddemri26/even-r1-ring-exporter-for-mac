# Connect your Mac to ChatGPT

Start with a successful [local export](installation.md). Create a tunnel in your own OpenAI Platform organization and connect it to your personal ChatGPT workspace. In a managed workspace, you also need permission to add a custom MCP server. [OpenAI’s secure tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

## First connection

1. Open [OpenAI Platform tunnels](https://platform.openai.com/settings/organization/tunnels). Check the active organization, create a tunnel and associate it with that organization and your ChatGPT workspace. Copy the identifier beginning with `tunnel_`. Creating a tunnel requires **Tunnels Read + Manage**.
2. Create a [project API key](https://platform.openai.com/settings/organization/api-keys) dedicated to this Mac. Select **Restricted** and grant **Read** and **Use** under **Tunnels**.
3. In R1 Bridge, select **ChatGPT Connection → Connect ChatGPT…**. You can also open **Connect ChatGPT.command** from the DMG. Enter your tunnel identifier. The assistant downloads the official OpenAI client for Apple silicon and checks its SHA-256 digest. [Tunnel client used in this release](https://github.com/openai/tunnel-client/releases/tag/v0.0.21)
4. Paste the entire API key at the hidden Terminal prompt and press Return. The assistant checks that the key can reach your tunnel, saves it in your Mac’s Keychain and starts the service. Wait for confirmation that it has connected to OpenAI.
5. In the [ChatGPT plugin directory](https://chatgpt.com/plugins), select **+ → Add custom MCP server**. Give it a name such as **My R1 Ring**, choose **Tunnel** and select your tunnel. For this local server, select **No authentication** at the MCP level. The tunnel key and workspace association authenticate the connection. Limit access to your own workspace.
6. Review the prompt, create the plugin, select **Connect**, then **Try in chat**. Ask “How much did I sleep each night over the last seven days?” or “What are my latest readings, and how old are they?”

After upgrading from an earlier alpha, refresh or reconnect the plugin to discover its English tool names. The API key stays in Keychain.

## What the connector can read

- `sleep_durations` returns sleep minutes by local wake-up date. It aggregates distinct sessions, including naps, for each date requested.
- `sleep_stages` returns awake, light, deep and REM minutes during sleep sessions. A missing date means Even supplied no session. A `null` value marks data that could not be reconciled.
- `latest_readings` returns the selected Even cards with their displayed age. Where card values agree with the export, the result also includes the matching batch date.
- `reading_history` returns changes in card values that the Mac has observed since collection began. The observation time records when the Mac saw a value. Adding successive snapshots of steps or active calories can count the same activity more than once.

Keep the Mac awake and online when you ask a question. Scheduled collection and the tunnel are separate services. You can stop remote access and continue collecting locally.

## Check the connection

After setting up the Mac, run the following commands in Terminal.

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" status
/usr/bin/python3 -B "$runtime/tunnel.py" status
```

An **HTTP 401** means OpenAI declined the key. Re-enter the complete key through the setup assistant’s hidden prompt. For an **HTTP 403**, check the organization, project, tunnel permissions and workspace association. If plugin creation fails, check whether the tunnel client has connected to OpenAI. [OpenAI tunnel troubleshooting](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels/#troubleshooting)
