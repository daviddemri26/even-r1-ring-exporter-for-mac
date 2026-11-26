# Even R1 Ring Guide for G2 Glasses

This optional guide displays five short cards on the G2 glasses. They explain how to check a night on the Even R1 ring, sync it to the Even app, and ask about it through **Even R1 Ring Data for ChatGPT**. The guide runs offline after loading. Its text is bundled with the app and it requests no network or health permissions. [Install Even R1 Ring Exporter for Mac separately](../docs/installation.md).

## Using the guide

- Tap or scroll down to advance one card. Scroll up to go back.
- Double-tap to open the system exit menu. On the phone, use **Previous** and **Next** to browse the same cards.
- [Download the G2 guide package](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.4/Even-R1-Ring-Guide-for-G2-Glasses.ehpk). The English guide is version 0.1.2. Physical G2 testing is pending before an Even Hub catalog submission.

## Building the package

Run the following in `evenhub/` with Node.js 22 and npm. The official CLI packages the app for Even Hub SDK 0.0.16.

```sh
npm ci
npm test
npm run pack
```

The build produces `dist/` with the phone interface, glasses code and SDK license. Packaging creates `Even-R1-Ring-Guide-for-G2-Glasses.ehpk`. Edit `app.json` to update the manifest or `src/guide.js` to change the cards.

## Try the guide on a phone or G2 glasses

1. Build the package using the steps above. In the same `evenhub/` folder, start a server for the guide files.

```sh
python3 -m http.server 8080 --bind 0.0.0.0 --directory dist
```

2. On your Mac, open `http://localhost:8080/`. Use **Next** and **Previous** to try the five cards.
3. For a glasses test, connect the iPhone and Mac to the same trusted Wi-Fi network. Pair the G2 with the Even app. Sign in to Even Hub and the phone app using the same account.
4. Find your Mac’s Wi-Fi address in **System Settings → Wi-Fi → Details → TCP/IP**. Open a second Terminal in `evenhub/`. Replace `YOUR_MAC_IP` with that address and generate a QR code.

```sh
node node_modules/@evenrealities/evenhub-cli/main.js qr --url http://YOUR_MAC_IP:8080/
```

5. In the Even app, open **Even Hub → Profile → Prototype Mode** and scan the code. When you finish, stop the server with **Control-C** in the first Terminal. [Even’s developer tutorials](https://hub.evenrealities.com/docs/learn/videos)

## Even Hub listing draft

Even Hub limits the display name to 20 characters. The package appears there as **Even R1 Guide for G2**.

**Even R1 Ring Guide for G2 Glasses** helps R1 owners check a missing night from their G2 glasses. Browse five cards to find the wake-up date in Even, collect an export on the Mac and ask your own ChatGPT connector about it. Available in English. An independent project for Even G2.

The guide uses the gestures exposed by the Even Hub SDK. The separate Mac app reads the official health export from Even. [Device APIs](https://hub.evenrealities.com/docs/build/device-apis) · [Even Hub quick start](https://hub.evenrealities.com/docs/get-started/quickstart/first-app) · [Submission process](https://hub.evenrealities.com/docs/ship/app-submission)
