# Even R1 Ring Exporter for Mac

Even R1 Ring Exporter for Mac saves the sleep and activity readings from your ring on your Mac. **Even R1 Ring Collector for Mac**, the helper included in the app, runs the official Even export and keeps the ZIP archives on your Mac.

To ask about those readings without attaching a file, set up **Even R1 Ring Data for ChatGPT**, the optional read-only connector for your own ChatGPT workspace. **Even R1 Ring Guide for G2 Glasses** is a separate offline companion that displays setup tips on the glasses.

**Public alpha for Macs with Apple silicon.** [Project website](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/) · [Download the Mac app](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.4-arm64.dmg) · [Installation guide](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/)

## Questions you can ask

- **“How much did I sleep each night over the last seven days?”** The connector groups distinct sessions, including naps, by the local date you woke up. A missing date means Even supplied no session for that date.
- **“How much light, deep and REM sleep did Even record?”** The connector can also report time awake during recorded sessions. It flags readings whose stages cannot be reliably determined.
- **“What were my latest readings, and how old are they?”** You can query steps, active calories, heart rate, heart rate variability, blood oxygen saturation and skin temperature variation. Each reading includes the age shown in Even.

## How it works

1. Open the **Mac App Store on your Mac**. Under **iPhone & iPad Apps**, install **Even Realities** by Even Realities Ltd., marked **Designed for iPhone**. Sign in with the same Even account as on your iPhone. Keep your ring paired to your iPhone and enable Even’s cloud backup to sync the readings. [Even Realities in the App Store](https://apps.apple.com/us/app/even-realities/id6747017725)
2. The Mac collector triggers Even’s built-in export, checks the ZIP and deduplicates repeated exports. You can run a local export before setting up ChatGPT.
3. The guided installation verifies the first export and turns on **Schedule Collection**. From then on, the collector opens Even and saves exports automatically when the Mac is awake, unlocked and idle. No daily clicks or file uploads are needed. The three collection windows start at **8:15 a.m., 12:15 p.m. and 6:15 p.m.** local time.
4. To use ChatGPT on the web, connect the Mac to a tunnel in your own OpenAI account. Keep it awake and online whenever ChatGPT needs to read an export. [Connect your ring data to ChatGPT](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/)

The pilot completed scheduled collection and queried sleep and all six readings in ChatGPT on the web. A second person testing their own Mac and two consecutive nights of collection are still needed to establish compatibility beyond the pilot. This release supports Mac and ChatGPT. Apple Health would require an iPhone integration with HealthKit.

## Guides

[Browse all guides on the website](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/).

- [Hardware, installation, permissions and troubleshooting](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/)
- [Set up your ChatGPT connector](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/)
- [Data access, storage and removal](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/privacy/)
- [Even R1 Ring Guide for G2 Glasses](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/)
- [Ask about your readings](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/ask/)
- [Troubleshoot a missing reading](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/troubleshooting/)
- [Build from source](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/build/)
- [Test the alpha on another Mac](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/test/)

## Build from source

On an Apple silicon Mac with Apple’s Command Line Tools installed, run `./scripts/build-macos.sh` from the repository root. Find the resulting DMG in `dist/`. Use `./scripts/verify-macos.sh` to verify its contents.

The Mac app and collector are in `macos/`, and the ChatGPT setup assistant is in `integration/`. The [G2 project](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/glasses/) has its own build. To rebuild the website guides, run `npm ci --prefix site` and `npm run build:guides --prefix site`. To preview the website, run `python3 -m http.server --bind 127.0.0.1 --directory site/dist 8080` and open `http://localhost:8080`.

This project is independent of Even Realities, Apple and OpenAI. Even Realities, Apple, OpenAI and ChatGPT are trademarks of their respective owners.
