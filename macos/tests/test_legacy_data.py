"""Exercise the original alpha's storage layout with a synthetic user profile."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import archive_match
import card_report
import collection
import legacy_upgrade


class LegacyDataTest(unittest.TestCase):
    def test_upgrade_and_replay(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            collection.setup(base)
            stamp = "2001-03-04T02:00:00+00:00"
            archive = b"synthetic archive used to verify its fingerprint"
            digest = hashlib.sha256(archive).hexdigest()
            (base / "Archives" / (digest + ".zip")).write_bytes(archive)
            with closing(sqlite3.connect(base / "suivi.sqlite3")) as db, db:
                db.executescript("""
                    CREATE TABLE nuits (jour TEXT PRIMARY KEY);
                    CREATE TABLE archives (empreinte TEXT PRIMARY KEY);
                    CREATE TABLE essais (id INTEGER PRIMARY KEY, debut TEXT, mode TEXT, etat TEXT,
                                         detail TEXT, dernier_jour TEXT, fin TEXT, empreinte TEXT);
                    CREATE TABLE controles_planifies (creneau TEXT PRIMARY KEY, controle TEXT, etat TEXT, detail TEXT);
                    INSERT INTO nuits VALUES ('2001-03-04');
                    INSERT INTO controles_planifies VALUES ('2001-03-04T08:15', '2001-03-04T08:15:00Z', 'différé', 'test');
                """)
                db.execute("INSERT INTO archives VALUES (?)", (digest,))
                db.execute("INSERT INTO essais VALUES (1, ?, 'manuel', 'réussi', 'test', '2001-03-04', ?, ?)",
                           (stamp, stamp, digest))
            with closing(sqlite3.connect(base / "cartes_historique.sqlite3")) as db, db:
                db.executescript("""
                    CREATE TABLE capture (id INTEGER PRIMARY KEY, utc TEXT);
                    CREATE TABLE etat (categorie TEXT PRIMARY KEY, utc TEXT, valeur TEXT, unite TEXT);
                    CREATE TABLE changements (categorie TEXT, utc TEXT, observation TEXT, jour TEXT,
                                              valeur TEXT, unite TEXT, anciennete TEXT, initiale INTEGER,
                                              PRIMARY KEY(categorie, utc));
                """)
                db.execute("INSERT INTO etat VALUES ('steps', ?, '1234', 'pas')", (stamp,))
                db.execute("INSERT INTO changements VALUES ('steps', ?, ?, '2001-03-04', '1234', 'pas', '1 hour ago', 1)",
                           (stamp, stamp))
            snapshot = {"version": 1, "recorded_at": stamp,
                        "metrics": {"steps": {"value": 1234, "unit": "pas", "recency": "1 hour ago"}}}
            (base / "releves_even.json").write_text(json.dumps(snapshot))
            (base / "etat_cartes.txt").write_text("CARDS_OK\n")
            (base / "Reception").mkdir(mode=0o700)
            (base / "Reception/partial.zip").write_bytes(b"partial")
            legacy_upgrade.import_data(base)
            self.assertEqual(archive_match.latest_digest(base), digest)
            self.assertEqual(card_report.last_cards(base, ["steps"], include_batch=False)["metrics"]["steps"]["unit"], "steps")
            day = date(2001, 3, 4)
            self.assertEqual(card_report.history(base, ["steps"], day, day)["changes"][0]["unit"], "steps")
            with closing(collection.connect(base)) as db, db:
                self.assertEqual(tuple(db.execute("SELECT mode,status,latest_wake_date FROM attempts").fetchone()),
                                 ("manual", "succeeded", "2001-03-04"))
                self.assertEqual(db.execute("SELECT status FROM schedule_checks").fetchone()[0], "deferred")
                db.execute("INSERT INTO nights VALUES ('2001-03-05')")
            self.assertEqual((base / "Incoming/partial.zip").read_bytes(), b"partial")
            self.assertFalse((base / "Reception/partial.zip").exists())
            self.assertEqual((base / "card_status.txt").read_text(), "CARDS_OK\n")
            legacy_upgrade.import_data(base)
            with closing(collection.connect(base)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM nights").fetchone()[0], 2)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
