#!/bin/bash
# Verify the read-only disk image with synthetic data and a temporary user folder.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
image="${1:-"$root/dist/R1-Bridge-0.1.0-alpha.3-macOS-arm64.dmg"}"
image_dir=$(cd "$(dirname "$image")" && pwd)
image="$image_dir/$(basename "$image")"
mount_dir=$(mktemp -d "${TMPDIR:-/tmp}/r1-bridge-mount.XXXXXXXX")
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
app="$mount_dir/R1 Bridge.app"
runtime="$app/Contents/Resources/runtime"
native="$runtime/Export.workflow/Contents/Resources"
for script in "$root/macos/runtime/"*.py; do cmp "$script" "$runtime/${script##*/}"; done
cmp "$root/integration/Connect ChatGPT.command" "$mount_dir/Connect ChatGPT.command"
/usr/bin/codesign --verify --strict --deep "$app"
/usr/bin/codesign --verify --strict "$native/R1 Bridge Collector.app"
/usr/bin/codesign --verify --strict "$native/even_cards"
for binary in "$app/Contents/MacOS/R1 Bridge" "$native/even_cards" "$native/R1 Bridge Collector.app/Contents/MacOS/EvenR1Export"; do
    /usr/bin/lipo "$binary" -verify_arch arm64
    if ! /usr/bin/strings -a "$binary" | /usr/bin/awk 'index($0, "/Users/") { found = 1 } END { exit found ? 1 : 0 }'; then
        echo 'An executable contains a user-specific build path.' >&2
        exit 1
    fi
done
"$native/even_cards" --self-test
"$native/R1 Bridge Collector.app/Contents/MacOS/EvenR1Export" --self-test
cmp "$mount_dir/Connect ChatGPT.command" "$app/Contents/Resources/Connect ChatGPT.command"
"$app/Contents/MacOS/R1 Bridge" --verify-install
