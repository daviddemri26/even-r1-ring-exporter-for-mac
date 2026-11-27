"""Synthetic history, corrections, and read-only legacy source coverage for iPhone sync."""
import csv
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
import sleep_feed as feed


FIELDS = ["start_ts", "end_ts", "total_time", "wake_time", "rem_time",
          "light_time", "deep_time", "stages", "source"]
FIRST = datetime(2001, 3, 4, 1, tzinfo=timezone.utc)


def sleep(start=FIRST, runs=((2, 5), (3, 4), (2, 3), (1, 2), (0, 1))):
    seconds = [0, 0, 0, 0]
    for kind, units in runs:
        seconds[kind] += units * 30
    awake, rem, core, deep = seconds
    end = start + timedelta(seconds=sum(seconds))
    stages = [{"type": kind, "half_minutes": units} for kind, units in runs]
    return dict(zip(FIELDS, (start.isoformat(), end.isoformat(), sum(seconds) - awake,
                             awake, rem, core, deep, json.dumps(stages), "R1")))


class SleepFeedTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.base = Path(scratch.name)
        self.ledger = self.base / "phone"
        self.tick = 0
        self.specs = []

    def source(self, legacy=False, unlinked=False):
        proto = feed.PILOT if legacy else feed.PUBLIC
        folder = self.base / ("legacy" if legacy else "public")
        (folder / "Archives").mkdir(parents=True)
        spec = (folder, *proto[1:])
        self.specs.append(spec)
        base, filename, attempts, status, _, fingerprint, finished, wake = spec
        with closing(sqlite3.connect(base / filename)) as db, db:
            db.execute(f"CREATE TABLE archives ({fingerprint} TEXT PRIMARY KEY)")
            optional = "" if unlinked else f", {fingerprint} TEXT"
            db.execute(f"CREATE TABLE {attempts} (id INTEGER PRIMARY KEY, {status} TEXT, "
                       f"{finished} TEXT, {wake} TEXT{optional})")
        return spec

    def collect(self, spec, rows, *, status=None, wake=None, linked=True):
        folder, filename, attempts, status_col, success, fingerprint, finished, wake_col = spec
        data = io.StringIO(newline="")
        writer = csv.DictWriter(data, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr(zipfile.ZipInfo("fixture/sleep.csv"), data.getvalue())
        digest = hashlib.sha256(raw.getvalue()).hexdigest()
        target = folder / "Archives" / (digest + ".zip")
        target.write_bytes(raw.getvalue())
        self.tick += 1
        done = (FIRST + timedelta(days=365, seconds=self.tick)).isoformat()
        day = wake or max((row["end_ts"][:10] for row in rows), default=None)
        with closing(sqlite3.connect(folder / filename)) as db, db:
            db.execute(f"INSERT OR IGNORE INTO archives ({fingerprint}) VALUES (?)", (digest,))
            columns = [status_col, finished, wake_col]
            values = [status or success, done, day]
            if linked:
                columns.append(fingerprint)
                values.append(digest)
            db.execute(f"INSERT INTO {attempts} ({','.join(columns)}) VALUES "
                       f"({','.join('?' for _ in values)})", values)
        return target

    def page(self, after=0):
        return feed.page(after, self.specs, self.ledger)

    def test_all_archives_pagination_naps_and_read_only_pilot(self):
        pilot = self.source(legacy=True)
        public = self.source()
        night = sleep()
        self.collect(pilot, [night, night, sleep(FIRST + timedelta(hours=12))])
        self.collect(public, [night, *(sleep(FIRST + timedelta(days=n)) for n in range(1, 11))])
        self.collect(public, [sleep(FIRST + timedelta(days=22))], status="failed")
        db_path = pilot[0] / pilot[1]
        old = db_path.read_bytes()
        page1 = self.page()
        self.assertEqual(len(page1["sessions"]), feed.PAGE_SIZE)
        self.assertTrue(page1["more"])
        page2 = self.page(page1["cursor"])
        combined = page1["sessions"] + page2["sessions"]
        self.assertEqual(len({s["id"] for s in combined}), 12)
        self.assertFalse(page2["more"])
        self.assertEqual([s["wakeDate"] for s in combined].count(night["end_ts"][:10]), 2)
        self.assertEqual(self.page(page2["cursor"]), {
            "sessions": [], "cursor": page2["cursor"], "more": False, "skipped": 0,
            "latestWakeDate": "2001-03-14"})
        self.assertEqual(self.page(), page1)
        self.assertEqual(db_path.read_bytes(), old)
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.ledger / "sleep-feed.sqlite3").stat().st_mode & 0o777, 0o600)
        with patch.object(feed, "verified_rows", side_effect=AssertionError("already indexed")):
            self.assertEqual(self.page(), page1)

    def test_actual_order_dst_local_wake_and_exact_duration(self):
        origin = datetime.fromisoformat("2001-10-28T01:59:00-07:00")
        rows = [sleep(origin, ((0, 1), (2, 1), (2, 1), (1, 1), (3, 1), (2, 1)))]
        end = datetime.fromisoformat("2001-10-28T01:02:00-08:00")
        rows[0]["end_ts"] = end.isoformat()
        # This row ends on the next UTC date but still belongs to the 28th locally.
        local = datetime.fromisoformat("2001-10-28T22:59:00-08:00")
        rows.append(sleep(local))
        self.collect(self.source(), rows)
        first, second = self.page()["sessions"]
        stages = first["stages"]
        self.assertEqual([i["kind"] for i in stages], ["awake", "core", "rem", "deep", "core"])
        self.assertEqual(stages[0]["start"], origin.timestamp())
        self.assertEqual(stages[-1]["end"], end.timestamp())
        self.assertTrue(all(a["end"] == b["start"] for a, b in zip(stages, stages[1:])))
        self.assertEqual(second["wakeDate"], "2001-10-28")

    def test_changed_timeline_then_reinstated_digest_and_no_duplicate_on_retry(self):
        public = self.source()
        original = sleep()
        changed = sleep(runs=((3, 4), (2, 8), (1, 2), (0, 1)))
        a = self.collect(public, [original])
        first = self.page()
        self.collect(public, [changed])
        second = self.page(first["cursor"])
        original_again = self.collect(public, [original])
        self.assertEqual(a, original_again)
        third = self.page(second["cursor"])
        for number, result in enumerate((first, second, third), 1):
            self.assertEqual(result["sessions"][0]["id"], first["sessions"][0]["id"])
            self.assertEqual(result["sessions"][0]["version"], number)
        self.assertEqual(third["sessions"][0]["stages"], first["sessions"][0]["stages"])
        self.collect(public, [original])
        self.assertEqual(self.page(third["cursor"])["sessions"], [])

    def test_withholds_conflicts_unknown_stages_and_rounding(self):
        public = self.source()
        bad = sleep(FIRST + timedelta(days=1))
        bad["end_ts"] = (datetime.fromisoformat(bad["end_ts"]) + timedelta(seconds=30)).isoformat()
        unknown = sleep(FIRST + timedelta(days=2))
        unknown["stages"] = '[{"type":4,"half_minutes":15}]'
        other_source = dict(sleep(FIRST + timedelta(days=3)), source="other")
        clean = sleep(FIRST + timedelta(days=5))
        self.collect(public, [sleep(), sleep(FIRST + timedelta(minutes=2)),
                              bad, unknown, other_source, clean])
        page = self.page()
        self.assertEqual([s["wakeDate"] for s in page["sessions"]], [clean["end_ts"][:10]])
        self.assertEqual(page["skipped"], 4)

    def test_known_boundary_correction_and_ambiguous_shift(self):
        public = self.source()
        self.collect(public, [sleep()])
        first = self.page()
        self.collect(public, [sleep(runs=((3, 5), (2, 4)))])
        second = self.page(first["cursor"])
        self.assertEqual(second["sessions"][0]["id"], first["sessions"][0]["id"])
        self.assertEqual(second["sessions"][0]["version"], 2)
        self.collect(public, [sleep(FIRST + timedelta(seconds=30))])
        self.assertEqual(self.page(second["cursor"])["sessions"], [])
        self.assertGreater(self.page()["skipped"], 0)
        self.assertEqual(self.page()["sessions"], [])
        self.assertIsNone(self.page()["latestWakeDate"])

    def test_latest_wake_date_can_move_back_across_midnight(self):
        source = self.source()
        start = FIRST.replace(hour=23, minute=56)
        self.collect(source, [sleep(start, ((2, 10),))])
        old = self.page()
        self.collect(source, [sleep(start, ((2, 6),))])
        new = self.page(old["cursor"])
        self.assertEqual(old["sessions"][0]["id"], new["sessions"][0]["id"])
        self.assertEqual(old["latestWakeDate"], "2001-03-05")
        self.assertEqual(new["latestWakeDate"], "2001-03-04")
        self.assertEqual(self.page(new["cursor"])["latestWakeDate"], "2001-03-04")

    def test_cli_distinguishes_restored_mac_index_from_collection_failure(self):
        env = {**os.environ, "HOME": str(self.base)}
        cli = [sys.executable, "-B", str(RUNTIME / "sleep_feed.py"), "12"]
        missing = subprocess.run(cli, env=env, capture_output=True, timeout=10)
        self.assertEqual(missing.returncode, 1)
        public = self.source()
        self.collect(public, [sleep()])
        location = self.base / "Library/Application Support/R1 Bridge"
        location.parent.mkdir(parents=True)
        public[0].rename(location)
        reset = subprocess.run(cli, env=env, capture_output=True, timeout=10)
        self.assertEqual(reset.returncode, 3)
        self.assertEqual(reset.stdout, b"")

    def test_shortened_night_then_distinct_nap_at_its_old_start(self):
        public = self.source()
        self.collect(public, [sleep(runs=((2, 8),))])
        original_id = self.page()["sessions"][0]["id"]
        shortened = sleep(FIRST + timedelta(seconds=120), ((2, 4),))
        self.collect(public, [shortened])
        self.assertEqual(self.page()["sessions"][0]["id"], original_id)
        self.collect(public, [shortened, sleep(runs=((3, 2),))])
        both = self.page()["sessions"]
        self.assertEqual(len({s["id"] for s in both}), 2)
        self.assertIn(original_id, [s["id"] for s in both])

    def test_conflicting_order_and_damaged_secondary_source(self):
        public = self.source()
        pilot = self.source(legacy=True)
        (pilot[0] / pilot[1]).write_bytes(b"synthetic unreadable index")
        self.collect(public, [sleep(), sleep(runs=((3, 4), (2, 8), (1, 2), (0, 1))),
                              sleep(FIRST + timedelta(days=1))])
        self.assertEqual(len(self.page()["sessions"]), 1)
        self.assertEqual(self.page()["skipped"], 2)

    def test_legacy_unlinked_candidate_requires_verified_day(self):
        pilot = self.source(legacy=True, unlinked=True)
        self.collect(pilot, [sleep()], linked=False, wake="2004-07-01")
        with self.assertRaises(feed.FeedError):
            self.page()
        self.collect(pilot, [sleep()], linked=False)
        self.assertEqual(len(self.page()["sessions"]), 1)
        # In a fresh ledger the two possible archives cannot be attributed.
        self.collect(pilot, [sleep(FIRST + timedelta(days=1))], linked=False)
        with self.assertRaises(feed.FeedError):
            feed.page(0, [pilot], self.base / "another-ledger")

    def test_invalid_archive_isolated_and_reported(self):
        public = self.source()
        bad = self.collect(public, [sleep()])
        self.collect(public, [sleep(FIRST + timedelta(days=1))])
        (bad.parent / "other.zip").write_bytes(bad.read_bytes())
        bad.write_bytes(b"corrupted on disk")
        page = self.page()
        self.assertEqual(len(page["sessions"]), 1)
        self.assertEqual(page["skipped"], 1)
        bad.unlink()
        bad.symlink_to(bad.parent / "other.zip")
        self.assertEqual(self.page(), page)
        with self.assertRaises(feed.FeedError):
            self.page(page["cursor"] + 1)

    def test_concurrent_pull_replays_same_versions(self):
        source = self.source()
        self.collect(source, [sleep()])
        with ThreadPoolExecutor(max_workers=3) as pool:
            pages = list(pool.map(lambda _: self.page(), range(3)))
        self.assertEqual(pages[0], pages[1])
        self.assertEqual(pages[0], pages[2])
        self.assertEqual(pages[0]["sessions"][0]["version"], 1)


if __name__ == "__main__":
    unittest.main()
