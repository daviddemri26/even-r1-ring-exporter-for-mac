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
        "StartCalendarInterval": [{"Hour": hour, "Minute": 15} for hour in HOURS],
    })
    same = PLIST.exists() and PLIST.read_bytes() == spec
    if not same:
        if loaded() and ctl("bootout", SERVICE):
            raise collecte.CollectError("Impossible de recharger le LaunchAgent.")
        atomic_file(PLIST, spec)
    if not loaded():
        if ctl("enable", SERVICE) or ctl("bootstrap", DOMAIN, str(PLIST)) or not loaded():
            raise collecte.CollectError("Le LaunchAgent n’a pas été chargé dans la session GUI.")
    print("Collecte planifiée à 08 h 15, 12 h 15 et 18 h 15, heure locale.")


def arreter():
    if loaded() and ctl("bootout", SERVICE):
        raise collecte.CollectError("Impossible d’arrêter le LaunchAgent.")
    PLIST.unlink(missing_ok=True)
    print("Collecte planifiée arrêtée. Les archives restent disponibles.")


def last_scheduled(db):
    return db.execute("SELECT * FROM essais WHERE mode='launchd' ORDER BY id DESC LIMIT 1").fetchone()


def essai_planifie():
    if not loaded():
        raise collecte.CollectError("Le LaunchAgent doit être chargé pour cet essai.")
    with closing(collecte.connect(BASE)) as db:
        previous = last_scheduled(db)
        last_id = previous["id"] if previous else 0
        # Si launchd a déjà lancé le travail, observer son résultat sans le tuer.
        running_id = previous["id"] if previous and previous["etat"] == "en cours" else None
        if ctl("kickstart", SERVICE):
            raise collecte.CollectError("launchctl n’a pas pu démarrer l’essai.")
        deadline = time.monotonic() + collecte.TIMEOUT + 45
        while time.monotonic() < deadline:
            latest = last_scheduled(db)
            if latest and (latest["id"] > last_id or latest["id"] == running_id):
                if latest["etat"] != "en cours":
                    print("Essai launchd.", latest["detail"])
                    return 0 if latest["etat"] == "réussi" else 1
            time.sleep(0.5)
    raise collecte.CollectError("Aucun résultat du LaunchAgent dans le délai prévu.")


def next_attempt():
    current = datetime.now()
    for days in (0, 1):
        for hour in HOURS:
            next_run = (current + timedelta(days=days)).replace(
                hour=hour, minute=15, second=0, microsecond=0)
            if next_run > current:
                return next_run.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def etat():
    if loaded():
        print("Prochaine tentative programmée", next_attempt())
    else:
        print("Planification inactive.")
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
        code, msg = collecte.run(BASE, "launchd" if action == "_launchd" else "manuel")
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
