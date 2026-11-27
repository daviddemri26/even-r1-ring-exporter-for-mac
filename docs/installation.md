# Install Even R1 Ring Exporter for Mac

Wear your ring and let Even sync. After this one-time setup, your Mac exports new readings automatically when it’s awake, unlocked and idle. You can close the exporter and ask ChatGPT about the latest saved readings once connected.

You’ll use **two apps on the Mac**. Get **Even Realities** (the iPhone app) from the **Mac App Store on your Mac**. Get **Even R1 Ring Exporter for Mac** (the `.dmg`) from this site. The prompt below can take care of both.

## Set up automatic collection with Codex

```codex-prompt
Set up Even R1 Ring Exporter for Mac for hands-free daily collection. Verify one initial export, then enable the automatic schedule on this Mac. Do the work you can, then give me one short instruction at a time for anything I need to do on my iPhone or in a macOS consent dialog. Resume after each answer. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/ as the project guide.

1. Check for Apple silicon, macOS 14 or later, /usr/bin/python3 version 3.9 or later, and the Even Realities app installed ON THIS MAC. If Even is missing, open the Mac App Store at https://apps.apple.com/us/app/even-realities/id6747017725. In search, select iPhone & iPad Apps if offered. Install Even Realities by Even Realities Ltd., labeled Designed for iPhone. Open it and let me sign in with my iPhone's Even account. If the App Store won't offer it on my Mac or in my region, explain and stop. Check whether the exporter and collector are already installed. Resume any partial setup. Preserve existing archives, settings and schedules. Ask before replacing a newer or unfamiliar app.
2. Help me sync the ring in Even on my iPhone. I handle sign-in and decide whether to enable Even's Cloud processing & backup. Confirm that Health on the Mac shows a reading from the same account. I can confirm this without giving you the value.
3. If installation is needed, get the Apple silicon DMG from https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.7-arm64.dmg and compare its SHA-256 with the matching filename in https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/SHA256SUMS before opening it. Stop on a mismatch. Install the .app in Applications, open that copy and run Mac Collection → Set Up This Mac. Leave macOS security protections enabled.
4. Show me where to allow Even R1 Ring Collector for Mac under Accessibility. If macOS requests access to other apps' data for this collector, explain that it reads Even's exported ZIP. Wait for me to approve. With my Mac unlocked, run Test an Export and Refresh. Verify a new manual attempt marked succeeded with “Export verified.” If it fails, fix the reported cause and retry. An unchanged archive or an export without sleep sessions can pass.
5. After the export passes, choose Mac Collection → Schedule Collection. Refresh and verify the app displays “Next scheduled check”. Report the initial export result and the next local check time separately. Only describe a scheduled export as completed if the app actually recorded it. If either check fails, diagnose it or tell me the precise blocker. Keep archives and readings on this Mac. If I want to ask about my saved readings in ChatGPT web, continue using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/ and verify one reading there without attaching a file. The G2 glasses guide is optional.
```

- Keep your iPhone nearby and your Mac unlocked for setup. You can do the whole installation in one Codex chat.
- Setup is complete when **Mac Collection → Refresh** shows both **Export verified** for the test and a time under **Next scheduled check**. Future runs collect whatever your ring has synced to Even.

## Check the Mac and sync the ring

```codex-prompt
Check whether my Mac is ready for Even R1 Ring Exporter using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/. Inspect the chip, macOS version, /usr/bin/python3 version and whether Even Realities is installed. If Apple's Python is missing, help me open the Command Line Tools installer and recheck after I finish. On this Mac, open the Mac App Store listing https://apps.apple.com/us/app/even-realities/id6747017725. If searching, select iPhone & iPad Apps if offered. Install or open Even Realities by Even Realities Ltd. (Designed for iPhone) and let me sign in with my iPhone's Even account. If unavailable for my Mac or region, explain and stop. Guide me through pairing or syncing my ring on my iPhone, confirming health tracking, and reviewing Even's Cloud processing & backup choice. I will handle sign-in and consent. Ask me whether I see a reading in Health on both devices under the same account. A yes or no is enough. Tell me whether I'm ready to install or which prerequisite is missing.
```

