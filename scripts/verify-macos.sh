#!/bin/bash
# Verify the read-only disk image with synthetic data and a temporary user folder.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
image="${1:-"$root/dist/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.5-arm64.dmg"}"
image_dir=$(cd "$(dirname "$image")" && pwd)
image="$image_dir/$(basename "$image")"
mount_dir=$(mktemp -d "${TMPDIR:-/tmp}/even-r1-ring-exporter-mount.XXXXXXXX")
mounted=0
cleanup() {
    if [ "$mounted" -eq 1 ]; then /usr/bin/hdiutil detach -quiet "$mount_dir"; fi
    rmdir "$mount_dir"
}
trap cleanup EXIT
(cd "$image_dir"; /usr/bin/shasum -a 256 -c "$(basename "$image").sha256")
/usr/bin/hdiutil verify -quiet "$image"
/usr/bin/hdiutil attach -quiet -readonly -nobrowse -mountpoint "$mount_dir" "$image"
mounted=1
product="Even R1 Ring Exporter for Mac"
collector="Even R1 Ring Collector for Mac"
app="$mount_dir/$product.app"
runtime="$app/Contents/Resources/runtime"
native="$runtime/Export.workflow/Contents/Resources"
app_info="$app/Contents/Info.plist"
collector_info="$native/$collector.app/Contents/Info.plist"
test "$(/usr/bin/plutil -extract CFBundleDisplayName raw -o - "$app_info")" = "$product"
test "$(/usr/bin/plutil -extract CFBundleExecutable raw -o - "$app_info")" = "$product"
test "$(/usr/bin/plutil -extract CFBundleDisplayName raw -o - "$collector_info")" = "$collector"
test "$(/usr/bin/plutil -extract CFBundleIdentifier raw -o - "$app_info")" = "local.r1bridge.app"
test "$(/usr/bin/plutil -extract CFBundleIdentifier raw -o - "$collector_info")" = "local.r1bridge.exporter"
for script in "$root/macos/runtime/"*.py; do cmp "$script" "$runtime/${script##*/}"; done
cmp "$root/integration/Connect Even R1 Ring to ChatGPT.command" "$mount_dir/Connect Even R1 Ring to ChatGPT.command"
/usr/bin/codesign --verify --strict --deep "$app"
/usr/bin/codesign --verify --strict "$native/Even R1 Ring Collector for Mac.app"
/usr/bin/codesign --verify --strict "$native/even_cards"
for binary in "$app/Contents/MacOS/Even R1 Ring Exporter for Mac" "$native/even_cards" "$native/Even R1 Ring Collector for Mac.app/Contents/MacOS/EvenR1Export"; do
    /usr/bin/lipo "$binary" -verify_arch arm64
    if ! /usr/bin/strings -a "$binary" | /usr/bin/awk 'index($0, "/Users/") { found = 1 } END { exit found ? 1 : 0 }'; then
        echo 'An executable contains a user-specific build path.' >&2
        exit 1
    fi
done
"$native/even_cards" --self-test
"$native/Even R1 Ring Collector for Mac.app/Contents/MacOS/EvenR1Export" --self-test
cmp "$mount_dir/Connect Even R1 Ring to ChatGPT.command" "$app/Contents/Resources/Connect Even R1 Ring to ChatGPT.command"
"$app/Contents/MacOS/Even R1 Ring Exporter for Mac" --verify-install
