#!/usr/bin/python3
"""Infinity OS first-login application chooser."""

import getpass
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk

from launcher_backend import APPS, available, install, installed


MARKER = Path.home() / ".config/infinityos/launcher-complete"
ICON_DIR = Path(__file__).with_name("launcher-icons")
SECTIONS = (
    ("AI", "utilities-terminal-symbolic"),
    ("System", "preferences-system-symbolic"),
    ("Gaming", "applications-games-symbolic"),
    ("Creative", "applications-graphics-symbolic"),
    ("Office", "applications-office-symbolic"),
    ("Programming", "applications-development-symbolic"),
)

CSS = b"""
window.infinity-backdrop { background: rgba(7, 5, 13, 0.82); }
box.infinity-card { background: #17131f; border: 1px solid #635085; border-radius: 22px; box-shadow: 0 0 70px 14px rgba(100,83,148,0.32), 0 22px 70px rgba(0,0,0,0.6); color: #f0ebf6; }
button.infinity-tab { background: #2a2236; border: 1px solid #40334f; border-radius: 12px; color: #cfc5df; min-height: 62px; }
button.infinity-tab:checked { background: #645394; border-color: #a18ac7; color: white; }
box.infinity-row { background: #211b2b; border: 1px solid #392f49; border-radius: 12px; padding: 12px; }
label.infinity-section { color: #b9a8d7; font-weight: bold; letter-spacing: 1px; }
button.infinity-save { background: #645394; color: white; border-radius: 10px; min-width: 110px; min-height: 40px; }
button.infinity-close { background: transparent; color: #cfc5df; }
label.infinity-muted { color: #a69bb7; }
"""


