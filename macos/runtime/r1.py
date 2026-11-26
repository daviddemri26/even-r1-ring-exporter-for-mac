"""Manage local Even R1 exports and the macOS collection schedule."""
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

import collection
import legacy_upgrade
import legacy_services

BASE = collection.BASE
LABEL = "local.r1bridge.collection"
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
        collection.check_session()
        raw = subprocess.check_output(["/usr/sbin/ioreg", "-a", "-r", "-c", "IOHIDSystem", "-d", "1"],
                                      stderr=subprocess.DEVNULL, timeout=5)
        values = [item.get("HIDIdleTime") for item in plistlib.loads(raw)]
        if not values or any(type(v) is not int or v < 0 for v in values):
            return "the Mac's activity could not be determined"
        if min(values) < IDLE_SECONDS * 1_000_000_000:
            return "the Mac was in use within the last two minutes"
    except collection.CollectError as error:
        return str(error)
    except (subprocess.SubprocessError, OSError, ValueError, AttributeError, TypeError, plistlib.InvalidFileException):
        return "the Mac's activity could not be determined"
    return None


def schedule_db(base):
    db = collection.connect(base)
    db.execute("""CREATE TABLE IF NOT EXISTS schedule_checks (
        slot TEXT PRIMARY KEY, checked_at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL
    )""")
    return db


def previous_export_in_slot(db, slot):
    # Upgrades can occur after an export run by the previous calendar schedule.
    row = db.execute("""SELECT start FROM attempts WHERE mode='launchd' AND status <> 'busy'
                        ORDER BY id DESC LIMIT 1""").fetchone()
    if not row:
        return False
    previous = datetime.fromisoformat(row[0]).astimezone().replace(tzinfo=None)
    return current_slot(previous) == slot


