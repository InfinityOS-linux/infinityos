#!/usr/bin/python3
"""Infinity OS first-login application chooser."""

import getpass
import sys
import threading
from time import monotonic
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk

from launcher_backend import APPS, active_local_model, available, install, installed
from launcher_i18n import tr


MARKER = Path.home() / ".config/infinityos/launcher-complete"
NEXT_START = Path.home() / ".config/infinityos/launcher-next-start"
ICON_DIR = Path(__file__).with_name("launcher-icons")
SECTIONS = (
    ("AI", "utilities-terminal-symbolic", "Assistants and command-line tools"),
    ("System", "preferences-system-symbolic", "Everyday essentials"),
    ("Gaming", "applications-games-symbolic", "Games, launchers and friends"),
    ("Creative", "applications-graphics-symbolic", "Tools for making things"),
    ("Office", "applications-office-symbolic", "Documents and productivity"),
    ("Programming", "applications-development-symbolic", "Build your workspace"),
)

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
label.infinity-page-title { color: #f0eaf6; font-size: 19px; font-weight: 700; }
box.infinity-row { background: #211b2b; border: 1px solid #3d314e; border-radius: 12px; padding: 11px 14px; }
box.infinity-row:hover { background: #292136; border-color: #65517d; }
label.infinity-section { color: #bea7df; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
label.infinity-app-name { color: #f3eef8; font-weight: 700; }
button.infinity-save { background: #745aa4; border: 1px solid #9478c4; color: white; border-radius: 10px; min-width: 124px; min-height: 42px; font-weight: 700; }
button.infinity-save:hover { background: #8569b8; }
button.infinity-save:disabled { background: #413451; color: #a99cb8; }
button.infinity-close { background: #251d30; border: 1px solid #40334f; border-radius: 20px; color: #d6c9e6; min-width: 34px; min-height: 34px; }
button.infinity-close:hover { background: #403250; color: white; }
box.infinity-footer { border-top: 1px solid #392d49; padding-top: 16px; }
label.infinity-muted { color: #a99db8; }
progressbar.infinity-install-progress trough { min-height: 5px; background: #2d233b; border-radius: 0 0 22px 22px; }
progressbar.infinity-install-progress progress { min-height: 5px; background: #ad82e9; border-radius: 0 0 22px 22px; }
"""


def label(text, style=None):
    widget = Gtk.Label(label=text)
    widget.set_xalign(0)
    if style:
        widget.add_css_class(style)
    return widget


class InfinityLauncher(Gtk.Application):
    def __init__(self, first_run=False):
        super().__init__(application_id="org.infinityos.Launcher")
        self.first_run = first_run
        self.window = None
        self.switches = {}
        self.notes = {}
        self.busy = False
        self.closing = False
        self.applied = False
        self.progress_source = 0

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title="InfinityLauncher")
        self.window.set_decorated(False)
        self.window.add_css_class("infinity-window")
        self.window.connect("close-request", self._close_requested)
        self.window.maximize()

        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

        overlay = Gtk.Overlay()
        self.shade = Gtk.Box()
        self.shade.add_css_class("infinity-shade")
        overlay.set_child(self.shade)
        backdrop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        backdrop.set_halign(Gtk.Align.CENTER)
        backdrop.set_valign(Gtk.Align.CENTER)
        monitor = self.window.get_display().get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        backdrop.set_size_request(min(1020, geometry.width - 48), min(640, geometry.height - 48))
        backdrop.add_css_class("infinity-card")
        overlay.add_overlay(backdrop)
        self.window.set_child(overlay)
        self.card = backdrop

        heading = Gtk.Overlay()
        heading.set_margin_start(30)
        heading.set_margin_end(22)
        heading.set_margin_top(24)
        heading.set_margin_bottom(20)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title_box.set_hexpand(True)
        title_box.set_halign(Gtk.Align.CENTER)
        eyebrow = label(tr("WELCOME TO INFINITY OS"), "infinity-eyebrow")
        eyebrow.set_xalign(0.5)
        title_box.append(eyebrow)
        title = label("InfinityLauncher", "infinity-title")
        title.set_xalign(0.5)
        title_box.append(title)
        subtitle = label(tr("Make it yours. Pick the apps you want, then add more anytime."), "infinity-subtitle")
        subtitle.set_xalign(0.5)
        title_box.append(subtitle)
        heading.set_child(title_box)
        close = Gtk.Button(icon_name="window-close-symbolic")
        close.add_css_class("infinity-close")
        close.set_halign(Gtk.Align.END)
        close.set_valign(Gtk.Align.CENTER)
        close.set_tooltip_text(tr("Close"))
        close.connect("clicked", lambda _button: self.window.close())
        heading.add_overlay(close)
        backdrop.append(heading)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(100)
        navigation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        navigation.add_css_class("infinity-nav")
        navigation.set_margin_start(26)
        navigation.set_margin_end(26)
        navigation.set_margin_bottom(20)
        first = None
        for section, icon, description in SECTIONS:
            tab = Gtk.ToggleButton()
            tab.add_css_class("infinity-tab")
            tab.set_hexpand(True)
            if first:
                tab.set_group(first)
            else:
                first = tab
            tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
            tab_content.set_halign(Gtk.Align.CENTER)
            tab_icon = Gtk.Image.new_from_icon_name(icon)
            tab_icon.set_pixel_size(17)
            tab_content.append(tab_icon)
            tab_content.append(Gtk.Label(label=tr(section)))
            tab.set_child(tab_content)
            tab.connect("toggled", self._select_tab, section.lower())
            navigation.append(tab)
            self.stack.add_named(self._page(section, description), section.lower())
        first.set_active(True)
        backdrop.append(navigation)
        backdrop.append(self.stack)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        footer.add_css_class("infinity-footer")
        footer.set_margin_start(28)
        footer.set_margin_end(28)
        footer.set_margin_top(10)
        footer.set_margin_bottom(22)
        self.status = label(tr("Your changes install when you click Apply."), "infinity-muted")
        self.status.set_wrap(True)
        self.status.set_hexpand(True)
        footer.append(self.status)
        self.next_start = Gtk.CheckButton(label=tr("Run at next startup"))
        self.next_start.set_active(NEXT_START.exists() and not self.first_run)
        footer.append(self.next_start)
        self.save_button = Gtk.Button(label=tr("Apply"))
        self.save_button.add_css_class("infinity-save")
        self.save_button.connect("clicked", self._save)
        footer.append(self.save_button)
        backdrop.append(footer)
        self.progress = Gtk.ProgressBar()
        self.progress.add_css_class("infinity-install-progress")
        self.progress.set_pulse_step(0.04)
        # Keep the activity strip inside the card's rounded bottom corners.
        self.progress.set_margin_start(18)
        self.progress.set_margin_end(18)
        self.progress.set_margin_bottom(2)
        self.progress.set_visible(False)
        backdrop.append(self.progress)
        self.shade.set_opacity(0)
        self.card.set_opacity(0)
        self.window.present()
        self._animate(opening=True)

    def _select_tab(self, button, name):
        if button.get_active():
            self.stack.set_visible_child_name(name)

    def _page(self, section, description):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_margin_start(28)
        scroller.set_margin_end(28)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_bottom(16)
        scroller.set_child(body)
        page_heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        page_heading.set_margin_bottom(7)
        page_heading.append(label(tr(section), "infinity-page-title"))
        page_heading.append(label(tr(description), "infinity-muted"))
        body.append(page_heading)
        previous_group = None
        local_model_group = None
        selected_model = active_local_model()
        for app in (item for item in APPS if item.category == section):
            if app.group != previous_group:
                if previous_group:
                    body.append(Gtk.Separator())
                group = label(tr(app.group).upper(), "infinity-section")
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
                size = 30 if app.source.startswith("storytold/") else 36
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_file), size, size, True)
                icon = Gtk.Picture.new_for_pixbuf(pixbuf)
            else:
                if not Gtk.IconTheme.get_for_display(self.window.get_display()).has_icon(icon_name):
                    icon_name = app.icon
                icon = Gtk.Image.new_from_icon_name(icon_name)
                icon.set_pixel_size(36)
            icon_cell = Gtk.Box()
            icon_cell.set_size_request(36, 36)
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            icon_cell.append(icon)
            row.append(icon_cell)
            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            details.set_hexpand(True)
            details.append(label(app.name, "infinity-app-name"))
            note = label(tr(app.description), "infinity-muted")
            note.set_wrap(True)
            details.append(note)
            if app.website.startswith("https://github.com/storytold/"):
                link = Gtk.LinkButton(uri=app.website, label=tr("View source and releases"))
                link.set_halign(Gtk.Align.START)
                details.append(link)
            row.append(details)
            if app.kind == "local-model":
                switch = Gtk.CheckButton()
                if local_model_group:
                    switch.set_group(local_model_group)
                else:
                    local_model_group = switch
            else:
                switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            supported = available(app)
            already = supported and installed(app)
            switch.set_active(already if app.kind != "local-model" else
                              already and app.source == selected_model)
            switch.set_sensitive(supported and (app.kind == "local-model" or not already))
            if already and app.kind != "local-model":
                note.set_text(tr("Installed"))
            elif not supported:
                note.set_text(tr("Available on x86_64"))
            self.switches[app] = switch
            self.notes[app] = note
            row.append(switch)
            body.append(row)
        return scroller

    def _save(self, _button):
        selected = [app for app, switch in self.switches.items()
                    if switch.get_sensitive() and switch.get_active() and
                    (app.kind != "local-model" or
                     app.source != active_local_model() or not installed(app))]
        if not selected:
            self._complete()
            return
        self.busy = True
        self.save_button.set_sensitive(False)
        self.progress.set_visible(True)
        self.progress_source = GLib.timeout_add(80, self._pulse_progress)
        for switch in self.switches.values():
            switch.set_sensitive(False)
        threading.Thread(target=self._install, args=(selected,), daemon=True).start()

    def _pulse_progress(self):
        self.progress.pulse()
        return True

    def _install(self, selected):
        errors = []
        for index, app in enumerate(selected, 1):
            GLib.idle_add(self.status.set_text, tr("Installing {index}/{total}: {name}…").format(
                index=index, total=len(selected), name=app.name))
            try:
                install(app)
            except Exception as exc:
                errors.append(f"{app.name}: {exc}")
            else:
                GLib.idle_add(self._installed, app)
        GLib.idle_add(self._finished, errors)

    def _installed(self, app):
        self.notes[app].set_text(tr("Active local model") if app.kind == "local-model"
                                 else tr("Installed"))
        self.switches[app].set_active(True)
        return False

    def _finished(self, errors):
        self.busy = False
        if self.progress_source:
            GLib.source_remove(self.progress_source)
            self.progress_source = 0
        self.progress.set_visible(False)
        if errors:
            self.status.set_text(tr("Could not install:\n") + "\n".join(errors))
            active_model = active_local_model()
            for app, switch in self.switches.items():
                if (app.kind == "local-model" or self.notes[app].get_text() != tr("Installed")) and available(app):
                    switch.set_sensitive(True)
                if app.kind == "local-model":
                    switch.set_active(app.source == active_model)
            self.save_button.set_sensitive(True)
        else:
            self._complete()
        return False

    def _complete(self):
        self.applied = True
        self._begin_close()

    def _animate(self, opening):
        if not Gtk.Settings.get_default().get_property("gtk-enable-animations"):
            self.shade.set_opacity(1 if opening else 0)
            self.card.set_opacity(1 if opening else 0)
            if not opening:
                self._finish_close()
            return

        started = monotonic()
        duration = 0.17 if opening else 0.14

        def frame(_widget, _clock):
            progress = min((monotonic() - started) / duration, 1)
            eased = 1 - (1 - progress) ** 3
            visibility = eased if opening else 1 - eased
            self.shade.set_opacity(visibility)
            self.card.set_opacity(visibility)
            self.card.set_margin_top(round(12 * (1 - visibility)))
            if progress < 1:
                return True
            if not opening:
                self._finish_close()
            return False

        self.window.add_tick_callback(frame)

    def _begin_close(self):
        if self.closing:
            return
        self.closing = True
        self._animate(opening=False)

    def _finish_close(self):
        NEXT_START.parent.mkdir(parents=True, exist_ok=True)
        if self.next_start.get_active():
            NEXT_START.touch()
        else:
            NEXT_START.unlink(missing_ok=True)
        self.window.destroy()
        self.window = None
        if self.first_run or self.applied:
            MARKER.parent.mkdir(parents=True, exist_ok=True)
            MARKER.touch()

    def _close_requested(self, _window):
        if self.busy:
            self.status.set_text(tr("Wait for installation to finish."))
            return True
        self._begin_close()
        return True


if __name__ == "__main__":
    first_run = "--first-run" in sys.argv
    if first_run and (getpass.getuser() in ("gnome-initial-setup", "liveuser") or
                      (MARKER.exists() and not NEXT_START.exists())):
        raise SystemExit(0)
    raise SystemExit(InfinityLauncher(first_run=first_run).run([sys.argv[0]]))
