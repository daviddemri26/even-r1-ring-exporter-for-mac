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

- The schedule checks at **8:15 a.m., 12:15 p.m. and 6:15 p.m.** local time. Note whether an active session defers the export and whether the ZIP dialog closes after the idle export.
- Wear the ring overnight and sync it to Even on your iPhone after waking. Repeat the next night. Confirm each night appears on the Mac after it appears on the phone.
- A repeat export of the first night does not verify the second night.

## Test a private ChatGPT query and record the result

```codex-prompt
Help me test the optional Even R1 Ring Data for ChatGPT connection using https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/. Use my own private ChatGPT workspace. Guide me through a fresh chat with the connector selected and no attachments. Ask for sleep over seven local wake dates, then one available health card and its age. I will compare results privately with Even. Draft a short test report here with versions, language, step, expected behavior and pass, missing or different. Omit values and identifiers. At the end, offer to stop services started for this test.
```

- If you only want to test the Mac app, skip the connector. The export tests still count.
- Keep results in your private chat. In a public report, include the failing step and a redacted error. Leave out ZIPs, exact readings, keys, tunnel identifiers and screenshots of readings.
- Check that the schedule and tunnel can stop independently. Preserve any service you already used before testing. [Pausing or removing the app](privacy.md)

The alpha still needs feedback on second-device setup, Python installation and first launch. Developer ID signing and notarization are separate release work. Physical G2 gesture tests and listing images are also pending. [Optional glasses tests](../evenhub/README.md)
