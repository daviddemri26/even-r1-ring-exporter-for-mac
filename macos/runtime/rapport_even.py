"""Lecture des dernières cartes Health affichées par Even sur ce Mac."""
import argparse
import json
import math
import os
import re
import sqlite3
import stat
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import collecte
import rapprochement_even


UNITS = {
    "steps": {"pas"},
    "calories": {"kcal"},
    "heartRate": {"bpm"},
    "hrv": {"ms"},
    "spo2": {"%"},
    "skinTemperature": {"°C", "°F"},
}
MEANING = (
    "Dernières cartes publiées par Even. Chaque recorded_at date la capture concernée. "
    "Le libellé recency est celui affiché à cet instant pour la carte. "
    "Les valeurs ne constituent pas un relevé ni un cumul pour la date de la requête."
)
CARD_TOOL = {
    "name": "dernier_releve_even",
    "description": ("Lit les dernières cartes Health demandées. Un lot_csv éventuel indique "
                    "la date locale du lot R1 dont la valeur et l’ancienneté concordent, "
                    "sans établir l’heure exacte de mesure. " + MEANING),
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
HISTORY_DB = "cartes_historique.sqlite3"
MAX_CHANGES = 3 * 31 * len(UNITS)
HISTORY_MEANING = (
    "L’historique débute à la première observation locale de chaque carte. "
    "Il conserve cette première valeur puis seulement les changements de valeur ou d’unité. "
    "Les dates sont celles où le Mac a vu les valeurs affichées, et recency est le libellé "
    "affiché à cet instant. La date de mesure reste inconnue. Les pas et calories "
    "sont les valeurs des cartes et ne doivent pas être additionnés."
)
HISTORY_TOOL = {
    "name": "evolution_cartes_even",
    "description": "Changements observés sur 1 à 31 dates locales incluses. " + HISTORY_MEANING,
    "inputSchema": {"type": "object", "properties": {
        **CARD_TOOL["inputSchema"]["properties"],
        "debut": {"type": "string", "format": "date"}, "fin": {"type": "string", "format": "date"}},
        "required": ["categories", "debut", "fin"], "additionalProperties": False},
    "annotations": CARD_TOOL["annotations"],
}
LIMIT = 16 * 1024
# Ne restituer que les libellés temporels, sans interpréter leur précision ni leur date.
RECENCY = re.compile(
    r"(?:just now|now|today|yesterday|maintenant|à l[’']instant|aujourd[’']hui|hier|"
    r"(?:[0-9]{1,5}|an?|one) (?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?) ago|"
    r"il y a (?:[0-9]{1,5}|une?) (?:secondes?|minutes?|heures?|jours?|semaines?|mois|ans?|années?|s|min|h|j))",
    re.IGNORECASE,
)


class SnapshotError(Exception):
    pass


class HistoryError(Exception):
    pass


def date_range(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"debut", "fin"}:
        raise ValueError()
    dates = []
    for key in ("debut", "fin"):
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
    return collecte.timestamp(when)


def load_snapshot(base):
    fd = os.open(base / "releves_even.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
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


def last_cards(base, names, *, avec_lot=True):
    try:
        snapshot, timestamp = load_snapshot(base)
    except (OSError, ValueError, RecursionError, SnapshotError) as exc:
        raise SnapshotError() from exc
    values = {}
    for name in names:
        value = card(name, snapshot["metrics"].get(name), snapshot["recorded_at"], timestamp)
        if value is not None:
            values[name] = value
    if avec_lot:
        for name, lot in rapprochement_even.corroborate(base, values).items():
            values[name]["lot_csv"] = lot
    return {"recorded_at": snapshot["recorded_at"], "description": MEANING,
            "metrics": values, "indisponibles": [n for n in names if n not in values]}


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


def enregistrer_changements(base):
    snapshot = last_cards(base, UNITS, avec_lot=False)
    instant = utc_key(snapshot["recorded_at"])
    count = 0
    try:
        with closing(history_connection(base, True)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS capture (id INTEGER PRIMARY KEY, utc TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS etat (
                categorie TEXT PRIMARY KEY, utc TEXT NOT NULL, valeur TEXT NOT NULL, unite TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS changements (
                categorie TEXT NOT NULL, utc TEXT NOT NULL, observation TEXT NOT NULL,
                jour TEXT NOT NULL, valeur TEXT NOT NULL, unite TEXT NOT NULL,
                anciennete TEXT NOT NULL, initiale INTEGER NOT NULL, PRIMARY KEY (categorie,utc))""")
            previous = db.execute("SELECT utc FROM capture WHERE id=1").fetchone()
            if previous and instant <= previous[0]:
                return 0
            for name, metric in snapshot["metrics"].items():
                stamp = metric["recorded_at"]
                utc = utc_key(stamp)
                value, unit = metric["value"], metric["unit"]
                prior = db.execute("SELECT utc,valeur,unite FROM etat WHERE categorie=?", (name,)).fetchone()
                if prior and utc <= prior[0]:
                    continue
                stored = json.dumps(value, allow_nan=False)
                if not prior or (json.loads(prior[1]), prior[2]) != (value, unit):
                    db.execute("INSERT INTO changements VALUES (?,?,?,?,?,?,?,?)",
                               (name, utc, stamp, stamp[:10], stored, unit, metric["recency"], int(not prior)))
                    count += 1
                # Même une valeur inchangée avance la limite contre les captures rejouées.
                db.execute("INSERT OR REPLACE INTO etat VALUES (?,?,?,?)", (name, utc, stored, unit))
            db.execute("INSERT OR REPLACE INTO capture VALUES (1,?)", (instant,))
    except (OSError, sqlite3.Error, ValueError, OverflowError) as exc:
        raise HistoryError() from exc
    return count


def evolution(base, names, first, last):
    starts = dict.fromkeys(names)
    changes = []
    try:
        with closing(history_connection(base, False)) as db, db:
            db.execute("BEGIN")
            for name in names:
                first_seen = db.execute("""SELECT observation FROM changements WHERE categorie=?
                                        ORDER BY utc LIMIT 1""", (name,)).fetchone()
                if first_seen:
                    starts[name] = first_seen[0]
            placeholders = ",".join("?" for _ in names)
            rows = db.execute("""SELECT categorie,observation,valeur,unite,anciennete,initiale
                              FROM changements WHERE categorie IN (""" + placeholders + """)
                              AND jour BETWEEN ? AND ? ORDER BY utc DESC, categorie DESC LIMIT ?""",
                              (*names, first.isoformat(), last.isoformat(), MAX_CHANGES + 1))
            for name, stamp, value, unit, recency, initial in rows:
                changes.append({"categorie": name, "observe_le": stamp, "value": json.loads(value),
                                "unit": unit, "recency": recency, "initiale": bool(initial)})
    except FileNotFoundError:
        pass
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HistoryError() from exc
    return {"description": HISTORY_MEANING, "premiere_observation": starts,
            "changements": list(reversed(changes[:MAX_CHANGES])),
            "tronque_aux_plus_recents": len(changes) > MAX_CHANGES, "limite": MAX_CHANGES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--enregistrer", action="store_true", help="Actualiser l’historique local.")
    actions.add_argument("--evolution", nargs=2, metavar=("DEBUT", "FIN"), help="Dates locales incluses.")
    parser.add_argument("categories", nargs="*", metavar="CATÉGORIE", help=", ".join(UNITS))
    args = parser.parse_args()
    try:
        if args.enregistrer:
            if args.categories:
                parser.error("--enregistrer ne prend pas de catégorie")
            enregistrer_changements(collecte.BASE)
            return
        names = categories({"categories": args.categories})
        if args.evolution:
            first, last = date_range(dict(zip(("debut", "fin"), args.evolution)))
            result = evolution(collecte.BASE, names, first, last)
        else:
            result = last_cards(collecte.BASE, names)
        print(json.dumps(result, ensure_ascii=False))
    except ValueError:
        parser.exit(2, "Choisir une à six catégories distinctes et une période de 1 à 31 dates.\n")
    except SnapshotError:
        parser.exit(1, "Aucune capture locale validée des cartes Even disponible.\n")
    except HistoryError:
        parser.exit(1, "Historique local des cartes indisponible.\n")


if __name__ == "__main__":
    main()
