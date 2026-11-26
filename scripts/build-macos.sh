#!/bin/bash
# Produit l’alpha arm64 à partir des seules sources suivies, sans lire les archives utilisateur.
set -euo pipefail
umask 022
root=$(cd "$(dirname "$0")/.." && pwd)
output="${1:-"$root/dist"}"
mkdir -p "$output"
output=$(cd "$output" && pwd)
build=$(mktemp -d "${TMPDIR:-/tmp}/r1-bridge-build.XXXXXXXX")
trap 'rm -rf "$build"' EXIT
name='R1 Bridge'
dmg_name='R1-Bridge-0.1.0-alpha.2-macOS-arm64.dmg'
app="$build/image/$name.app"
resources="$app/Contents/Resources"
source_runtime="$root/macos/runtime"
runtime="$resources/runtime"
flow='Export.workflow/Contents'
helper='R1 Bridge Collector.app'
target=arm64-apple-macos14.0
sdk=$(/usr/bin/xcrun --sdk macosx --show-sdk-path)
flags=(-O -sdk "$sdk" -target "$target" -file-prefix-map "$root=R1Bridge" -debug-prefix-map "$root=R1Bridge" -file-prefix-map "$build=build" -debug-prefix-map "$build=build")
mkdir -p "$app/Contents/MacOS" "$runtime/$flow/Resources/$helper/Contents/MacOS" "$build/AppIcon.iconset"
cp "$root/macos/app/Info.plist" "$app/Contents/Info.plist"
install -m 755 "$root/integration/Connecter ChatGPT.command" "$resources/Connecter ChatGPT.command"
install -m 755 "$root/integration/Connecter ChatGPT.command" "$build/image/Connecter ChatGPT.command"
for script in collecte r1 rapport_even rapprochement_even controle_sommeil serveur_sommeil tunnel_r1; do
    cp "$source_runtime/$script.py" "$runtime/"
done
cp "$source_runtime/$flow/document.wflow" "$runtime/$flow/"
cp "$source_runtime/$flow/Resources/import_export.py" "$runtime/$flow/Resources/"
cp "$source_runtime/$flow/Resources/$helper/Contents/Info.plist" "$runtime/$flow/Resources/$helper/Contents/"
native="$runtime/$flow/Resources"
swiftc_path=$(/usr/bin/xcrun --find swiftc)
cd "$root"
"$swiftc_path" "${flags[@]}" "macos/runtime/$flow/Resources/cartes_even.swift" -o "$native/cartes_even"
"$swiftc_path" "${flags[@]}" "macos/runtime/$flow/Resources/EvenR1Export.swift" -o "$native/$helper/Contents/MacOS/EvenR1Export"
"$swiftc_path" "${flags[@]}" "macos/app/main.swift" -o "$app/Contents/MacOS/$name"
/usr/bin/xcrun --sdk macosx swift macos/app/icon.swift "$build/AppIcon.iconset"
/usr/bin/iconutil -c icns "$build/AppIcon.iconset" -o "$resources/AppIcon.icns"
/usr/bin/codesign --force --sign - --timestamp=none "$native/cartes_even"
/usr/bin/codesign --force --sign - --timestamp=none "$native/$helper"
(cd "$runtime"; LC_ALL=C /usr/bin/find . -type f | LC_ALL=C /usr/bin/sort | while IFS= read -r file; do /usr/bin/shasum -a 256 "$file"; done) | /usr/bin/shasum -a 256 | /usr/bin/cut -d ' ' -f 1 > "$resources/runtime.sha256"
/usr/bin/codesign --force --sign - --timestamp=none "$app"
/usr/bin/codesign --verify --deep --strict "$app"
/usr/bin/codesign --verify --strict "$native/$helper"
/usr/bin/plutil -lint "$app/Contents/Info.plist" "$native/$helper/Contents/Info.plist" >/dev/null
ln -s /Applications "$build/image/Applications"
/usr/bin/hdiutil create -quiet -volname "$name" -format UDZO -srcfolder "$build/image" "$build/$dmg_name"
/usr/bin/hdiutil verify -quiet "$build/$dmg_name"
mv -f "$build/$dmg_name" "$output/$dmg_name"
(cd "$output"; /usr/bin/shasum -a 256 "$dmg_name" > "$dmg_name.sha256")
echo "$output/$dmg_name"
