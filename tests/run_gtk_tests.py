"""Required Fedora GTK gate: a missing display or skipped test is a failure."""
import sys
import unittest
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

if not Gtk.init_check():
    raise SystemExit("GTK display unavailable")
suite = unittest.defaultTestLoader.discover("tests", pattern="test_*_page.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1)
