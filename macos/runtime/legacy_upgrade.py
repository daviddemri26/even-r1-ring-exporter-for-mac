"""Import private data created by the French-language alpha releases."""

import fcntl
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

from collection import CollectError, DATABASE


@contextmanager
def previous_collection_lock(base):
    """Wait for any old-style export before reading its files."""
    old_lock = base / ".collecte.lock"
    try:
        fd = os.open(old_lock, os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        yield
        return
    with os.fdopen(fd, "r+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


COLLECTION_SCHEMA = {
    "nuits": ("nights", {"jour": "day"}),
    "archives": ("archives", {"empreinte": "checksum"}),
    "essais": ("attempts", {"debut": "start", "fin": "end", "etat": "status",
                            "dernier_jour": "latest_wake_date", "empreinte": "checksum"}),
    "controles_planifies": ("schedule_checks", {"creneau": "slot", "controle": "checked_at",
                                                "etat": "status"}),
}
CARD_SCHEMA = {
    "etat": ("status", {"categorie": "category", "valeur": "value", "unite": "unit"}),
    "changements": ("changes", {"categorie": "category", "jour": "day", "valeur": "value",
                                "unite": "unit", "anciennete": "recency", "initiale": "initial"}),
}
STATES = {"réussi": "succeeded", "échec": "failed", "occupé": "busy", "interrompu": "interrupted",
          "en cours": "running", "différé": "deferred", "réservé": "reserved", "terminé": "completed",
          "traité": "handled"}


def previous_file(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise CollectError("The previous installation contains an unexpected file type or owner.")
    return True


def import_database(old, new, schema):
    # The original is retained for rollback. Publish a complete translated snapshot
    # in one step so an interrupted upgrade can safely be run again.
    if new.exists() or not previous_file(old):
        return
    with tempfile.TemporaryDirectory(prefix=".upgrade-", dir=old.parent) as staging:
        output = Path(staging) / new.name
        with closing(sqlite3.connect(old.as_uri() + "?mode=ro", uri=True)) as source, \
                closing(sqlite3.connect(output)) as db:
            source.backup(db)
            with db:
                db.execute("BEGIN IMMEDIATE")
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table, (target, columns) in schema.items():
                    if table not in tables:
                        continue
                    if table != target:
                        db.execute(f'ALTER TABLE "{table}" RENAME TO "{target}"')
                    fields = {row[1] for row in db.execute(f'PRAGMA table_info("{target}")')}
                    for field, replacement in columns.items():
                        if field in fields:
                            db.execute(f'ALTER TABLE "{target}" RENAME COLUMN "{field}" TO "{replacement}"')
                    if target in ("status", "changes"):
                        db.execute(f"""UPDATE "{target}" SET unit='steps' WHERE category='steps' AND unit='pas'""")
                    elif target in ("attempts", "schedule_checks"):
                        db.executemany(f'UPDATE "{target}" SET status=? WHERE status=?',
                                       [(english, previous) for previous, english in STATES.items()])
                        # Full historical diagnostics remain in the original database.
                        db.execute(f"""UPDATE "{target}" SET detail='Previous version: ' || status
                                      WHERE detail IS NOT NULL""")
                    if target == "attempts":
                        db.execute("UPDATE attempts SET mode='manual' WHERE mode='manuel'")
        output.chmod(0o600)
        os.link(output, new)


def import_data(base):
    import_database(base / "suivi.sqlite3", base / DATABASE, COLLECTION_SCHEMA)
    import_database(base / "cartes_historique.sqlite3", base / "card_history.sqlite3", CARD_SCHEMA)
    for old_name, new_name in (("releves_even.json", "readings.json"), ("etat_cartes.txt", "card_status.txt")):
        old, new = base / old_name, base / new_name
        if new.exists() or not previous_file(old):
            continue
        if old.stat().st_size > 16 * 1024:
            raise CollectError("The previous card snapshot is too large to import.")
        data = old.read_bytes()
        if new_name == "readings.json":
            snapshot = json.loads(data)
            steps = snapshot["metrics"].get("steps")
            if isinstance(steps, dict) and steps.get("unit") == "pas":
                steps["unit"] = "steps"
            data = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
        with tempfile.NamedTemporaryFile(dir=base) as staged:
            staged.write(data)
            staged.flush()
            os.fsync(staged.fileno())
            os.link(staged.name, new)

    previous_inbox = base / "Reception"
    if previous_inbox.is_dir() and not previous_inbox.is_symlink():
        for old in previous_inbox.glob("*.zip"):
            if not previous_file(old):
                continue
            new = base / "Incoming" / old.name
            try:
                os.link(old, new)
            except FileExistsError:
                if not old.samefile(new):
                    raise CollectError("Two incoming archives have the same name. Preserve both before retrying.")
            old.unlink()
