#!/bin/bash
# Create a local archive. The app-store mode also exports an IPA without uploading it.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
mode=${1:-unsigned}
output=${SLEEP_SYNC_OUTPUT:-"$root/dist/iphone"}
mkdir -p "$output"
output=$(cd "$output" && pwd)
scratch=$(mktemp -d "${TMPDIR:-/tmp}/sleep-sync-archive.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
options=(-project ios/SleepSync.xcodeproj -scheme SleepSync -configuration Release
    -destination generic/platform=iOS -derivedDataPath "$scratch/derived")
case "$mode" in
    unsigned)
        archive="$output/SleepSync-unsigned.xcarchive"
        xcodebuild "${options[@]}" -archivePath "$archive" CODE_SIGNING_ALLOWED=NO archive -quiet
        ;;
    app-store)
        team=${2:?Pass your ten-character Apple Developer team ID as the second argument}
        [[ "$team" =~ ^[A-Z0-9]{10}$ ]] || { echo 'Invalid Apple Developer team ID.' >&2; exit 2; }
        archive="$output/SleepSync.xcarchive"
        xcodebuild "${options[@]}" -archivePath "$archive" -allowProvisioningUpdates DEVELOPMENT_TEAM="$team" archive -quiet
        /usr/bin/plutil -create xml1 "$scratch/export.plist"
        /usr/bin/plutil -insert method -string app-store-connect "$scratch/export.plist"
        /usr/bin/plutil -insert destination -string export "$scratch/export.plist"
        /usr/bin/plutil -insert teamID -string "$team" "$scratch/export.plist"
        /usr/bin/plutil -insert signingStyle -string automatic "$scratch/export.plist"
        /usr/bin/plutil -insert manageAppVersionAndBuildNumber -bool NO "$scratch/export.plist"
        xcodebuild -exportArchive -archivePath "$archive" -exportOptionsPlist "$scratch/export.plist" \
            -exportPath "$output/export" -allowProvisioningUpdates -quiet
        ;;
    *) echo 'Usage: build-iphone.sh unsigned | app-store TEAM_ID' >&2; exit 2 ;;
esac
app="$archive/Products/Applications/SleepSync.app"
test -x "$app/SleepSync"
test -s "$app/Assets.car"
test -s "$app/PrivacyInfo.xcprivacy"
/usr/bin/plutil -lint "$app/Info.plist" >/dev/null
test "$(/usr/bin/plutil -extract CFBundleIdentifier raw -o - "$app/Info.plist")" = "io.github.daviddemri26.sleepsync"
if [ "$mode" = "app-store" ]; then
    /usr/bin/codesign --verify --strict "$app"
    test -n "$(find "$output/export" -name '*.ipa' -type f -print -quit)"
fi
echo "$archive"
