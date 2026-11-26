"""End-to-end local collector and MCP checks using a temporary home and invented data."""
import csv
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
import collection
import card_report


def export_fixture(base, *, include_sleep):
    csv_data = io.StringIO(newline="")
    writer = csv.writer(csv_data)
    writer.writerow(("start_ts", "end_ts", "total_time", "wake_time", "rem_time",
                     "light_time", "deep_time", "stages"))
    if include_sleep:
        stages = json.dumps([{"type": i, "half_minutes": n}
                             for i, n in enumerate((20, 30, 60, 10))])
        row = ("2001-03-04T00:00:00Z", "2001-03-04T01:00:00Z", 3000, 600, 900, 1800, 300, stages)
        writer.writerows([row, row])  # Identical overlapping sessions are a single night.
    with zipfile.ZipFile(base / "Incoming" / "fixture.zip", "w") as archive:
        # Fixed member timestamps keep the archive byte-identical on repeated exports.
        archive.writestr(zipfile.ZipInfo("sleep.csv"), csv_data.getvalue())
        archive.writestr(zipfile.ZipInfo("steps.csv"),
                         "timestamp,source,value\n2001-03-04T01:00:00Z,R1,1234\n")


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.base = self.home / "Library/Application Support/R1 Bridge"
        self.dates = {"start": "2001-03-01", "end": "2001-03-07"}

    def request(self, method, params):
        message = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        proc = subprocess.run([sys.executable, "-B", str(RUNTIME / "mcp_server.py"), "--stdio"],
                              env={**os.environ, "HOME": str(self.home)}, check=True,
                              capture_output=True, text=True, timeout=10, input=json.dumps(message) + "\n")
        response = json.loads(proc.stdout)
        self.assertNotIn("error", response)
        result = response["result"]
        self.assertFalse(result.get("isError"), result)
        return result

    def call(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        return json.loads(result["content"][0]["text"])

    def collect(self, include_sleep):
        def exporter(base):
            export_fixture(base, include_sleep=include_sleep)

        code, detail = collection.run(self.base, "launchd", exporter)
        self.assertEqual(code, 0, detail)

    @unittest.skipUnless(sys.platform == "darwin", "the installer swaps whole workflows using the macOS filesystem API")
    def test_named_exporter_upgrade_keeps_alpha3_data_and_tunnel(self):
        self.collect(True)
        workflow = Path("Export.workflow/Contents/Resources")
        previous_helper = self.base / workflow / "R1 Bridge Collector.app"
        previous_helper.mkdir(parents=True)
        connection = self.base / "tunnel/even-r1.yaml"
        connection.parent.mkdir()
        connection.write_text(f"command: '/usr/bin/python3' '{self.base}/mcp_server.py' --stdio\n")
        agent = self.home / "Library/LaunchAgents/local.r1bridge.tunnel.plist"
        agent.parent.mkdir(parents=True)
        agent.write_bytes(plistlib.dumps({"Label": "local.r1bridge.tunnel",
                                         "ProgramArguments": ["/usr/bin/python3", "-B", str(self.base / "tunnel.py"),
                                                              "run-keychain"]}))
        original = [path.read_bytes() for path in (connection, agent)]

        # The DMG check separately verifies real compiled executables. These stubs
        # exercise just the install transition without starting an export or tunnel.
        package = self.home / "packaged-runtime"
        package.mkdir()
        for script in RUNTIME.glob("*.py"):
            shutil.copy2(script, package / script.name)
        executable = workflow / "Even R1 Ring Collector for Mac.app/Contents/MacOS/EvenR1Export"
        for stub in (executable, workflow / "even_cards"):
            path = package / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        env = {**os.environ, "HOME": str(self.home)}
        subprocess.run([sys.executable, "-B", str(package / "r1.py"), "prepare"],
                       env=env, check=True, capture_output=True, timeout=10)
        self.assertTrue(os.access(self.base / executable, os.X_OK))
        self.assertFalse(previous_helper.exists())
        self.assertEqual([path.read_bytes() for path in (connection, agent)], original)
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-11-25"}}
        latest = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "sleep_durations", "arguments": self.dates}}
        session = subprocess.run([sys.executable, "-B", str(self.base / "mcp_server.py"), "--stdio"],
                                 env=env, input="".join(json.dumps(x) + "\n" for x in (request, latest)),
                                 capture_output=True, text=True, check=True, timeout=10)
        setup, reading = [json.loads(line)["result"] for line in session.stdout.splitlines()]
        self.assertEqual(setup["serverInfo"]["title"], "Even R1 Ring Data for ChatGPT")
        self.assertEqual(setup["serverInfo"]["name"], "even-r1-ring-data")
        self.assertEqual(json.loads(reading["content"][0]["text"])[0]["duration_minutes"], 50)

    def test_sleep_phases_dates_and_replay(self):
        self.collect(True)
        self.collect(True)
        self.assertEqual(len(list((self.base / "Archives").glob("*.zip"))), 1)
        self.assertEqual(self.call("sleep_durations", self.dates),
                         [{"wake_date": "2001-03-04", "duration_minutes": 50}])
        self.assertEqual(self.call("sleep_stages", self.dates),
                         [{"wake_date": "2001-03-04", "awake_minutes": 10,
                           "rem_minutes": 15, "light_minutes": 30, "deep_minutes": 5}])

    def test_empty_first_export(self):
        self.collect(False)
        self.assertEqual(self.call("sleep_durations", self.dates), [])
        with closing(collection.connect(self.base)) as db:
            self.assertFalse(collection.evidence(db))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM nights").fetchone()[0], 0)

    def test_six_cards_and_unchanged_observations(self):
        self.collect(True)
        measurements = {"steps": (1234, "steps"), "calories": (100, "kcal"),
                        "hrv": (40, "ms"), "heartRate": (60, "bpm"), "spo2": (97, "%"),
                        "skinTemperature": (-0.2, "°C")}
        metrics = {name: {"value": value, "unit": unit, "recency": "1 hour ago"}
                   for name, (value, unit) in measurements.items()}
        path = self.base / "readings.json"
        for hour, expected in [(2, 6), (3, 0)]:
            snapshot = {"version": 1, "recorded_at": f"2001-03-04T{hour:02d}:00:00Z", "metrics": metrics}
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(card_report.record_changes(self.base), expected)
        categories = {"categories": list(measurements)}
        latest = self.call("latest_readings", categories)
        self.assertEqual(latest["unavailable"], [])
        self.assertEqual(latest["metrics"]["steps"]["csv_batch"]["local_date"], "2001-03-04")
        for name, (value, unit) in measurements.items():
            self.assertEqual((latest["metrics"][name]["value"], latest["metrics"][name]["unit"]), (value, unit))
        history = self.call("reading_history", {**categories, **self.dates})
        self.assertEqual(len(history["changes"]), 6)
        self.assertTrue(all(change["initial"] for change in history["changes"]))
        tools = self.request("tools/list", {})["tools"]
        self.assertEqual(len(tools), 4)
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))

    def test_localized_card_age_is_translated_only_on_output(self):
        self.collect(True)
        translations = {"steps": ("il y a une heure", "1 hour ago"),
                        "hrv": ("il y a 3 jours", "3 days ago"),
                        "spo2": ("AUJOURD’HUI", "today"),
                        "calories": ("il y a 2 mois", "2 months ago")}
        metrics = {name: {"value": 1234 if name == "steps" else 42, "unit": next(iter(card_report.UNITS[name])),
                          "recency": original} for name, (original, _) in translations.items()}
        snapshot = {"version": 1, "recorded_at": "2001-03-04T02:00:00Z", "metrics": metrics}
        path = self.base / "readings.json"
        path.write_text(json.dumps(snapshot))
        path.chmod(0o600)
        self.assertEqual(card_report.record_changes(self.base), len(metrics))
        selection = {"categories": list(metrics)}
        latest = self.call("latest_readings", selection)["metrics"]
        self.assertEqual(latest["steps"]["csv_batch"]["local_date"], "2001-03-04")
        history = self.call("reading_history", {**selection, **self.dates})["changes"]
        expected = {name: translated for name, (_, translated) in translations.items()}
        self.assertEqual({name: reading["recency"] for name, reading in latest.items()}, expected)
        self.assertEqual({reading["category"]: reading["recency"] for reading in history}, expected)
        with closing(card_report.history_connection(self.base, False)) as db:
            self.assertEqual(dict(db.execute("SELECT category,recency FROM changes")),
                             {name: original for name, (original, _) in translations.items()})
        self.assertEqual(json.loads(path.read_text()), snapshot)


if __name__ == "__main__":
    unittest.main()
