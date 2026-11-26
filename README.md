# R1 Bridge

R1 Bridge brings sleep and activity readings from your Even R1 ring into ChatGPT. The Mac app runs Even’s health export, keeps the ZIP archives on your Mac, and lets your personal ChatGPT account query them through a read-only connector.

**Public alpha for Macs with Apple silicon.** [Project website](https://daviddemri26.github.io/r1-bridge/) · [Download the Mac app](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.3) · [Installation guide](docs/installation.md)

## Questions you can ask

- **“How much did I sleep each night over the last seven days?”** R1 Bridge groups distinct sessions, including naps, by the local date you woke up. A missing date means Even supplied no session for that date.
- **“How much light, deep and REM sleep did Even record?”** The connector can also report time awake during recorded sessions. It flags readings whose stages cannot be reliably determined.
- **“What were my latest readings, and how old are they?”** You can query steps, active calories, heart rate, heart rate variability, blood oxygen saturation and skin temperature variation. Each reading includes the age shown in Even.

## How it works

1. Keep your R1 ring and G2 glasses paired to Even on your iPhone. With cloud backup enabled, Even makes your readings available under the same account on the Mac.
2. R1 Bridge triggers Even’s built-in export, checks the ZIP and deduplicates repeated exports. You can run a local export before setting up ChatGPT.
3. If you enable scheduling, the collector looks for a quiet moment starting at **8:15 a.m., 12:15 p.m. and 6:15 p.m.** local time. It waits for an idle, unlocked Mac. Use **Test an Export** to run it yourself at any time.
4. To use ChatGPT on the web, connect the Mac to a tunnel in your own OpenAI account. Keep it awake and online whenever ChatGPT needs to read an export. [Connect ChatGPT](docs/chatgpt.md)

The pilot completed scheduled collection and queried sleep and all six readings in ChatGPT on the web. A second person testing their own Mac and two consecutive nights of collection are still needed to establish compatibility beyond the pilot. This release supports Mac and ChatGPT. Apple Health would require an iPhone integration with HealthKit.

## Guides

- [Hardware, installation, permissions and troubleshooting](docs/installation.md)
- [Set up your ChatGPT connector](docs/chatgpt.md)
- [Data access, storage and removal](docs/privacy.md)
- [Optional offline guide for Even G2](evenhub/README.md)
- [Test the alpha on another Mac](docs/alpha-testing.md)

## Build from source

On an Apple silicon Mac with Apple’s Command Line Tools installed, run `./scripts/build-macos.sh` from the repository root. Find the resulting DMG in `dist/`. Use `./scripts/verify-macos.sh` to verify its contents.

The Mac app and collector are in `macos/`, and the ChatGPT setup assistant is in `integration/`. The [G2 project](evenhub/README.md) has its own build. To preview the public website, run `python3 -m http.server --bind 127.0.0.1 --directory site/dist 8080` and open `http://localhost:8080`.

R1 Bridge is an independent project. Even Realities, Apple, OpenAI and ChatGPT are trademarks of their respective owners.
