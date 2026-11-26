"""Commande locale pour l'export Even R1 et son LaunchAgent macOS."""
import argparse
import json
import ctypes
import fcntl
import os
import plistlib
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import collecte

BASE = collecte.BASE
LABEL = "local.r1bridge.collecte"
DOMAIN = "gui/%d" % os.getuid()
SERVICE = DOMAIN + "/" + LABEL
PLIST = Path.home() / "Library" / "LaunchAgents" / (LABEL + ".plist")
HOURS = (8, 12, 18)
IDLE_SECONDS = 120
CHECK_MINUTES = tuple(range(0, 61, 10))


def schedule_times(day):
    for hour in HOURS:
        slot = day.replace(hour=hour, minute=15, second=0, microsecond=0)
        for minutes in CHECK_MINUTES:
            yield slot, slot + timedelta(minutes=minutes)


def current_slot(current):
    # Local wall-clock dates also identify slots across a restart or a clock change.
    for hour in HOURS:
        slot = current.replace(hour=hour, minute=15, second=0, microsecond=0)
        if slot <= current < slot + timedelta(minutes=CHECK_MINUTES[-1] + 1):
            return slot
    return None


def quiet_reason():
    try:
        collecte.check_session()
        raw = subprocess.check_output(["/usr/sbin/ioreg", "-a", "-r", "-c", "IOHIDSystem", "-d", "1"],
                                      stderr=subprocess.DEVNULL, timeout=5)
        values = [item.get("HIDIdleTime") for item in plistlib.loads(raw)]
        if not values or any(type(v) is not int or v < 0 for v in values):
            return "activité du Mac indéterminée"
        if min(values) < IDLE_SECONDS * 1_000_000_000:
            return "Mac utilisé au cours des deux dernières minutes"
    except collecte.CollectError as error:
        return str(error)
    except (subprocess.SubprocessError, OSError, ValueError, AttributeError, TypeError, plistlib.InvalidFileException):
        return "activité du Mac indéterminée"
    return None


def schedule_db(base):
    db = collecte.connect(base)
    db.execute("""CREATE TABLE IF NOT EXISTS controles_planifies (
        creneau TEXT PRIMARY KEY, controle TEXT NOT NULL, etat TEXT NOT NULL, detail TEXT NOT NULL
    )""")
    return db


def previous_export_in_slot(db, slot):
    # Upgrades can occur after an export run by the previous calendar schedule.
    row = db.execute("""SELECT debut FROM essais WHERE mode='launchd' AND etat <> 'occupé'
                        ORDER BY id DESC LIMIT 1""").fetchone()
    if not row:
        return False
    previous = datetime.fromisoformat(row[0]).astimezone().replace(tzinfo=None)
    return current_slot(previous) == slot


def scheduled_run(base, current=None):
    current = current or datetime.now()
    slot = current_slot(current)
    if slot is None:
        return 0, "Hors créneau de collecte discrète."
    key = slot.isoformat(timespec="minutes")
    collecte.setup(base)
    with closing(schedule_db(base)) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT etat FROM controles_planifies WHERE creneau=?", (key,)).fetchone()
            if row and row[0] != "différé":
                return 0, "Le créneau a déjà été pris en compte."
            if not row and previous_export_in_slot(db, slot):
                state, detail = "traité", "Un export avait déjà été tenté pendant ce créneau."
            else:
                reason = quiet_reason()
                state, detail = (("différé", "Export différé. " + reason)
                                 if reason else ("réservé", "Lancement de la collecte discrète."))
            db.execute("INSERT OR REPLACE INTO controles_planifies VALUES (?, ?, ?, ?)",
                       (key, datetime.now().astimezone().isoformat(), state, detail))
        # Reserve the slot durably before opening Even. A crash cannot trigger a
        # second export from the same slot. Deferred checks never touch freshness.
        if state != "réservé":
            return 0, detail
        code, detail = collecte.run(base, "launchd")
        state = "différé" if code == 75 else ("terminé" if code == 0 else "échec")
        with db:
            db.execute("UPDATE controles_planifies SET controle=?, etat=?, detail=? WHERE creneau=?",
                       (datetime.now().astimezone().isoformat(), state, detail, key))
        return code, detail


def atomic_file(target, content):
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)


