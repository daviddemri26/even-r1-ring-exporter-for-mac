# R1 Ring Data→ChatGPT

**Connect R1 Ring Data to ChatGPT.** This G2 companion shows the short setup address on your glasses. Open [is.gd/r1mac](https://is.gd/r1mac) on your Mac, click **Copy setup prompt**, and paste it into Codex on that Mac. Codex installs the exporter and connects your ring data to ChatGPT. You handle sign-ins and permissions.

## Get the G2 companion

**0.2.0** is the current marketplace candidate. The [store listing](store-listing.md) includes the app description, release notes and simulator screenshot. The [Mac release](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/tag/v0.1.0-alpha.5) still includes the earlier G2 package (0.1.2).

## Preview the companion on your Mac

```codex-prompt
Help me preview the R1 Ring Data→ChatGPT on this Mac. Follow the optional G2 source build at https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/build/. Use the project source in my folder and report the version in evenhub/app.json. Use Node.js 22 and npm. In evenhub/, install locked dependencies, run the tests and pack the guide. Serve only evenhub/dist on a free loopback port. Open its phone interface and verify the screen matches that version. In 0.2.0, check the short address and the Mac setup link. Give me the local preview URL and the command to stop it.
```

- With Node.js 22 and npm, run `npm ci && npm test && npm run pack` inside `evenhub/`. In the 0.2.0 source this produces `R1-Ring-Data-to-ChatGPT-for-G2-0.2.0.ehpk` and `dist/`. The build uses the official CLI and Even Hub SDK 0.0.16. [Build the tagged alpha](../docs/build-from-source.md)
- From `evenhub/`, run the command below. Open `http://127.0.0.1:8080/` in your Mac browser. Press **Control-C** to stop the server.

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

For contributors, `app.json` is the manifest. The built `dist/` directory includes the phone interface, glasses code and SDK license.

## Test on physical G2 glasses

```codex-prompt
Help me test R1 Ring Data→ChatGPT in Even Hub Prototype Mode on my own devices. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/. Build the optional guide if needed. Help me confirm the Mac and iPhone are on the same trusted Wi-Fi, the G2 is paired and the Even Hub accounts match. Serve only the built evenhub/dist folder on the Mac’s Wi-Fi address. Generate a QR code with the project’s Even Hub CLI. Guide me through scanning, checking readability and confirming that double-tap opens the system exit menu. Stop the test server when I finish. Report which hardware steps I confirmed.
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

4. In the Even app, open **Even Hub → Profile → Prototype Mode** and scan the code. Read the instructions on your glasses, type the displayed short address on your Mac, then double-tap on the glasses to check the exit menu. Stop the server with **Control-C** in the first Terminal. [Even’s developer tutorials](https://hub.evenrealities.com/docs/learn/videos)

For store review, repeat the launch and exit test with a beta build on physical G2 glasses and the phone locked. [Beta testing](https://hub.evenrealities.com/docs/test/beta-testing) · [Submission and QA](https://hub.evenrealities.com/docs/ship/app-submission)
