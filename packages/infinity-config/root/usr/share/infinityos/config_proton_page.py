"""Proton manager UI; downloads never block the GTK thread."""
import threading

from gi.repository import Gio, GLib, Gtk
import config_proton as backend
from config_proton_i18n import tr


def label(message):
    return Gtk.Label(label=message, xalign=0, wrap=True, selectable=True)


def button(message, action):
    widget = Gtk.Button(label=tr(message))
    widget.connect('clicked', lambda _: action())
    return widget


class ProtonPage:
    def __init__(self, app, nav, group):
        self.app = app
        self.busy = False
        self.alive = True
        self.started = False
        self.generation = 0
        self.catalog = {}
        tab = Gtk.ToggleButton(label='Proton', hexpand=True)
        tab.add_css_class('infinity-tab')
        tab.set_group(group)
        tab.connect('toggled', app._select_tab, 'Proton')
        nav.append(tab)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ('start', 'end', 'top', 'bottom'):
            getattr(self.body, 'set_margin_' + side)(24)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=280)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.body)
        app.stack.add_named(scroll, 'Proton')
        app.stack.connect('notify::visible-child-name', self.selected)

    def selected(self, *_args):
        if self.app.stack.get_visible_child_name() == 'Proton' and not self.started:
            self.started = True
            self.refresh()

    def close(self, *_args):
        if self.busy:
            self.app.status.set_text(tr('Wait for the current Proton operation to finish.'))
            return True
        self.alive = False
        return False

    def open_uri(self, uri):
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except GLib.Error:
            self.app.status.set_text(tr('Operation failed. Check the connection, available disk space and folder permissions.'))

    def refresh(self, fetch=True):
        if self.busy or not self.alive:
            return
        self.generation += 1
        generation = self.generation
        while self.body.get_first_child():
            self.body.remove(self.body.get_first_child())
        title = label(tr('Proton versions'))
        title.add_css_class('infinity-page-title')
        self.body.append(title)
        self.body.append(label(tr('Manage compatibility tools for this account and Steam.')))
        self.body.append(label(tr('Restart Steam after changes. Updates keep older versions used by your games.')))
        self.refresh_button = button('Refresh', self.refresh)
        self.body.append(self.refresh_button)
        self.progress = Gtk.ProgressBar(show_text=True, visible=False)
        self.body.append(self.progress)
        self.body.append(label(tr('Downloaded versions')))
        try:
            self.rows = backend.installed()
        except (OSError, ValueError):
            self.rows = []
            self.body.append(label(tr('Operation failed. Check the connection, available disk space and folder permissions.')))
        if not self.rows:
            self.body.append(label(tr('No downloaded versions.')))
        for record in self.rows:
            card = self.card(record['name'])
            card.append(label('\n'.join(str(p) for p in record['paths'])))
            card.append(button('Open folder', lambda row=record: self.open_uri(row['paths'][0].as_uri())))
            if record['steam']:
                card.append(label(tr('Installed by Steam; updates and removal are handled by Steam.')))
                card.append(button('Manage in Steam', lambda: self.open_uri('steam://open/games')))
            else:
                card.append(button('Remove', lambda row=record: self.confirm_remove(row)))
        self.body.append(label(tr('Available releases')))
        pending = set(backend.PROVIDERS) if fetch else set()
        self.refresh_button.set_sensitive(not pending)
        for provider, repo in backend.PROVIDERS.items():
            card = self.card(provider)
            card.append(Gtk.LinkButton(uri=f'https://github.com/{repo}/releases', label=tr('Official releases')))
            state = label(tr('Loading releases…'))
            card.append(state)
            if not fetch:
                self.release_controls(card, state, self.catalog.get(provider))
                continue

            def load(provider=provider, card=card, state=state):
                try:
                    releases = backend.releases(provider)
                except Exception:
                    releases = None
                def finish():
                    if not self.alive or generation != self.generation:
                        return False
                    self.catalog[provider] = releases
                    self.release_controls(card, state, releases)
                    pending.discard(provider)
                    self.refresh_button.set_sensitive(not pending)
                    return False
                GLib.idle_add(finish)
            threading.Thread(target=load, daemon=True).start()

    def card(self, title):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class('infinity-row')
        card.append(label(title))
        self.body.append(card)
        return card

    def release_controls(self, card, state, releases):
        if not releases:
            state.set_text(tr('Release list unavailable. Check your connection and refresh.') if releases is None
                           else tr('No verified release for this architecture.'))
            return
        card.remove(state)
        dropdown = Gtk.DropDown.new_from_strings([item['tag'] for item in releases])
        card.append(dropdown)
        action = button('Install', lambda: self.install(releases[dropdown.get_selected()]))
        card.append(action)
        def selection(*_args):
            asset = releases[dropdown.get_selected()]
            same_provider = [row for row in self.rows if (row['metadata'] or {}).get('provider') == asset['provider']]
            current = any((row['metadata'] or {}).get('digest') == asset['digest'] and
                          len(row['paths']) == len(backend.tool_roots()) for row in same_provider)
            action.set_label(tr('Installed' if current else 'Update' if same_provider else 'Install'))
            action.set_sensitive(not current)
        dropdown.connect('notify::selected', selection)
        selection()

    def job(self, work, message):
        if self.busy:
            return
        self.busy = True
        self.body.set_sensitive(False)
        self.progress.set_visible(True)
        self.progress.set_text(tr(message))
        def finish(failed):
            self.busy = False
            self.body.set_sensitive(True)
            self.refresh(fetch=False)
            self.app.status.set_text(tr('Operation failed. Check the connection, available disk space and folder permissions.') if failed
                                     else tr('Done. Restart Steam to refresh its compatibility tools.'))
            return False
        def worker():
            try:
                work()
            except Exception:
                GLib.idle_add(finish, True)
            else:
                GLib.idle_add(finish, False)
        threading.Thread(target=worker, daemon=True).start()

    def install(self, asset):
        def progress(done, total):
            def update():
                if self.busy:
                    self.progress.set_fraction(done / total)
                    self.progress.set_text(tr('Downloading: {percent}%').format(percent=int(done * 100 / total)) if done < total else tr('Installing…'))
                return False
            GLib.idle_add(update)
        self.job(lambda: backend.install(asset, progress=progress), 'Installing…')

    def confirm_remove(self, record):
        dialog = Gtk.MessageDialog(transient_for=self.app.window, modal=True,
                                   text=tr('Remove {name}?').format(name=record['name']),
                                   secondary_text=tr('Removes this version from native Steam and Flatpak where listed. Games using it will need another version. Game saves and prefixes are kept.'))
        dialog.add_button(tr('Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(tr('Remove'), Gtk.ResponseType.OK)
        def response(dialog, answer):
            dialog.destroy()
            if answer == Gtk.ResponseType.OK:
                self.job(lambda: backend.remove(record), 'Removing…')
        dialog.connect('response', response)
        dialog.present()
