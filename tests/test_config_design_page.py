"""Exercise the Design page's two-way GNOME settings bindings under Xvfb."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gio, Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, "GTK requires the Fedora test environment")
class DesignPageTests(unittest.TestCase):
    def test_scroll_preferences_are_independent_and_bidirectional(self):
        if not Gtk.init_check():
            self.skipTest("GTK tests need a display")
        packages = Path(__file__).resolve().parents[1] / "packages"
        for package in ("infinity-config", "infinity-setup"):
            sys.path.insert(0, str(packages / package / "root/usr/share/infinityos"))
        from config import InfinityConfig

        backend = Gio.memory_settings_backend_new()
        mouse_schema = "org.gnome.desktop.peripherals.mouse"
        touchpad_schema = "org.gnome.desktop.peripherals.touchpad"
        mouse = Gio.Settings.new_with_backend(mouse_schema, backend)
        touchpad = Gio.Settings.new_with_backend(touchpad_schema, backend)
        key = "natural-scroll"
        mouse.set_boolean(key, False)
        touchpad.set_boolean(key, True)

        page = Gtk.Box()
        with patch.object(Gio.Settings, "new", side_effect={mouse_schema: mouse,
                                                           touchpad_schema: touchpad}.__getitem__):
            InfinityConfig()._add_scroll_direction(page)
        row = page.get_first_child()
        mouse_toggle, touchpad_toggle = [child for child in row if isinstance(child, Gtk.CheckButton)]
        self.assertFalse(mouse_toggle.get_active())
        self.assertTrue(touchpad_toggle.get_active())
        touchpad_toggle.set_active(False)
        mouse_toggle.set_active(True)
        self.assertTrue(mouse.get_boolean(key))
        self.assertFalse(touchpad.get_boolean(key))
        mouse.set_boolean(key, False)
        self.assertFalse(mouse_toggle.get_active())
