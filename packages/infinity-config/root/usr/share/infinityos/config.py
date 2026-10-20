#!/usr/bin/python3
"""Infinity OS desktop controls."""

import sys
import subprocess
import threading
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from config_backend import (
    CURSOR_SCHEMA, DOCK_SCHEMA, DOCK_SCHEMA_DIR, cursor_percent,
    cursor_size, dock_percent, dock_size, percent_to_slider,
    slider_to_percent,
)
from diagnostics import write_report


CSS = b"""
window.infinity-window { background: transparent; }
box.infinity-shade { background: rgba(6, 4, 11, 0.76); }
box.infinity-card { background: #17121f; border: 1px solid #715b94; border-radius: 22px; box-shadow: 0 0 64px 8px rgba(100,83,148,0.28), 0 24px 72px rgba(0,0,0,0.65); color: #f3eef8; }
label.infinity-eyebrow { color: #bb9ce5; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
label.infinity-title { color: #f8f5fc; font-size: 29px; font-weight: 700; }
label.infinity-subtitle { color: #ada1bd; font-size: 13px; }
box.infinity-nav { background: #211a2c; border: 1px solid #3c304e; border-radius: 14px; padding: 5px; }
button.infinity-tab { background: transparent; border: 1px solid transparent; border-radius: 10px; color: #b8abc9; min-height: 42px; padding: 0 8px; font-size: 13px; font-weight: 600; box-shadow: none; }
button.infinity-tab:hover { background: #332940; color: #f4ecff; }
button.infinity-tab:checked { background: #66518f; border-color: #9275bd; color: #fff; box-shadow: 0 2px 9px rgba(0,0,0,0.25); }
button.infinity-tab:focus-visible { outline: 2px solid #c3a2ef; outline-offset: -2px; }
button.infinity-close { background: #251d30; border: 1px solid #40334f; border-radius: 20px; color: #d6c9e6; min-width: 34px; min-height: 34px; }
button.infinity-close:hover { background: #403250; color: white; }
label.infinity-page-title { color: #f0eaf6; font-size: 19px; font-weight: 700; }
box.infinity-row { background: #211b2b; border: 1px solid #3d314e; border-radius: 12px; padding: 20px; }
label.infinity-setting-name { color: #f3eef8; font-size: 16px; font-weight: 700; }
label.infinity-value { color: #d7b6ff; font-size: 17px; font-weight: 700; }
label.infinity-muted { color: #a99db8; font-size: 13px; }
scale.infinity-scale trough { min-height: 8px; border-radius: 8px; background: #3c304e; }
scale.infinity-scale highlight { border-radius: 8px; background: #a77bdb; }
scale.infinity-scale slider { min-width: 20px; min-height: 20px; margin: -6px; border-radius: 50%; background: #f4eaff; border: 0; box-shadow: 0 0 0 2px #a77bdb; }
scale.infinity-scale marks label { color: #aa9bbd; font-size: 12px; }
button.infinity-action { background: #211b2b; border: 1px solid #3d314e; border-radius: 12px; padding: 14px 18px; color: #f3eef8; box-shadow: none; }
button.infinity-action:hover { background: #352942; border-color: #8c6db5; }
button.infinity-action:focus-visible { outline: 2px solid #c3a2ef; }
box.infinity-footer { border-top: 1px solid #392d49; padding-top: 16px; }
"""


def label(text, style=None):
    widget = Gtk.Label(label=text)
    widget.set_xalign(0)
    if style:
        widget.add_css_class(style)
    return widget


def dock_settings():
    parent = Gio.SettingsSchemaSource.get_default()
    source = Gio.SettingsSchemaSource.new_from_directory(DOCK_SCHEMA_DIR, parent, False)
    schema = source.lookup(DOCK_SCHEMA, False)
    if schema is None:
        raise RuntimeError("Dash2Dock Animated settings are unavailable")
    return Gio.Settings.new_full(schema, None, None)


