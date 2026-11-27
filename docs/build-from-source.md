# Build from source

This guide is for contributors who want to build a release or preview the website. For a ready-to-use Mac app, follow the [installation guide](installation.md). Each build below can run on its own.

## Build and verify the Mac disk image

```codex-prompt
Build the public Even R1 Ring Exporter for Mac alpha 7 disk image. Download the tagged source from https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/source.zip and extract it into a new folder. Check for Apple silicon, macOS 14 or later, Apple Command Line Tools and /usr/bin/python3 version 3.9 or later. If an Apple installer needs my input, give me the next click. Run the repository’s runtime unit tests, build the DMG and run its verification script. Use synthetic data only. Leave the installed exporter and its services alone. Report the DMG and checksum locations and which checks passed.
```

- Codex can download the [alpha 7 source ZIP](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/archive/refs/tags/v0.1.0-alpha.7.zip). It contains the project files for building the app.
- To build manually, extract it and open Terminal in the folder containing `macos/` and `scripts/`. If Apple’s Command Line Tools are missing, run `xcode-select --install`.
- Run the tests, build and verification from that folder.

```sh
/usr/bin/python3 -B -m unittest discover -s macos/tests &&
  ./scripts/build-macos.sh &&
  ./scripts/verify-macos.sh
```

Find `Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.7-arm64.dmg` and its `.sha256` file in `dist/`. The build uses ad hoc signing. Verification checks the checksum, mounts the disk image read-only, checks signatures and architecture, and tests setup in a temporary user folder.

The Mac app, its collector and the website use the [original Even Hub ring icon](../site/dist/assets/even-r1-ring-icon.png). The Mac build generates the Finder icon from that PNG. To regenerate a web size, run the same renderer, for example `xcrun swift macos/app/icon.swift site/dist/assets/even-r1-ring-icon.png site/dist/assets/favicon-32.png 32`.

## Build the optional G2 glasses package

```codex-prompt
Build the public Even R1 Ring Guide for G2 Glasses from the alpha 7 source. Use an existing clean copy of that release or extract https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/source.zip into a new folder. Check for Node.js 22 and npm. From evenhub/, run npm ci, npm test and npm run pack in order. Verify that the .ehpk file was produced and report its path and test result. Keep this build local and leave my Even devices and accounts alone.
```

- For the ready-made companion, go to the [glasses guide](../evenhub/README.md).
- To build it yourself, run the following from the extracted project folder with Node.js 22 and npm.

```sh
(cd evenhub && npm ci && npm test && npm run pack)
```

The output is `evenhub/Even-R1-Ring-Guide-for-G2-Glasses.ehpk`. The package contains the offline guide.

## Preview the website on your Mac

```codex-prompt
Preview the Even R1 Ring Exporter for Mac website locally. Use the current project folder if it contains the website. Otherwise clone https://github.com/daviddemri26/even-r1-ring-exporter-for-mac.git into a new folder. With Node.js 22 and npm, install the locked site dependencies, generate the setup page and serve only site/dist on a free loopback port. Verify the homepage and setup guide load. Give me the local URL and how to stop the preview.
```

To run it manually, use the following commands from the project folder.

```sh
npm ci --prefix site &&
  npm run build:guides --prefix site &&
  /usr/bin/python3 -m http.server --bind 127.0.0.1 --directory site/dist 8080
```

Open `http://127.0.0.1:8080/`. Press **Control-C** in that Terminal to stop the preview. Use the public site for release downloads.
