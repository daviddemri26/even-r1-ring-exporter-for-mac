# Where your ring readings go

Your Mac can collect readings on its own. Connecting your personal ChatGPT account is optional.

<a name="r1-ring-guide-for-g2-privacy-policy"></a>

## G2 app privacy policy

The G2 app (version 0.2.0) shows where to open the Mac setup page. It requests no device permissions and does not read, store or send ring measurements. It has no account, analytics or backend.

The setup page is hosted on GitHub Pages. Typing **is.gd/r1mac** on your Mac takes you there through the is.gd redirect service. The address is the same for everyone and contains no personal information. If you install the separate Mac exporter and connect your own ChatGPT account, those tools handle readings as described below.

For privacy questions, contact the maintainer through [project issues](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/issues). Issues are public. Keep personal details and ring readings private.

## Check who can see your readings

```codex-prompt
Explain where my readings go when I use Even R1 Ring Exporter for Mac. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/privacy/ as the reference. Check whether the public Mac app and its collection and tunnel services are installed or running on this Mac. Inspect service status only. Leave settings alone and keep archives, readings, keys and tunnel identifiers out of the chat. Tell me which settings I can verify myself in Even and ChatGPT.
```

- **Even** uses its cloud backup to sync readings from the iPhone to the Mac in the tested setup. You control that setting in Even. [Even’s health data backup guide](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- **Your Mac** uses Even’s export controls and stores health ZIPs, collection status and observed cards in `~/Library/Application Support/R1 Bridge/`. A backup that includes this folder also contains your exports.
- **Your ChatGPT account** receives results when you use the private connector. Anyone you authorize to use it can query its four read-only tools. Keep it in your own workspace. Results become part of that conversation. The dedicated API key is stored in your Mac’s Keychain.
- **The website and G2 glasses guide** provide setup instructions. Both the earlier five-card guide (0.1.2) and the single-screen guide (0.2.0) work without access to your readings.

## Pause collection or ChatGPT access

```codex-prompt
Help me pause Even R1 Ring Exporter for Mac. Ask which part I want to stop: scheduled collection, the private ChatGPT tunnel, or both. Use the installed public app or its documented stop command for only what I selected. Keep the archives, API key and other services intact. Verify each selected service is stopped and tell me how to restart it from the app. Report only service status.
```

- In **Mac Collection**, open **Show Collection Options** and choose **Stop Schedule** to pause automatic exports.
- In **ChatGPT Connection**, open **Show Connection Options** and choose **Stop Tunnel** to pause remote queries. Your saved archives stay on the Mac.
- From Terminal, run the command for the service you want to stop.

```sh
/usr/bin/python3 -B "$HOME/Library/Application Support/R1 Bridge/r1.py" stop
```

```sh
/usr/bin/python3 -B "$HOME/Library/Application Support/R1 Bridge/tunnel.py" stop
```

## Remove the app or revoke access

```codex-prompt
Help me remove Even R1 Ring Exporter for Mac using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/privacy/. First explain which actions affect the app, collection, its ChatGPT connector and my saved exports. Ask what I want to keep. Stop only the relevant services. Get my confirmation before removing an app, credential, tunnel or archive. Guide me through any account or macOS actions I must take myself. Never display keys or health data. Summarize what was removed and what remains.
```

1. Stop the schedule and tunnel you used. Quit **Even R1 Ring Exporter for Mac** and move it to the Trash.
2. In **System Settings → Privacy & Security → Accessibility**, remove **Even R1 Ring Collector for Mac**.
3. To revoke remote access, disconnect **Even R1 Ring Data for ChatGPT** in ChatGPT. Revoke the dedicated key and remove the tunnel association in your OpenAI Platform account. Its Keychain item is named **R1 Bridge - OpenAI Tunnel**.
4. Keep any exports you want before deleting the `R1 Bridge` folder. Mac backups, Even cloud data and ChatGPT conversations have their own deletion controls.
