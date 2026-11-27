"""Read verified Even sleep timelines into the paired iPhone's private, replayable feed."""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import sys
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import timezone
from pathlib import Path, PurePosixPath

import collection
from archive_match import DataError, MAX_ARCHIVE_BYTES, MAX_CSV_BYTES, READ_ERRORS
from mcp_server import row_seconds


KINDS = ("awake", "rem", "core", "deep")
PAGE_SIZE = 8
SUPPORT = Path.home() / "Library" / "Application Support"
COMPANION = SUPPORT / "R1 Sleep Companion"
PUBLIC = (collection.BASE, "collection.sqlite3", "attempts", "status", "succeeded",
          "checksum", "end", "latest_wake_date")
PILOT = (SUPPORT / "Even R1 Mac", "suivi.sqlite3", "essais", "etat", "réussi",
         "empreinte", "fin", "dernier_jour")


class FeedError(Exception):
    """A diagnostic safe to show without disclosing health data."""


class CursorResetError(FeedError):
    """The client's cursor belongs to a newer revision of the Mac index."""


def source_archives(spec, priority):
    base, filename, attempts, status, success, fingerprint, finished, wake = spec
    path = base / filename
    if not path.exists():
        return [], 0
    if path.is_symlink() or not path.is_file():
        raise FeedError("The sleep collection index is unavailable.")
    sources = []
    gaps = 0
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        columns = {row[1] for row in db.execute(f'PRAGMA table_info("{attempts}")')}
        fingerprints = db.execute(f'SELECT "{fingerprint}" FROM archives LIMIT 2').fetchall()
        candidate = fingerprints[0][0] if len(fingerprints) == 1 else None
        has_link = fingerprint in columns
        link = f'a."{fingerprint}"' if has_link else "NULL"
        rows = db.execute(f'''
            SELECT a.id, a."{finished}", a."{wake}", {link}, r."{fingerprint}"
            FROM "{attempts}" AS a LEFT JOIN archives AS r ON {link} = r."{fingerprint}"
            WHERE a."{status}"=? ORDER BY a.id
        ''', (success,))
        for run_id, completion, wake_date, linked, registered in rows:
            digest = linked if linked is not None else candidate
            # Older trackers had no per-attempt link. A single registered ZIP is
            # eligible only when its verified latest wake date matches the attempt.
            expected = () if linked is not None else (wake_date,)
            if ((linked is not None and registered != linked) or not isinstance(digest, str)
                    or not re.fullmatch("[a-f0-9]{64}", digest)):
                gaps += 1
                continue
            try:
                observed = collection.timestamp(completion).astimezone(timezone.utc)
            except (ValueError, TypeError, OverflowError):
                gaps += 1
                continue
            order = (observed.isoformat(timespec="microseconds"), priority, run_id)
            sources.append((order, base, digest, expected))
    return sources, gaps


def timeline(row, start, end):
    seconds = (end - start).total_seconds()
    totals = row_seconds(row, seconds, detailed=True)
    if totals is None or sum(totals) != seconds:
        return None
    # row_seconds has checked stage types, duplicate JSON keys, and duration totals.
    runs = []
    timestamp = start.timestamp()
    for stage in json.loads(row["stages"]):
        duration = stage["half_minutes"] * 30
        if not duration:
            continue
        kind = KINDS[stage["type"]]
        stop = timestamp + duration
        if runs and runs[-1]["kind"] == kind:
            runs[-1]["end"] = stop
        else:
            runs.append({"start": timestamp, "end": stop, "kind": kind})
        timestamp = stop
    return json.dumps(runs, separators=(",", ":")) if runs else None