- Use an Even R1 ring, your iPhone and an Apple silicon Mac (M1 or later) with macOS 14 or later. The pilot also used paired G2 glasses.
- **On the Mac**, open the **Mac App Store**, search for **Even Realities** and select **iPhone & iPad Apps** if offered. Choose **Even Realities** by **Even Realities Ltd.**, marked **Designed for iPhone**. Click **Get** or the download icon, then **Open**. Sign in with the same Even account as on your iPhone. [Open the App Store listing on your Mac](https://apps.apple.com/us/app/even-realities/id6747017725)
- In Even on iPhone, sync the ring. Under **Health → Settings**, check **Health tracking** and review **Cloud processing & backup**. Turn on backup if you agree to sync with Even. Sign in to the same account on the Mac and check that a reading appears in **Health**. [Even’s backup guide](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- The exporter uses Apple’s Python 3.9 or later. To check manually, run `/usr/bin/python3 --version` in Terminal. If it’s missing, run `xcode-select --install` and finish Apple’s installer.

## Install the Mac app

```codex-prompt
Install Even R1 Ring Exporter for Mac using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/. First check that Even's iPhone app is on this Mac. If missing, open the Mac App Store at https://apps.apple.com/us/app/even-realities/id6747017725. If searching, select iPhone & iPad Apps if offered. Install or open Even Realities by Even Realities Ltd. (Designed for iPhone) and let me sign in with the same Even account as on my iPhone. Stop if the store says it's unavailable. Then check for an existing exporter. Use the installed copy if already current. Otherwise download or reuse https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.7-arm64.dmg. Calculate its SHA-256 and require an exact match for that filename in https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/downloads/SHA256SUMS before mounting it. Stop if verification fails. Copy the app to Applications and open that copy. Run Mac Collection → Set Up This Mac if needed. Keep existing archives and settings. Ask before replacing a newer or unfamiliar copy. If macOS blocks opening this ad hoc signed alpha, explain Apple's per-app review and let me decide. Leave the optional ChatGPT command for later. Confirm the collector is ready for its permission step.
```

**Which file do I need?**

- **.dmg — Mac exporter.** Open the verified disk image. Inside, drag **Even R1 Ring Exporter for Mac.app** to the **Applications** shortcut. This app collects your ring data. [Download the disk image](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.7/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.7-arm64.dmg) · [Release checksums](https://github.com/daviddemri26/even-r1-ring-exporter-for-mac/releases/download/v0.1.0-alpha.7/SHA256SUMS)
- **.ehpk — optional G2 glasses guide.** This is a separate download with five setup tips for the glasses. The Mac exporter works without this file. [About the glasses guide](../evenhub/README.md)
- **Inside the DMG**, **Connect Even R1 Ring to ChatGPT.command**, starts the optional web connection. You can eject the disk image now. The same assistant is available later in the installed app. [Connect ChatGPT](chatgpt.md)
- Open the app from **Applications**, then choose **Mac Collection → Set Up This Mac**. Apple hasn’t notarized this alpha. If macOS blocks it, review Apple’s instructions before choosing whether to open it. [Apple’s opening guide](https://support.apple.com/en-us/102445)

## Verify your first export

```codex-prompt
Verify a fresh local export in Even R1 Ring Exporter for Mac. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/. Check that Even Realities is installed and signed in to my iPhone's Even account on this Mac. If missing, open https://apps.apple.com/us/app/even-realities/id6747017725 in the Mac App Store. Use iPhone & iPad Apps if searching and offered. Install Even Realities by Even Realities Ltd. (Designed for iPhone), open it and let me sign in. If unavailable, explain and stop. Open the exporter's Mac Collection tab. If it needs setup, run Set Up This Mac first. Open Show Collection Options and use Show Collector and Accessibility Settings to guide me to the installed Even R1 Ring Collector for Mac. I will grant the macOS permissions myself. With Even signed in and the Mac unlocked, run Test an Export. If macOS asks this collector to access other apps' data, explain why, wait for my choice and retry after approval. Refresh and match the time, manual mode, succeeded status and “Export verified” message to this test. If a test is already running, let it finish. Report the time and result or diagnose the actual error using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/troubleshooting/. Keep the ZIP and readings on my Mac.
```

- Open **Show Collection Options**, then use **Show Collector** and **Accessibility Settings**. Enable **Even R1 Ring Collector for Mac.app** so it can press Even’s export button. If it’s missing, add the app revealed by **Show Collector**.
- Select **Test an Export**. If macOS asks to let the collector access other apps’ data, this allows it to read the ZIP Even creates. After approving, run the test again.
- Select **Refresh**. “Export verified. No new wake dates.” also means the test passed. If a Save dialog for `Even_health_data_…zip` lingers after success, choose **Cancel**. The collector has already archived the export. [Troubleshoot an export or a missing night](troubleshooting.md)

## Turn on automatic collection

```codex-prompt
Enable automatic local collection for Even R1 Ring Exporter for Mac using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/. Confirm the Mac has Even Realities signed in with my iPhone's Even account. If missing, open https://apps.apple.com/us/app/even-realities/id6747017725 in the Mac App Store. Select iPhone & iPad Apps if offered, install Even Realities by Even Realities Ltd. (Designed for iPhone), open it and let me sign in. Stop if unavailable. Check for a verified manual export. If none exists, help me complete that test. Open Mac Collection and select Schedule Collection. Refresh and read back the next scheduled check and its local time. Explain the unlocked and idle conditions and where to stop the schedule. Report future checks as scheduled until the app records an actual run. Keep the existing archives and ChatGPT connection settings intact.
```

- If you already use an earlier version, install the new app and choose **Mac Collection → Set Up This Mac** to update the collector.
- Select **Schedule Collection**, then **Refresh** to see the next check. Under **Show Collection Options**, choose **Stop Schedule** whenever you want to turn it off.
- Collection windows start at **5:15 a.m., 8:15 a.m., 12:15 p.m., 6:15 p.m. and 11:15 p.m.** local time. The late window ends at **12:15 a.m.** the following day.
- Leave the Mac awake, signed in and unlocked. It checks every ten minutes for up to an hour and exports when you’ve been idle for two minutes. If the whole window is missed, it tries at the next one.
- Ready to ask about your readings without attaching a file? The next guide connects the Mac to your own ChatGPT account. [Connect ChatGPT](chatgpt.md)
