#!/usr/bin/python3
"""Infinity OS first-login application chooser."""

import getpass
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from launcher_backend import APPS, available, install, installed


MARKER = Path.home() / ".config/infinityos/launcher-complete"
SECTIONS = ("System", "Gaming", "Creative", "Programming", "AI")


class InfinityLauncher(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.infinityos.Launcher")
        self.window = None
        self.switches = {}
        self.notes = {}
        self.busy = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title="Infinity Launcher")
        self.window.set_default_size(850, 620)
        self.window.connect("close-request", self._close_requested)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(root)

        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        heading.set_margin_top(24)
        heading.set_margin_bottom(16)
        heading.set_margin_start(24)
        heading.set_margin_end(24)
        title = Gtk.Label(label="Infinity Launcher")
        title.set_xalign(0)
        title.add_css_class("title-1")
        heading.append(title)
        subtitle = Gtk.Label(label="Wybierz aplikacje. Instalacja rozpocznie się dopiero po naciśnięciu SAVE.")
        subtitle.set_xalign(0)
        subtitle.set_wrap(True)
        heading.append(subtitle)
        root.append(heading)

        stack = Gtk.Stack()
        stack.set_vexpand(True)
        tabs = Gtk.StackSwitcher(stack=stack)
        tabs.set_halign(Gtk.Align.CENTER)
        tabs.set_margin_bottom(12)
        root.append(tabs)
        root.append(stack)
        for section in SECTIONS:
            stack.add_titled(self._page(section), section.lower(), section)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        footer.set_margin_top(12)
        footer.set_margin_bottom(18)
        footer.set_margin_start(24)
        footer.set_margin_end(24)
        self.status = Gtk.Label(label="Gotowe do wyboru")
        self.status.set_xalign(0)
        self.status.set_wrap(True)
        self.status.set_hexpand(True)
        footer.append(self.status)
        self.save_button = Gtk.Button(label="SAVE")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._save)
        footer.append(self.save_button)
        root.append(footer)

        css = Gtk.CssProvider()
        css.load_from_data(b"button.suggested-action { background: #645394; color: white; min-width: 96px; } ")
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.window.present()

    def _page(self, section):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.set_margin_start(24)
        body.set_margin_end(24)
        body.set_margin_bottom(20)
        scroller.set_child(body)
        if section == "System":
            label = Gtk.Label(label="TODO")
            label.add_css_class("title-2")
            label.set_valign(Gtk.Align.CENTER)
            label.set_vexpand(True)
            body.append(label)
            return scroller

        for app in (item for item in APPS if item.category == section):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            row.set_margin_top(8)
            row.set_margin_bottom(8)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            text.set_hexpand(True)
            name = Gtk.Label(label=app.name)
            name.set_xalign(0)
            name.add_css_class("heading")
            text.append(name)
            note = Gtk.Label(label=app.description)
            note.set_xalign(0)
            note.set_wrap(True)
            note.add_css_class("dim-label")
            text.append(note)
            row.append(text)
            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            supported = available(app)
            already = supported and installed(app)
            switch.set_active(already)
            switch.set_sensitive(supported and not already)
            if already:
                note.set_text("Zainstalowane")
            elif app.x86_only and not supported:
                note.set_text("Dostępne na x86_64")
            self.switches[app] = switch
            self.notes[app] = note
            row.append(switch)
            body.append(row)
            body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        return scroller

    def _save(self, _button):
        selected = [app for app, switch in self.switches.items()
                    if switch.get_sensitive() and switch.get_active()]
        if not selected:
            self._complete()
            return
        self.busy = True
        self.save_button.set_sensitive(False)
        for switch in self.switches.values():
            switch.set_sensitive(False)
        threading.Thread(target=self._install, args=(selected,), daemon=True).start()

    def _install(self, selected):
        errors = []
        for index, app in enumerate(selected, 1):
            GLib.idle_add(self.status.set_text, f"Instalowanie {index}/{len(selected)}: {app.name}…")
            try:
                install(app)
            except Exception as exc:
                errors.append(f"{app.name}: {exc}")
            else:
                GLib.idle_add(self._installed, app)
        GLib.idle_add(self._finished, errors)

    def _installed(self, app):
        self.notes[app].set_text("Zainstalowane")
        self.switches[app].set_active(True)
        return False

    def _finished(self, errors):
        self.busy = False
        if errors:
            self.status.set_text("Nie udało się zainstalować:\n" + "\n".join(errors))
            for app, switch in self.switches.items():
                if self.notes[app].get_text() != "Zainstalowane" and available(app):
                    switch.set_sensitive(True)
            self.save_button.set_sensitive(True)
        else:
            self._complete()
        return False

    def _complete(self):
        MARKER.parent.mkdir(parents=True, exist_ok=True)
        MARKER.touch()
        self.status.set_text("Zapisano. Infinity Launcher znajdziesz później w menu aplikacji.")
        self.save_button.set_sensitive(False)

    def _close_requested(self, _window):
        if self.busy:
            self.status.set_text("Poczekaj na zakończenie instalacji.")
            return True
        return False


if __name__ == "__main__":
    first_run = "--first-run" in sys.argv
    if first_run and (MARKER.exists() or getpass.getuser() in ("gnome-initial-setup", "liveuser")):
        raise SystemExit(0)
    raise SystemExit(InfinityLauncher().run([sys.argv[0]]))
