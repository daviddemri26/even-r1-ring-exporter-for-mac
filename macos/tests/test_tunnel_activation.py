"""Exercise tunnel LaunchAgent replacement with a simulated launchctl."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import tunnel


class TunnelActivationTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.plist = base / "launch-agent.plist"
        runner = base / "tunnel.py"
        runner.touch()
        profile = base / "profile.yaml"
        profile.touch()
        paths = patch.multiple(tunnel, RUNNER=runner, PROFILE=profile, PLIST=self.plist)
        paths.start()
        self.addCleanup(paths.stop)
        # Record the configuration for an existing service that uses a different key source.
        self.original = tunnel.agent_config(base / "previous.env")
        self.plist.write_bytes(self.original)
        self.loaded = True
        self.previous_restarts = 0

    def replace(self, *, bootout_fails=False):
        def launch(action, *arguments):
            if action == "print":
                return 0 if self.loaded else 1
            if action == "bootout":
                if bootout_fails:
                    return 1  # The old service is still running.
                self.loaded = False
            elif action == "bootstrap":
                if self.plist.read_bytes() != self.original:
                    return 1  # The new job cannot load; the previous definition can.
                self.previous_restarts += 1
                self.loaded = True
            elif action != "enable":
                self.fail(f"Unexpected launchctl command {action}")
            return 0

        with patch.object(tunnel, "keychain_item"), patch.object(tunnel.time, "sleep"), \
                patch.object(tunnel, "launch", side_effect=launch):
            with self.assertRaises(tunnel.SetupError):
                tunnel.activate()

    def test_previous_definition_and_service_are_restored_if_bootstrap_fails(self):
        self.replace()
        self.assertEqual(self.plist.read_bytes(), self.original)
        self.assertTrue(self.loaded)
        self.assertEqual(self.previous_restarts, 1)

    def test_failed_bootout_leaves_working_service_running(self):
        self.replace(bootout_fails=True)
        self.assertEqual(self.plist.read_bytes(), self.original)
        self.assertTrue(self.loaded)
        self.assertEqual(self.previous_restarts, 0)