RUNTIME_FILES = ("collecte.py", "rapport_even.py", "rapprochement_even.py",
                 "serveur_sommeil.py", "controle_sommeil.py", "tunnel_r1.py", "r1.py")


def install_runtime(source):
    workflow = source / "Export.workflow"
    resources = workflow / "Contents" / "Resources"
    helper = resources / "R1 Bridge Collector.app/Contents/MacOS/EvenR1Export"
    if not all((source / name).is_file() for name in RUNTIME_FILES):
        raise collecte.CollectError("Le moteur est incomplet. Réinstaller l’application Mac.")
    if not helper.is_file() or not os.access(helper, os.X_OK) or not os.access(resources / "cartes_even", os.X_OK):
        raise collecte.CollectError("Le collecteur doit être compilé. Installer l’application Mac construite.")
    target = BASE / workflow.name
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise collecte.CollectError("La destination du workflow doit être un dossier local.")
    # Valider et copier tous les composants avant de remplacer la version active.
    with tempfile.TemporaryDirectory(dir=BASE, prefix=".installation-") as stage:
        staged = Path(stage) / workflow.name
        subprocess.run(["/usr/bin/ditto", str(workflow), str(staged)], check=True)
        for name in RUNTIME_FILES:
            atomic_file(Path(stage) / name, (source / name).read_bytes())
        if target.exists():
            # Darwin RENAME_SWAP conserve les exécutables en cours sans fenêtre
            # pendant laquelle le workflow installé serait absent.
            swap = ctypes.CDLL(None, use_errno=True).renamex_np
            swap.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
            swap.restype = ctypes.c_int
            if swap(os.fsencode(staged), os.fsencode(target), 0x00000002):
                raise collecte.CollectError("Échange du workflow impossible.")
        else:
            staged.rename(target)
        for name in RUNTIME_FILES:
            os.replace(Path(stage) / name, BASE / name)


def preparer():
    collecte.setup(BASE)
    source = Path(__file__).resolve().parent
    with (BASE / ".collecte.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if source != BASE.resolve():
            install_runtime(source)
        if (BASE / collecte.DATABASE).is_file():
            with closing(collecte.connect(BASE)):
                pass
    print("Moteur R1 Bridge installé dans", BASE)


def ctl(*args):
    return subprocess.run(["/bin/launchctl", *args], stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, timeout=20).returncode


def loaded():
    return ctl("print", SERVICE) == 0


def planifier():
    if not (BASE / "r1.py").is_file() or not (BASE / "Export.workflow").exists():
        raise collecte.CollectError("Préparer le pilote et installer Export.workflow d’abord.")
    PLIST.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    spec = plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": ["/usr/bin/python3", "-B", str(BASE / "r1.py"), "_launchd"],
        "WorkingDirectory": str(BASE),
        "ProcessType": "Interactive",
        "LimitLoadToSessionType": "Aqua",
        "Umask": 0o077,
        "StartCalendarInterval": [{"Hour": check.hour, "Minute": check.minute}
                                  for _, check in schedule_times(datetime.now())],
    })
    same = PLIST.exists() and PLIST.read_bytes() == spec
    if not same:
        if loaded() and ctl("bootout", SERVICE):
            raise collecte.CollectError("Impossible de recharger le LaunchAgent.")
        atomic_file(PLIST, spec)
    if not loaded():
        if ctl("enable", SERVICE) or ctl("bootstrap", DOMAIN, str(PLIST)) or not loaded():
            raise collecte.CollectError("Le LaunchAgent n’a pas été chargé dans la session GUI.")
    print("Collecte discrète à partir de 08 h 15, 12 h 15 et 18 h 15. Contrôle toutes les dix minutes pendant une heure.")


def arreter():
    if loaded() and ctl("bootout", SERVICE):
        raise collecte.CollectError("Impossible d’arrêter le LaunchAgent.")
    PLIST.unlink(missing_ok=True)
    print("Collecte planifiée arrêtée. Les archives restent disponibles.")


