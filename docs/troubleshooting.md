# Troubleshoot a missing reading

Start with one reading you recognize. For sleep, use the local date when you woke up. Follow that date from the iPhone to the Mac, then to ChatGPT.

## The night is missing on the iPhone

- Open **Even → Health** on the iPhone paired with your ring.
- Check whether you wore the R1 that night. In Health settings, check **Health tracking**.
- Let the ring sync with Even. Look for the same wake date again.
- If Even still has no session, the exporter has no duration for that date. [Even’s guide to missing readings](https://support.evenrealities.com/hc/en-us/articles/17144131645327-Detected-Health-Data-Is-Missing)

## The night is on the iPhone but missing on the Mac

- Check that Even is signed into the same account on both devices.
- In Even’s Health settings, check **Cloud processing & backup**. This workflow uses Even’s cloud to sync between devices. [How Even backup works](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- Open **Health** in Even on the Mac. When the night appears, open **Even R1 Ring Exporter for Mac**.
- Select **Mac Collection → Test an Export**, then **Refresh**. Check the result of the last attempt and the latest recorded wake date.

## The scheduled export did not run

- Check that you selected **Schedule Collection** in the Mac app.
- The Mac checks every ten minutes for an hour starting at 8:15 a.m., 12:15 p.m. and 6:15 p.m. local time.
- Leave the Mac awake and unlocked. An export can start after two minutes without keyboard or mouse input.
- If the Mac stays busy throughout the hour, collection waits for the next window. Select **Test an Export** to collect now.

## The Mac shows a permission error or a ZIP window

- For `ACCESSIBILITY`, select **Show Collector** in the exporter. Open **Accessibility Settings** and enable **Even R1 Ring Collector for Mac**.
- After an app update, macOS can still list the old helper. If the switch is on and the error persists, replace the entry with the helper revealed by **Show Collector**. [Installation steps](installation.md)
- For `APP_DATA_PERMISSION`, the collector needs permission to read the ZIP that Even creates. Allow that request for the collector and repeat **Test an Export**.
- If a Save window stays open for `Even_health_data_…zip`, select **Cancel** in that window. The collector reads Even’s cached copy.
- Return to **Mac Collection → Refresh** and check the last attempt. An export can succeed without adding a new night.

## The Mac has the reading but ChatGPT cannot find it

1. Keep the Mac awake and online. Open **ChatGPT Connection** in the exporter and select **Refresh**. Look for confirmation that the tunnel connected to OpenAI.
2. In ChatGPT, open the connected **Even R1 Ring Data for ChatGPT** plugin. Select **Try in chat** and ask about the same wake date. [Try a dated question](ask-about-readings.md)
3. For **HTTP 401**, OpenAI rejected the key. Use **ChatGPT Connection → Update Key…** to enter the complete key at the hidden prompt.
4. For **HTTP 403**, check the OpenAI organization and project that own the tunnel. Check the key’s **Tunnels Read** and **Use** permissions and the tunnel’s association with your ChatGPT workspace. [Connection setup](chatgpt.md)
5. After upgrading, refresh or reconnect the plugin if it still shows older tool names.

For a support report, include the app version, macOS version, Even version and the error code. Omit your key, ZIP and personal readings. [Data and privacy](privacy.md)
