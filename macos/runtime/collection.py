"""Archive Even exports locally and index available wake dates."""
import csv
import fcntl
import hashlib
import io
import os
import plistlib
import re
import sqlite3
import subprocess
import zipfile
import zlib
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath

BASE = Path.home() / "Library" / "Application Support" / "R1 Bridge"
DATABASE = "collection.sqlite3"
TIMEOUT = 300


class CollectError(Exception):
    """A diagnostic that may be displayed without logging account or health data."""


def setup(base):
    for path in [base, base / "Incoming", base / "Archives"]:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.chmod(0o700)


def connect(base):
    db = sqlite3.connect(str(base / DATABASE), timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS nights (day TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS archives (checksum TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY, start TEXT NOT NULL, mode TEXT NOT NULL,
            status TEXT NOT NULL, detail TEXT, latest_wake_date TEXT, end TEXT, checksum TEXT
        );
    """)
    def has_fingerprint():
        return any(row["name"] == "checksum" for row in db.execute("PRAGMA table_info(attempts)"))

    if not has_fingerprint():
        with db:
            db.execute("BEGIN IMMEDIATE")
            if not has_fingerprint():
                db.execute("ALTER TABLE attempts ADD COLUMN checksum TEXT")
                # Older attempts did not reference an archive. If only one ZIP is registered,
                # verify its checksum and wake date before associating it with an attempt.
                registered = db.execute("SELECT checksum FROM archives LIMIT 2").fetchall()
                if len(registered) == 1:
                    checksum = registered[0][0]
                    path = base / "Archives" / (checksum + ".zip")
                    if re.fullmatch("[0-9a-f]{64}", checksum) and path.is_file():
                        try:
                            if digest(path) == checksum:
                                latest = max(read_sleep(path), default=None)
                                db.execute("""UPDATE attempts SET checksum=?
                                           WHERE status='succeeded' AND latest_wake_date=?""", (checksum, latest))
                        except (CollectError, OSError):
                            pass  # Keep unverified attempts unlinked.
    (base / DATABASE).chmod(0o600)
    return db


def timestamp(value):
    value = (value or "").strip()
    # macOS Python 3.9 accepts only 3 or 6 fractional digits and ±HH:MM.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    value = re.sub(r"([+-][0-9]{2})([0-9]{2})$", r"\1:\2", value)
    value = re.sub(r"(?<=:[0-9]{2})[.,]([0-9]+)(?=[+-])",
                   lambda match: "." + match[1][:6].ljust(6, "0"), value)
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("offset")
    return result


def read_sleep(path):
    """Validate each interval before recording its local wake date."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = [f for f in archive.infolist()
                       if PurePosixPath(f.filename).name.casefold() == "sleep.csv"
                       and "__MACOSX" not in PurePosixPath(f.filename).parts]
            if len(members) != 1:
                raise CollectError("The ZIP must contain exactly one sleep.csv.")
            days = set()
            with archive.open(members[0]) as stream, io.TextIOWrapper(
                    stream, encoding="utf-8-sig", newline="") as contents:
                reader = csv.DictReader(contents, strict=True)
                columns = reader.fieldnames or []
                if not {"start_ts", "end_ts"}.issubset(columns):
                    raise CollectError("Missing start_ts or end_ts in sleep.csv.")
                if len(columns) != len(set(columns)):
                    raise CollectError("Duplicate column name in sleep.csv.")
                for row in reader:
                    if None in row:
                        raise CollectError("Unexpected extra field in sleep.csv.")
                    start, end = timestamp(row["start_ts"]), timestamp(row["end_ts"])
                    if not timedelta() < end - start <= timedelta(days=1):
                        raise CollectError("Invalid sleep interval in sleep.csv.")
                    days.add(end.date().isoformat())
            return days
    except (ValueError, csv.Error, zipfile.BadZipFile, zlib.error, RuntimeError, EOFError) as exc:
        raise CollectError("Cannot read the ZIP, CSV or timezone-qualified timestamp.") from exc


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(db, base, path):
    """Archive and index a ZIP before removing its incoming copy. Safe to retry."""
    days = read_sleep(path)
    checksum = digest(path)
    archive = base / "Archives" / (checksum + ".zip")
    path.chmod(0o600)
    try:
        os.link(path, archive)
    except FileExistsError:
        if digest(archive) != checksum:
            raise CollectError("The existing archive failed its integrity check.")
    with db:
        old_changes = db.total_changes
        db.executemany("INSERT OR IGNORE INTO nights VALUES (?)", [(d,) for d in days])
        new_days = db.total_changes - old_changes
        db.execute("INSERT OR IGNORE INTO archives VALUES (?)", (checksum,))
    # The archive and its index are durable at this point.
    path.unlink()
    return max(days, default=None), new_days, checksum


def incoming(base):
    result = {}
    for path in (base / "Incoming").iterdir():
        if path.suffix.lower() != ".zip" or path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        result[path] = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
    return result


def check_session():
    try:
        raw = subprocess.check_output(["/usr/sbin/ioreg", "-n", "Root", "-d1", "-a"],
                                      stderr=subprocess.DEVNULL, timeout=15)
        info = plistlib.loads(raw)
        if isinstance(info, list):
            info = info[0]
        for user in info.get("IOConsoleUsers", []):
            if (user.get("kCGSSessionUserIDKey") == os.getuid()
                    and user.get("kCGSSessionOnConsoleKey")
                    and not info.get("IOConsoleLocked")
                    and not user.get("CGSSessionScreenIsLocked")):
                return
    except (subprocess.SubprocessError, OSError, ValueError, IndexError, AttributeError) as exc:
        raise CollectError("Could not verify the graphical session.") from exc
    raise CollectError("An active, unlocked graphical session is required.")


def export(base):
    workflow = base / "Export.workflow"
    if not workflow.exists():
        raise CollectError("Export.workflow is missing from the collection directory.")
    check_session()
    try:
        result = subprocess.run(["/usr/bin/automator", str(workflow)], cwd=base,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise CollectError("The Automator workflow timed out.") from exc
    # Only recognized workflow messages are suitable for logging.
    messages = {
        "ACCESSIBILITY": "Allow Even R1 Ring Collector for Mac in System Settings > Privacy & Security > Accessibility.",
        "APP_DATA_PERMISSION": "macOS denied Even R1 Ring Collector for Mac access to the Even export.",
        "EVEN_UNAVAILABLE": "Could not open the Even window.",
        "EVEN_NAVIGATION": "The collector could not reach the export button in Even.",
        "EVEN_SHARE": "The collector could not dismiss the Even export panel.",
        "EVEN_TIMEOUT": "Even did not finish its export in time.",
        "EVEN_IMPORT": "The collector could not copy the new export into Incoming.",
    }
    match = re.search(rb"Even R1:\s*([A-Z_]+)\b", result.stdout)
    if match:
        key = match[1].decode("ascii")
        if key in messages:
            raise CollectError("%s — %s" % (key, messages[key]))
    if b"Even R1: helper did not complete" in result.stdout:
        raise CollectError("Even R1 Ring Collector for Mac exited before reporting its result.")
    if result.returncode:
        error = result.stdout.lower()
        if any(word in error for word in [b"-1743", b"-25211", b"not authorized",
                                          b"not allowed", b"assistive access", b"accessibility"]):
            raise CollectError("Automator reported that macOS denied permission.")
        raise CollectError("Automator failed (exit code %d)." % result.returncode)


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(base=BASE, mode="manual", exporter=export):
    setup(base)
    with (base / ".collection.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            message = "A collection is already running."
            with closing(connect(base)) as db, db:
                db.execute("""INSERT INTO attempts(start, mode, status, detail, end)
                              VALUES (?, ?, 'busy', ?, ?)""", (now(), mode, message, now()))
            return 75, message
        with closing(connect(base)) as db:
            with db:
                db.execute("""UPDATE attempts SET status='interrupted', end=?,
                           detail='Collection was interrupted.' WHERE status='running'""", (now(),))
                run_id = db.execute("INSERT INTO attempts(start, mode, status) VALUES (?, ?, 'running')",
                                    (now(), mode)).lastrowid
            try:
                # Recover earlier files separately from the evidence of a new export.
                for path in incoming(base):
                    try:
                        ingest(db, base, path)
                    except CollectError:
                        pass  # Keep unverified files in Incoming.
                before = incoming(base)
                exporter(base)
                new = [p for p, sig in incoming(base).items() if sig != before.get(p)]
                if len(new) != 1:
                    raise CollectError("Expected exactly one new export ZIP.")
                latest, count, checksum = ingest(db, base, new[0])
                if latest is None:
                    detail = "Export verified. Even supplied no sleep sessions."
                elif count:
                    detail = "Export verified. New wake dates recorded."
                else:
                    detail = "Export verified. No new wake dates."
                status, code = "succeeded", 0
            except (CollectError, OSError, sqlite3.Error) as exc:
                latest = checksum = None
                detail = str(exc) if isinstance(exc, CollectError) else "Local storage error."
                status, code = "failed", 1
            with db:
                db.execute("""UPDATE attempts SET status=?, detail=?, latest_wake_date=?, end=?,
                              checksum=? WHERE id=?""", (status, detail, latest, now(), checksum, run_id))
            return code, detail


def evidence(db):
    """Check whether two scheduled exports show consecutive recent nights."""
    high_water = None
    prior_fresh = None
    for row in db.execute("""SELECT latest_wake_date, end FROM attempts
                             WHERE mode='launchd' AND status='succeeded'
                               AND latest_wake_date IS NOT NULL ORDER BY id"""):
        night = date.fromisoformat(row["latest_wake_date"])
        if high_water is not None and night <= high_water:
            continue  # Ignore an old ZIP followed by a replay of the latest export.
        high_water = night
        seen = datetime.fromisoformat(row["end"]).date()
        if timedelta() <= seen - night <= timedelta(days=1):
            if prior_fresh == night - timedelta(days=1):
                return True
            prior_fresh = night
    return False
