"""CraftSuite is a grouped selection, never a dependency metapackage."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires the Fedora test environment')
class CraftSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check():
            raise unittest.SkipTest('Run with xvfb-run')
        directory = Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos'
        sys.path.insert(0, str(directory))
        import launcher
        cls.launcher = launcher

    def suite(self, installed=False):
        app = self.launcher.InfinitySetup()
        app._add_craft_suite(Gtk.Box())
        for item in self.launcher.APPS:
            if item.source in self.launcher.CRAFT_SUITE:
                switch = Gtk.Switch(active=installed)
                app.switches[item] = switch
                app.initial_active[item] = installed
                switch.connect('notify::active', app._sync_craft_suite)
        app._sync_craft_suite()
        return app

    def test_enabling_suite_selects_all_four_independent_apps(self):
        app = self.suite()
        self.assertFalse(app.suite_switch.get_active())
        app.suite_switch.set_active(True)
        self.assertEqual({item.name for item, switch in app.switches.items() if switch.get_active()},
                         {'PDFCraft', 'WordCraft', 'GridCraft', 'DeckCraft'})

    def test_removing_one_member_keeps_other_three_selected(self):
        app = self.suite(installed=True)
        self.assertTrue(app.suite_switch.get_active())
        pdf = next(item for item in app.switches if item.name == 'PDFCraft')
        app.switches[pdf].set_active(False)
        self.assertFalse(app.suite_switch.get_active())
        self.assertEqual(sum(s.get_active() for s in app.switches.values()), 3)
        changes = [(item.name, s.get_active()) for item, s in app.switches.items()
                   if s.get_active() != app.initial_active[item]]
        self.assertEqual(changes, [('PDFCraft', False)])

    def test_disabling_suite_selects_removal_of_all_members(self):
        app = self.suite(installed=True)
        app.suite_switch.set_active(False)
        self.assertFalse(any(s.get_active() for s in app.switches.values()))
