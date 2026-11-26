"""Scheduling checks use an isolated directory and never open Even or change launchd."""
import os
import plistlib
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path
from threading import Event
from unittest.mock import patch

RUNTIME = Path(os.environ.get("R1BRIDGE_TEST_RUNTIME",
                              Path(__file__).resolve().parents[1] / "runtime"))
sys.path.insert(0, str(RUNTIME))
import r1


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.morning = datetime(2001, 4, 1, 8, 15)
        self.later = self.morning.replace(minute=55)
        self.noon = self.morning.replace(hour=12)

    def test_calendar_windows_and_wake(self):
        checks = [t.strftime("%H:%M") for _, t in r1.schedule_times(self.morning)]
        self.assertEqual(len(checks), 21)
        self.assertEqual(checks[:7], ["08:15", "08:25", "08:35", "08:45", "08:55", "09:05", "09:15"])
        self.assertEqual(r1.current_slot(self.morning.replace(hour=9, second=59)), self.morning)
        self.assertIsNone(r1.current_slot(self.morning.replace(hour=9, minute=16)))
        with patch.object(r1, "quiet_reason") as idle, patch.object(r1.collection, "run") as runner:
            self.assertEqual(r1.scheduled_run(self.base, self.morning.replace(hour=11))[0], 0)
            idle.assert_not_called()
            runner.assert_not_called()
        self.assertIn("12:15", r1.next_attempt(self.morning, self.morning.isoformat(timespec="minutes")))
        self.assertIn("08:15", r1.next_attempt(self.morning.replace(hour=23)))

    def test_deferral_never_changes_export_and_repeated_checks_reserve_one_window(self):
        with patch.object(r1, "quiet_reason", return_value="Mac in use"), patch.object(r1.collection, "run") as runner:
            r1.scheduled_run(self.base, self.morning)
            runner.assert_not_called()
        with closing(r1.schedule_db(self.base)) as db:
            self.assertEqual(db.execute("SELECT status FROM schedule_checks").fetchone()[0], "deferred")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 0)
            self.assertIsNone(db.execute("SELECT MAX(day) FROM nights").fetchone()[0])
        with patch.object(r1, "quiet_reason", return_value=None), patch.object(r1.collection, "run", return_value=(0, "verified")) as runner:
            r1.scheduled_run(self.base, self.later)
            r1.scheduled_run(self.base, self.later)
            r1.scheduled_run(self.base, self.noon)
            self.assertEqual(runner.call_count, 2)

    def test_parallel_checks_and_crash_do_not_repeat_export(self):
        entered, finish = Event(), Event()
        def export(*_):
            entered.set()
            self.assertTrue(finish.wait(5))
            raise RuntimeError("test interrupted")
        with patch.object(r1, "quiet_reason", return_value=None), patch.object(r1.collection, "run", side_effect=export) as runner:
            with ThreadPoolExecutor(max_workers=2) as executor:
                launch = executor.submit(r1.scheduled_run, self.base, self.morning)
                self.assertTrue(entered.wait(5))
                try:
                    self.assertEqual(r1.scheduled_run(self.base, self.morning)[0], 0)
                finally:
                    finish.set()
                with self.assertRaises(RuntimeError):
                    launch.result()
            self.assertEqual(r1.scheduled_run(self.base, self.later)[0], 0)
            self.assertEqual(runner.call_count, 1)

    def test_migration_from_previous_schedule_and_manual_availability(self):
        r1.collection.setup(self.base)
        with closing(r1.schedule_db(self.base)) as db, db:
            db.execute("INSERT INTO attempts (start,mode,status) VALUES (?, 'launchd', 'succeeded')",
                       (self.morning.astimezone().isoformat(),))
        with patch.object(r1, "quiet_reason") as idle, patch.object(r1.collection, "run", return_value=(0,"manual export")) as runner:
            r1.scheduled_run(self.base, self.later)
            runner.assert_not_called()
            idle.assert_not_called()
            with patch.object(sys, "argv", ["r1.py", "export"]), patch.object(r1, "BASE", self.base), patch("builtins.print"):
                self.assertEqual(r1.main(), 0)
            runner.assert_called_once_with(self.base, "manual")

    def test_fail_closed_on_session_or_idle_information(self):
        with patch.object(r1.collection, "check_session", side_effect=r1.collection.CollectError("session locked")), \
                patch.object(r1.subprocess, "check_output") as query:
            self.assertIn("locked", r1.quiet_reason())
            query.assert_not_called()
        with patch.object(r1.collection, "check_session"), patch.object(r1.subprocess, "check_output") as query:
            for value in (None, -10, False, 119_999_999_999):
                query.return_value = plistlib.dumps([{} if value is None else {"HIDIdleTime": value}])
                self.assertIsNotNone(r1.quiet_reason())
            query.return_value = plistlib.dumps([{"HIDIdleTime": 120_000_000_000}])
            self.assertIsNone(r1.quiet_reason())


if __name__ == "__main__":
    unittest.main()
