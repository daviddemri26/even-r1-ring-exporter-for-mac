"""Exercise corrupt and valid Even exports using only temporary directories."""
import struct
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(RUNTIME / "Export.workflow/Contents/Resources"))
import collection
import import_export
from archive_match import latest_digest

VALID_SLEEP_CSV = "start_ts,end_ts\n2001-03-04T00:00Z,2001-03-04T01:00Z\n"


def write_export(path, contents=VALID_SLEEP_CSV, *, corrupt=False):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("sleep.csv", contents)
    if corrupt:
        data = bytearray(path.read_bytes())
        name_size, extra_size = struct.unpack_from("<HH", data, 26)
        start = 30 + name_size + extra_size
        data[start] |= 0b110  # Reserved DEFLATE block type; keep the ZIP headers valid.
        path.write_bytes(data)


class ArchiveRecoveryTest(unittest.TestCase):
    def test_bad_incoming_archive_does_not_block_the_next_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            incoming = base / "Incoming"
            code, _ = collection.run(base, exporter=lambda _: write_export(incoming / "bad.zip", corrupt=True))
            self.assertEqual(code, 1)
            self.assertTrue((incoming / "bad.zip").is_file())

            code, detail = collection.run(base, exporter=lambda _: write_export(incoming / "valid.zip"))
            self.assertEqual(code, 0, detail)
            with closing(collection.connect(base)) as db:
                self.assertEqual([row[0] for row in db.execute("SELECT status FROM attempts ORDER BY id")],
                                 ["failed", "succeeded"])
                self.assertEqual([row[0] for row in db.execute("SELECT day FROM nights")], ["2001-03-04"])
            self.assertEqual(list(incoming.iterdir()), [incoming / "bad.zip"])

    def test_ambiguous_sleep_csv_keeps_the_last_verified_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            incoming = base / "Incoming"
            code, detail = collection.run(base, exporter=lambda _: write_export(incoming / "valid.zip"))
            self.assertEqual(code, 0, detail)
            verified = latest_digest(base)
            ambiguous = {
                "duplicate": "start_ts,end_ts,end_ts\n2001-03-06T22:00Z,2001-03-06T23:00Z,2001-03-07T01:00Z\n",
                "extra": "start_ts,end_ts\n2001-03-06T22:00Z,2001-03-07T01:00Z,unlabeled\n",
            }
            for name, contents in ambiguous.items():
                with self.subTest(name=name):
                    target = incoming / (name + ".zip")
                    code, _ = collection.run(base, exporter=lambda _: write_export(target, contents))
                    self.assertEqual(code, 1)
                    self.assertEqual(latest_digest(base), verified)
                    with closing(collection.connect(base)) as db:
                        self.assertEqual([row[0] for row in db.execute("SELECT day FROM nights")], ["2001-03-04"])
                        self.assertEqual(db.execute("SELECT count(*) FROM archives").fetchone()[0], 1)

    def test_cache_import_retries_a_damaged_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache, incoming = root / "cache", root / "Incoming"
            incoming.mkdir()
            folder = cache / "01234567-89ab-cdef-0123-456789abcdef"
            folder.mkdir(parents=True)
            path = folder / "Even_health_data_20010304.zip"
            name = path.relative_to(cache).as_posix()
            with patch.object(import_export, "CACHE", cache), patch.object(import_export, "INCOMING", incoming):
                write_export(path, corrupt=True)
                self.assertFalse(import_export.finished_copy(name, import_export.exports()[name]))
                self.assertEqual(list(incoming.iterdir()), [])
                write_export(path)
                self.assertTrue(import_export.finished_copy(name, import_export.exports()[name]))
                self.assertEqual([p.read_bytes() for p in incoming.iterdir()], [path.read_bytes()])


if __name__ == "__main__":
    unittest.main()
