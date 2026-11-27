#!/bin/bash
# Verify the read-only disk image with synthetic data and a temporary user folder.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
image="${1:-"$root/dist/Even-R1-Ring-Exporter-for-Mac-0.1.0-alpha.6-arm64.dmg"}"
image_dir=$(cd "$(dirname "$image")" && pwd)
image="$image_dir/$(basename "$image")"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/even-r1-ring-exporter-verify.XXXXXXXX")
mount_dir="$scratch/mount"
mkdir "$mount_dir"
mounted=0
cleanup() {
    if [ "$mounted" -eq 1 ]; then
        /usr/bin/hdiutil detach -quiet "$mount_dir" || return 1
    fi
    rm -rf "$scratch"
}
trap cleanup EXIT
# Check the selected image even when the sidecar was copied from another release.
read -r expected_digest _ < "$image.sha256"
actual_digest=$(/usr/bin/shasum -a 256 < "$image")
if [[ ! "$expected_digest" =~ ^[[:xdigit:]]{64}$ ]] ||
    [[ "$(echo "$expected_digest" | /usr/bin/tr A-F a-f)" != "${actual_digest%% *}" ]]; then
    echo "SHA-256 mismatch for $(basename "$image")." >&2
    exit 1
fi
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
for info in "$app_info" "$collector_info"; do
    test "$(/usr/bin/plutil -extract CFBundleIconFile raw -o - "$info")" = "AppIcon"
done
cmp "$app/Contents/Resources/AppIcon.icns" "$native/$collector.app/Contents/Resources/AppIcon.icns"
/usr/bin/iconutil -c iconset "$app/Contents/Resources/AppIcon.icns" -o "$scratch/packaged.iconset"
mkdir "$scratch/expected.iconset"
/usr/bin/xcrun --sdk macosx swift "$root/macos/app/icon.swift" "$root/site/dist/assets/even-r1-ring-icon.png" "$scratch/expected.iconset"
for points in 16 32 128 256 512; do
    for scale in 1 2; do
        suffix=""
        if [ "$scale" -eq 2 ]; then suffix="@2x"; fi
        name="icon_${points}x${points}${suffix}.png"
        # Decode the artwork in both images. Legacy ICNS slots encode translucent tile corners differently.
        mark_size=$((points * scale * 24 / 32))
        for kind in packaged expected; do
            /usr/bin/sips -s format bmp --cropToHeightWidth "$mark_size" "$mark_size" \
                "$scratch/$kind.iconset/$name" --out "$scratch/$kind.bmp" >/dev/null
        done
        cmp "$scratch/expected.bmp" "$scratch/packaged.bmp"
    done
done
for script in "$root/macos/runtime/"*.py; do cmp "$script" "$runtime/${script##*/}"; done
workflow='Export.workflow/Contents'
cmp "$root/macos/runtime/$workflow/document.wflow" "$runtime/$workflow/document.wflow"
cmp "$root/macos/runtime/$workflow/Resources/import_export.py" "$native/import_export.py"
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
