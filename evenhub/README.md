# Even R1 Ring Guide for G2 Glasses

**Connect your R1 ring data to ChatGPT.** Set it up once on your Mac. Then ask about your ring’s sensor readings right in the chat. The G2 companion displays this message and opens the setup guide from your phone. [Set up on your Mac](../docs/installation.md)

## Get the glasses guide

```codex-prompt
Get the optional Even R1 Ring Guide for G2 Glasses from https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/. Download its .ehpk file into my chosen project folder, or locate an existing copy there. Compare its SHA-256 with the same release’s published SHA256SUMS. Tell me the file name, location and result. Tell me which version I have. Leave my Mac exporter, health data and Even Hub account alone.
```

- **R1 Ring Guide for G2** is the one-screen **0.2.0 prototype**. On your phone, choose **Set up on Mac** to open the installation guide.
- The [public alpha download](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.4/Even-R1-Ring-Guide-for-G2-Glasses.ehpk) contains the earlier **0.1.2** guide. The `.ehpk` file is for the glasses. The `.dmg` installs the Mac exporter.

## Preview the companion on your Mac

```codex-prompt
Help me preview the Even R1 Ring Guide for G2 Glasses on this Mac. Follow the optional G2 source build at https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/build/. Use the project source in my folder and report the version in evenhub/app.json. Use Node.js 22 and npm. In evenhub/, install locked dependencies, run the tests and pack the guide. Serve only evenhub/dist on a free loopback port. Open its phone interface and verify the screen matches that version. In 0.2.0, check the Mac setup link. Give me the local preview URL and the command to stop it.
```

- With Node.js 22 and npm, run `npm ci && npm test && npm run pack` inside `evenhub/`. In the 0.2.0 source this produces `Even-R1-Ring-Guide-for-G2-Glasses-0.2.0.ehpk` and `dist/`. The build uses the official CLI and Even Hub SDK 0.0.16. [Build the tagged alpha](../docs/build-from-source.md)
- From `evenhub/`, run the command below. Open `http://127.0.0.1:8080/` in your Mac browser. Press **Control-C** to stop the server.

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

For contributors, `app.json` is the manifest. The built `dist/` directory includes the phone interface, glasses code and SDK license.

## Test on physical G2 glasses

```codex-prompt
Help me test Even R1 Ring Guide for G2 Glasses in Even Hub Prototype Mode on my own devices. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/. Build the optional guide if needed. Help me confirm the Mac and iPhone are on the same trusted Wi-Fi, the G2 is paired and the Even Hub accounts match. Serve only the built evenhub/dist folder on the Mac’s Wi-Fi address. Generate a QR code with the project’s Even Hub CLI. Guide me through scanning, checking readability and confirming that double-tap opens the system exit menu. Stop the test server when I finish. Report which hardware steps I confirmed.
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

4. In the Even app, open **Even Hub → Profile → Prototype Mode** and scan the code. Read the message on your glasses, open the setup guide from the phone, then double-tap on the glasses to check the exit menu. Stop the server with **Control-C** in the first Terminal. [Even’s developer tutorials](https://hub.evenrealities.com/docs/learn/videos)

Even Hub’s publication terms exclude health-related content and services. This companion points to a Mac exporter that handles ring sensor data. Clarify eligibility with Even before submitting. An eligible build also needs a beta test on physical G2 glasses with the phone locked. [Platform terms, section 3.3](https://support.evenrealities.com/hc/en-us/articles/15606676690703-Even-Hub-Developer-Platform-Terms-of-Service) · [Submission and QA](https://hub.evenrealities.com/docs/ship/app-submission)
