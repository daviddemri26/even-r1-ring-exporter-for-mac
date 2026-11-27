# Connect your Mac to ChatGPT

The Mac app can collect readings on its own. Add this optional, read-only connection if you want to ask about those readings in your personal ChatGPT web account. Your Mac must be awake and online when you ask. [Install and test the Mac app](installation.md)

If you already import sleep with **Sleep Sync Companion**, you can also ask **ChatGPT Health** about those nights through Apple Health. This uses ChatGPT’s permission to read **Sleep** on your iPhone. The private connector described below queries the Mac’s sleep archive and its six health cards. [Ask about sleep in ChatGPT Health](ask-about-readings.md#which-ring-nights-can-chatgpt-health-see)

## Set up my private connection

```codex-prompt
Help me connect Even R1 Ring Exporter for Mac to my personal ChatGPT web account. Work on this Mac and follow https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/. First check that the exporter has completed a local export and check the existing tunnel status. If the local export is missing, follow https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/ first. It requires the official Even Realities iPhone app on this Mac, signed in with the same Even account as my physical iPhone. Reuse any working configuration. If setup is missing, check that my personal workspace supports custom MCP servers and that my OpenAI Platform organization supports secure tunnels. Help me create a dedicated tunnel, associate it with my workspace, and create a restricted project key with Tunnels Read and Use. Use the app’s connection assistant, which verifies the tunnel client. Let me sign in and enter the key myself at the hidden Terminal prompt. Never request the key in chat or read it back. Finish the private connector setup in my own workspace. Verify the tunnel has connected to OpenAI, then test the connector with a dated reading in my personal ChatGPT web chat, without an attachment. Tell me which steps succeeded and identify any step that still needs my action.
```

1. **Choose the account.** Sign in to your personal ChatGPT workspace and its OpenAI Platform organization. You need access to custom MCP servers and secure tunnels. [OpenAI tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
2. **Create the tunnel.** Associate it with your organization and personal ChatGPT workspace. Creating a tunnel requires **Tunnels Read + Manage**. Copy its `tunnel_` identifier. [OpenAI Platform tunnels](https://platform.openai.com/settings/organization/tunnels)
3. **Create the Mac’s key.** Choose a dedicated project key with **Restricted → Tunnels Read and Use**. [OpenAI Platform API keys](https://platform.openai.com/settings/organization/api-keys)
4. **Connect the Mac.** In the exporter, select **ChatGPT Connection → Connect Even R1 Ring to ChatGPT…**. The same assistant is available as **Connect Even R1 Ring to ChatGPT.command** inside the disk image. Enter the tunnel ID. Paste the complete key at the hidden Terminal prompt and press Return. The assistant stores it in your Mac’s Keychain.
5. **Add the connector.** In the personal ChatGPT plugin directory, select **+ → Add custom MCP server**. Name it **Even R1 Ring Data for ChatGPT**, choose **Tunnel**, and select your tunnel. Choose **No authentication** for the local server behind this private tunnel. Keep the connector in your own workspace. Select **Connect**, then **Try in chat**. [Open ChatGPT plugins](https://chatgpt.com/plugins)

## Check that ChatGPT can read an export

```codex-prompt
Verify Even R1 Ring Data for ChatGPT end to end. On this Mac, check the latest export status and the latest local wake date. Check that the tunnel has connected to OpenAI. With my Mac awake and online, open my private connector in my personal ChatGPT web workspace and use Try in chat. Ask for sleep duration on the latest recorded wake date, without attaching a file or including the answer in the question. Compare the tool response with the local result and tell me whether they agree. If no night exists yet, test a recorded health card instead. If you can only check one side, identify which side you verified.
```

- On the Mac, open **Mac Collection → Refresh**. Note the latest recorded wake date.
- In your personal ChatGPT web chat, ask “How much sleep did my Even R1 record on [wake date]?” Compare the answer with **Health** in Even on your iPhone.
- The connector supports sleep duration, sleep stages, the six latest health cards and changes the Mac has observed. [Questions to try](ask-about-readings.md)

## Repair a connection that stopped working

```codex-prompt
Diagnose my existing private Even R1 connection using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/. Check the Mac collection status and the tunnel status separately. Use the reported error to choose the next step. For HTTP 401, help me use Update Key and let me enter the complete key privately. For HTTP 403, check the organization, project, Tunnels Read and Use permissions, and personal workspace association with me. If the tunnel is healthy but the plugin shows older tool names, refresh or reconnect that plugin. Reuse the existing tunnel and preserve my archives. Retest from my personal ChatGPT web account without a file and report the result. Keep keys and raw logs out of chat.
```

- Select **ChatGPT Connection → Refresh** and check for confirmation of a connection to OpenAI. The app controls scheduled exports and the tunnel separately.
- **HTTP 401** means the key was declined. Under **Show Connection Options**, choose **Update Key…** and enter the complete key at the hidden prompt.
- **HTTP 403** calls for a check of the organization, project, key permissions and workspace association. [OpenAI troubleshooting](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels/#troubleshooting)
- To check both statuses in Terminal after setup, run these read-only commands.

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" status
/usr/bin/python3 -B "$runtime/tunnel.py" status
```
