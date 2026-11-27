#!/bin/bash
# Build the arm64 release from project sources in a temporary directory.
set -euo pipefail
umask 022
root=$(cd "$(dirname "$0")/.." && pwd)
output="${1:-"$root/dist"}"
mkdir -p "$output"
output=$(cd "$output" && pwd)
build=$(mktemp -d "${TMPDIR:-/tmp}/even-r1-ring-exporter-build.XXXXXXXX")
trap 'rm -rf "$build"' EXIT
name='Even R1 Ring Exporter for Mac'
dmg_name='Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.8-arm64.dmg'
app="$build/image/$name.app"
resources="$app/Contents/Resources"
source_runtime="$root/macos/runtime"
runtime="$resources/runtime"
flow='Export.workflow/Contents'
helper='Even R1 Ring Collector for Mac.app'
target=arm64-apple-macos14.0
sdk=$(/usr/bin/xcrun --sdk macosx --show-sdk-path)
flags=(
    -O -sdk "$sdk" -target "$target"
    -file-prefix-map "$root=EvenR1RingExporterForMac"
    -debug-prefix-map "$root=EvenR1RingExporterForMac"
    -file-prefix-map "$build=build"
    -debug-prefix-map "$build=build"
)
identity=${MAC_SIGN_IDENTITY:--}
notary_profile=${NOTARY_PROFILE:-}
if [[ "$identity" == "developer-id" ]]; then
    identity=$(/usr/bin/security find-identity -v -p codesigning | /usr/bin/awk '/"Developer ID Application:/ {print $2}')
    if [[ ! "$identity" =~ ^[0-9A-Fa-f]{40}$ ]]; then
        echo "Set MAC_SIGN_IDENTITY to one valid Developer ID Application certificate hash." >&2
        exit 1
    fi
fi
sign_flags=(--force --sign "$identity")
if [[ "$identity" == "-" ]]; then
    [[ -z "$notary_profile" ]] || { echo "Notarization needs a Developer ID certificate." >&2; exit 1; }
    sign_flags+=(--timestamp=none)
else
    sign_flags+=(--timestamp --options runtime)
fi
mkdir -p "$app/Contents/Library/LaunchAgents" "$app/Contents/MacOS" "$runtime/$flow/Resources/$helper/Contents/MacOS" "$build/AppIcon.iconset"
cp "$root/macos/app/Info.plist" "$app/Contents/Info.plist"
install -m 644 "$root/macos/companion/local.r1bridge.iphone.plist" "$app/Contents/Library/LaunchAgents/"
install -m 755 "$root/integration/Connect Even R1 Ring to ChatGPT.command" "$resources/Connect Even R1 Ring to ChatGPT.command"
install -m 755 "$root/integration/Connect Even R1 Ring to ChatGPT.command" "$build/image/Connect Even R1 Ring to ChatGPT.command"
for script in collection r1 card_report archive_match sleep_report sleep_feed mcp_server tunnel legacy_upgrade legacy_services; do
    cp "$source_runtime/$script.py" "$runtime/"
done
cp "$source_runtime/$flow/document.wflow" "$runtime/$flow/"
cp "$source_runtime/$flow/Resources/import_export.py" "$runtime/$flow/Resources/"
cp "$source_runtime/$flow/Resources/$helper/Contents/Info.plist" "$runtime/$flow/Resources/$helper/Contents/"
native="$runtime/$flow/Resources"
swiftc_path=$(/usr/bin/xcrun --find swiftc)
cd "$root"
"$swiftc_path" "${flags[@]}" "macos/runtime/$flow/Resources/even_cards.swift" -o "$native/even_cards"
"$swiftc_path" "${flags[@]}" "macos/runtime/$flow/Resources/EvenR1Export.swift" -o "$native/$helper/Contents/MacOS/EvenR1Export"
"$swiftc_path" "${flags[@]}" "macos/app/main.swift" macos/companion/*.swift companion/Wire.swift -o "$app/Contents/MacOS/$name"
/usr/bin/xcrun --sdk macosx swift macos/app/icon.swift site/dist/assets/even-r1-ring-icon.png "$build/AppIcon.iconset"
/usr/bin/iconutil -c icns "$build/AppIcon.iconset" -o "$resources/AppIcon.icns"
mkdir -p "$native/$helper/Contents/Resources"
cp "$resources/AppIcon.icns" "$native/$helper/Contents/Resources/AppIcon.icns"
/usr/bin/codesign "${sign_flags[@]}" "$native/even_cards"
/usr/bin/codesign "${sign_flags[@]}" "$native/$helper"
(
    cd "$runtime"
    export LC_ALL=C
    /usr/bin/find . -type f | /usr/bin/sort | while IFS= read -r file; do
        /usr/bin/shasum -a 256 "$file"
    done
) | /usr/bin/shasum -a 256 | /usr/bin/cut -d ' ' -f 1 > "$resources/runtime.sha256"
/usr/bin/codesign "${sign_flags[@]}" "$app"
/usr/bin/codesign --verify --deep --strict "$app"
/usr/bin/codesign --verify --strict "$native/$helper"
/usr/bin/plutil -lint "$app/Contents/Info.plist" "$native/$helper/Contents/Info.plist" >/dev/null
ln -s /Applications "$build/image/Applications"
/usr/bin/hdiutil create -quiet -volname "$name" -format UDZO -srcfolder "$build/image" "$build/$dmg_name"
if [[ "$identity" != "-" ]]; then
    /usr/bin/codesign --force --sign "$identity" --timestamp "$build/$dmg_name"
fi
if [[ -n "$notary_profile" ]]; then
    /usr/bin/xcrun notarytool submit "$build/$dmg_name" --keychain-profile "$notary_profile" --wait
    /usr/bin/xcrun stapler staple "$build/$dmg_name"
    /usr/bin/xcrun stapler validate "$build/$dmg_name"
fi
/usr/bin/hdiutil verify -quiet "$build/$dmg_name"
mv -f "$build/$dmg_name" "$output/$dmg_name"
(cd "$output"; /usr/bin/shasum -a 256 "$dmg_name" > "$dmg_name.sha256")
echo "$output/$dmg_name"
