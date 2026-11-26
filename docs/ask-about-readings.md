# Ask ChatGPT about your ring readings

Use **Even R1 Ring Data for ChatGPT** to read the latest verified export on your Mac. You can leave the ZIP in its archive folder.

## Ask about seven nights

1. Open **Even R1 Ring Exporter for Mac**. In **Mac Collection**, select **Refresh**. Check the latest recorded wake date.
2. Pick seven consecutive local wake dates that include a night you recognize. The example below uses November 16 through November 22, 2026.
3. Keep your Mac awake and online. In ChatGPT on the web, open the connected **Even R1 Ring Data for ChatGPT** plugin and choose **Try in chat**. [Connect the plugin](chatgpt.md)
4. Send this message without adding an attachment.

```text
Use Even R1 Ring Data for ChatGPT. For each wake date from November 16 through November 22, 2026 inclusive, list my recorded sleep in hours and minutes. Mark dates without a session. If you calculate an average, give the number of usable dates.
```

5. Compare one result with **Health** in Even on your iPhone. Match the date you woke up. To check for a new night, ask for the dates after the last one you recognized.

## Read the sleep results

- A day’s total includes distinct recorded sleep sessions ending on that date, including naps.
- A missing date means the export has no sleep session for that wake date. Sleeping without wearing the ring can leave a gap.
- A `null` duration means the records were inconsistent or ambiguous. Exclude missing and ambiguous dates from averages.
- For stages, ask “For the wake date November 22, how many minutes did Even record as awake, light, deep and REM?” Awake time covers the recorded sessions.
- One query can cover up to 31 local wake dates. [Troubleshoot a missing night](troubleshooting.md)

## Ask about the six latest readings

Send this follow-up in the same chat.

```text
List my latest steps, active calories, heart rate, heart rate variability, blood oxygen saturation and skin temperature variation. Include the unit, how old each reading was when observed, and when my Mac observed it.
```

- **Steps and active calories** can be partial daily totals. Adding successive card values can count activity twice.
- **Heart rate** is shown in beats per minute. **Heart rate variability** is shown in milliseconds.
- **Blood oxygen saturation** is shown as a percentage. **Skin temperature variation** is a temperature change. Keep the unit Even displayed.
- Read each card’s age alongside its observation time. A card labelled “3 days ago” was already three days old when the Mac saw it.
- To check changes, ask “Which readings changed between November 16 and November 22?” Local history starts when the Mac first observes a value. An unchanged card does not create another entry.