def verified_rows(base, checksum):
    path = base / "Archives" / (checksum + ".zip")
    if path.parent.is_symlink():
        raise DataError()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_BYTES:
            raise DataError()
        hash_value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(block)
        if hash_value.hexdigest() != checksum:
            raise DataError()
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            members = [m for m in archive.infolist()
                       if PurePosixPath(m.filename).name.casefold() == "sleep.csv"
                       and "__MACOSX" not in PurePosixPath(m.filename).parts]
            if len(members) != 1 or members[0].file_size > MAX_CSV_BYTES:
                raise DataError()
            with archive.open(members[0]) as raw, io.TextIOWrapper(
                    raw, encoding="utf-8-sig", newline="") as contents:
                reader = csv.DictReader(contents, strict=True)
                columns = reader.fieldnames or []
                if (not {"start_ts", "end_ts"}.issubset(columns)
                        or len(columns) != len(set(columns))):
                    raise DataError()
                records = defaultdict(set)
                latest = None
                for index, row in enumerate(reader):
                    if index >= 100_000 or None in row:
                        raise DataError()
                    start = collection.timestamp(row["start_ts"])
                    end = collection.timestamp(row["end_ts"])
                    if not 0 < (end - start).total_seconds() <= 86400:
                        raise DataError()
                    day = end.date().isoformat()
                    latest = max(latest or day, day)
                    if "source" in row and row["source"] != "R1":
                        continue
                    records[start.timestamp(), end.timestamp()].add((day, timeline(row, start, end)))
    return records, latest


def observations(records):
    # Adjacent runs and separate naps are valid; all intervals in an overlapping
    # chain are withheld, even if they happen to have the same daily stage totals.
    group = []
    group_end = None
    for (start, end), options in sorted(records.items()):
        if group and start >= group_end:
            yield from resolve_group(group)
            group = []
        group.append((start, end, options))
        group_end = max(group_end or end, end)
    yield from resolve_group(group)


def resolve_group(group):
    for start, end, options in group:
        if len(group) == 1 and len(options) == 1:
            day, stages = next(iter(options))
        else:
            day, stages = None, None
        yield start, end, day, stages


def new_session_id(db, start, end):
    # A correction may move the original session's start but preserve its ID.
    # A later, separate nap can then occupy that original start instant.
    key = "even-r1-sleep-v1/" + start.hex()
    session_id = hashlib.sha256(key.encode("ascii")).hexdigest()
    while db.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone():
        key += "/" + end.hex()
        session_id = hashlib.sha256(key.encode("ascii")).hexdigest()
    return session_id


