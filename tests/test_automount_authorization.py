from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "root/usr/libexec/infinityos-configure-automount"


class AutomountAuthorizationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.rules = Path(temporary.name)
        self.gio = SimpleNamespace(Settings=Mock())
        repository = SimpleNamespace(Gio=self.gio, GLib=SimpleNamespace())
        loader = SourceFileLoader("configure_automount", str(HELPER))
        spec = spec_from_loader(loader.name, loader)
        self.helper = module_from_spec(spec)
        with patch.dict("sys.modules", {"gi": SimpleNamespace(repository=repository), "gi.repository": repository}):
            loader.exec_module(self.helper)
        self.helper.RULE_DIR = self.rules
        self.user = SimpleNamespace(pw_uid=1000, pw_name="tester")
        self.block = {"IdUUID": "filesystem-id", "HintSystem": True}
        self.drive = {"WWN": "hardware-id", "Serial": "other-hardware-id"}
        self.partition = {"UUID": "partition-id"}

    def test_rule_matches_only_one_user_filesystem_and_drive(self):
        grant = self.helper.grant_identity(self.block, self.drive, self.partition)
        self.helper.write_grants(self.user, {"filesystem-id": grant})
        self.assertEqual(self.helper.read_grants(1000), {"filesystem-id": grant})
        rule = self.helper.rule_path(1000).read_text(encoding="utf-8")
        script = """
const assert = require('node:assert/strict');
let evaluate;
const polkit = {Result: {YES: 'allow'}, addRule(rule) {evaluate = rule;}};
""" + rule + """
const identity = {'id.uuid': 'filesystem-id', 'drive.wwn': 'hardware-id', 'partition.uuid': 'partition-id'};
function mount(action, user, values) {
    return evaluate({id: action, lookup(key) {return values[key];}}, {user});
}
const action = 'org.freedesktop.udisks2.filesystem-mount-system';
assert.equal(mount(action, 'tester', identity), 'allow');
assert.equal(mount(action, 'someone-else', identity), undefined);
assert.equal(mount(action, 'tester', {...identity, 'id.uuid': 'different'}), undefined);
assert.equal(mount(action, 'tester', {...identity, 'drive.wwn': 'different'}), undefined);
assert.equal(mount(action, 'tester', {...identity, 'partition.uuid': 'different'}), undefined);
assert.equal(mount('org.freedesktop.udisks2.filesystem-mount-other-seat', 'tester', identity), undefined);
"""
        subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        self.helper.write_grants(self.user, {})
        self.assertEqual(self.helper.read_grants(1000), {})
        self.assertFalse(self.helper.rule_path(1000).exists())

    def test_protected_drive_asks_once_and_saves_only_after_approval(self):
        settings = self.gio.Settings.new.return_value
        settings.is_writable.return_value = True
        settings.get_strv.return_value = ["another-volume"]
        volume = self.block, self.drive, self.partition
        with patch.object(self.helper, "disk_properties", return_value=volume), \
                patch.object(self.helper.subprocess, "run", side_effect=subprocess.CalledProcessError(126, ["pkexec"])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.helper.configure("enable", "/dev/sdb1", "filesystem-id")
        settings.set_strv.assert_not_called()
        with patch.object(self.helper, "disk_properties", return_value=volume), \
                patch.object(self.helper.subprocess, "run") as run:
            self.helper.configure("enable", "/dev/sdb1", "filesystem-id")
            run.assert_called_once_with(["pkexec", self.helper.__file__, "--allow", "/dev/sdb1", "filesystem-id"], check=True)
            settings.set_strv.assert_called_once_with("volume-uuids", ["another-volume", "filesystem-id"])
            run.reset_mock()
            self.helper.configure("disable", "/dev/sdb1", "filesystem-id")
            run.assert_called_once_with(["pkexec", self.helper.__file__, "--forget", "/dev/sdb1", "filesystem-id"], check=True)
            settings.set_strv.assert_called_with("volume-uuids", ["another-volume"])

    def test_an_unprotected_volume_does_not_request_administrator_approval(self):
        settings = self.gio.Settings.new.return_value
        settings.is_writable.return_value = True
        settings.get_strv.return_value = []
        with patch.object(self.helper, "disk_properties", return_value=({"HintSystem": False}, {}, {})), \
                patch.object(self.helper.subprocess, "run") as run:
            self.helper.configure("enable", "/dev/sdb1", "portable-volume")
        run.assert_not_called()
        settings.set_strv.assert_called_once_with("volume-uuids", ["portable-volume"])

    def test_protected_volume_without_a_real_drive_cannot_be_authorized(self):
        with self.assertRaises(ValueError):
            self.helper.grant_identity(self.block, {}, {"UUID": "partition-id"})
        with self.assertRaises(ValueError):
            self.helper.grant_identity(self.block, {"Serial": ""}, {})


if __name__ == "__main__":
    unittest.main()
