"""Run the production updater window and DBus/CSS lifecycle without package IO."""
import ast
import json
import os
from pathlib import Path
import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

source = Path(os.environ['INFINITY_SMOKE_UPDATER'])
tree = ast.parse(source.read_text())
style = next(node for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'STYLE'
                     for target in node.targets))
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
updater = next(node for node in main.body if isinstance(node, ast.ClassDef) and node.name == 'Updater')
read_state = lambda: {'updates': [], 'errors': []}
tr = lambda text: text
exec(compile(ast.Module(body=[style, updater], type_ignores=[]), str(source), 'exec'))
# Only package IO is replaced. The production window, stylesheet, theme
# switching, async Shell proxy and readiness callback all run unmodified.
Updater.watch_state = lambda self: None
Updater.on_refresh = lambda self, *args, **kwargs: None
app = Updater()
report = Path(os.environ['INFINITY_SMOKE_BACKDROP_REPORT'])

def observe():
    window = getattr(app, 'window', None)
    report.write_text(json.dumps({'transparent': bool(window and window.has_css_class('shell-backdrop'))}))
    return GLib.SOURCE_CONTINUE

GLib.timeout_add(100, observe)
raise SystemExit(app.run([sys.argv[0]]))