def open_ledger(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise FeedError("The iPhone sync folder is unavailable.")
    directory.chmod(0o700)
    path = directory / "sleep-feed.sqlite3"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise FeedError("The iPhone sync index is unavailable.")
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS imports (
            observed TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(observed, digest)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, start REAL NOT NULL, end REAL NOT NULL, wake TEXT NOT NULL,
            stages TEXT NOT NULL, version INTEGER NOT NULL, position INTEGER NOT NULL UNIQUE,
            observed TEXT NOT NULL, visible INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS boundaries ON sessions(start, end);
        CREATE TABLE IF NOT EXISTS issues (
            start REAL NOT NULL, end REAL NOT NULL, observed TEXT NOT NULL, PRIMARY KEY(start,end)
        );
        CREATE TABLE IF NOT EXISTS counter (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER NOT NULL);
        INSERT OR IGNORE INTO counter VALUES(1,0);
    """)
    return db


def store_observation(db, start, end, day, stages, observed):
    prior = db.execute("SELECT * FROM sessions WHERE start < ? AND end > ?", (end, start)).fetchall()
    # Only an unchanged boundary can identify a corrected session. A split, merge,
    # or a shift of both ends could be another session and needs better source data.
    matches = [r for r in prior if r["start"] == start or r["end"] == end]
    if any(r["observed"] > observed for r in prior):
        return
    newer_issue = db.execute("SELECT 1 FROM issues WHERE start < ? AND end > ? AND observed > ? LIMIT 1",
                             (end, start, observed)).fetchone()
    if newer_issue:
        return
    if stages is None or (prior and (len(prior) != 1 or len(matches) != 1)):
        db.execute("""INSERT OR REPLACE INTO issues VALUES (?,?,?)""", (start, end, observed))
        db.execute("UPDATE sessions SET visible=0, observed=? WHERE start < ? AND end > ?",
                   (observed, end, start))
        return
    db.execute("DELETE FROM issues WHERE start=? AND end=?", (start, end))
    old = matches[0] if matches else None
    if old and old["stages"] == stages and old["wake"] == day and old["visible"]:
        db.execute("UPDATE sessions SET observed=? WHERE id=?", (observed, old["id"]))
        return
    if old:
        session_id = old["id"]
        version = old["version"] + 1
    else:
        session_id = new_session_id(db, start, end)
        version = 1
    db.execute("UPDATE counter SET value=value+1 WHERE id=1")
    db.execute("""
        INSERT OR REPLACE INTO sessions(id,start,end,wake,stages,version,position,observed,visible)
        VALUES(?,?,?,?,?,?,(SELECT value FROM counter WHERE id=1),?,1)
    """, (session_id, start, end, day, stages, version, observed))


def page(after, specs=(PILOT, PUBLIC), directory=COMPANION):
    if not 0 <= after <= 2**63 - 1:
        raise FeedError("Invalid sync cursor.")
    archives = []
    skipped = 0
    for priority, spec in enumerate(specs):
        try:
            sources, gaps = source_archives(spec, priority)
        except (FeedError, *READ_ERRORS):
            skipped += 1
            continue
        archives.extend(sources)
        skipped += gaps
    if not archives:
        raise FeedError("No verified sleep export is available. Run a collection on the Mac.")
    with closing(open_ledger(directory)) as db:
        valid = set()
        failed = set()
        completed = {(r["observed"], r["digest"]) for r in db.execute("SELECT * FROM imports")}
        last_snapshot = None
        for order, base, checksum, expected in sorted(archives):
            stamp, priority, run_id = order
            observed = f"{stamp}/{priority}/{run_id:020d}"
            if (observed, checksum) in completed:
                valid.add(checksum)
                continue
            # A later export can reinstate a previously seen sequence. Process each
            # successful observation once, including A -> B -> A. Keep only the
            # most recent parsed ZIP in memory to handle adjacent repeated exports.
            if last_snapshot != (base, checksum):
                try:
                    records, latest = verified_rows(base, checksum)
                except READ_ERRORS:
                    failed.add(checksum)
                    continue
                last_snapshot = (base, checksum)
            if expected and latest != expected[0]:
                failed.add(checksum)
                continue
            with db:
                db.execute("BEGIN IMMEDIATE")
                inserted = db.execute("INSERT OR IGNORE INTO imports VALUES(?,?)",
                                      (observed, checksum)).rowcount
                if inserted:
                    for args in observations(records):
                        store_observation(db, *args, observed)
            valid.add(checksum)
        if not valid:
            raise FeedError("The Mac could not verify any available sleep archive.")
        db.execute("BEGIN")
        high = db.execute("SELECT value FROM counter WHERE id=1").fetchone()[0]
        if after > high:
            raise CursorResetError("The Mac sync index was reset. Rescan from the beginning.")
        rows = db.execute("""SELECT * FROM sessions WHERE visible=1 AND position>?
                             ORDER BY position LIMIT ?""", (after, PAGE_SIZE + 1)).fetchall()
        sessions = [{"id": r["id"], "version": r["version"], "wakeDate": r["wake"],
                     "stages": json.loads(r["stages"])} for r in rows[:PAGE_SIZE]]
        more = len(rows) > PAGE_SIZE
        cursor = rows[PAGE_SIZE - 1]["position"] if more else high
        skipped += len(failed - valid) + db.execute("SELECT count(*) FROM issues").fetchone()[0]
        latest = db.execute("SELECT MAX(wake) FROM sessions WHERE visible=1").fetchone()[0]
        return {"sessions": sessions, "cursor": cursor, "more": more, "skipped": skipped,
                "latestWakeDate": latest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("after", type=int, help="Last completed sync cursor")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(page(args.after), separators=(",", ":")))
    except CursorResetError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except FeedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except READ_ERRORS:
        print("The verified sleep feed is temporarily unavailable.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
