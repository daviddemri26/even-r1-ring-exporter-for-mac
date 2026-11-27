#!/bin/bash
# Run the iPhone import checks and a synthetic encrypted Mac–iPhone protocol round trip.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d "${TMPDIR:-/tmp}/sleep-companion-test.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
cd "$root"
common=(-module-cache-path "$scratch/modules" ios/SleepSync/Models.swift)
/usr/bin/xcrun --sdk macosx swiftc "${common[@]}" ios/SleepSync/SleepImport.swift \
    ios/Tests/SleepImportCheck.swift -o "$scratch/SleepImportCheck"
"$scratch/SleepImportCheck"
/usr/bin/xcrun --sdk macosx swiftc "${common[@]}" companion/Wire.swift ios/SleepSync/NetworkClient.swift \
    macos/companion/PhonePairing.swift macos/companion/PhoneServer.swift macos/companion/VerifyPhonePairing.swift \
    companion/Tests/LocalSyncCheck.swift -o "$scratch/LocalSyncCheck"
fixture="$scratch/collection"
/usr/bin/python3 -B docs/companion/create-review-fixture.py "$fixture"
/usr/bin/python3 -B - "$scratch" <<'PYDATA'
import json
import sys
from pathlib import Path
sys.path.insert(0, "macos/runtime")
import sleep_feed

scratch = Path(sys.argv[1])
source = (scratch / "collection", *sleep_feed.PUBLIC[1:])
def snapshot(after):
    return sleep_feed.page(after, specs=[source], directory=scratch / "ledger")

first = snapshot(0)
(scratch / "first.json").write_text(json.dumps(first))
(scratch / "caught-up.json").write_text(json.dumps(snapshot(first["cursor"])))
PYDATA
"$scratch/LocalSyncCheck" "$scratch/first.json" "$scratch/caught-up.json"
