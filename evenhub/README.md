# R1 Bridge Guide for Even G2

Five short cards help you trace a night from your ring to the Even app, your Mac and ChatGPT. The guide runs offline after loading. Its text is bundled with the app and it requests no network or health permissions. [Install the Mac app separately](../docs/installation.md).

## Using the guide

- Tap or scroll down to advance one card. Scroll up to go back.
- Double-tap to open the system exit menu. On the phone, use **Previous** and **Next** to browse the same cards.
- Download `r1-bridge-guide.ehpk` from the [public alpha release](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.3). The English guide is version 0.1.1. Physical G2 testing is pending before an Even Hub catalog submission.

## Building the package

Run the following in `evenhub/` with Node.js 22 and npm. The official CLI packages the app for Even Hub SDK 0.0.16.

```sh
npm ci
npm test
npm run pack
```

The build produces `dist/` with the phone interface, glasses code and SDK license. Packaging creates `r1-bridge-guide.ehpk`. Edit `app.json` to update the manifest or `src/guide.js` to change the cards.

## Even Hub listing draft

**R1 Bridge Guide** helps R1 owners check a missing night from their G2 glasses. Browse five cards to find the wake-up date in Even, collect an export on the Mac and ask your own ChatGPT connector about it. Available in English. An independent project for Even G2.

The guide uses the gestures exposed by the Even Hub SDK. The separate Mac app reads the official health export from Even. [Device APIs](https://hub.evenrealities.com/docs/build/device-apis) · [Even Hub quick start](https://hub.evenrealities.com/docs/get-started/quickstart/first-app) · [Submission process](https://hub.evenrealities.com/docs/ship/app-submission)
