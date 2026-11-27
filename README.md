# <img src="site/dist/assets/favicon-32.png" width="32" height="32" alt=""> Even R1 Ring Exporter for Mac

Connect your Even R1 ring data to ChatGPT. Set it up once on your Mac, then ask about your ring’s sensor readings in chat.

**[Set up on your Mac](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/)** · [Project website](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/)

## Sleep Sync Companion for iPhone

Sleep Sync Companion brings verified Even R1 sleep stages and naps into Apple Health on iOS 17 or later. Pair your iPhone once with the Mac’s QR code and allow the companion to write **Sleep**. On the same local network, the iPhone checks for new sessions when you open the app and when iOS allows background refresh. You can also schedule **Sync Sleep** in Shortcuts.

To use these sessions in ChatGPT Health, connect Apple Health on your iPhone and give ChatGPT permission to read **Sleep**. After the connection syncs, ask “Which sleep sessions came from Sleep Sync Companion?”

Pairing requires the alpha 8 Mac build and a signed iPhone build. The public alpha 7 download supports the Mac collector and its ChatGPT connector. [iPhone setup, support and privacy](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/) · [Build and test the iPhone app](docs/companion/build.md) · [App Store materials and reviewer walkthrough](docs/companion/app-store.md)

## Technical documentation

- [Mac installation, export permissions and scheduling](docs/installation.md)
- [Private ChatGPT connection and account requirements](docs/chatgpt.md)
- [Supported readings and their interpretation](docs/ask-about-readings.md)
- [Troubleshooting](docs/troubleshooting.md) and [privacy, permissions and removal](docs/privacy.md)
- [Build the Mac app, glasses guide or website](docs/build-from-source.md)
- [Test the public alpha](docs/alpha-testing.md) and [work on the optional G2 glasses guide](evenhub/README.md)

The Mac app and collector are in `macos/`, the ChatGPT connection assistant is in `integration/`, the glasses guide is in `evenhub/`, and the website is in `site/`. To update the public setup guide, edit `site/setup.md` and run `npm ci --prefix site` followed by `npm run build:guides --prefix site`.

The pilot verified scheduled collection and ChatGPT web queries. Independent second-Mac and two-night tests are still pending. This project is independent of Even Realities, Apple and OpenAI.
