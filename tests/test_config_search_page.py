from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires Fedora and Xvfb')
class SettingsSearchTests(unittest.TestCase):
    def test_search_reaches_settings_and_clears_results(self):
        if not Gtk.init_check():
            self.skipTest('GTK needs a display')
        root = Path(__file__).resolve().parents[1]
        for package in ('infinity-config', 'infinity-setup'):
            sys.path.insert(0, str(root / 'packages' / package / 'root/usr/share/infinityos'))
        from config import InfinityConfig
        stack = Gtk.Stack()
        page = Gtk.Box()
        page.append(Gtk.Label(label='Cursor size'))
        stack.add_named(page, 'Desktop')
        tab = Gtk.ToggleButton()
        app = SimpleNamespace(stack=stack, search_results=Gtk.Box(), search_tabs={'Desktop': tab})
        entry = Gtk.SearchEntry()
        entry.set_text('cursor')
        InfinityConfig._search_settings(app, entry)
        app.search_results.get_first_child().emit('clicked')
        self.assertTrue(tab.get_active())
        entry.set_text('')
        InfinityConfig._search_settings(app, entry)
        self.assertIsNone(app.search_results.get_first_child())
