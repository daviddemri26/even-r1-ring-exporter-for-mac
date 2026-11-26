"""Archivage local des exports Even et suivi des dates de sommeil disponibles."""
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
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath

BASE = Path.home() / "Library" / "Application Support" / "R1 Bridge"
DATABASE = "suivi.sqlite3"
TIMEOUT = 300


class CollectError(Exception):
    """Texte technique présentable sans journaliser les données ou le compte."""


def setup(base):
    for path in [base, base / "Reception", base / "Archives"]:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.chmod(0o700)


def connect(base):
    db = sqlite3.connect(str(base / DATABASE), timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS nuits (jour TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS archives (empreinte TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS essais (
            id INTEGER PRIMARY KEY, debut TEXT NOT NULL, mode TEXT NOT NULL,
            etat TEXT NOT NULL, detail TEXT, dernier_jour TEXT, fin TEXT, empreinte TEXT
        );
    """)
    def has_fingerprint():
        return any(row["name"] == "empreinte" for row in db.execute("PRAGMA table_info(essais)"))

    if not has_fingerprint():
        with db:
            db.execute("BEGIN IMMEDIATE")
            if not has_fingerprint():
                db.execute("ALTER TABLE essais ADD COLUMN empreinte TEXT")
                # Les anciens essais ne désignaient pas leur ZIP. Si le registre contient
                # un seul ZIP, vérifier son intégrité et sa date avant de les relier.
                registered = db.execute("SELECT empreinte FROM archives LIMIT 2").fetchall()
                if len(registered) == 1:
                    checksum = registered[0][0]
                    path = base / "Archives" / (checksum + ".zip")
                    if re.fullmatch("[0-9a-f]{64}", checksum) and path.is_file():
                        try:
                            if digest(path) == checksum:
                                latest = max(read_sleep(path), default=None)
                                db.execute("""UPDATE essais SET empreinte=?
                                           WHERE etat='réussi' AND dernier_jour=?""", (checksum, latest))
                        except (CollectError, OSError):
                            pass  # Sans preuve, conserver l'essai antérieur sans empreinte.
    (base / DATABASE).chmod(0o600)
    return db


def timestamp(value):
    value = (value or "").strip()
    # Le Python 3.9 livré par macOS accepte uniquement 3/6 décimales et ±HH:MM.
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
    """Valide chaque intervalle avant de retenir la date locale de fin."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = [f for f in archive.infolist()
                       if PurePosixPath(f.filename).name.casefold() == "sleep.csv"
                       and "__MACOSX" not in PurePosixPath(f.filename).parts]
            if len(members) != 1:
                raise CollectError("Le ZIP doit contenir un unique sleep.csv.")
            days = set()
            with archive.open(members[0]) as stream, io.TextIOWrapper(
                    stream, encoding="utf-8-sig", newline="") as contents:
                reader = csv.DictReader(contents, strict=True)
                if not {"start_ts", "end_ts"}.issubset(reader.fieldnames or []):
                    raise CollectError("Colonnes start_ts/end_ts absentes dans sleep.csv.")
                for row in reader:
                    start, end = timestamp(row["start_ts"]), timestamp(row["end_ts"])
                    if not timedelta() < end - start <= timedelta(days=1):
                        raise CollectError("Intervalle de sommeil invalide dans sleep.csv.")
                    days.add(end.date().isoformat())
            return days
    except (ValueError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise CollectError("ZIP, CSV ou horodatage avec décalage illisible.") from exc


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(db, base, path):
    """Archivage rejouable après interruption, sans effacer un ZIP non validé."""
    days = read_sleep(path)
    checksum = digest(path)
    archive = base / "Archives" / (checksum + ".zip")
    path.chmod(0o600)
    try:
        os.link(path, archive)
    except FileExistsError:
        if digest(archive) != checksum:
            raise CollectError("Intégrité de l’archive locale à vérifier.")
    with db:
        old_changes = db.total_changes
        db.executemany("INSERT OR IGNORE INTO nuits VALUES (?)", [(d,) for d in days])
        new_days = db.total_changes - old_changes
        db.execute("INSERT OR IGNORE INTO archives VALUES (?)", (checksum,))
    # Le fichier archivé existe et l'index est durable avant ce retrait.
    path.unlink()
    return max(days, default=None), new_days, checksum


def incoming(base):
    result = {}
    for path in (base / "Reception").iterdir():
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
        raise CollectError("Impossible de vérifier la session graphique.") from exc
    raise CollectError("La session graphique doit être ouverte, active et déverrouillée.")


def export(base):
    workflow = base / "Export.workflow"
    if not workflow.exists():
        raise CollectError("Export.workflow est absent du dossier de collecte.")
    check_session()
    try:
        result = subprocess.run(["/usr/bin/automator", str(workflow)], cwd=base,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise CollectError("Le délai du processus Automator est dépassé.") from exc
    # Seuls les messages constants du workflow peuvent apparaître dans le journal.
    messages = {
        "ACCESSIBILITY": "Autoriser R1 Bridge Collector dans Réglages Système > Confidentialité et sécurité > Accessibilité.",
        "APP_DATA_PERMISSION": "macOS a refusé à R1 Bridge Collector l’accès aux données d’Even pour lire le ZIP.",
        "EVEN_UNAVAILABLE": "Impossible d’ouvrir la fenêtre d’Even.",
        "EVEN_NAVIGATION": "Le collecteur n’a pas pu atteindre le bouton d’export dans Even.",
        "EVEN_SHARE": "Le collecteur n’a pas pu refermer la feuille de partage d’Even.",
        "EVEN_TIMEOUT": "Even n’a pas terminé son export dans le délai prévu.",
        "EVEN_IMPORT": "Le collecteur n’a pas pu récupérer le nouveau ZIP officiel dans Reception.",
    }
    match = re.search(rb"Even R1:\s*([A-Z_]+)\b", result.stdout)
    if match:
        key = match[1].decode("ascii")
        if key in messages:
            raise CollectError("%s — %s" % (key, messages[key]))
    if b"Even R1: helper did not complete" in result.stdout:
        raise CollectError("R1 Bridge Collector s’est arrêté avant de retourner son résultat.")
    if result.returncode:
        error = result.stdout.lower()
        if any(word in error for word in [b"-1743", b"-25211", b"not authorized",
                                          b"not allowed", b"assistive access", b"accessibility"]):
            raise CollectError("Automator a signalé un refus de permission macOS.")
        raise CollectError("Échec du processus Automator (code %d)." % result.returncode)


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(base=BASE, mode="manuel", exporter=export):
    setup(base)
    with (base / ".collecte.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            message = "Une collecte est déjà en cours."
            with closing(connect(base)) as db, db:
                db.execute("""INSERT INTO essais(debut, mode, etat, detail, fin)
                              VALUES (?, ?, 'occupé', ?, ?)""", (now(), mode, message, now()))
            return 75, message
        with closing(connect(base)) as db:
            with db:
                db.execute("""UPDATE essais SET etat='interrompu', fin=?,
                           detail='Collecte interrompue.' WHERE etat='en cours'""", (now(),))
                run_id = db.execute("INSERT INTO essais(debut, mode, etat) VALUES (?, ?, 'en cours')",
                                    (now(), mode)).lastrowid
            try:
                # Un ancien dépôt reste récupérable, mais ne prouve jamais un nouvel export.
                for path in incoming(base):
                    try:
                        ingest(db, base, path)
                    except CollectError:
                        pass  # Laisser le ZIP non validé dans Reception.
                before = incoming(base)
                exporter(base)
                new = [p for p, sig in incoming(base).items() if sig != before.get(p)]
                if len(new) != 1:
                    raise CollectError("Le workflow doit déposer exactement un nouveau ZIP.")
                latest, count, checksum = ingest(db, base, new[0])
                if latest is None:
                    detail = "Export validé. Even n’a fourni aucune session de sommeil."
                elif count:
                    detail = "Export validé. Nouvelles dates enregistrées."
                else:
                    detail = "Export validé. Aucune nouvelle date."
                status, code = "réussi", 0
            except (CollectError, OSError, sqlite3.Error) as exc:
                latest = checksum = None
                detail = str(exc) if isinstance(exc, CollectError) else "Erreur de stockage local."
                status, code = "échec", 1
            with db:
                db.execute("""UPDATE essais SET etat=?, detail=?, dernier_jour=?, fin=?,
                              empreinte=? WHERE id=?""", (status, detail, latest, now(), checksum, run_id))
            return code, detail


def evidence(db):
    """Deux exports automatiques distincts avec progression d'une nuit récente."""
    high_water = None
    prior_fresh = None
    for row in db.execute("""SELECT dernier_jour, fin FROM essais
                             WHERE mode='launchd' AND etat='réussi'
                               AND dernier_jour IS NOT NULL ORDER BY id"""):
        night = date.fromisoformat(row["dernier_jour"])
        if high_water is not None and night <= high_water:
            continue  # Ignorer aussi un ancien ZIP suivi de la réapparition du plus récent.
        high_water = night
        seen = datetime.fromisoformat(row["fin"]).date()
        if timedelta() <= seen - night <= timedelta(days=1):
            if prior_fresh == night - timedelta(days=1):
                return True
            prior_fresh = night
    return False
