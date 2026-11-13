"""Exercise the real GTK catalog and global filters without package operations."""
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


@unittest.skipUnless(Gtk, 'GTK requires Fedora and Xvfb')
class SetupPageTests(unittest.TestCase):
    def test_global_search_and_pending_filter_preserve_selection(self):
        if not Gtk.init_check():
            self.skipTest('GTK needs a display')
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos'))
        import launcher
        app = launcher.InfinitySetup()
        app.window = Gtk.Window()
        self.addCleanup(app.window.destroy)
        app.stack, app.card, app.shade = Gtk.Stack(), Gtk.Box(), Gtk.Box()
        app.window.set_child(app.card)
        app.ai_models = ()
        app.catalog_status = {}
        with patch.object(app, '_animate'), patch.object(app, '_refresh_ai'), \
             patch.object(launcher, 'tv_enabled', return_value=False):
            app._build_catalog()
        candidate = next(item for item in app.switches if item.category == 'Programming')
        app.search.set_text(candidate.name)
        app._filter_catalog()
        self.assertTrue(app.rows[candidate].get_visible())
        self.assertEqual(app.stack.get_visible_child_name(), 'programming')
        app.switches[candidate].set_active(True)
        app.filter.set_selected(3)
        app._filter_catalog()
        self.assertTrue(app.rows[candidate].get_visible())
        app.search.set_text('no application has this name')
        app._filter_catalog()
        self.assertFalse(any(row.get_visible() for row in app.rows.values()))
        self.assertTrue(app.switches[candidate].get_active())
