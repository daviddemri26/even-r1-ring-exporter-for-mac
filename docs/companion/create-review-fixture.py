"""Prepare invented sleep sessions for an isolated App Review Mac account."""
import argparse
import csv
import io
import json
import os
import sys
import zipfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "macos/runtime"))
import collection


MARKER = ".sleep-sync-synthetic-review"
FIELDS = ("start_ts", "end_ts", "total_time", "wake_time", "rem_time",
          "light_time", "deep_time", "stages", "source")
OFFSET = timezone(-timedelta(hours=8))
FIRST = datetime(2026, 11, 14, 23, tzinfo=OFFSET)


def stage_row(start, runs):
    seconds = [0, 0, 0, 0]
    for kind, minutes in runs:
        seconds[kind] += minutes * 60
    end = start + timedelta(seconds=sum(seconds))
    spans = [{"type": kind, "half_minutes": minutes * 2} for kind, minutes in runs]
    awake, rem, core, deep = seconds
    return (start.isoformat(), end.isoformat(), core + rem + deep, awake, rem,
            core, deep, json.dumps(spans), "R1")


def export_synthetic(folder, next_night):
    stages = [(2, 100), (3, 45), (1, 30), (0, 5), (2, 165), (1, 55), (2, 80)]
    rows = [stage_row(FIRST, stages),
            stage_row(FIRST + timedelta(hours=15), [(2, 15), (3, 10), (2, 5)])]
    if next_night:
        rows.append(stage_row(FIRST + timedelta(days=1), stages))
    data = io.StringIO(newline="")
    writer = csv.writer(data)
    writer.writerow(FIELDS)
    writer.writerows(rows)
    with zipfile.ZipFile(folder / "Incoming" / "synthetic-review.zip", "x") as archive:
        archive.writestr(zipfile.ZipInfo("sleep.csv"), data.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="A new folder for the synthetic Mac collection")
    parser.add_argument("--add-night", action="store_true", help="Add a second night to this script's fixture")
    args = parser.parse_args()
    folder = args.folder.expanduser().absolute()
    marker = folder / MARKER
    if args.add_night:
        if marker.is_symlink() or not marker.is_file() or folder.is_symlink():
            parser.error("Select an existing synthetic review fixture.")
        # Advance only the fixture this tool created. A collection with a new or
        # replacement archive may have been used for real data since setup.
        recorded = marker.read_text(encoding="ascii").strip()
        expected = folder / "Archives" / (recorded + ".zip")
        if (len(recorded) != 64 or any(c not in "0123456789abcdef" for c in recorded)
                or set((folder / "Archives").iterdir()) != {expected}
                or any((folder / "Incoming").iterdir()) or expected.is_symlink()
                or collection.digest(expected) != recorded):
            parser.error("Only the original, unmodified synthetic fixture can receive the next night.")
    else:
        try:
            folder.mkdir(mode=0o700, parents=True, exist_ok=False)
        except FileExistsError:
            parser.error("Choose a new folder. An existing collection must stay intact.")
    code, _ = collection.run(folder, "synthetic-review", lambda base: export_synthetic(base, args.add_night))
    if code:
        parser.exit(1, "Could not prepare the synthetic fixture.\n")
    if not args.add_night:
        with closing(collection.connect(folder)) as db:
            (checksum,) = db.execute("SELECT checksum FROM archives").fetchone()
        marker.write_text(checksum, encoding="ascii")
    print("Synthetic review collection ready.")


if __name__ == "__main__":
    os.umask(0o077)
    main()
