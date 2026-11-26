"""Match displayed Even cards to dated R1 export batches."""
import csv
import hashlib
import io
import os
import re
import sqlite3
import stat
import zipfile
import zlib
from collections import defaultdict
from contextlib import closing, contextmanager
from decimal import Decimal, localcontext
from pathlib import PurePosixPath

import collection


MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_CSV_BYTES = 32 * 1024 * 1024
MAX_TOTAL_CSV_BYTES = 64 * 1024 * 1024
# Archive member, comparable column and card unit. Temperature cards have no matching export.
SPECS = {
    "steps": ("steps.csv", "value", "steps"),
    "calories": ("calories.csv", "active", "kcal"),
    "heartRate": ("heart_rate.csv", "avg", "bpm"),
    "hrv": ("hrv.csv", "avg", "ms"),
    "spo2": ("blood_oxygen.csv", "avg", "%"),
}


class DataError(Exception):
    pass


READ_ERRORS = (DataError, OSError, ValueError, EOFError, RuntimeError, OverflowError,
               csv.Error, sqlite3.Error, zipfile.BadZipFile, zlib.error)


def latest_digest(base):
    uri = (base / collection.DATABASE).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=3)) as db:
        row = db.execute("""
            SELECT attempts.checksum,archives.checksum FROM attempts
            LEFT JOIN archives ON archives.checksum = attempts.checksum
            WHERE attempts.status = 'succeeded' ORDER BY attempts.id DESC LIMIT 1
        """).fetchone()
    if not row or not isinstance(row[0], str) or row[0] != row[1] or not re.fullmatch(r"[a-f0-9]{64}", row[0]):
        raise DataError()
    return row[0]


@contextmanager
def verified_stream(base):
    digest = latest_digest(base)
    fd = os.open(base / "Archives" / (digest + ".zip"), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_BYTES:
            raise DataError()
        checksum = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
        if checksum.hexdigest() != digest:
            raise DataError()
        stream.seek(0)
        yield stream


def expected_age(recency):
    words = " ".join(recency.casefold().split())
    en = re.fullmatch(r"([0-9]{1,5}|an?|one) (hours?|hrs?|minutes?|mins?) ago", words)
    fr = re.fullmatch(r"il y a ([0-9]{1,5}|une?) (heures?|h|minutes?|min)", words)
    match = en or fr
    if match:
        amount, unit = match.groups()
        step = 3600 if unit.startswith("h") else 60
        return (int(amount) if amount.isdigit() else 1) * step, step
    return None


def numeric(text, name):
    if not isinstance(text, str) or not re.fullmatch(r"[+]?[0-9]{1,16}(?:\.[0-9]{1,12})?", text.strip()):
        return None
    value = Decimal(text.strip())
    if name == "steps" and value != value.to_integral_value():
        return None
    if name == "spo2" and value > 100:
        return None
    return value


def match_batch(archive, member, name, card, age):
    _, field, unit = SPECS[name]
    average = field == "avg"
    required = {"timestamp", "source", "value", "ty"} if average else {"timestamp", "source", field}
    groups = defaultdict(dict)
    days = defaultdict(set)
    conflicting = set()
    latest = None
    with archive.open(member) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames or []
        if not required.issubset(columns) or len(columns) != len(set(columns)):
            return None
        for index, row in enumerate(reader):
            if index >= 100_000 or None in row:
                raise DataError()
            if row["source"] != "R1":
                continue
            stamp = collection.timestamp(row["timestamp"])
            day = stamp.date()
            kind = row["ty"] if average else field
            value = numeric(row["value"] if average else row[field], name)
            if latest is None or stamp > latest:
                latest = stamp
            values = groups[stamp]
            if (value is None or (average and kind not in ("min", "avg", "max"))
                    or kind in values and values[kind] != value):
                conflicting.add(stamp)
            values[kind] = value
            days[stamp].add((day, stamp.utcoffset()))
    if latest is None or latest in conflicting or len(days[latest]) != 1:
        return None
    seconds = (collection.timestamp(card["recorded_at"]) - latest).total_seconds()
    target, tolerance = age
    if seconds < 0 or abs(seconds - target) > tolerance:
        return None
    local_day, local_offset = next(iter(days[latest]))
    if average:
        stats = groups[latest]
        value = stats.get("avg")
        if value is None or stats.get("min", value) > value or stats.get("max", value) < value:
            return None
        meaning = "Average of the latest R1 batch. Its duration is unknown."
    else:
        value = Decimal(0)
        with localcontext() as context:
            context.prec = 40
            for stamp, labels in days.items():
                if any(day == local_day for day, _ in labels):
                    if labels != {(local_day, local_offset)} or stamp in conflicting:
                        return None
                    value += groups[stamp][field]
        meaning = ("Partial R1 step total observed on this date." if name == "steps" else
                   "Partial R1 active-calorie total observed on this date.")
    if card["unit"] != unit or Decimal(str(card["value"])) != value:
        return None
    return {"local_date": local_day.isoformat(), "source": "R1", "match": meaning}


def corroborate(base, cards):
    selected = {name: (card, expected_age(card["recency"])) for name, card in cards.items()
                if name in SPECS and card["unit"] == SPECS[name][2]}
    selected = {name: pair for name, pair in selected.items() if pair[1] is not None}
    if not selected:
        return {}
    matches = {}
    try:
        with verified_stream(base) as stream, zipfile.ZipFile(stream) as archive:
            files = defaultdict(list)
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                if "__MACOSX" not in path.parts:
                    files[path.name.casefold()].append(member)
            budget = MAX_TOTAL_CSV_BYTES
            for name, (card, age) in selected.items():
                members = files[SPECS[name][0]]
                if len(members) != 1 or members[0].file_size > min(MAX_CSV_BYTES, budget):
                    continue
                budget -= members[0].file_size
                try:
                    match = match_batch(archive, members[0], name, card, age)
                    if match:
                        matches[name] = match
                except READ_ERRORS:
                    continue
    except READ_ERRORS:
        return {}
    return matches
