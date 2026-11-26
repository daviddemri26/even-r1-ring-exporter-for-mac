# Test Even R1 Ring Exporter for Mac on another Mac

This test checks whether someone with an R1 ring can follow the guides on their own Mac and get the same readings in their ChatGPT account as they see in Even.

1. **Record the setup.** Note the Mac model, macOS version, Even version and interface language. Find a recorded night on the iPhone and compare its wake-up date and duration with Even on the Mac.
2. **Install from scratch.** Download the DMG and follow the [Mac installation guide](installation.md). Note any step where you needed help, including Apple’s Command Line Tools or Accessibility permissions.
3. **Run two exports.** Test an export, then repeat it while the source data is unchanged. Check that the overnight duration stays the same. A new user with no recorded nights should also be able to start collection and understand its status.
4. **Check scheduled collection.** Use the Mac during a scheduled check, then leave it idle and unlocked during that collection window. Check the recorded status and whether the ZIP dialog closes. Wear the ring on two consecutive nights and compare each new wake-up date with the iPhone.
5. **Ask ChatGPT.** Connect the tester’s own workspace through their own tunnel. Start a fresh chat, select **Even R1 Ring Data for ChatGPT** and ask about the last seven wake-up dates. Ask for one card’s value and its age. Compare the answers with Even without attaching any files.
6. **Stop the services.** Stop the schedule and the tunnel independently and check their status on the Mac. [Data access and removal](privacy.md)

A useful report gives the step, expected behavior, observed behavior and versions tested. For personal readings, report “matches,” “missing” or “different.” Keep exact health values, exports and API keys private.

## What still needs testing

- Complete this workflow on a second Mac and Even account. Record the versions and interface languages actually verified.
- Test Apple Developer ID signing and notarization to simplify first launch. Use installation feedback to decide whether the app should bundle Python.
- Check readability, navigation and exit on physical G2 glasses with the R1. Prepare listing images before deciding whether to submit the companion to Even Hub. [Even’s submission process](https://hub.evenrealities.com/docs/ship/app-submission)
