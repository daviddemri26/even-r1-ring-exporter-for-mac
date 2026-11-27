# Build Sleep Sync Companion

The iPhone target runs on iOS 17 and later. The Mac exporter requires Apple silicon and macOS 14 or later. Build the iPhone app with Xcode 26 or later for the included project format and current App Store toolchain.

## Try it on your own devices

1. Get the [current source from the main branch](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/tree/main). The tagged alpha 7 download is for Mac collection and the private ChatGPT connector. iPhone pairing starts with alpha 8.
2. From the checkout, run `./scripts/build-macos.sh` and then `./scripts/verify-macos.sh`. Open the generated DMG in `dist/` and install **Even R1 Ring Exporter for Mac** in Applications.
3. Open `ios/SleepSync.xcodeproj` in Xcode and select the **SleepSync** target. Under **Signing & Capabilities**, select your development team with HealthKit support. When building with your own team, use a unique bundle identifier registered to that team and keep the HealthKit capability enabled.
4. Choose your trusted iPhone as the run destination and click **Run**. Once the app is installed, follow the [iPhone pairing and Apple Health guide](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/). Routine sync uses the local network.

## Development

1. Open `ios/SleepSync.xcodeproj` and select the **SleepSync** scheme. Choose an iPhone simulator and run. The connection menu contains **Try a Preview** for viewing the screens with sample data.
2. Run the Mac and companion tests from the project root. The companion check uses a temporary directory, synthetic sessions, a short-lived local Bonjour listener, and in-memory credentials.
3. Use an isolated macOS account and a dedicated test iPhone for device acceptance. See the [App Review walkthrough](app-store.md) for the physical pairing, Health permission, correction, and offline checks.

```sh
/usr/bin/python3 -B -m unittest discover -s macos/tests
./scripts/test-companion.sh
```

## Local release artifacts

- If you have a locally prepared simulator ZIP, unzip it and drag `SleepSync.app` onto a booted Apple silicon iPhone simulator. From a fresh checkout, run the simulator target in Xcode and select **Try a Preview** from the app’s connection menu.
- Run `./scripts/build-iphone.sh unsigned` to produce `dist/iphone/SleepSync-unsigned.xcarchive` for inspecting the device binary and resources.
- To prepare the App Store archive and export a locally signed IPA, run `./scripts/build-iphone.sh app-store YOUR_TEAM_ID` on a Mac signed in to the owning Apple Developer team. Xcode uses automatic provisioning, including the HealthKit capability. The archive and export are written under `dist/iphone/`. Upload and review are separate actions in App Store Connect.
- The local hardware-test build is `dist/iphone/device-test/SleepSync.ipa`. To regenerate it, select the signed iPhone archive in Xcode Organizer, choose **Distribute App → Custom → Debugging**, and export locally. In **Window → Devices and Simulators**, select a connected, trusted iPhone included in that development profile and install the IPA under **Installed Apps**. Allow Developer Mode on the phone if iOS requests it.
- For the Mac package, run `./scripts/build-macos.sh` followed by `./scripts/verify-macos.sh`. For a release, set `MAC_SIGN_IDENTITY=developer-id` and set `NOTARY_PROFILE` to the name of your notarytool Keychain profile before building. The script signs, submits, staples, and verifies the DMG. The release DMG supports **Pair iPhone** from alpha 8.
- Store screenshots come from the Release simulator app using the launch arguments `-preview-setup`, `-preview-connected`, and `-preview-waiting`. The committed images use an iPhone 17 Pro Max simulator. The original icon can be regenerated with `xcrun swift ios/Artwork/make-icon.swift ios/SleepSync/Assets.xcassets/AppIcon.appiconset/SleepSync.png`.
