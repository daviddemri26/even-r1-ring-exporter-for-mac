import os
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import legacy_services as upgrade


class ServiceMigrationTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.home = Path(scratch.name)
        self.base = self.home / "Library/Application Support/R1 Bridge"
        self.base.mkdir(parents=True)
        self.agents = self.home / "Library/LaunchAgents"
        self.agents.mkdir()
        self.folder = self.base / "tunnel"
        self.folder.mkdir()
        self.domain = "gui/%d" % os.getuid()
        self.loaded = set()
        self.events = []
        self.schedule = Mock()
        def launch(*args):
            self.events.append(args)
            action, target = args[:2]
            if action == "print":
                return 0 if target in self.loaded else 1
            if action == "bootout":
                self.loaded.remove(target)
            elif action == "bootstrap":
                self.loaded.add(target + "/" + plistlib.loads(Path(args[2]).read_bytes())["Label"])
            return 0
        patcher = patch.object(upgrade.tunnel, "launch", side_effect=launch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def migrate(self):
        upgrade.migrate_services(self.base, self.schedule)

    def fixture(self, label, args):
        path = self.agents / (label + ".plist")
        path.write_bytes(plistlib.dumps({"Label":label, "ProgramArguments":args}))
        return path

    def test_fresh_install_and_second_run_do_not_contact_launchd(self):
        self.migrate()
        self.migrate()
        self.assertEqual([], self.events)
        self.schedule.assert_not_called()

    def test_active_tunnel_preserves_key_source_and_restarts_once(self):
        name = "local.r1bridge.tunnel"
        service = self.domain + "/" + name
        self.loaded.add(service)
        argv = ["/usr/bin/python3", "-B", str(self.base / "tunnel_r1.py"), "executer", "/test/example.env"]
        plist = self.fixture(name, argv)
        profile = self.folder / "even-r1.yaml"
        profile.write_text("command: '/test/serveur_sommeil.py' --stdio\n")
        old_launcher = self.folder / "Enregistrer la clé.command"
        old_launcher.write_text('exec /usr/bin/python3 -B "$HOME/Library/Application Support/R1 Bridge/tunnel_r1.py" enregistrer-trousseau\n')
        self.migrate()
        self.assertEqual("command: '/test/mcp_server.py' --stdio\n", profile.read_text())
        self.assertEqual([*argv[:2], str(self.base / "tunnel.py"), "run", "/test/example.env"],
                         plistlib.loads(plist.read_bytes())["ProgramArguments"])
        self.assertTrue((self.folder / "Store Key.command").is_file())
        self.assertFalse(old_launcher.exists())
        self.assertIn(service, self.loaded)
        self.assertEqual(["print","bootout","print","bootstrap"], [v[0] for v in self.events])
        self.events.clear()
        self.migrate()
        self.assertEqual([], self.events)

    def test_disabled_services_stay_unloaded(self):
        collection = "local.r1bridge.collecte"
        original = self.fixture(collection, ["/usr/bin/python3", "-B", str(self.base / "r1.py"), "_launchd"])
        name = "local.r1bridge.tunnel"
        self.fixture(name, ["/usr/bin/python3", "-B", str(self.base / "tunnel_r1.py"), "executer-trousseau"])
        self.migrate()
        self.assertTrue((self.agents / "local.r1bridge.collection.plist").is_file())
        self.assertFalse(original.exists())
        self.assertFalse(self.loaded)
        self.schedule.assert_not_called()

    def test_pending_tunnel_restart_resumes_after_interruption(self):
        name = "local.r1bridge.tunnel"
        self.fixture(name, ["/usr/bin/python3", "-B", str(self.base / "tunnel.py"), "run-keychain"])
        marker = self.folder / ".resume-tunnel"
        marker.touch()
        self.migrate()
        self.assertIn(self.domain + "/" + name, self.loaded)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
