"""Read the latest Even Health cards observed on this Mac."""
import argparse
import json
import math
import os
import re
import sqlite3
import stat
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import collection
import archive_match


UNITS = {
    "steps": {"steps"},
    "calories": {"kcal"},
    "heartRate": {"bpm"},
    "hrv": {"ms"},
    "spo2": {"%"},
    "skinTemperature": {"°C", "°F"},
}
MEANING = (
    "Latest cards shown by Even. Each recorded_at timestamp identifies a local observation. "
    "Recency expresses the age shown on the card at that time, in English. "
    "The observation date alone cannot establish a measurement date or daily total."
)
CARD_TOOL = {
    "name": "latest_readings",
    "description": ("Read the latest requested Health cards. An optional csv_batch identifies "
                    "the local date of a matching R1 batch by value and recency. "
                    "The exact measurement time is unknown. " + MEANING),
    "inputSchema": {
        "type": "object",
        "properties": {"categories": {"type": "array", "minItems": 1,
                       "maxItems": len(UNITS), "uniqueItems": True,
                       "items": {"type": "string", "enum": list(UNITS)}}},
        "required": ["categories"],
        "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
}
HISTORY_DB = "card_history.sqlite3"
MAX_CHANGES = 3 * 31 * len(UNITS)
HISTORY_MEANING = (
    "History begins with the first local observation of each card. "
    "It records that value and subsequent changes in value or unit. "
    "Dates represent when the Mac observed the displayed values. Recency expresses "
    "the age shown at the time, in English. The measurement date is unknown. Steps and calories "
    "can be running totals. Do not add successive readings."
)
HISTORY_TOOL = {
    "name": "reading_history",
    "description": "Changes observed over an inclusive range of 1 to 31 local dates. " + HISTORY_MEANING,
    "inputSchema": {"type": "object", "properties": {
        **CARD_TOOL["inputSchema"]["properties"],
        "start": {"type": "string", "format": "date"}, "end": {"type": "string", "format": "date"}},
        "required": ["categories", "start", "end"], "additionalProperties": False},
    "annotations": CARD_TOOL["annotations"],
}
LIMIT = 16 * 1024
# Return only recognizable recency labels, preserving their displayed precision.
RECENCY = re.compile(
    r"(?:just now|now|today|yesterday|maintenant|à l[’']instant|aujourd[’']hui|hier|"
    r"(?:[0-9]{1,5}|an?|one) (?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?) ago|"
    r"il y a (?:[0-9]{1,5}|une?) (?:secondes?|minutes?|heures?|jours?|semaines?|mois|ans?|années?|s|min|h|j))",
    re.IGNORECASE,
)
FRENCH_RECENCY = {"maintenant": "now", "à l'instant": "just now", "aujourd'hui": "today", "hier": "yesterday"}
FRENCH_UNITS = {
    "s": "second", "seconde": "second", "min": "minute", "minute": "minute",
    "h": "hour", "heure": "hour", "j": "day", "jour": "day", "semaine": "week",
    "mois": "month", "an": "year", "année": "year",
}


def english_recency(label):
    """Render a validated device label without converting its unit or guessing an absolute date."""
    words = " ".join(label.casefold().split()).replace("’", "'")
    if words in FRENCH_RECENCY:
        return FRENCH_RECENCY[words]
    if words.startswith("il y a "):
        amount, unit = words[7:].split()
        number = 1 if amount in ("un", "une") else int(amount)
        english_unit = FRENCH_UNITS.get(unit) or FRENCH_UNITS[unit.removesuffix("s")]
        return f"{number} {english_unit}{'' if number == 1 else 's'} ago"
    return label


class SnapshotError(Exception):
    pass


class HistoryError(Exception):
    pass


def date_range(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"start", "end"}:
        raise ValueError()
    dates = []
    for key in ("start", "end"):
        value = arguments[key]
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError()
        dates.append(date.fromisoformat(value))
    if not timedelta() <= dates[1] - dates[0] < timedelta(days=31):
        raise ValueError()
    return dates


def categories(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"categories"}:
        raise ValueError()
    names = arguments["categories"]
    if (not isinstance(names, list) or not 1 <= len(names) <= len(UNITS)
            or any(not isinstance(n, str) or n not in UNITS for n in names)
            or len(names) != len(set(names))):
        raise ValueError()
    return names


def unique_keys(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise SnapshotError()
    return result


def capture_time(when):
    if not isinstance(when, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})", when):
        raise ValueError()
    return collection.timestamp(when)


def load_snapshot(base):
    fd = os.open(base / "readings.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > LIMIT):
            raise SnapshotError()
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise SnapshotError()
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    if (not isinstance(data, dict) or type(data.get("version")) is not int
            or data["version"] != 1 or not isinstance(data.get("metrics"), dict)):
        raise SnapshotError()
    timestamp = capture_time(data.get("recorded_at"))
    if timestamp > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise SnapshotError()
    return data, timestamp


def card(name, candidate, when, timestamp):
    if not isinstance(candidate, dict):
        return None
    value, unit, recency = (candidate.get(k) for k in ("value", "unit", "recency"))
    if type(value) not in (int, float) or not isinstance(unit, str) or unit not in UNITS[name]:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if name != "skinTemperature" and value < 0:
        return None
    if name == "steps" and isinstance(value, float) and not value.is_integer():
        return None
    if name == "spo2" and value > 100:
        return None
    if not isinstance(recency, str) or len(recency) > 80:
        return None
    if any(not ch.isprintable() and ch not in "\u00a0\u202f" for ch in recency):
        return None
    normalized = " ".join(recency.split())
    if not RECENCY.fullmatch(normalized):
        return None
    captured = candidate.get("recorded_at", when)
    try:
        if capture_time(captured) > timestamp:
            return None
    except ValueError:
        return None
    return {"value": value, "unit": unit, "recency": recency, "recorded_at": captured}


def observed_cards(base, names):
    try:
        snapshot, timestamp = load_snapshot(base)
    except (OSError, ValueError, RecursionError, SnapshotError) as exc:
        raise SnapshotError() from exc
    values = {}
    for name in names:
        value = card(name, snapshot["metrics"].get(name), snapshot["recorded_at"], timestamp)
        if value is not None:
            values[name] = value
    return snapshot["recorded_at"], values


def last_cards(base, names, *, include_batch=True):
    recorded_at, values = observed_cards(base, names)
    if include_batch:
        for name, batch in archive_match.corroborate(base, values).items():
            values[name]["csv_batch"] = batch
    for reading in values.values():
        reading["recency"] = english_recency(reading["recency"])
    return {"recorded_at": recorded_at, "description": MEANING,
            "metrics": values, "unavailable": [n for n in names if n not in values]}


def history_connection(base, writable):
    path = base / HISTORY_DB
    flags = os.O_RDWR | os.O_CREAT if writable else os.O_RDONLY
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise HistoryError()
        return sqlite3.connect(path.as_uri() + ("?mode=rw" if writable else "?mode=ro"),
                               uri=True, timeout=10)
    finally:
        os.close(fd)


def utc_key(stamp):
    return capture_time(stamp).astimezone(timezone.utc).isoformat(timespec="microseconds")


def record_changes(base):
    recorded_at, values = observed_cards(base, UNITS)
    instant = utc_key(recorded_at)
    count = 0
    try:
        with closing(history_connection(base, True)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS capture (id INTEGER PRIMARY KEY, utc TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS status (
                category TEXT PRIMARY KEY, utc TEXT NOT NULL, value TEXT NOT NULL, unit TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS changes (
                category TEXT NOT NULL, utc TEXT NOT NULL, observation TEXT NOT NULL,
                day TEXT NOT NULL, value TEXT NOT NULL, unit TEXT NOT NULL,
                recency TEXT NOT NULL, initial INTEGER NOT NULL, PRIMARY KEY (category,utc))""")
            previous = db.execute("SELECT utc FROM capture WHERE id=1").fetchone()
            if previous and instant <= previous[0]:
                return 0
            for name, metric in values.items():
                stamp = metric["recorded_at"]
                utc = utc_key(stamp)
                value, unit = metric["value"], metric["unit"]
                prior = db.execute("SELECT utc,value,unit FROM status WHERE category=?", (name,)).fetchone()
                if prior and utc <= prior[0]:
                    continue
                stored = json.dumps(value, allow_nan=False)
                if not prior or (json.loads(prior[1]), prior[2]) != (value, unit):
                    db.execute("INSERT INTO changes VALUES (?,?,?,?,?,?,?,?)",
                               (name, utc, stamp, stamp[:10], stored, unit, metric["recency"], int(not prior)))
                    count += 1
                # Advance the watermark even when the displayed value is unchanged.
                db.execute("INSERT OR REPLACE INTO status VALUES (?,?,?,?)", (name, utc, stored, unit))
            db.execute("INSERT OR REPLACE INTO capture VALUES (1,?)", (instant,))
    except (OSError, sqlite3.Error, ValueError, OverflowError) as exc:
        raise HistoryError() from exc
    return count


def history(base, names, first, last):
    starts = dict.fromkeys(names)
    changes = []
    try:
        with closing(history_connection(base, False)) as db, db:
            db.execute("BEGIN")
            for name in names:
                first_seen = db.execute("""SELECT observation FROM changes WHERE category=?
                                        ORDER BY utc LIMIT 1""", (name,)).fetchone()
                if first_seen:
                    starts[name] = first_seen[0]
            placeholders = ",".join("?" for _ in names)
            rows = db.execute("""SELECT category,observation,value,unit,recency,initial
                              FROM changes WHERE category IN (""" + placeholders + """)
                              AND day BETWEEN ? AND ? ORDER BY utc DESC, category DESC LIMIT ?""",
                              (*names, first.isoformat(), last.isoformat(), MAX_CHANGES + 1))
            for name, stamp, value, unit, recency, initial in rows:
                if not isinstance(recency, str) or not RECENCY.fullmatch(" ".join(recency.split())):
                    raise HistoryError()
                changes.append({"category": name, "observed_at": stamp, "value": json.loads(value),
                                "unit": unit, "recency": english_recency(recency), "initial": bool(initial)})
    except FileNotFoundError:
        pass
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HistoryError() from exc
    return {"description": HISTORY_MEANING, "first_observation": starts,
            "changes": list(reversed(changes[:MAX_CHANGES])),
            "truncated_to_latest": len(changes) > MAX_CHANGES, "limit": MAX_CHANGES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--record", action="store_true", help="Record changes in local card history.")
    actions.add_argument("--history", nargs=2, metavar=("START", "END"), help="Inclusive local dates.")
    parser.add_argument("categories", nargs="*", metavar="CATEGORY", help=", ".join(UNITS))
    args = parser.parse_args()
    try:
        if args.record:
            if args.categories:
                parser.error("--record does not take categories")
            record_changes(collection.BASE)
            return
        names = categories({"categories": args.categories})
        if args.history:
            first, last = date_range(dict(zip(("start", "end"), args.history)))
            result = history(collection.BASE, names, first, last)
        else:
            result = last_cards(collection.BASE, names)
        print(json.dumps(result, ensure_ascii=False))
    except ValueError:
        parser.exit(2, "Choose one to six distinct categories and an inclusive range of 1 to 31 dates.\n")
    except SnapshotError:
        parser.exit(1, "No verified local snapshot of the Even cards is available.\n")
    except HistoryError:
        parser.exit(1, "Local card history is unavailable.\n")


if __name__ == "__main__":
    main()
