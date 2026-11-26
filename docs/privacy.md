# Where your readings go

Each person sets up their own Mac and decides whether to connect it to their ChatGPT account.

- **Even.** The tested workflow uses Even’s cloud backup so the Mac can see readings from the iPhone. Even controls this setting in its app. [Even’s health data backup guide](https://support.evenrealities.com/hc/en-us/articles/17995940335119-Manage-Health-Data-Cloud-Processing-and-Backup)
- **Your Mac.** The collector operates Even’s export controls and reads the ZIP that Even creates. It saves archives, collection status and observed cards under `~/Library/Application Support/R1 Bridge/`. The ZIP files contain personal data. A backup of this folder will include it.
- **ChatGPT.** If you enable the tunnel, anyone authorized to use your connector can request results from its four read-only tools. Keep the connection in your own workspace. The readings returned to ChatGPT become part of that conversation. The dedicated API key is saved in the Mac’s Keychain.
- **Website and glasses.** The public website contains instructions and sample questions. The optional G2 app displays five bundled text cards. Both can be used without providing personal readings.

## Stop collection or uninstall

1. In **Mac Collection**, choose **Stop Schedule**. If you enabled the tunnel, you can also choose **Stop Tunnel** in **ChatGPT Connection**. The archives remain available on your Mac.
2. To remove remote access, disconnect the plugin in ChatGPT, revoke the dedicated key and remove the tunnel association on OpenAI Platform. The password item in Keychain is named **R1 Bridge - OpenAI Tunnel**.
3. To uninstall, quit R1 Bridge, move the app to the Trash and remove **R1 Bridge Collector** from **Privacy & Security → Accessibility** in System Settings. Keep or back up any exports you want before deleting the `R1 Bridge` folder in your user Library. Backups, Even’s cloud data and ChatGPT conversations each have their own deletion controls.

You can also stop the two services from Terminal.

```sh
runtime="$HOME/Library/Application Support/R1 Bridge"
/usr/bin/python3 -B "$runtime/r1.py" stop
/usr/bin/python3 -B "$runtime/tunnel.py" stop
```

For a bug report, include the R1 Bridge, Even and macOS versions, the interface language, the step that failed and a redacted error message. Keep ZIP files, keys, tunnel identifiers and screenshots of your readings out of public reports.
