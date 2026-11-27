# Set up your R1 ring with ChatGPT

On your Mac, open [ChatGPT for Mac](https://chatgpt.com/download), choose **Codex** and start a **local chat** in an empty folder. Keep the recommended model and default permissions. Copy the prompt below, paste it into Codex with **⌘V** and press **Return**.

```codex-prompt
Set up Even R1 Ring Exporter for Mac and connect it to my personal ChatGPT web account. Do the work on this Mac. Resume any working setup and preserve my archives. When I need to sign in, use my iPhone or approve a permission, give me one short instruction and continue after I finish.

1. Confirm Apple silicon, macOS 14 or later and Apple’s /usr/bin/python3 version 3.9 or later. If Python is missing, open Apple’s Command Line Tools installer. On the Mac, open https://apps.apple.com/us/app/even-realities/id6747017725 in the Mac App Store. If searching, select iPhone & iPad Apps if offered. Install or open Even Realities by Even Realities Ltd. (Designed for iPhone). Let me sign in with the same Even account as on my physical iPhone. Help me sync my ring on iPhone, review Health tracking and Cloud processing & backup, and confirm that a reading appears in Even on the Mac. If the store does not offer the app for this Mac, explain and stop.

2. Download the Mac disk image from {{DMG_URL}}. Verify its SHA-256 against the matching filename in {{CHECKSUMS_URL}} before opening it. Stop on a mismatch. Install the .app in Applications and open that copy. Keep macOS security protections enabled. In Mac Collection choose Set Up This Mac. Use Show Collection Options to find Accessibility Settings and Show Collector. Let me allow Even R1 Ring Collector for Mac under Accessibility. If macOS asks to let the collector read other apps’ data, explain that it reads Even’s export and wait for my decision. With the Mac unlocked, run Test an Export, then Refresh. Verify this attempt says “Export verified”. Enable Schedule Collection and confirm the time shown under “Next scheduled check”.

3. Check ChatGPT Connection for an existing working tunnel. If one is needed, confirm my personal ChatGPT workspace supports custom MCP servers and my OpenAI Platform organization supports secure tunnels. At https://platform.openai.com/settings/organization/tunnels create a dedicated tunnel linked to that workspace. Create a dedicated restricted project API key with Tunnels Read and Use. In ChatGPT Connection choose Connect Even R1 Ring to ChatGPT… and enter the tunnel ID. Let me enter the complete key privately at the assistant’s hidden Terminal prompt so it is stored in my Mac’s Keychain. Never ask for the key in chat or print it. Confirm the tunnel connects to OpenAI.

4. In my personal workspace at https://chatgpt.com/plugins, add a custom MCP server named Even R1 Ring Data for ChatGPT. Choose Tunnel, select my tunnel and use No authentication for the local server behind it. Keep the connector private. Choose Connect, then Try in chat. Ask “What are my latest ring readings?” without a file or any values in the question. Verify that the connector supplied the answer and compare one available result and its freshness with the local export or card. Keep raw archives on this Mac. Tell me whether the export, schedule and web query each worked. If anything is unavailable, identify the exact blocker.
```

## Install {#install}

You need your Even R1 ring, your iPhone and an Apple silicon Mac running macOS 14 or later. Codex helps install two apps on your Mac.

- **Even Realities** syncs your ring readings. In the [Mac App Store](https://apps.apple.com/us/app/even-realities/id6747017725), get the **Designed for iPhone** version. Sign in with the same Even account you use on your iPhone.
- **Even R1 Ring Exporter for Mac** collects those readings automatically. The [Mac download (.dmg)]({{DMG_URL}}) contains this app.

## Connect {#connect}

In the exporter, open **ChatGPT Connection → Connect Even R1 Ring to ChatGPT…**. Follow Codex through sign-in and permissions. It checks the first export, turns on automatic collection and tests a reply in your ChatGPT account.

## Ask {#ask}

In ChatGPT, choose **Even R1 Ring Data for ChatGPT** and ask “What are my latest ring readings?” Keep your Mac awake and online when you ask.

Your Mac checks for new readings automatically at 5:15 a.m., 8:15 a.m., 12:15 p.m., 6:15 p.m. and 11:15 p.m. local time. It retries every ten minutes for up to an hour while it waits for the Mac to be awake, unlocked and idle. To see the next check in your local time, open **Mac Collection** and select **Refresh**.

Need help? Give Codex the error message. For manual setup or troubleshooting, see the [technical documentation on GitHub](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/blob/main/README.md#technical-documentation).
