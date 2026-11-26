# Find a missing reading or fix an export

Start where you last saw the reading. For sleep, follow the date you woke up from Even on the iPhone to the Mac, then to your personal ChatGPT web chat.

## The night is missing from Even on my iPhone

```codex-prompt
Help me find out why a night is missing from my Even R1. Start with the local wake date. Guide me through Health in Even on the iPhone paired with my ring. I will check whether I wore the ring overnight, whether Health tracking was on, and whether the ring has synced. If the night is still absent on my iPhone, explain what the exporter can show for that date. Do not infer a duration or change my Mac setup. The guide is at https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/troubleshooting/.
```

- On the paired iPhone, open **Even → Health**. Check **Health tracking** and whether you wore the ring that night.
- Let the ring sync, then look for the same wake date. If Even has no session, the exporter has no duration to report. [Even’s guide to missing readings](https://support.evenrealities.com/hc/en-us/articles/17144131645327-Detected-Health-Data-Is-Missing)

## I see the night on my iPhone but not in my Mac export

```codex-prompt
Help me trace one Even R1 wake date from iPhone to Mac. Ask me for the wake date and whether it appears in Even on my iPhone. Check for the official Even Realities iPhone app on this Mac. If missing, open its Mac App Store listing at https://apps.apple.com/us/app/even-realities/id6747017725. If searching, select iPhone & iPad Apps and look for Even Realities by Even Realities Ltd., marked Designed for iPhone. Let me sign in with the Even account from my physical iPhone. If the store does not offer it for this Mac, tell me. Otherwise check the same wake date in Even on the Mac. If only the phone has it, guide me through the Cloud processing & backup choice. Let me decide whether to enable cloud backup. Once the Mac has the night, use Mac Collection → Test an Export and Refresh. Compare the recorded wake date and last-attempt status. Tell me where the reading stopped and whether a new session was actually imported. Keep my ZIP on the Mac.
```

- On the **Mac**, open the **Mac App Store** and search **iPhone & iPad Apps** for **Even Realities** by **Even Realities Ltd.** Install the version marked **Designed for iPhone** and sign in with the same Even account you use on your physical iPhone. [Open Even Realities in the App Store](https://apps.apple.com/us/app/even-realities/id6747017725)
- On the iPhone, open Even. Under **Health → Settings**, **Cloud processing & backup** lets Even sync across devices. [How Even backup works](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- Once the night appears in **Even → Health** on the Mac, choose **Mac Collection → Test an Export** in the exporter. Select **Refresh** and check the latest wake date.

## My scheduled export did not run

```codex-prompt
Check scheduled collection in Even R1 Ring Exporter for Mac. Read the collection status on this Mac, including the last attempt, whether scheduling is enabled, and the next collection window if available. Explain any idle, unlock, or timing condition that fits the evidence. If collection is due and the session is unlocked, run one Test an Export, refresh the result and report whether it succeeded and whether any new sleep date appeared. Keep my existing schedule and tunnel settings unless I ask to change them.
```

- Open **Mac Collection** and check **Schedule Collection**. The three one-hour windows begin at **8:15 a.m., 12:15 p.m. and 6:15 p.m.** local time.
- The Mac checks every ten minutes. Leave it awake and unlocked with two minutes of keyboard and mouse inactivity.
- If the whole window was busy, the collector waits for the next one. Choose **Test an Export** to collect now.

## I see a permission error or a ZIP Save window

```codex-prompt
Help me clear the specific Even R1 export problem on this Mac. Check the last attempt in Mac Collection. For ACCESSIBILITY, reveal the current collector with Show Collector and guide me through enabling that exact helper in Accessibility Settings. For APP_DATA_PERMISSION, let me approve the collector’s request to read Even’s cached export. If a Save dialog is open, dismiss only an identifiable Even_health_data_…zip export dialog. Leave unrelated prompts for me. Test one export, refresh the status and report the result, including a successful export with no new night. Preserve my archives.
```

- **ACCESSIBILITY** — Choose **Show Collector**, then **Accessibility Settings**. Enable **Even R1 Ring Collector for Mac**. If an old entry persists after an update, replace it with the helper revealed by **Show Collector**. [Mac setup guide](installation.md)
- **APP_DATA_PERMISSION** — Allow the collector to read Even’s cached ZIP when macOS asks. Repeat **Test an Export**.
- **Save window** — For `Even_health_data_…zip`, select **Cancel**. The collector reads the cached copy. Check **Mac Collection → Refresh** for the outcome.

## The Mac has the reading but ChatGPT cannot find it

```codex-prompt
Diagnose a reading that exists in my Even R1 Mac export but is missing from my personal ChatGPT web chat. With my Mac awake and online, check the local export date and private tunnel status. Use https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/ for the error reported. Check that the personal workspace has the correct connector and refresh or reconnect it if its tool names are outdated. Use Try in chat to query the same date without an attachment. Report the web result separately from local checks. If I need support, prepare a short summary using only versions, interface language and the error code. Keep readings, ZIPs, keys and tunnel IDs private.
```

- Open **ChatGPT Connection → Refresh**. **HTTP 401** means the key was rejected. Choose **Update Key…** and enter it at the hidden prompt. For **HTTP 403**, check the organization, project, tunnel permissions and workspace association. [Fix the private connection](chatgpt.md)
- In your personal ChatGPT workspace, open **Even R1 Ring Data for ChatGPT → Try in chat**. Ask for the same wake date. Older plugins may need a refresh or reconnection after an upgrade. [Try a dated question](ask-about-readings.md)
- For support, share your macOS, Even and exporter versions, interface language and the error code. Keep your API key, tunnel ID, ZIP and personal readings private. [Data and privacy](privacy.md)
