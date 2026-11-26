# Even R1 Ring Guide for G2 Glasses

This optional companion puts five English instruction cards on Even G2 glasses. You can install the Mac exporter and query your ring without the glasses guide. [Install the Mac app](../docs/installation.md)

## Get the glasses guide

```codex-prompt
Get the optional Even R1 Ring Guide for G2 Glasses from https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/. Download its .ehpk file into my chosen project folder, or locate an existing copy there. Compare its SHA-256 with the same release’s published SHA256SUMS. Tell me the file name, location and result. Explain what the five instruction cards do and how to navigate them. Leave my Mac exporter, health data and Even Hub account alone.
```

- The [G2 guide package](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.4/Even-R1-Ring-Guide-for-G2-Glasses.ehpk) is version **0.1.2**. The `.ehpk` file is for Even G2 glasses. The separate `.dmg` installs the Mac exporter.
- The cards explain how to find a recorded night in Even, sync it to the Mac and ask about it in ChatGPT. They work offline after loading and request no health or network permissions.
- Tap or scroll down to advance. Scroll up to go back. Double-tap to open the system exit menu. On the phone, use **Previous** and **Next**.
- The alpha still needs physical G2 testing before a catalog submission. The next sections are for people who want to try the prototype.

## Preview the five cards on your Mac

```codex-prompt
Help me preview the Even R1 Ring Guide for G2 Glasses on this Mac. Follow the optional G2 source build at https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/build/. Use a clean copy of the tagged source, Node.js 22 and npm. In evenhub/, install locked dependencies, run the tests and pack the guide. Serve only evenhub/dist on a free loopback port. Open its phone interface and verify that Next and Previous move through the five cards. Give me the local preview URL and the command to stop it.
```

- [Build the optional G2 guide](../docs/build-from-source.md). With Node.js 22 and npm, `npm ci && npm test && npm run pack` inside `evenhub/` produces the package and `dist/`. The build uses the official CLI and Even Hub SDK 0.0.16.
- From `evenhub/`, run the command below. Open `http://127.0.0.1:8080/` in your Mac browser. Press **Control-C** to stop the server.

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

For contributors, `app.json` is the manifest and `src/guide.js` contains the cards. The built `dist/` directory includes the phone interface, glasses code and SDK license.

## Test on physical G2 glasses

```codex-prompt
Help me test Even R1 Ring Guide for G2 Glasses in Even Hub Prototype Mode on my own devices. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/. Build the optional guide if needed. Help me confirm the Mac and iPhone are on the same trusted Wi-Fi, the G2 is paired and the Even Hub accounts match. Serve only the built evenhub/dist folder on the Mac’s Wi-Fi address. Generate a QR code with the project’s Even Hub CLI. Guide me through scanning, checking readability, moving between cards and exiting. Stop the test server when I finish. Report which hardware steps I confirmed.
```

1. Pair the G2 with the Even app. Use the same Even Hub account on the phone and for prototype testing. Connect the Mac and iPhone to the same trusted Wi-Fi.
2. Find the Mac’s Wi-Fi address in **System Settings → Wi-Fi → Details → TCP/IP**. In `evenhub/`, replace `YOUR_MAC_IP` with that address and start the server.

```sh
python3 -m http.server 8080 --bind YOUR_MAC_IP --directory dist
```

3. Open a second Terminal in `evenhub/`. Use the same address to generate the QR code.

```sh
node node_modules/@evenrealities/evenhub-cli/main.js qr --url http://YOUR_MAC_IP:8080/
```

4. In the Even app, open **Even Hub → Profile → Prototype Mode** and scan the code. Check readability and gestures on the glasses. Stop the server with **Control-C** in the first Terminal. [Even’s developer tutorials](https://hub.evenrealities.com/docs/learn/videos)

The proposed catalog name is **Even R1 Guide for G2**, within Even Hub’s 20-character limit. The independent guide is in English. Physical verification and listing images are still pending. [Even Hub quick start](https://hub.evenrealities.com/docs/get-started/quickstart/first-app) · [Device APIs](https://hub.evenrealities.com/docs/build/device-apis) · [Submission process](https://hub.evenrealities.com/docs/ship/app-submission)
