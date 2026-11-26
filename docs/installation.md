# Install R1 Bridge on your Mac

## What you need

- **Ring and iPhone.** The pilot used an Even R1 ring and Even G2 glasses paired to an iPhone with the **Even Realities** app. To record a night, wear the ring while you sleep. Look for its wake-up date in **Health** on your iPhone.
- **Mac.** Use a Mac with Apple silicon (M1 or later) running macOS 14 or later. Your Mac must also be able to run the Even app available for your account. The pilot used macOS 26.5.1 and Even 2.4.1. Apple lists Even as designed for iPhone. [Even on the App Store](https://apps.apple.com/us/app/even-realities/id6747017725)
- **Command Line Tools.** The alpha needs Apple’s `/usr/bin/python3`, version 3.9 or later. Run `/usr/bin/python3 --version` in Terminal to check. If macOS asks to install the Command Line Tools, finish the installation. You can also run `xcode-select --install`.
- **Even account.** Sign in to the same Even account on your Mac and iPhone. This workflow uses **Health → Settings → Cloud processing & backup** to sync readings through Even’s cloud. Enable it if you agree to store your readings with Even, then compare the date of a reading on both devices. [Even’s cloud backup guide](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- **ChatGPT web (optional).** To ask ChatGPT about a reading, use an account that supports custom MCP servers and an OpenAI Platform organization with tunnel access. [ChatGPT setup](chatgpt.md)

## Install the alpha

1. Download the **arm64 DMG** from the [GitHub release](https://github.com/daviddemri26/r1-bridge/releases/tag/v0.1.0-alpha.3) and open it. The release also includes a SHA-256 checksum.
2. Drag **R1 Bridge.app** to **Applications**, eject the DMG and open the app from Applications.
3. This alpha is ad hoc signed. Apple Developer ID signing and notarization are pending. If Gatekeeper blocks it, verify the source and published checksum or build the app from source. [Apple’s guide to opening downloaded apps](https://support.apple.com/en-us/102445)

**Updating an earlier alpha.** Quit the old app, replace it in Applications and open the new version. Select **Set Up This Mac**. Check the new collector’s Accessibility permission and run **Test an Export**. If you used scheduled collection before, choose **Schedule Collection** again. Reconnect the plugin in ChatGPT if you previously installed the connector and it still lists the old tool names. [ChatGPT setup](chatgpt.md)

## Run your first export

1. Open **Health** in Even on the Mac and find a reading you recognize. Even’s manual export is under **Health → Settings → Export Health data**. [Even’s export guide](https://support.evenrealities.com/hc/en-us/articles/17995748835599-Export-Your-Health-Data)
2. Select **Set Up This Mac** in R1 Bridge. Keep the Mac unlocked. The collector can start Even in the background. Even may briefly display a window during export.
3. Under **System Settings → Privacy & Security → Accessibility**, allow **R1 Bridge Collector**. **Show Collector** in R1 Bridge reveals the app you need. If macOS denies access after an update while the switch is on, remove the old entry. Click **+**, press **⌘⇧G** and enter `~/Library/Application Support/R1 Bridge/Export.workflow/Contents/Resources/R1 Bridge Collector.app` to add the new version.
4. Return to R1 Bridge and select **Test an Export**. If macOS asks for access to other apps’ data, the collector needs it to read the ZIP Even just created. Run the test again after granting the permission. Check the last attempt and the latest wake-up date. A successful export can contain the same nights as the previous one.
5. Select **Schedule Collection** for automatic exports. At 8:15 a.m., 12:15 p.m. and 6:15 p.m. local time, R1 Bridge starts checking every ten minutes for one hour. An export starts once the session is unlocked and the keyboard and mouse have been idle for two minutes. If the Mac stays busy throughout the hour, collection waits for the next window.

## If Even asks where to save a ZIP

Even may offer to save `Even_health_data_…zip` to Documents during export. R1 Bridge collects the copy in Even’s cache and dismisses the matching export panel. If the panel remains open, choose **Cancel** in the window containing that filename, then check the export status in R1 Bridge.

## If a night is missing

- **Missing on the iPhone.** Check that you wore the ring, enabled health tracking and synced with Even. R1 Bridge can read only the sessions that Even supplies. [Even’s missing health data guide](https://support.evenrealities.com/hc/en-us/articles/17144131645327-Detected-Health-Data-Is-Missing)
- **Visible on the iPhone only.** Check the Even account and cloud backup setting on both devices, then open Health on the Mac.
- **Visible on the Mac but the export failed.** Check that the session was unlocked, the collector has Accessibility permission and Even is ready to accept input. An Even update or a different interface language can change the export controls.
- **The export succeeded but the reading’s age stayed the same.** Steps and active calories may be partial daily totals. An older temperature reading may stay on screen until Even has a newer measurement.
