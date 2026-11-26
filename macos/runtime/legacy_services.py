"""Upgrade schedules and tunnel configuration created by the first two alphas."""
import os
import plistlib
import re
import time

from collection import CollectError
import tunnel


def start_job(domain, path):
    # launchd can take a moment to release a job name after a bootout.
    for attempt in range(12):
        if tunnel.launch("bootstrap", domain, str(path)) == 0:
            return
        if attempt < 11:
            time.sleep(0.5)
    raise CollectError("Could not restart the private tunnel. Run Set Up This Mac again.")


def migrate_tunnel(base, agents, domain):
    folder = base / "tunnel"
    profile = folder / "even-r1.yaml"
    launcher = folder / "Enregistrer la clé.command"
    agent = agents / "local.r1bridge.tunnel.plist"
    resume = folder / ".resume-tunnel"
    original = profile.read_bytes() if profile.is_file() else b""
    # Replace the generated stdio entry point, preserving the tunnel and all other settings.
    updated = re.sub(rb"/serveur_sommeil\.py(?=[\s'\"\\]|$)", b"/mcp_server.py", original)
    if launcher.is_file():
        if launcher.read_text().strip().endswith('tunnel_r1.py" enregistrer-trousseau'):
            tunnel.put(folder / "Store Key.command", tunnel.KEYCHAIN_ENTRY.encode("utf-8"), 0o700)
            launcher.unlink()

    job = plistlib.loads(agent.read_bytes()) if agent.is_file() else {}
    args = job.get("ProgramArguments", [])
    label = "local.r1bridge.tunnel"
    old_runner = args[:3] == ["/usr/bin/python3", "-B", str(base / "tunnel_r1.py")]
    replace_runner = old_runner and job.get("Label") == label
    if replace_runner:
        actions = {"executer": "run", "executer-trousseau": "run-keychain"}
        if len(args) < 4 or args[3] not in actions:
            raise CollectError("Unrecognized tunnel launch command. Check the tunnel settings before upgrading.")
        args[2:4] = [str(base / "tunnel.py"), actions[args[3]]]
    if updated == original and not replace_runner and not resume.is_file():
        return
    service = domain + "/" + label
    reload_job = resume.is_file()
    if replace_runner or updated != original:
        if job.get("Label") == label and tunnel.launch("print", service) == 0:
            # Record the intent before unloading so a failed or interrupted migration can resume.
            tunnel.put(resume, b"")
            reload_job = True
            if tunnel.launch("bootout", service):
                raise CollectError("Could not stop the previous tunnel service for the upgrade.")
    if updated != original:
        tunnel.put(profile, updated)
    if replace_runner:
        tunnel.put(agent, plistlib.dumps(job))
    if reload_job:
        if not agent.is_file():
            raise CollectError("The previous tunnel service definition is missing.")
        if tunnel.launch("print", service) != 0:
            start_job(domain, agent)
        resume.unlink(missing_ok=True)


def migrate_services(base, schedule):
    """Migrate only services configured in this installation's home directory."""
    agents = base.parents[2] / "Library/LaunchAgents"
    domain = "gui/%d" % os.getuid()
    old = agents / "local.r1bridge.collecte.plist"
    if old.is_file():
        job = plistlib.loads(old.read_bytes())
        old_label = "local.r1bridge.collecte"
        if (job.get("Label") != old_label or
                job.get("ProgramArguments") != ["/usr/bin/python3", "-B", str(base / "r1.py"), "_launchd"]):
            raise CollectError("Unexpected configuration for the previous collection schedule.")
        service = domain + "/" + old_label
        if tunnel.launch("print", service) == 0:
            schedule()
            if tunnel.launch("bootout", service):
                raise CollectError("Could not stop the previous collection schedule.")
        else:
            # An unloaded schedule stays unloaded when its definition is renamed.
            label = "local.r1bridge.collection"
            destination = agents / (label + ".plist")
            if not destination.exists():
                job["Label"] = label
                tunnel.put(destination, plistlib.dumps(job))
        old.unlink()
    migrate_tunnel(base, agents, domain)
