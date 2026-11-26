"""End-to-end local collector and MCP checks using a temporary home and invented data."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
import collecte
import rapport_even


def export_fixture(base, *, include_sleep):
    csv_data = io.StringIO(newline="")
    writer = csv.writer(csv_data)
    writer.writerow(("start_ts", "end_ts", "total_time", "wake_time", "rem_time",
                     "light_time", "deep_time", "stages"))
    if include_sleep:
        phases = json.dumps([{"type": i, "half_minutes": n}
                             for i, n in enumerate((20, 30, 60, 10))])
        row = ("2001-03-04T00:00:00Z", "2001-03-04T01:00:00Z", 3000, 600, 900, 1800, 300, phases)
        writer.writerows([row, row])  # Identical overlapping sessions are a single night.
    with zipfile.ZipFile(base / "Reception" / "fixture.zip", "w") as archive:
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
        self.dates = {"debut": "2001-03-01", "fin": "2001-03-07"}

    def request(self, method, params):
        message = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        proc = subprocess.run([sys.executable, "-B", str(RUNTIME / "serveur_sommeil.py"), "--stdio"],
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

        code, detail = collecte.run(self.base, "launchd", exporter)
        self.assertEqual(code, 0, detail)

    def test_sleep_phases_dates_and_replay(self):
        self.collect(True)
        self.collect(True)
        self.assertEqual(len(list((self.base / "Archives").glob("*.zip"))), 1)
        self.assertEqual(self.call("durees_sommeil", self.dates),
                         [{"date_reveil": "2001-03-04", "duree_minutes": 50}])
        self.assertEqual(self.call("phases_sommeil", self.dates),
                         [{"date_reveil": "2001-03-04", "eveil_minutes": 10,
                           "paradoxal_minutes": 15, "leger_minutes": 30, "profond_minutes": 5}])

    def test_empty_first_export(self):
        self.collect(False)
        self.assertEqual(self.call("durees_sommeil", self.dates), [])
        with closing(collecte.connect(self.base)) as db:
            self.assertFalse(collecte.evidence(db))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM nuits").fetchone()[0], 0)

    def test_six_cards_and_unchanged_observations(self):
        self.collect(True)
        measurements = {"steps": (1234, "pas"), "calories": (100, "kcal"),
                        "hrv": (40, "ms"), "heartRate": (60, "bpm"), "spo2": (97, "%"),
                        "skinTemperature": (-0.2, "°C")}
        metrics = {name: {"value": value, "unit": unit, "recency": "1 hour ago"}
                   for name, (value, unit) in measurements.items()}
        path = self.base / "releves_even.json"
        for hour, expected in [(2, 6), (3, 0)]:
            snapshot = {"version": 1, "recorded_at": f"2001-03-04T{hour:02d}:00:00Z", "metrics": metrics}
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(rapport_even.enregistrer_changements(self.base), expected)
        categories = {"categories": list(measurements)}
        latest = self.call("dernier_releve_even", categories)
        self.assertEqual(latest["indisponibles"], [])
        self.assertEqual(latest["metrics"]["steps"]["lot_csv"]["date_locale"], "2001-03-04")
        for name, (value, unit) in measurements.items():
            self.assertEqual((latest["metrics"][name]["value"], latest["metrics"][name]["unit"]), (value, unit))
        history = self.call("evolution_cartes_even", {**categories, **self.dates})
        self.assertEqual(len(history["changements"]), 6)
        self.assertTrue(all(change["initiale"] for change in history["changements"]))
        tools = self.request("tools/list", {})["tools"]
        self.assertEqual(len(tools), 4)
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))


if __name__ == "__main__":
    unittest.main()
