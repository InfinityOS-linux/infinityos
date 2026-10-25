"""Check InfinitySetup's Steam and TV Mode dependency behavior."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


CATALOG = Path(__file__).resolve().parents[1] / "packages/infinity-setup/root/usr/share/infinityos"
sys.path.insert(0, str(CATALOG))

gi = types.ModuleType("gi")
gi.require_version = lambda *_args: None
repository = types.ModuleType("gi.repository")
repository.GdkPixbuf = SimpleNamespace()
repository.Gio = SimpleNamespace()
repository.GLib = SimpleNamespace(idle_add=lambda callback, *args: callback(*args))
repository.Gtk = SimpleNamespace(Application=object)
gi.repository = repository
with patch.dict(sys.modules, {"gi": gi, "gi.repository": repository}):
    spec = importlib.util.spec_from_file_location("infinity_setup_ui", CATALOG / "launcher.py")
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)


class Switch:
    def __init__(self, active=False):
        self.active = active

    def get_active(self):
        return self.active

    def set_active(self, active):
        self.active = active


class SetupDependencyTests(unittest.TestCase):
    def make_setup(self):
        setup = setup_module.InfinitySetup.__new__(setup_module.InfinitySetup)
        steam = next(app for app in setup_module.APPS if app.name == "Steam")
        setup.switches = {steam: Switch()}
        setup.tv_switches = {"steam": Switch()}
        return setup, steam

    def test_enabling_steam_tv_selects_steam_and_disabling_steam_clears_tv(self):
        setup, steam = self.make_setup()
        setup.tv_switches["steam"].set_active(True)
        setup._steam_tv_toggled(setup.tv_switches["steam"], None)
        self.assertTrue(setup.switches[steam].get_active())
        setup.switches[steam].set_active(False)
        setup._steam_toggled(setup.switches[steam], None)
        self.assertFalse(setup.tv_switches["steam"].get_active())

    def test_disabling_tv_mode_keeps_regular_steam_selected(self):
        setup, steam = self.make_setup()
        setup.switches[steam].set_active(True)
        setup.tv_switches["steam"].set_active(False)
        setup._steam_tv_toggled(setup.tv_switches["steam"], None)
        self.assertTrue(setup.switches[steam].get_active())

    def test_uninstall_disables_tv_before_removing_steam(self):
        setup, steam = self.make_setup()
        setup.status = SimpleNamespace(set_text=lambda *_args: None)
        setup._installed = Mock()
        setup._tv_applied = Mock()
        setup._finished = Mock()
        actions = []
        with patch.object(setup_module, "set_tv_enabled", side_effect=lambda *_args: actions.append("tv off")), \
             patch.object(setup_module, "uninstall", side_effect=lambda *_args: actions.append("steam off")):
            setup._install([(steam, False)], [("steam", False)])
        self.assertEqual(actions, ["tv off", "steam off"])

    def test_tv_activation_installs_steam_first(self):
        setup, steam = self.make_setup()
        setup.status = SimpleNamespace(set_text=lambda *_args: None)
        setup._installed = Mock()
        setup._tv_applied = Mock()
        setup._finished = Mock()
        actions = []
        with patch.object(setup_module, "install", side_effect=lambda *_args, **_kwargs: actions.append("steam on")), \
             patch.object(setup_module, "set_tv_enabled", side_effect=lambda *_args: actions.append("tv on")):
            setup._install([(steam, True)], [("steam", True)])
        self.assertEqual(actions, ["steam on", "tv on"])

    def test_failed_steam_install_does_not_activate_tv(self):
        setup, steam = self.make_setup()
        setup.status = SimpleNamespace(set_text=lambda *_args: None)
        setup._installed = Mock()
        setup._tv_applied = Mock()
        setup._finished = Mock()
        with patch.object(setup_module, "install", side_effect=RuntimeError("install failed")), \
             patch.object(setup_module, "set_tv_enabled") as set_tv_enabled:
            setup._install([(steam, True)], [("steam", True)])
        set_tv_enabled.assert_not_called()
        self.assertTrue(setup._finished.call_args.args[0])

    def test_failed_tv_deactivation_does_not_remove_steam(self):
        setup, steam = self.make_setup()
        setup.status = SimpleNamespace(set_text=lambda *_args: None)
        setup._installed = Mock()
        setup._tv_applied = Mock()
        setup._finished = Mock()
        with patch.object(setup_module, "set_tv_enabled", side_effect=RuntimeError("deactivation failed")), \
             patch.object(setup_module, "uninstall") as uninstall:
            setup._install([(steam, False)], [("steam", False)])
        uninstall.assert_not_called()
        self.assertTrue(setup._finished.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