def scheduled_run(base, current=None):
    current = current or datetime.now()
    slot = current_slot(current)
    if slot is None:
        return 0, "Outside a scheduled collection window."
    key = slot.isoformat(timespec="minutes")
    collection.setup(base)
    with closing(schedule_db(base)) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM schedule_checks WHERE slot=?", (key,)).fetchone()
            if row and row[0] != "deferred":
                return 0, "This collection window was already handled."
            if not row and previous_export_in_slot(db, slot):
                state, detail = "handled", "An export was already attempted in this window."
            else:
                reason = quiet_reason()
                state, detail = (("deferred", "Export deferred because " + reason)
                                 if reason else ("reserved", "Starting a background export."))
            db.execute("INSERT OR REPLACE INTO schedule_checks VALUES (?, ?, ?, ?)",
                       (key, datetime.now().astimezone().isoformat(), state, detail))
        # Reserve the slot durably before opening Even. A crash cannot trigger a
        # second export from the same slot. Deferred checks never touch freshness.
        if state != "reserved":
            return 0, detail
        code, detail = collection.run(base, "launchd")
        state = "deferred" if code == 75 else ("completed" if code == 0 else "failed")
        with db:
            db.execute("UPDATE schedule_checks SET checked_at=?, status=?, detail=? WHERE slot=?",
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


RUNTIME_FILES = ("collection.py", "card_report.py", "archive_match.py",
                 "mcp_server.py", "sleep_report.py", "tunnel.py", "legacy_upgrade.py",
                 "legacy_services.py", "r1.py")


def install_runtime(source):
    workflow = source / "Export.workflow"
    resources = workflow / "Contents" / "Resources"
    helper = resources / "Even R1 Ring Collector for Mac.app/Contents/MacOS/EvenR1Export"
    if not all((source / name).is_file() for name in RUNTIME_FILES):
        raise collection.CollectError("The runtime is incomplete. Reinstall the Mac app.")
    if not helper.is_file() or not os.access(helper, os.X_OK) or not os.access(resources / "even_cards", os.X_OK):
        raise collection.CollectError("The compiled collector is missing. Install the built Mac app.")
    target = BASE / workflow.name
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise collection.CollectError("The workflow destination must be a local directory.")
    # Stage and verify all components before switching the active installation.
    with tempfile.TemporaryDirectory(dir=BASE, prefix=".install-") as stage:
        staged = Path(stage) / workflow.name
        subprocess.run(["/usr/bin/ditto", str(workflow), str(staged)], check=True)
        for name in RUNTIME_FILES:
            atomic_file(Path(stage) / name, (source / name).read_bytes())
        if target.exists():
            # Darwin RENAME_SWAP preserves running executables while atomically
            # replacing the workflow at its installed path.
            swap = ctypes.CDLL(None, use_errno=True).renamex_np
            swap.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
            swap.restype = ctypes.c_int
            if swap(os.fsencode(staged), os.fsencode(target), 0x00000002):
                raise collection.CollectError("Could not replace the installed workflow.")
        else:
            staged.rename(target)
        for name in RUNTIME_FILES:
            os.replace(Path(stage) / name, BASE / name)


def prepare():
    collection.setup(BASE)
    source = Path(__file__).resolve().parent
    with legacy_upgrade.previous_collection_lock(BASE), (BASE / ".collection.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if source != BASE.resolve():
            install_runtime(source)
        legacy_upgrade.import_data(BASE)
        if (BASE / collection.DATABASE).is_file():
            with closing(collection.connect(BASE)):
                pass
        legacy_services.migrate_services(BASE, schedule)
    print("Even R1 Ring Exporter for Mac runtime installed at", BASE)


def ctl(*args):
    return subprocess.run(["/bin/launchctl", *args], stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, timeout=20).returncode


def loaded():
    return ctl("print", SERVICE) == 0


def schedule():
    if not (BASE / "r1.py").is_file() or not (BASE / "Export.workflow").exists():
        raise collection.CollectError("Prepare the runtime and install Export.workflow first.")
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
            raise collection.CollectError("Could not reload the collection LaunchAgent.")
        atomic_file(PLIST, spec)
    if not loaded():
        if ctl("enable", SERVICE) or ctl("bootstrap", DOMAIN, str(PLIST)) or not loaded():
            raise collection.CollectError("The collection LaunchAgent could not load in the graphical session.")
    print("Collection windows start at 08:15, 12:15 and 18:15 local time. Activity is checked every ten minutes for an hour.")


def stop():
    if loaded() and ctl("bootout", SERVICE):
        raise collection.CollectError("Could not stop the collection LaunchAgent.")
    PLIST.unlink(missing_ok=True)
    print("Scheduled collection stopped. Your archives are still available.")


def test_schedule():
    if not loaded():
        raise collection.CollectError("Load the collection LaunchAgent before running a scheduled test.")
    slot = current_slot(datetime.now())
    if slot is None:
        print("Outside a collection window. Use the export command to run a manual export now.")
        return 0
    key = slot.isoformat(timespec="minutes")
    with closing(schedule_db(BASE)) as db:
        def record():
            return db.execute("SELECT checked_at, status, detail FROM schedule_checks WHERE slot=?",
                              (key,)).fetchone()
        prior = record()
        if prior and prior["status"] != "deferred":
            print(prior["detail"])
            return 0 if prior["status"] != "failed" else 1
        if ctl("kickstart", SERVICE):
            raise collection.CollectError("launchctl could not start the scheduled test.")
        deadline = time.monotonic() + collection.TIMEOUT + 45
        while time.monotonic() < deadline:
            latest = record()
            if latest and latest != prior and latest["status"] != "reserved":
                print("Scheduled test.", latest["detail"])
                return 0 if latest["status"] != "failed" else 1
            if current_slot(datetime.now()) != slot:
                print("The collection window has ended.")
                return 0
            time.sleep(0.5)
    raise collection.CollectError("The collection LaunchAgent did not report a result in time.")


def next_attempt(current=None, consumed=None):
    current = current or datetime.now()
    for days in (0, 1):
        for slot, check in schedule_times(current + timedelta(days=days)):
            if slot.isoformat(timespec="minutes") != consumed and check > current:
                return check.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def status():
    latest_control = None
    if (BASE / collection.DATABASE).is_file():
        with closing(schedule_db(BASE)) as db:
            latest_control = db.execute("""SELECT * FROM schedule_checks
                                          ORDER BY checked_at DESC LIMIT 1""").fetchone()
    if loaded():
        consumed = latest_control["slot"] if latest_control and latest_control["status"] != "deferred" else None
        print("Next scheduled check", next_attempt(consumed=consumed))
    else:
        print("Scheduled collection is off.")
    if latest_control:
        print("Last scheduled check", latest_control["checked_at"], latest_control["status"])
        print(latest_control["detail"])
    snapshot = BASE / "readings.json"
    if snapshot.is_file():
        try:
            cards_data = json.loads(snapshot.read_text())
            observed = collection.timestamp(cards_data["recorded_at"])
            count = len(cards_data["metrics"])
            if observed.utcoffset() is not None and 0 < count <= 6:
                print("Latest card update", observed.isoformat(timespec="minutes"),
                      "(%d categories available)" % count)
        except (ValueError, KeyError, OSError, TypeError):
            print("The card capture date is unavailable.")
    cards = BASE / "card_status.txt"
    if cards.is_file():
        status = cards.read_text().strip()
        if status == "CARDS_OK":
            print("Latest check read all six Even cards.")
        elif status == "CARDS_PARTIAL":
            print("Latest check read some Even cards.")
        elif status == "CARDS_HISTORY_ERROR":
            print("Cards were read. Check that history was saved.")
        else:
            print("The Even interface was unavailable at the last card check.")
    if not (BASE / collection.DATABASE).is_file():
        print("No export has been recorded.")
        return
    with closing(collection.connect(BASE)) as db:
        attempt = db.execute("SELECT * FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
        if attempt:
            print("Last attempt", attempt["start"], attempt["mode"], attempt["status"])
            if attempt["detail"]:
                print(attempt["detail"])
        latest = db.execute("SELECT MAX(day) FROM nights").fetchone()[0]
        print("Latest recorded wake date", latest or "none")
        print("Daily synchronization confirmed." if collection.evidence(db)
              else "Two consecutive nights have yet to be verified by automatic collection.")


def main():
    os.umask(0o077)
    choices = ("prepare", "export", "schedule", "test-schedule", "status", "stop", "_launchd")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=choices)
    action = parser.parse_args().action
    if action in ("export", "_launchd"):
        code, msg = scheduled_run(BASE) if action == "_launchd" else collection.run(BASE, "manual")
        print(msg)
        return code
    dispatch = {"prepare": prepare, "schedule": schedule,
                "test-schedule": test_schedule, "status": status, "stop": stop}
    return dispatch[action]() or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except collection.CollectError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as error:
        print("Local operation failed (%s)." % type(error).__name__, file=sys.stderr)
        sys.exit(1)
