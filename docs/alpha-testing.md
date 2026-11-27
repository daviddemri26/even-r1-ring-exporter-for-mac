# Test the public alpha on a second Mac

This guide is for volunteers testing their own ring and Mac. For everyday use, start with the [Mac installation guide](installation.md).

## Check the first export

```codex-prompt
Help me test the public Even R1 Ring Exporter for Mac alpha on my own Mac. Follow https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/. Record the Mac model, macOS version, Even app version and interface language. Preserve any existing setup. Help me install the app if needed, then run Test an Export twice with unchanged source data. Check collection status for duplicate or missing sessions. I will compare one night privately on my iPhone and Mac. Record only matches, missing or different. Keep measurements, archives and screenshots out of the report.
```

- Use your own Even account on both devices. If you have a recorded night, compare its wake date and duration privately.
- Repeat the export before new data arrives. The same night should appear once with the same duration. If you have no recorded night, check that the app explains its status.
- Record which install steps needed assistance, including Apple’s Command Line Tools and Accessibility.

## Check automatic collection over two nights

```codex-prompt
Help me test scheduled exports in Even R1 Ring Exporter for Mac using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/test/. Check whether scheduling is already on. Enable it for this test if needed. Explain how to observe a check while I am working, then while the Mac is idle and unlocked. I will wear the ring for two consecutive nights and compare each wake date privately in Even. Use local status to distinguish new, unchanged, deferred and failed checks. Report pass, missing, different or pending without reading out health values. Mark future checks pending.
```

- In **Mac Collection**, select **Refresh** and note the next scheduled check. Test whether an active session defers the export and whether the ZIP dialog closes after the idle export.
- Wear the ring overnight and sync it to Even on your iPhone after waking. Repeat the next night. Confirm each night appears on the Mac after it appears on the phone.
- A repeat export of the first night does not verify the second night.

## Test a private ChatGPT query and record the result

```codex-prompt
Help me test the optional Even R1 Ring Data for ChatGPT connection using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/. Use my own private ChatGPT workspace. Guide me through a fresh chat with the connector selected and no attachments. Ask for sleep over seven local wake dates, then one available health card and its age. I will compare results privately with Even. Draft a short test report here with versions, language, step, expected behavior and pass, missing or different. Omit values and identifiers. At the end, offer to stop services started for this test.
```

- If you only want to test the Mac app, skip the connector. The export tests still count.
- Keep results in your private chat. In a public report, include the failing step and a redacted error. Leave out ZIPs, exact readings, keys, tunnel identifiers and screenshots of readings.
- Check that the schedule and tunnel can stop independently. Preserve any service you already used before testing. [Pausing or removing the app](privacy.md)

## Check iPhone sleep sync

Use the public alpha 8 disk image for your Mac. With Sleep Sync Companion installed on your iPhone, follow the [iPhone setup guide](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/). Record the outcome of each check without publishing sleep dates, values or screenshots.

- After allowing Sleep writes, check for **Up to date**. In Apple Health, open a stage entry for a known session and verify that its source is **Sleep Sync Companion**.
- Tap **Sync Now** again and confirm that the same entry appears only once for that source.
- If you also use ChatGPT Health, allow ChatGPT to read Sleep, then ask which sleep source it sees for that session. Record this result separately from the Apple Health import.

For repeatable test nights and naps, see the [synthetic device walkthrough](companion/app-store.md#physical-device-test-and-review-video). The public Mac alpha still needs independent feedback on installation and automatic collection over two nights. [Optional glasses tests](../evenhub/README.md)