def essai_planifie():
    if not loaded():
        raise collecte.CollectError("Le LaunchAgent doit être chargé pour cet essai.")
    slot = current_slot(datetime.now())
    if slot is None:
        print("Hors créneau. Utilisez « essai » pour demander un export manuel immédiat.")
        return 0
    key = slot.isoformat(timespec="minutes")
    with closing(schedule_db(BASE)) as db:
        def record():
            return db.execute("SELECT controle, etat, detail FROM controles_planifies WHERE creneau=?",
                              (key,)).fetchone()
        prior = record()
        if prior and prior["etat"] != "différé":
            print(prior["detail"])
            return 0 if prior["etat"] != "échec" else 1
        if ctl("kickstart", SERVICE):
            raise collecte.CollectError("launchctl n’a pas pu démarrer l’essai.")
        deadline = time.monotonic() + collecte.TIMEOUT + 45
        while time.monotonic() < deadline:
            latest = record()
            if latest and latest != prior and latest["etat"] != "réservé":
                print("Essai launchd.", latest["detail"])
                return 0 if latest["etat"] != "échec" else 1
            if current_slot(datetime.now()) != slot:
                print("La fenêtre de collecte est terminée.")
                return 0
            time.sleep(0.5)
    raise collecte.CollectError("Aucun résultat du LaunchAgent dans le délai prévu.")


def next_attempt(current=None, consumed=None):
    current = current or datetime.now()
    for days in (0, 1):
        for slot, check in schedule_times(current + timedelta(days=days)):
            if slot.isoformat(timespec="minutes") != consumed and check > current:
                return check.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def etat():
    latest_control = None
    if (BASE / collecte.DATABASE).is_file():
        with closing(schedule_db(BASE)) as db:
            latest_control = db.execute("""SELECT * FROM controles_planifies
                                          ORDER BY controle DESC LIMIT 1""").fetchone()
    if loaded():
        consumed = latest_control["creneau"] if latest_control and latest_control["etat"] != "différé" else None
        print("Prochain contrôle programmé", next_attempt(consumed=consumed))
    else:
        print("Planification inactive.")
    if latest_control:
        print("Dernier contrôle de planification", latest_control["controle"], latest_control["etat"])
        print(latest_control["detail"])
    snapshot = BASE / "releves_even.json"
    if snapshot.is_file():
        try:
            cards_data = json.loads(snapshot.read_text())
            observed = collecte.timestamp(cards_data["recorded_at"])
            count = len(cards_data["metrics"])
            if observed.utcoffset() is not None and 0 < count <= 6:
                print("Dernière mise à jour des cartes", observed.isoformat(timespec="minutes"),
                      "(%d catégories disponibles)" % count)
        except (ValueError, KeyError, OSError, TypeError):
            print("Date des cartes indisponible.")
    cards = BASE / "etat_cartes.txt"
    if cards.is_file():
        status = cards.read_text().strip()
        if status == "CARDS_OK":
            print("Dernier contrôle des cartes Even : six cartes lisibles.")
        elif status == "CARDS_PARTIAL":
            print("Dernier contrôle des cartes Even : lecture partielle.")
        elif status == "CARDS_HISTORY_ERROR":
            print("Cartes lues ; enregistrement de leur historique à vérifier.")
        else:
            print("Dernier contrôle des cartes Even : interface indisponible.")
    if not (BASE / collecte.DATABASE).is_file():
        print("Aucun export enregistré.")
        return
    with closing(collecte.connect(BASE)) as db:
        attempt = db.execute("SELECT * FROM essais ORDER BY id DESC LIMIT 1").fetchone()
        if attempt:
            print("Dernière tentative", attempt["debut"], attempt["mode"], attempt["etat"])
            if attempt["detail"]:
                print(attempt["detail"])
        latest = db.execute("SELECT MAX(jour) FROM nuits").fetchone()[0]
        print("Dernière date de réveil enregistrée", latest or "aucune")
        print("Synchronisation quotidienne confirmée." if collecte.evidence(db)
              else "Deux nuits successives en collecte automatique restent à confirmer.")


def main():
    os.umask(0o077)
    choices = ("preparer", "essai", "planifier", "essai-planifie", "etat", "arreter", "_launchd")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=choices)
    action = parser.parse_args().action
    if action in ("essai", "_launchd"):
        code, msg = scheduled_run(BASE) if action == "_launchd" else collecte.run(BASE, "manuel")
        print(msg)
        return code
    dispatch = {"preparer": preparer, "planifier": planifier,
                "essai-planifie": essai_planifie, "etat": etat, "arreter": arreter}
    return dispatch[action]() or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except collecte.CollectError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as error:
        print("Échec local (%s)." % type(error).__name__, file=sys.stderr)
        sys.exit(1)
