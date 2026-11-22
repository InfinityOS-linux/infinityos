"""Map the same GTK backdrop client used by Setup and Config."""

import os
from pathlib import Path
import runpy
import sys

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


app_id, ready_property, report_file = sys.argv[1:]
report = Path(report_file)
backdrop = runpy.run_path(os.environ["INFINITY_SMOKE_APP_BACKDROP"])["PanelBackdrop"]
app = Gtk.Application(application_id=app_id)


def activate(app):
    window = Gtk.ApplicationWindow(application=app, title=app_id, decorated=False)
    window.add_css_class("infinity-window")
    window.maximize()
    backdrop(window, ready_property)

    def observe():
        temporary = report.with_suffix(".tmp")
        temporary.write_text("ready" if window.has_css_class("shell-backdrop") else "opaque")
        temporary.replace(report)
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add(100, observe)
    window.present()


app.connect("activate", activate)
raise SystemExit(app.run([sys.argv[0]]))
