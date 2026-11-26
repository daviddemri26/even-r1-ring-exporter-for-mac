# Build from source

Use the tagged source to reproduce a particular alpha. The Mac app, G2 guide and website can each be built or previewed separately.

## Get the release source

1. Download the [alpha 4 source ZIP](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/archive/refs/tags/v0.1.0-alpha.4.zip).
2. Extract the ZIP. Open Terminal in the extracted folder containing `README.md`, `macos/` and `scripts/`.
3. Run the commands below from that folder. If you only need the app, use the [installation guide](installation.md).

## Build and verify the Mac app

- Use a Mac with Apple silicon running macOS 14 or later.
- Install Apple’s Command Line Tools. Run `xcode-select --install` if they are missing.
- Check that `/usr/bin/python3 --version` reports Python 3.9 or later.
- Run the runtime tests, build the disk image and verify it.

```sh
/usr/bin/python3 -B -m unittest discover -s macos/tests
./scripts/build-macos.sh
./scripts/verify-macos.sh
```

- Find `Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.4-arm64.dmg` and its SHA-256 checksum in `dist/`.
- The verification script mounts the DMG read-only. It checks signatures, architecture and setup in a temporary user folder.
- The local build uses ad hoc signing. To try a real export, follow the [first export steps](installation.md).

## Build the optional G2 guide

- Install Node.js 22 and npm. The G2 and website builds use them.
- Run the following commands from the extracted project folder. The parentheses return you to that folder afterward.

```sh
(
  cd evenhub || exit 1
  npm ci && npm test && npm run pack
)
```

- Find `Even-R1-Ring-Guide-for-G2-Glasses.ehpk` in `evenhub/`.
- The package contains the offline guide. Publishing it in the Even Hub catalog is a separate step. [About the G2 guide](../evenhub/README.md)

## Preview the website

- Rebuild the website guides from the Markdown sources. Then start a local server from the project folder.

```sh
npm ci --prefix site
npm run build:guides --prefix site
/usr/bin/python3 -m http.server --bind 127.0.0.1 --directory site/dist 8080
```

- Open `http://127.0.0.1:8080/` in your browser. The server serves the pages in `site/dist/` on this Mac. Use the public website for release downloads.
- Press **Control-C** in Terminal when you finish.
