"""Exercise normal GTK Wayland cursor-shape requests without any Shell grab."""
import json
import os
from pathlib import Path
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk

report = Path(os.environ['INFINITY_SMOKE_CURSOR_REPORT'])
command = report.with_suffix('.mode')
state = {'mode': None, 'hover': False}
app = Gtk.Application(application_id='org.infinityos.CursorSmoke',
                      flags=Gio.ApplicationFlags.NON_UNIQUE)

def activate(application):
    window = Gtk.ApplicationWindow(application=application, title='Infinity cursor playback')
    window.set_default_size(400, 200)
    window.set_decorated(False)
    label = Gtk.Label(label='Native Wayland waiting cursor')
    window.set_child(label)
    motion = Gtk.EventControllerMotion()
    motion.connect('enter', lambda *_: state.update(hover=True))
    motion.connect('leave', lambda *_: state.update(hover=False))
    window.add_controller(motion)

    def observe():
        mode = command.read_text().strip() if command.exists() else 'wait'
        if mode != state['mode']:
            window.set_cursor_from_name(mode)
            state['mode'] = mode
        pointer = window.get_display().get_default_seat().get_pointer()
        surface, x, y = pointer.get_surface_at_position() if pointer else (None, 0, 0)
        state['pointer_here'] = surface is not None and surface == window.get_surface()
        state['point'] = [x, y]
        pending = report.with_suffix('.tmp')
        pending.write_text(json.dumps(state))
        pending.replace(report)
        return GLib.SOURCE_CONTINUE

    observe()
    GLib.timeout_add(50, observe)
    window.present()

app.connect('activate', activate)
raise SystemExit(app.run([]))
