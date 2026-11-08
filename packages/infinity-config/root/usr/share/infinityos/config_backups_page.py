"""Recovery snapshot management through the shared privileged helper."""
import json
import subprocess
import threading

from gi.repository import GLib, Gtk
from config_backups_i18n import tr


def label(text):
    return Gtk.Label(label=text, xalign=0, wrap=True, selectable=True)


class BackupsPage:
    def __init__(self, app, nav, group):
        self.app = app
        self.busy = False
        self.alive = True
        self.started = False
        self.tab = Gtk.ToggleButton(hexpand=True)
        content = Gtk.Box(spacing=8)
        content.set_halign(Gtk.Align.CENTER)
        content.append(Gtk.Image.new_from_icon_name('document-revert-symbolic'))
        content.append(Gtk.Label(label=tr('Backups')))
        self.tab.set_child(content)
        self.tab.add_css_class('infinity-tab')
        self.tab.set_group(group)
        self.tab.connect('toggled', app._select_tab, 'Backups')
        nav.append(self.tab)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ('start', 'end', 'top', 'bottom'):
            getattr(self.body, 'set_margin_' + side)(24)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=280)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.body)
        app.stack.add_named(scroll, 'Backups')
        title = label(tr('Backups'))
        title.add_css_class('infinity-page-title')
        self.body.append(title)
        for message in (
            'Create or restore backups by restarting and choosing Backups in the boot menu. Updates create a backup after restart.',
            'Snapshots on this disk do not protect against disk failure.',
            'Administrator authentication is required to view or delete system snapshots.',
        ):
            self.body.append(label(tr(message)))
        self.refresh = Gtk.Button(label=tr('Refresh'))
        self.refresh.connect('clicked', lambda _: self.load())
        self.body.append(self.refresh)
        self.rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.body.append(self.rows)
        app.stack.connect('notify::visible-child-name', self.selected)

    def selected(self, *_args):
        if self.app.stack.get_visible_child_name() == 'Backups' and not self.started:
            self.started = True
            self.load()

    def load(self, number=None):
        if self.busy or not self.alive:
            return
        self.busy = True
        self.body.set_sensitive(False)
        self.app.status.set_text(tr('Deleting snapshot…' if number is not None else 'Loading snapshots…'))
        def worker():
            result, error = None, None
            try:
                command = ['pkexec', '/usr/libexec/infinityos-backups-manage']
                command += ['list'] if number is None else ['delete', number]
                process = subprocess.run(command, check=True, capture_output=True, text=True)
                result = json.loads(process.stdout)
            except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                error = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
            GLib.idle_add(self.finish, result, error, number is not None)
        threading.Thread(target=worker, daemon=True).start()

    def finish(self, result, error, deleted):
        self.busy = False
        if not self.alive:
            return False
        self.body.set_sensitive(True)
        while self.rows.get_first_child():
            self.rows.remove(self.rows.get_first_child())
        if error is not None:
            message = tr('Operation failed or authentication was cancelled. Refresh to check the current state and retry.')
            self.rows.append(label(message))
            details = Gtk.Expander(label=tr('Error details'))
            details.set_child(label(error))
            self.rows.append(details)
            self.app.status.set_text(message)
            return False
        self.app.status.set_text(tr('Snapshot deleted.' if deleted else 'Snapshots refreshed.'))
        if not result['ready']:
            self.rows.append(label(tr('Backups are not initialized. Install InfinityOS on Btrfs to use system snapshots.')))
        elif not result['snapshots']:
            self.rows.append(label(tr('No snapshots yet.')))
        for record in result['snapshots']:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            row.add_css_class('infinity-row')
            row.append(label(f"#{record['number']} — {record['date']}"))
            row.append(label(record['description']))
            row.append(label(tr('System + /var; /home is preserved during restoration.' if record['complete'] else
                                'Incomplete or older backup; cannot restore system + /var.')))
            remove = Gtk.Button(label=tr('Delete'))
            remove.connect('clicked', lambda _, record=record: self.confirm_delete(record))
            row.append(remove)
            self.rows.append(row)
        return False

    def confirm_delete(self, record):
        dialog = Gtk.MessageDialog(transient_for=self.app.window, modal=True,
                                   text=tr('Delete snapshot #{number}?').format(number=record['number']),
                                   secondary_text=tr('This permanently deletes this recovery point and its /var copy. Current system files and /home are kept.'))
        dialog.add_button(tr('Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(tr('Delete'), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        def response(dialog, answer):
            dialog.destroy()
            if answer == Gtk.ResponseType.OK:
                self.load(record['number'])
        dialog.connect('response', response)
        dialog.present()
