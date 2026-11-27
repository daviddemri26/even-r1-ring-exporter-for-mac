# Ask ChatGPT about your ring readings

For the private Mac connector, keep your Mac awake and online. Open **Even R1 Ring Data for ChatGPT → Try in chat** in your personal ChatGPT web workspace. You can paste the connector prompts below into Codex on your Mac for help, or type the short questions directly in that web chat. [Connect your Mac to ChatGPT](chatgpt.md)

## Which ring nights can ChatGPT Health see?

After the iPhone companion shows **Up to date**, open **Health** in the ChatGPT iPhone app. If Health is available for your account, connect **Apple Health**, allow ChatGPT to read **Sleep**, and let it sync. You can check progress in **Health → ••• → Apple Health**. [OpenAI’s Health guide](https://help.openai.com/en/articles/20001036-health-in-chatgpt)

Ask “Which wake dates have sleep from Sleep Sync Companion in my Apple Health data? Show nights and naps separately where possible.” Naming the source helps identify your ring’s records if an Apple Watch or another app also contributes sleep. For a particular night, ask for time in **Awake, Core, Deep and REM**. Apple Health uses **Core** for the ring’s light sleep. [Pair the iPhone companion](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/#apple-health)

## How much did I sleep each night?

```codex-prompt
Use the private Even R1 Ring Data for ChatGPT connector in my personal ChatGPT web account. Ask it to call sleep_durations for the seven local wake dates ending today, without a file attachment. List all seven dates and each duration in hours and minutes. Label a missing session or an ambiguous duration explicitly. Average only usable dates and give their count. If I give you a previous wake date, check whether the export contains a later one through today, using separate requests of up to 31 dates if needed. Confirm that the result came from the web connector. If it is unavailable, identify the connection problem instead of guessing a duration.
```

- In ChatGPT, ask “How much did I sleep on each of the last seven wake dates? Has a new night appeared since [date]?”
- Match the date you woke up with **Health** in Even on your iPhone. Naps count toward the date they ended.
- A missing date means Even supplied no session. A `null` duration means the data was ambiguous. Both are excluded from the average. [Check a missing night](troubleshooting.md)

## How much time did I spend in each sleep stage?

```codex-prompt
In my personal ChatGPT web account, use the private Even R1 Ring Data for ChatGPT connector without an attachment. Ask which wake date I want if I did not supply one. Call sleep_stages for that local date and report the recorded minutes awake, in light sleep, in deep sleep and in REM. Identify any missing session or ambiguous result. Do not estimate missing values. Help me compare the answer with the same wake date in Even on my iPhone.
```

- In ChatGPT, ask “For [wake date], how many minutes were awake, light, deep and REM?”
- Awake minutes cover the recorded sessions. You can ask about up to 31 local wake dates in one request.

## What are my latest readings and what changed?

```codex-prompt
Use Even R1 Ring Data for ChatGPT in my personal ChatGPT web account without attaching a file. Call latest_readings for steps, active calories, heart rate, heart rate variability, blood oxygen saturation and skin temperature variation. Give each card’s value, unit, displayed age and the time my Mac observed it when available. If I ask what changed, call reading_history for my requested dates and report the changes the Mac actually observed. Distinguish a Mac observation from a sensor measurement time. Keep successive step and calorie totals separate, and mark unavailable readings or dates clearly.
```

- In ChatGPT, ask “Show my six latest readings, with units and freshness.” Then try “Which readings changed between [start date] and [end date]?”
- Steps and active calories may be running daily totals. Adding consecutive cards can count the same activity twice.
- Heart rate uses beats per minute, heart rate variability uses milliseconds, and blood oxygen saturation uses percent. Skin temperature variation is a change in the unit Even displays.
- A card showing “3 days ago” was already that old when the Mac saw it. History starts when the Mac first observes a card and records changes to its value or unit.
