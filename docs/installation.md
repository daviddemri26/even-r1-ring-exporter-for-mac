# Install Even R1 Ring Exporter for Mac

## Check your equipment

- Use an Even R1 ring and an iPhone running **Even Realities**. The pilot also paired Even G2 glasses to the iPhone.
- Use a Mac with Apple silicon (M1 or later), macOS 14 or later and a compatible version of the Even app. The pilot used macOS 26.5.1 and Even 2.4.1. [Even on the App Store](https://apps.apple.com/us/app/even-realities/id6747017725)
- In Terminal, run `/usr/bin/python3 --version`. The Mac app needs Python 3.9 or later. If it is missing, run `xcode-select --install` and finish installing Apple’s Command Line Tools.

## Sync your ring first

- Sign in to the same Even account on the iPhone and Mac.
- In Even, open **Health → Settings → Cloud processing & backup**. Enable it if you agree to save your readings with Even. [Even’s backup guide](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- Find a reading on the iPhone. Check that it also appears in **Health** on the Mac.
- To test sleep, wear the ring overnight and check the date you woke up.

## Install the Mac app

1. [Download the Apple silicon DMG](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.4/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.4-arm64.dmg) and double-click it.
2. Drag **Even R1 Ring Exporter for Mac.app** into **Applications**. Eject the DMG.
3. Open the app from Applications. Select **Set Up This Mac**.

This alpha is ad hoc signed. Apple notarization is pending. If Gatekeeper blocks the app, check the [release checksum](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.4/SHA256SUMS) and Apple’s instructions for downloaded apps. [Apple’s opening guide](https://support.apple.com/en-us/102445)

## Allow the collector

- Select **Show Collector** to reveal **Even R1 Ring Collector for Mac.app**.
- Open **System Settings → Privacy & Security → Accessibility**.
- Add or enable that collector. Its permission lets it press the export button in Even.
- If an update shows a blue switch but the app reports a denial, remove the old entry and add the new collector. In the file picker, press **⌘⇧G** and enter the path below.

```text
~/Library/Application Support/R1 Bridge/Export.workflow/Contents/Resources/Even R1 Ring Collector for Mac.app
```

## Test an export

1. Keep your Mac unlocked. In **Mac Collection**, select **Test an Export**.
2. If macOS asks the collector for access to other apps’ data, it needs that permission to read the new ZIP in Even’s cache. Run the test again after granting access.
3. Check the last attempt and latest wake-up date in the Mac app. A successful export can contain the same nights as the previous one.

The collector uses Even’s **Health → Settings → Export Health data** control. Even may briefly show a Save dialog. If it stays open, choose **Cancel** in the panel named `Even_health_data_…zip` and check the export status. [Even’s export guide](https://support.evenrealities.com/hc/en-us/articles/17995748835599-Export-Your-Health-Data)

## Turn on automatic exports

- Select **Schedule Collection**.
- Scheduled checks start at **8:15 a.m., 12:15 p.m. and 6:15 p.m.** local time.
- For one hour, the collector checks every ten minutes for an unlocked Mac with two minutes of keyboard and mouse inactivity.
- If the Mac stays busy, it waits for the next window. **Test an Export** is available at any time.

## Update from R1 Bridge

1. Quit the old **R1 Bridge** app. Copy **Even R1 Ring Exporter for Mac.app** into Applications.
2. Remove the old **R1 Bridge.app** bundle from Applications. Keep `~/Library/Application Support/R1 Bridge/`. It holds your archives and tunnel setup.
3. Open the new app, select **Set Up This Mac**, recheck Accessibility, then **Test an Export**.
4. If you used scheduled exports, select **Schedule Collection** again. Reconnect the ChatGPT plugin if it still lists older tool names.

## Troubleshoot a missing night

- **Missing on the iPhone.** Check that you wore the ring, enabled health tracking and synced with Even. [Even’s missing data guide](https://support.evenrealities.com/hc/en-us/articles/17144131645327-Detected-Health-Data-Is-Missing)
- **Visible only on the iPhone.** Check the Even account and cloud backup setting on both devices, then open Health on the Mac.
- **Visible on the Mac but the export failed.** Unlock the session, check Accessibility permission and close any unrelated dialog in Even. Updated or localized export controls may change what the collector can recognize.
- **Export succeeded but the value stayed the same.** An export only collects what Even has recorded. Steps and active calories may be partial daily totals.
