# Sleep Sync Companion · App Store release materials

## Product page

- **Name** — Sleep Sync Companion
- **Subtitle** — Ring sleep from Mac to Health
- **Price and category** — Free · Health & Fitness
- **Platform and language** — iPhone · iOS 17 or later · English
- **Bundle identifier** — `io.github.daviddemri26.sleepsync`
- **Keywords** — stages,nap,night,REM,deep,light,awake,wearable,import,local,automation
- **Support URL** — [Companion support](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/#support)
- **Privacy policy URL** — [Companion privacy](https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/#privacy)
- **Screenshots in listing order** — [Pair your Mac](screenshots/setup.png), [Up to date](screenshots/connected.png), [Waiting for Mac](screenshots/waiting.png)

### Description

Bring the sleep recorded by your Even R1 ring into Apple Health. Sleep Sync Companion works with Even R1 Ring Exporter for Mac. You need an iPhone running iOS 17 or later and an Apple silicon Mac running macOS 14 or later with a pairing-enabled exporter.

Scan the code on your Mac and allow the app to write Sleep. The first sync brings across verified sleep history, including naps. Open Sleep in Apple Health to see when you were awake or in REM, Core or Deep sleep.

Your Mac holds new nights while you’re away. The app checks when you open it on the same local network and when iOS schedules background refresh. Add the Sync Sleep action to a Shortcuts automation for a morning or home Wi-Fi check.

Sleep goes directly from your Mac to your iPhone over an encrypted connection. You control pairing and Apple Health access. Sleep Sync Companion is free and independent of Even Realities and Apple.

## App privacy in App Store Connect

Select **Data Not Collected** for this build. Pairing, the sync cursor and sleep samples are processed on devices controlled by the user. The app sends no data to the developer or third-party SDKs and implements no tracking. It requests camera and local-network access for pairing and permission to write the Sleep category. Existing Apple Health data is outside the app’s requested read permissions. [Apple’s app privacy definitions](https://developer.apple.com/app-store/app-privacy-details/)

The separate Mac exporter can use Even’s backup or an optional private ChatGPT connection. Users control Apple Health’s iCloud sync and their own Mac backup. Support and privacy links open the project’s GitHub Pages website. Recheck the privacy answers against the actual candidate and published policy at submission.

## Notes for App Review

Sleep Sync Companion transfers sleep from the paired Mac exporter to Apple Health. The iPhone app requires no developer account or sign-in. A live transfer requires a reachable Mac with a verified Even R1 sleep export. Attach a physical-device pairing video filmed using the steps below. The app uses Apple frameworks for device discovery, encryption and HealthKit access.

1. For an on-device preview, open the app and tap the ellipsis button, **Connection and help**, then **Try a Preview**. The summary shows an invented Mac, last sync and latest night.
2. Open **Connection and help → Show Waiting for Mac** to preview the offline state. Choose **End Preview** to return to pairing. This walkthrough keeps invented samples out of Health.
3. For full pairing and import, use the hardware and isolated account described below. Open **Mac Collection → Pair iPhone** on the Mac and **Scan Mac Code** on the phone. Allow camera, local network and Sleep write access. After import, open the Sleep category in Apple Health to inspect the source and stages.

## Verification to date

The iOS 26.5 simulator accepted the production writer’s Sleep-only permission request. Saving an invented four-stage night twice, then its two-stage correction twice, left the two corrected samples with the expected timestamps in HealthKit. The encrypted transport check also passed with a synthetic archive containing an overnight session and a nap.

A physical iPhone paired with the Mac, imported sleep into Apple Health and advanced its sync position. With separate permission to read Sleep, ChatGPT Health returned stage entries attributed to Sleep Sync Companion. The review video and the additional scenarios below remain separate checks.

## Physical-device test and review video

Use a dedicated iPhone with a test Health store and a fresh disposable macOS user account on the same local network. The camera should show the physical iPhone interacting with the Mac. Keep the pairing code out of the recorded frame or obscure it before sharing. The fixture contains only invented observations. [Apple’s hardware review instructions](https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review/)

1. Install the iPhone Release candidate and a matching Mac release in Applications. The Mac needs **Pair iPhone**, introduced in alpha 8. From the project root, prepare the initial fixture in the disposable Mac account. The script refuses an existing collection.

   ```sh
   demo_folder="$HOME/Library/Application Support/R1 Bridge"
   /usr/bin/python3 -B docs/companion/create-review-fixture.py "$demo_folder"
   ```

2. Film the Mac opening **Pair iPhone**, then the iPhone scanning the code and granting local-network and Sleep permissions. Film the phone’s paired status and successful first import.
3. Open Sleep in Apple Health and select entries from Sleep Sync Companion. The invented session starts at 11:00 p.m. on November 14, 2026 at UTC−08:00 and ends eight hours later. The sequence is Core, Deep, REM, Awake, Core, REM, Core. A separate 30-minute nap begins at 2:00 p.m. on November 15. Use the fixture’s time zone for comparisons.
4. Tap **Sync Now** twice. Confirm the same source entries appear once. Take the phone off the local network, sync, and film **Waiting for Mac**. In the same test Mac account, add the reserved second night.

   ```sh
   /usr/bin/python3 -B docs/companion/create-review-fixture.py "$demo_folder" --add-night
   ```

5. Rejoin the network and reopen the app. Confirm **Latest night** advances to November 16 and its seven intervals appear once. Show or test **Sync Sleep** from Shortcuts. Record iOS-scheduled background refresh separately if observed.
6. Verify denial and recovery for local-network and Sleep permissions, revocation on the Mac and reconnection using a fresh code. Privately compare the chronology of a genuine export against its Even sleep chart before shipping. Keep personal readings, accounts and clips out of the review package.
7. Record the iPhone model, OS versions, app builds and pass/fail results. Attach the physical-device video to App Review. The simulator screenshots illustrate the UI only.

## Submission handoff

The U.S. public catalog returned no exact title match on November 27, 2026. Before uploading, confirm the name when creating the English app record in the publisher’s App Store Connect account and use the project’s original companion icon. List Even R1 compatibility in the description. Use the publisher’s verified contact details in App Review’s private contact fields. Answer the age-rating and export-compliance questionnaires for the signed candidate, including its use of encryption built into Apple’s OS frameworks.

Publish the matching Mac download and the companion support and privacy page before submitting. Open both URLs from a clean device, verify the Mac download matches the released checksum, and attach the review video. The existing alpha 7 public Mac download predates pairing.