class InfinityConfig(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.infinityos.Config")
        self.window = None
        self.controls = {}
        self.syncing = False
        self.writing = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title="Infinity Config")
        self.window.set_decorated(False)
        self.window.add_css_class("infinity-window")
        self.window.maximize()
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

        overlay = Gtk.Overlay()
        shade = Gtk.Box()
        shade.add_css_class("infinity-shade")
        overlay.set_child(shade)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.CENTER)
        monitor = self.window.get_display().get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        card.set_size_request(min(760, max(400, geometry.width - 48)),
                              min(510, max(360, geometry.height - 48)))
        card.add_css_class("infinity-card")
        overlay.add_overlay(card)
        self.window.set_child(overlay)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header.set_margin_start(28)
        header.set_margin_end(22)
        header.set_margin_top(24)
        header.set_margin_bottom(20)
        icon = Gtk.Image.new_from_icon_name("infinity-config")
        icon.set_pixel_size(48)
        header.append(icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        titles.set_hexpand(True)
        titles.append(label("MAKE IT YOURS", "infinity-eyebrow"))
        titles.append(label("Infinity Config", "infinity-title"))
        titles.append(label("Adjust your Infinity OS desktop.", "infinity-subtitle"))
        header.append(titles)
        close = Gtk.Button(icon_name="window-close-symbolic")
        close.set_tooltip_text("Close Infinity Config")
        close.add_css_class("infinity-close")
        close.set_valign(Gtk.Align.START)
        close.connect("clicked", lambda _button: self.window.close())
        header.append(close)
        card.append(header)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav.add_css_class("infinity-nav")
        nav.set_margin_start(28)
        nav.set_margin_end(28)
        card.append(nav)
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        card.append(self.stack)

        group = None
        for name, symbol, description in (
            ("Desktop", "user-desktop-symbolic", "Pointer and desktop appearance"),
            ("Dock", "view-grid-symbolic", "Size and appearance of the dock"),
            ("Tweaks", "preferences-system-symbolic", "System tools and diagnostics"),
        ):
            button = Gtk.ToggleButton()
            tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            tab_content.set_halign(Gtk.Align.CENTER)
            tab_content.append(Gtk.Image.new_from_icon_name(symbol))
            tab_content.append(Gtk.Label(label=name))
            button.set_child(tab_content)
            button.set_hexpand(True)
            button.add_css_class("infinity-tab")
            if group:
                button.set_group(group)
            else:
                group = button
            button.connect("toggled", self._select_tab, name)
            nav.append(button)
            page = self._page(name, description)
            self.stack.add_named(page, name)
            if name == "Desktop":
                self._add_control(page, "Cursor size", "Scale the system pointer.",
                                  CURSOR_SCHEMA, "cursor-size", Gio.Settings.new(CURSOR_SCHEMA),
                                  cursor_percent, cursor_size, "int")
            elif name == "Dock":
                try:
                    settings = dock_settings()
                except Exception as exc:
                    page.append(label(f"Dock settings unavailable: {exc}", "infinity-muted"))
                else:
                    self._add_control(page, "Dock size", "Scale dock icons and their spacing.",
                                      DOCK_SCHEMA, "icon-size", settings,
                                      dock_percent, dock_size, "double")
            else:
                self._add_shortcut(page, "Extensions", "Enable or disable GNOME extensions.",
                                   "application-x-addon-symbolic", ["gnome-extensions-app"])
                self._add_shortcut(page, "System settings", "Open GNOME system settings.",
                                   "preferences-system-symbolic", ["gnome-control-center"])
                self._add_shortcut(page, "Updates", "Check packages and device firmware.",
                                   "software-update-available-symbolic", ["infinity-updater"])
                self._add_shortcut(page, "Save diagnostic report",
                                   "Save a private report without logs or personal identifiers.",
                                   "document-save-symbolic", None)
        group.set_active(True)

        footer = Gtk.Box()
        footer.add_css_class("infinity-footer")
        footer.set_margin_start(28)
        footer.set_margin_end(28)
        footer.set_margin_bottom(22)
        self.status = label("Changes apply immediately.", "infinity-muted")
        self.status.set_wrap(True)
        footer.append(self.status)
        card.append(footer)
        self.window.present()

    def _select_tab(self, button, name):
        if button.get_active():
            self.stack.set_visible_child_name(name)

    def _page(self, name, description):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(28)
        page.set_margin_end(28)
        page.set_margin_top(24)
        page.append(label(name, "infinity-page-title"))
        page.append(label(description, "infinity-muted"))
        return page

    def _add_shortcut(self, page, title, description, icon_name, command):
        button = Gtk.Button()
        button.add_css_class("infinity-action")
        button.set_margin_top(4)
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        content.append(icon)
        copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        copy.append(label(title, "infinity-setting-name"))
        copy.append(label(description, "infinity-muted"))
        content.append(copy)
        button.set_child(content)
        if command:
            button.connect("clicked", self._launch_tool, command)
        else:
            button.connect("clicked", self._save_diagnostics)
        page.append(button)

    def _launch_tool(self, _button, command):
        try:
            subprocess.Popen(command, start_new_session=True)
        except OSError as error:
            self.status.set_text(f"Could not open {command[0]}: {error}")

    def _save_diagnostics(self, _button):
        self.status.set_text("Collecting system information…")

        def work():
            try:
                path = write_report()
            except OSError as error:
                GLib.idle_add(self.status.set_text, f"Could not save report: {error}")
            else:
                GLib.idle_add(self.status.set_text, f"Saved private report: {path}")

        threading.Thread(target=work, daemon=True).start()

    def _add_control(self, page, title, description, schema, key, settings,
                     to_percent, to_value, value_type):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        row.add_css_class("infinity-row")
        row.set_margin_top(14)
        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        name = label(title, "infinity-setting-name")
        name.set_hexpand(True)
        heading.append(name)
        value = label("", "infinity-value")
        heading.append(value)
        row.append(heading)
        row.append(label(description, "infinity-muted"))
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.add_css_class("infinity-scale")
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        for position, caption in ((0, "20%"), (50, "100%"), (100, "200%")):
            scale.add_mark(position, Gtk.PositionType.BOTTOM, caption)
        getter = settings.get_int if value_type == "int" else settings.get_double
        current = to_percent(getter(key))
        scale.set_value(percent_to_slider(current))
        value.set_text(f"{current}%")
        scale.connect("value-changed", self._value_changed, schema)
        settings.connect(f"changed::{key}", self._setting_changed, schema)
        self.controls[schema] = (settings, key, scale, value, getter, to_percent,
                                 to_value, value_type)
        row.append(scale)
        page.append(row)

    def _value_changed(self, scale, schema):
        if self.syncing:
            return
        settings, key, _scale, value, _getter, _to_percent, to_value, value_type = self.controls[schema]
        percent = slider_to_percent(scale.get_value())
        value.set_text(f"{percent}%")
        if value_type == "int":
            self.writing = True
            try:
                settings.set_int(key, to_value(percent))
            finally:
                self.writing = False
        else:
            self.writing = True
            try:
                settings.set_double(key, to_value(percent))
            finally:
                self.writing = False

    def _setting_changed(self, _settings, _key, schema):
        if self.writing:
            return
        settings, key, scale, value, getter, to_percent, _to_value, _value_type = self.controls[schema]
        percent = to_percent(getter(key))
        self.syncing = True
        scale.set_value(percent_to_slider(percent))
        value.set_text(f"{percent}%")
        self.syncing = False


if __name__ == "__main__":
    raise SystemExit(InfinityConfig().run(sys.argv))