def label(text, style=None):
    widget = Gtk.Label(label=text)
    widget.set_xalign(0)
    if style:
        widget.add_css_class(style)
    return widget


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

        self.window = Gtk.ApplicationWindow(application=self, title="InfinityLauncher")
        self.window.set_decorated(False)
        self.window.add_css_class("infinity-backdrop")
        self.window.connect("close-request", self._close_requested)
        self.window.fullscreen()

        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        backdrop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        backdrop.set_halign(Gtk.Align.CENTER)
        backdrop.set_valign(Gtk.Align.CENTER)
        monitor = self.window.get_display().get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        backdrop.set_size_request(min(1100, geometry.width - 48), min(760, geometry.height - 48))
        backdrop.add_css_class("infinity-card")
        self.window.set_child(backdrop)

        heading = Gtk.Overlay()
        heading.set_margin_start(30)
        heading.set_margin_end(22)
        heading.set_margin_top(22)
        heading.set_margin_bottom(14)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title_box.set_hexpand(True)
        title_box.set_halign(Gtk.Align.CENTER)
        title = label("InfinityLauncher", "title-1")
        title.set_xalign(0.5)
        title_box.append(title)
        subtitle = label("Choose what belongs in your Infinity OS workspace.", "infinity-muted")
        subtitle.set_xalign(0.5)
        title_box.append(subtitle)
        heading.set_child(title_box)
        close = Gtk.Button(icon_name="window-close-symbolic")
        close.add_css_class("infinity-close")
        close.set_halign(Gtk.Align.END)
        close.set_valign(Gtk.Align.CENTER)
        close.set_tooltip_text("Close")
        close.connect("clicked", lambda _button: self.window.close())
        heading.add_overlay(close)
        backdrop.append(heading)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        navigation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        navigation.set_margin_start(26)
        navigation.set_margin_end(26)
        navigation.set_margin_bottom(16)
        first = None
        for section, icon in SECTIONS:
            tab = Gtk.ToggleButton()
            tab.add_css_class("infinity-tab")
            tab.set_hexpand(True)
            if first:
                tab.set_group(first)
            else:
                first = tab
            tab_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            tab_content.set_halign(Gtk.Align.CENTER)
            tab_content.append(Gtk.Image.new_from_icon_name(icon))
            tab_content.append(Gtk.Label(label=section))
            tab.set_child(tab_content)
            tab.connect("toggled", self._select_tab, section.lower())
            navigation.append(tab)
            self.stack.add_named(self._page(section), section.lower())
        first.set_active(True)
        backdrop.append(navigation)
        backdrop.append(self.stack)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        footer.set_margin_start(28)
        footer.set_margin_end(28)
        footer.set_margin_top(14)
        footer.set_margin_bottom(20)
        self.status = label("Select apps, then click APPLY to install them.", "infinity-muted")
        self.status.set_wrap(True)
        self.status.set_hexpand(True)
        footer.append(self.status)
        self.save_button = Gtk.Button(label="APPLY")
        self.save_button.add_css_class("infinity-save")
        self.save_button.connect("clicked", self._save)
        footer.append(self.save_button)
        backdrop.append(footer)
        self.window.present()

    def _select_tab(self, button, name):
        if button.get_active():
            self.stack.set_visible_child_name(name)

    def _page(self, section):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_margin_start(28)
        scroller.set_margin_end(28)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_bottom(16)
        scroller.set_child(body)
        previous_group = None
        for app in (item for item in APPS if item.category == section):
            if app.group != previous_group:
                if previous_group:
                    body.append(Gtk.Separator())
                group = label(app.group.upper(), "infinity-section")
                group.set_margin_top(10)
                group.set_margin_bottom(3)
                body.append(group)
                previous_group = app.group

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            row.add_css_class("infinity-row")
            icon_name = app.source if app.kind == "flatpak" else app.icon
            icon_file = next((path for path in (ICON_DIR / f"{icon_name}.png", ICON_DIR / f"{icon_name}.svg")
                              if path.exists()), None)
            if icon_file:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_file), 36, 36, True)
                icon = Gtk.Picture.new_for_pixbuf(pixbuf)
            else:
                if not Gtk.IconTheme.get_for_display(self.window.get_display()).has_icon(icon_name):
                    icon_name = app.icon
                icon = Gtk.Image.new_from_icon_name(icon_name)
                icon.set_pixel_size(36)
            row.append(icon)
            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            details.set_hexpand(True)
            details.append(label(app.name, "heading"))
            note = label(app.description, "infinity-muted")
            note.set_wrap(True)
            details.append(note)
            if app.website.startswith("https://github.com/storytold/"):
                link = Gtk.LinkButton(uri=app.website, label="View source and releases")
                link.set_halign(Gtk.Align.START)
                details.append(link)
            row.append(details)
            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            supported = available(app)
            already = supported and installed(app)
            switch.set_active(already)
            switch.set_sensitive(supported and not already)
            if already:
                note.set_text("Installed")
            elif not supported:
                note.set_text("Available on x86_64")
            self.switches[app] = switch
            self.notes[app] = note
            row.append(switch)
            body.append(row)
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
            GLib.idle_add(self.status.set_text, f"Installing {index}/{len(selected)}: {app.name}…")
            try:
                install(app)
            except Exception as exc:
                errors.append(f"{app.name}: {exc}")
            else:
                GLib.idle_add(self._installed, app)
        GLib.idle_add(self._finished, errors)

    def _installed(self, app):
        self.notes[app].set_text("Installed")
        self.switches[app].set_active(True)
        return False

    def _finished(self, errors):
        self.busy = False
        if errors:
            self.status.set_text("Could not install:\n" + "\n".join(errors))
            for app, switch in self.switches.items():
                if self.notes[app].get_text() != "Installed" and available(app):
                    switch.set_sensitive(True)
            self.save_button.set_sensitive(True)
        else:
            self._complete()
        return False

    def _complete(self):
        MARKER.parent.mkdir(parents=True, exist_ok=True)
        MARKER.touch()
        self.status.set_text("Applied. Open InfinityLauncher from the applications menu anytime.")
        self.save_button.set_sensitive(False)

    def _close_requested(self, _window):
        if self.busy:
            self.status.set_text("Wait for installation to finish.")
            return True
        return False


if __name__ == "__main__":
    first_run = "--first-run" in sys.argv
    if first_run and (MARKER.exists() or getpass.getuser() in ("gnome-initial-setup", "liveuser")):
        raise SystemExit(0)
    raise SystemExit(InfinityLauncher().run([sys.argv[0]]))
