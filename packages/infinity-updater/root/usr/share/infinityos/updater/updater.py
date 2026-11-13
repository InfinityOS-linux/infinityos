import sys
import threading
from history import read_history, record_operation
from datetime import datetime

from checker import check_updates, read_state, save_state, offline_status, state_path, refresh_state
from i18n import tr, update_count
from progress import run_update_command


EXTENSION_RPMS = {'infinityos-shell-extensions', 'infinity-terminal', 'infinity-updater'}


def includes_extension_update(updates):
    return any(item['kind'] == 'RPM' and item['name'] in EXTENSION_RPMS for item in updates)


def pending_rpm_names(before, after):
    requested = {item['name'] for item in before if item['kind'] == 'RPM'}
    return sorted(requested & {item['name'] for item in after if item['kind'] == 'RPM'})


STYLE = b'''
window.infinity-updater { background: #111018; color: #f4f0fa; }
window.infinity-updater.csd { box-shadow: -12px 0 28px 0 rgba(0, 0, 0, 0.32); }
window.infinity-updater.csd.light-mode { box-shadow: -10px 0 26px 0 rgba(27, 17, 43, 0.20); }
window.infinity-updater > .titlebar { min-height: 0; padding: 0; margin: 0; border: 0; }
.infinity-results, .infinity-results viewport { background: #111018; }
.hero { background: #1b1727; border-bottom: 1px solid #3b3152; padding: 20px; }
.hero-title { font-size: 24px; font-weight: 800; color: #ffffff; }
.hero-subtitle { color: #b9adcf; }
.pill { background: #392d58; color: #e4d4ff; border-radius: 999px; padding: 5px 13px; font-weight: 700; }
.update-card { background: #201b2b; border: 1px solid #3a304d; border-radius: 13px; padding: 13px 16px; }
.update-name { font-weight: 700; color: #ffffff; }
.muted { color: #b4a9c7; }
button.primary { background: #765caa; color: #ffffff; border-radius: 9px; padding: 9px 18px; font-weight: 700; }
button.primary label { color: #ffffff; }
button.primary:hover { background: #8e71c6; }
button.secondary { background: #322941; color: #f4edff; border-radius: 9px; padding: 9px 16px; }
button.secondary label { color: #f4edff; }
.footer { background: #17131f; border-top: 1px solid #3b3152; padding: 17px 24px; }
.update-progress trough { min-height: 5px; background: #322941; border-radius: 999px; }
.update-progress progress { min-height: 5px; background: #ad82e9; border-radius: 999px; }
@keyframes infinity-updater-spin { to { transform: rotate(1turn); } }
window.infinity-updater spinner {
  -gtk-icon-source: none;
  border: 4px solid #3b3152;
  border-top-color: #ad82e9;
  border-radius: 50%;
}
window.infinity-updater spinner:checked { animation: infinity-updater-spin 900ms linear infinite; }
.state-title { font-size: 22px; font-weight: 700; color: #ffffff; }
.state-icon { color: #ad82e9; }
window.infinity-updater.light-mode { background: #f6f3fa; color: #241b31; }
window.infinity-updater.light-mode .infinity-results,
window.infinity-updater.light-mode .infinity-results viewport { background: #f6f3fa; }
window.infinity-updater.light-mode .hero { background: #eee8f6; border-color: #d7c9e7; }
window.infinity-updater.light-mode .hero-title,
window.infinity-updater.light-mode .state-title { color: #241b31; }
window.infinity-updater.light-mode .hero-subtitle,
window.infinity-updater.light-mode .muted { color: #574c67; }
window.infinity-updater.light-mode .pill { background: #e5d9f3; color: #41275c; }
window.infinity-updater.light-mode .update-card { background: #ffffff; border-color: #d7c9e7; }
window.infinity-updater.light-mode .update-name { color: #241b31; }
window.infinity-updater.light-mode button.primary { background: #604583; color: #ffffff; }
window.infinity-updater.light-mode button.primary label { color: #ffffff; }
window.infinity-updater.light-mode button.primary:hover { background: #4d356e; }
window.infinity-updater.light-mode button.primary:disabled { background: #d8cce4; color: #554866; }
window.infinity-updater.light-mode button.primary:disabled label { color: #554866; }
window.infinity-updater.light-mode button.secondary { background: #e8e0f0; color: #2b203d; }
window.infinity-updater.light-mode button.secondary label { color: #2b203d; }
window.infinity-updater.light-mode button.secondary:hover { background: #ded2ea; }
window.infinity-updater.light-mode button.secondary:disabled { background: #e8e2ef; color: #665b72; }
window.infinity-updater.light-mode button.secondary:disabled label { color: #665b72; }
window.infinity-updater.light-mode button.primary:focus-visible,
window.infinity-updater.light-mode button.secondary:focus-visible { outline: 2px solid #604583; }
window.infinity-updater.light-mode .footer { background: #f1ebf7; border-color: #d7c9e7; }
window.infinity-updater.light-mode .update-progress trough { background: #ddd1e9; }
window.infinity-updater.light-mode .update-progress progress { background: #604583; }
window.infinity-updater.light-mode spinner { border-color: #d7c9e7; border-top-color: #604583; }
window.infinity-updater.light-mode .state-icon { color: #604583; }
window.infinity-updater button.restart { background: #b52c3c; color: #ffffff; border-radius: 9px; padding: 9px 16px; font-weight: 700; }
window.infinity-updater button.restart label { color: #ffffff; }
window.infinity-updater button.restart:hover { background: #ce3a4b; }
window.infinity-updater button.restart:disabled { background: #80515a; }
window.infinity-updater .update-actions button { padding: 9px 12px; }

'''


def network_is_offline(monitor, gio):
    """Only call a connection offline when GIO has a definite answer."""
    return (not monitor.get_network_available() or
            monitor.get_connectivity() in (gio.NetworkConnectivity.LOCAL,
                                           gio.NetworkConnectivity.LIMITED,
                                           gio.NetworkConnectivity.PORTAL))


def update_rows(updates, offline):
    """Keep queued versions visible when a repository no longer lists them."""
    queued = offline.get('packages', []) if offline.get('pending') else []
    rows = []
    for item in updates:
        ready = item['kind'] == 'RPM' and any(
            p['name'] == item['name'] and (not item.get('arch') or p['arch'] == item['arch'])
            and p['version'] == item['version'].removeprefix('0:')
            for p in queued)
        rows.append({**item, 'pending': ready})
    names = {(item['name'], item.get('arch')) for item in updates if item['kind'] == 'RPM'}
    rows.extend({**item, 'pending': True} for item in queued
                if (item['name'], item['arch']) not in names and (item['name'], None) not in names)
    return rows


def restart_ready(updates, offline):
    return bool(offline.get('pending')) and not any(not item.get('pending') for item in updates)


def install_commands(updates):
    kinds = {item['kind'] for item in updates}
    commands = []
    if 'RPM' in kinds:
        commands.append(('System packages', ['pkexec', '/usr/libexec/infinityos-upgrade-system']))
    for item in updates:
        if item['kind'] in ('InfinitySetup RPM', 'InfinitySetup AppImage'):
            commands.append((item['name'], ['python3',
                '/usr/share/infinityos/updater/github_update.py', item['source']]))
    if 'Flatpak system' in kinds:
        commands.append(('System Flatpaks', ['pkexec', '/usr/bin/flatpak', 'update',
                                              '--system', '--noninteractive', '--assumeyes']))
    if 'Flatpak user' in kinds:
        commands.append(('Your Flatpaks', ['flatpak', 'update', '--user',
                                            '--noninteractive', '--assumeyes']))
    if 'Firmware' in kinds:
        commands.append(('Device firmware', ['pkexec', '/usr/bin/fwupdmgr', 'update',
                                             '--assume-yes', '--no-reboot-check']))
    return commands


def main():
    if '--check' in sys.argv:
        refresh_state()
        return 0

    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gdk, Gio, GLib, Gtk, Pango

    class Updater(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='org.infinityos.Updater')
            self.state = read_state()
            self.busy = False
            self.checking = False
            self.offline = False
            self.network_monitor = Gio.NetworkMonitor.get_default()
            self.state_monitor = None

        def do_activate(self):
            if getattr(self, 'window', None):
                self.add_window(self.window)
                self.window.present()
                if not self.busy:
                    self.on_refresh(None, force=False)
                return
            css = Gtk.CssProvider()
            css.load_from_data(STYLE)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.window = Gtk.ApplicationWindow(application=self, title=tr('Infinity OS Updates'))
            # Keep GTK's shadow surface, but no title bar or window controls.
            self.window.set_titlebar(Gtk.Box(visible=False))
            self.window.connect('close-request', self.on_close_request)
            self.window.add_css_class('infinity-updater')
            self.color_settings = Gio.Settings.new('org.gnome.desktop.interface')
            self.color_settings.connect('changed::color-scheme', self._sync_color_scheme)
            self._sync_color_scheme()
            self.window.set_default_size(460, 680)

            layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.window.set_child(layout)

            hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            hero.add_css_class('hero')
            title = Gtk.Label(label=tr('Infinity OS Updates'), xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER)
            title.add_css_class('hero-title')
            hero.append(title)
            subtitle = Gtk.Label(label=tr('System packages · Flatpaks · Device firmware'), xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER)
            subtitle.add_css_class('hero-subtitle')
            hero.append(subtitle)
            layout.append(hero)

            self.content = Gtk.Stack(vexpand=True)
            self.content.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.content.set_transition_duration(260)
            scroll = Gtk.ScrolledWindow(vexpand=True)
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.add_css_class('infinity-results')
            self.items = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.items.set_margin_top(22)
            self.items.set_margin_bottom(22)
            self.items.set_margin_start(24)
            self.items.set_margin_end(24)
            scroll.set_child(self.items)
            self.content.add_named(scroll, 'results')

            checking = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                               halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            self.spinner = Gtk.Spinner()
            self.spinner.set_size_request(44, 44)
            self.spinner.set_halign(Gtk.Align.CENTER)
            checking.append(self.spinner)
            checking_title = Gtk.Label(label=tr('Checking for updates…'))
            checking_title.add_css_class('state-title')
            checking.append(checking_title)
            detail = Gtk.Label(label=tr('Checking package repositories and other sources.'))
            detail.add_css_class('muted')
            detail.set_wrap(True)
            detail.set_max_width_chars(36)
            detail.set_justify(Gtk.Justification.CENTER)
            checking.append(detail)
            self.content.add_named(checking, 'checking')

            offline = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                              halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            icon = Gtk.Image.new_from_icon_name('network-wireless-offline-symbolic')
            icon.set_pixel_size(48)
            icon.add_css_class('state-icon')
            offline.append(icon)
            offline_title = Gtk.Label(label=tr('No internet connection'))
            offline_title.add_css_class('state-title')
            offline.append(offline_title)
            hint = Gtk.Label(label=tr('Connect to the internet and check again.'))
            hint.add_css_class('muted')
            hint.set_wrap(True)
            hint.set_max_width_chars(36)
            hint.set_justify(Gtk.Justification.CENTER)
            offline.append(hint)
            self.content.add_named(offline, 'offline')
            layout.append(self.content)

            footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            footer.add_css_class('footer')
            self.progress = Gtk.ProgressBar()
            self.progress.add_css_class('update-progress')
            self.progress.set_visible(False)
            footer.append(self.progress)
            self.recovery = Gtk.Label(xalign=0.5, justify=Gtk.Justification.CENTER)
            self.recovery.add_css_class('muted')
            self.recovery.set_wrap(True)
            self.recovery.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.recovery.set_max_width_chars(80)
            self.recovery.set_visible(False)
            footer.append(self.recovery)
            self.status = Gtk.Label(xalign=0.5, hexpand=True, justify=Gtk.Justification.CENTER)
            self.status.add_css_class('muted')
            self.status.set_wrap(True)
            self.status.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.status.set_max_width_chars(80)
            footer.append(self.status)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            actions.add_css_class('update-actions')
            self.refresh = Gtk.Button(label=tr('Check again'))
            self.refresh.add_css_class('secondary')
            self.refresh.connect('clicked', self.on_refresh_action)
            actions.append(self.refresh)
            history_button = Gtk.Button(label=tr('History'))
            history_button.add_css_class('secondary')
            history_button.connect('clicked', self.show_history)
            actions.append(history_button)
            actions.append(Gtk.Box(hexpand=True))
            self.apply = Gtk.Button(label=tr('Install updates'))
            self.apply.add_css_class('restart')
            self.apply.connect('clicked', self.on_apply)
            actions.append(self.apply)
            self.release_apply = Gtk.Button(label=tr('Upgrade Infinity OS'))
            self.release_apply.add_css_class('primary')
            self.release_apply.connect('clicked', self.on_release)
            self.release_apply.set_halign(Gtk.Align.END)
            footer.append(self.release_apply)
            footer.append(actions)
            layout.append(footer)
            self.watch_state()
            self.on_refresh(None, force=False)
            self.window.present()

        def watch_state(self):
            try:
                directory = state_path().parent
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                # Watch the directory because saves atomically replace updates.json.
                self.state_monitor = Gio.File.new_for_path(str(directory)).monitor_directory(
                    Gio.FileMonitorFlags.NONE, None)
                self.state_monitor.connect('changed', self.on_state_changed)
            except (OSError, GLib.Error) as error:
                print(f'Could not watch update results: {error}', file=sys.stderr)

        def on_state_changed(self, _monitor, file, other_file, _event):
            if not any(candidate and candidate.get_basename() == 'updates.json'
                       for candidate in (file, other_file)):
                return
            if self.busy:
                return
            state = read_state()
            if state != self.state:
                self.state = state
                self.offline = False
                self.render()

        def do_shutdown(self):
            if self.state_monitor:
                self.state_monitor.cancel()
                self.state_monitor = None
            Gtk.Application.do_shutdown(self)

        def on_close_request(self, window):
            if not self.busy:
                return False
            # The operation's hold keeps the app alive until its completion releases it.
            window.set_visible(False)
            self.remove_window(window)
            return True

        def _sync_color_scheme(self, *_args):
            if self.color_settings.get_string('color-scheme') == 'prefer-dark':
                self.window.remove_css_class('light-mode')
            else:
                self.window.add_css_class('light-mode')

        def render(self):
            offline = offline_status()
            updates = update_rows(self.state.get('updates', []), offline)
            self.restart_ready = restart_ready(updates, offline)
            self.refresh.set_label(tr('Restart and install' if self.restart_ready else 'Check again'))
            self.refresh.remove_css_class('secondary' if self.restart_ready else 'restart')
            self.refresh.add_css_class('restart' if self.restart_ready else 'secondary')
            if self.checking:
                self.content.set_visible_child_name('checking')
                self.apply.set_visible(False)
                self.apply.set_sensitive(False)
                self.release_apply.set_visible(False)
                self.refresh.set_sensitive(False)
                return
            if self.offline:
                self.content.set_visible_child_name('offline')
                self.apply.set_visible(False)
                self.apply.set_sensitive(False)
                self.release_apply.set_visible(False)
                self.refresh.set_sensitive(True)
                self.status.set_text(tr('No internet connection'))
                return
            self.content.set_visible_child_name('results')
            while child := self.items.get_first_child():
                self.items.remove(child)
            errors = self.state.get('errors', [])
            release = self.state.get('release')
            empty_state = not (updates or errors or release or offline.get('pending') or offline.get('status') == 'failed')
            self.items.set_valign(Gtk.Align.CENTER if empty_state else Gtk.Align.FILL)
            if release:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                card.add_css_class('update-card')
                title = Gtk.Label(label=tr('Infinity OS {version} is available').format(
                    version=release['version']), xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER)
                title.add_css_class('update-name')
                card.append(title)
                message = (tr('After restart, system and /var are backed up before updating. /home is preserved.')
                           if release.get('supported') else
                           tr('This release changes the Fedora base and needs a dedicated migration path.'))
                detail = Gtk.Label(label=message, xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER)
                detail.add_css_class('muted')
                card.append(detail)
                self.items.append(card)
            count = Gtk.Label(label=update_count(len(updates)), xalign=0)
            count.add_css_class('pill')
            count_row = Gtk.Box(halign=Gtk.Align.CENTER)
            count_row.append(count)
            self.items.append(count_row)
            if not updates:
                message = (tr('Could not confirm whether updates are available.') if errors
                           else tr('Your system is up to date.'))
                empty = Gtk.Label(label=message, xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER)
                empty.set_margin_top(24)
                self.items.append(empty)
            for item in updates:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                card.add_css_class('update-card')
                name = Gtk.Label(label=item['name'], xalign=0)
                name.add_css_class('update-name')
                name.set_ellipsize(Pango.EllipsizeMode.END)
                title_row = Gtk.Box(spacing=8)
                name.set_hexpand(True)
                title_row.append(name)
                if item.get('pending'):
                    restart = Gtk.Image.new_from_icon_name('system-reboot-symbolic')
                    restart.set_tooltip_text(tr('Downloaded — installs after restart'))
                    title_row.append(restart)
                card.append(title_row)
                detail = Gtk.Label(label=f"{item['kind']}  ·  {item['version']}  ·  {item['source']}", xalign=0)
                detail.add_css_class('muted')
                detail.set_ellipsize(Pango.EllipsizeMode.END)
                card.append(detail)
                self.items.append(card)
            if errors:
                warning = Gtk.Label(label=tr('Some sources could not be checked:\n') +
                                    '\n'.join(errors), xalign=0)
                warning.set_wrap(True)
                warning.add_css_class('muted')
                self.items.append(warning)
            if offline.get('pending'):
                message = ''
            elif offline.get('status') == 'failed':
                message = tr('The last system update failed. Retry the update or restore system and /var from Backups in the boot menu. /home is preserved.')
                if offline.get('snapshot'):
                    message += " #" + str(offline['snapshot'])
                details = Gtk.Expander(label=tr('Error details'))
                text = Gtk.Label(label=offline.get('log', ''), xalign=0, wrap=True, selectable=True)
                details.set_child(text)
                self.items.append(details)
            else:
                message = ''
            if message:
                self.items.append(Gtk.Label(label=message, xalign=0.5, wrap=True, justify=Gtk.Justification.CENTER))
            installable = any(not item.get('pending') for item in updates)
            self.apply.set_visible(installable)
            self.apply.set_sensitive(installable and not self.busy)
            self.release_apply.set_visible(bool(release))
            self.release_apply.set_sensitive(bool(release and release.get('supported')) and not self.busy and not offline.get('pending'))
            self.refresh.set_sensitive(not self.busy)
            if not self.busy:
                checked_at = self.state.get('checked_at')
                if checked_at:
                    checked_at = datetime.fromisoformat(checked_at).astimezone().strftime('%d %b %Y, %H:%M')
                self.status.set_text(tr('Updates downloaded, restart to update.') if offline.get('pending')
                                     else tr('Last checked: ') + (checked_at or tr('never')))

        def on_refresh_action(self, button):
            if self.busy:
                return
            if not self.restart_ready:
                self.on_refresh(button)
                return
            self.state = read_state()
            offline = offline_status()
            if not restart_ready(update_rows(self.state.get('updates', []), offline), offline):
                self.render()
                return
            self.busy = True
            self.hold()
            self.render()

            def work():
                result = run_update_command(tr('Restart and install'),
                                            ['/usr/bin/systemctl', 'reboot'], self.report_progress)
                if result.returncode:
                    message = tr('Could not restart the system.') + '\n' + (result.stderr.strip() or result.stdout.strip())
                    GLib.idle_add(self.finish_error, message)
                else:
                    GLib.idle_add(self.finish_refresh, read_state())

            threading.Thread(target=work, daemon=True).start()

        def on_refresh(self, _button, force=True):
            if self.busy:
                return
            self.busy = True
            self.checking = True
            self.offline = False
            self.hold()
            self.status.set_text(tr('Checking for updates…'))
            self.render()
            self.spinner.start()

            if network_is_offline(self.network_monitor, Gio):
                self.finish_offline()
                return

            def work():
                try:
                    state = refresh_state(self.report_check, force=force)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    GLib.idle_add(self.finish_refresh, state)

            threading.Thread(target=work, daemon=True).start()

        def report_check(self, source):
            print('Checking: ' + source, file=sys.stderr, flush=True)
            GLib.idle_add(self.show_check_source, source)

        def show_check_source(self, source):
            if self.checking:
                self.status.set_text(tr('Checking: {source}').format(source=tr(source)))
            return GLib.SOURCE_REMOVE

        def finish_refresh(self, state, notice=None, recovery=None):
            if self.checking and network_is_offline(self.network_monitor, Gio):
                return self.finish_offline()
            # A background check may have published a newer result while we were busy.
            self.state = read_state()
            self.busy = False
            self.checking = False
            self.offline = False
            self.spinner.stop()
            self.stop_progress()
            self.render()
            if notice:
                self.status.set_text(notice)
            if recovery:
                self.recovery.set_text(recovery)
                self.recovery.set_visible(True)
            self.release()
            return GLib.SOURCE_REMOVE

        def finish_error(self, message):
            if self.checking and network_is_offline(self.network_monitor, Gio):
                return self.finish_offline()
            self.state = read_state()
            self.state['errors'] = [message] + self.state.get('errors', [])
            self.busy = False
            self.checking = False
            self.spinner.stop()
            self.stop_progress()
            self.render()
            self.release()
            return GLib.SOURCE_REMOVE

        def finish_offline(self):
            self.state = read_state()
            self.busy = False
            self.checking = False
            self.offline = True
            self.spinner.stop()
            self.stop_progress()
            self.render()
            self.release()
            return GLib.SOURCE_REMOVE

        def show_history(self, _button):
            dialog = Gtk.Window(title=tr('History'), transient_for=self.window, modal=True,
                                default_width=640, default_height=420)
            scroll = Gtk.ScrolledWindow()
            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                           margin_top=20, margin_bottom=20, margin_start=20, margin_end=20)
            entries = read_history()
            for entry in entries:
                text = entry['time'][:19].replace('T', ' ') + ' UTC · ' + tr(entry['source'])
                text += '\n' + tr(entry['status'])
                if entry.get('detail'):
                    text += '\n' + entry['detail']
                row = Gtk.Label(label=text, xalign=0, wrap=True, selectable=True)
                body.append(row)
            if not entries:
                body.append(Gtk.Label(label=tr('No update history yet.')))
            scroll.set_child(body)
            dialog.set_child(scroll)
            dialog.present()

        def on_apply(self, _button):
            updates = [item for item in update_rows(self.state['updates'], offline_status())
                       if not item.get('pending')]
            commands = install_commands(updates)
            if not commands:
                return
            self.busy = True
            self.hold()
            self.progress.set_fraction(0)
            self.progress.set_visible(True)
            self.recovery.set_visible(False)
            self.progress_known = False
            self.progress_source = GLib.timeout_add(100, self.pulse_progress)
            self.render()

            def work():
                errors = []
                firmware_updated = False
                for label, args in commands:
                    result = run_update_command(label, args, self.report_progress)
                    try:
                        record_operation(label, 'Failed' if result.returncode else
                                         'Downloaded; restart required' if offline_status().get('pending') and
                                         any('infinityos-upgrade-system' in arg for arg in args) else 'Completed',
                                         (result.stderr.strip() or result.stdout.strip()) if result.returncode else '')
                    except OSError as error:
                        errors.append('History: ' + str(error))
                    if result.returncode:
                        errors.append(label + ': ' + (result.stderr.strip() or
                                                      result.stdout.strip() or 'Update failed'))
                    elif label == 'Device firmware':
                        firmware_updated = True
                prepared = offline_status().get('pending', False)
                self.report_progress('Remaining updates', 'Checking', None, None)
                try:
                    state = check_updates()
                    if state.get('rpm_check_ok') and not prepared:
                        pending = pending_rpm_names(updates, state['updates'])
                        if pending:
                            errors.append(tr('RPM updates waiting for compatible dependencies: {packages}').format(
                                packages=', '.join(pending)))
                    state['errors'] = errors + state['errors']
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    notice = (tr('Some updates could not be installed.') if errors else
                              tr('Updates downloaded, restart to update.')
                              if prepared else tr('Firmware updated. Restart may be required.')
                              if firmware_updated else tr('Updates installed.'))
                    GLib.idle_add(self.finish_refresh, state, notice)


            threading.Thread(target=work, daemon=True).start()

        def on_release(self, _button):
            release = self.state.get('release')
            if not release or not release.get('supported') or self.busy:
                return
            version = release['version']
            fedora = release['fedora_release']
            self.busy = True
            self.hold()
            self.progress.set_fraction(0)
            self.progress.set_visible(True)
            self.recovery.set_visible(False)
            self.progress_known = False
            self.progress_source = GLib.timeout_add(100, self.pulse_progress)
            self.render()

            def work():
                try:
                    # The privileged release helper repeats the signed-manifest
                    # and pending-RPM checks before switching repositories.
                    self.report_progress('Current system packages', 'Checking', None, None)
                    state = check_updates()
                    if not state.get('rpm_check_ok') or any(item['kind'] == 'RPM' for item in state['updates']):
                        raise RuntimeError('Current RPM updates are still pending; release upgrade stopped')
                    installed = run_update_command(f'Infinity OS {version}',
                                                   ['pkexec', '/usr/libexec/infinityos-upgrade-release',
                                                    version, str(fedora)], self.report_progress)
                    if installed.returncode:
                        raise RuntimeError(installed.stderr.strip() or installed.stdout.strip() or
                                           'Release upgrade failed')
                    record_operation(f'Infinity OS {version}', 'Downloaded; restart required')
                    state = check_updates()
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    GLib.idle_add(self.finish_refresh, state,
                                  tr('Infinity OS {version} prepared. Restart to back up and install.').format(
                                      version=version))

            threading.Thread(target=work, daemon=True).start()

        def report_progress(self, label, phase, current, total):
            GLib.idle_add(self.show_progress, label, phase, current, total)

        def show_progress(self, label, phase, current, total):
            detail = f'{phase} {current}/{total}' if total else phase
            self.status.set_text(f'{detail} · {label}…')
            self.progress_known = total is not None
            self.progress.set_fraction(current / total if total else 0)
            return GLib.SOURCE_REMOVE

        def pulse_progress(self):
            if not self.progress_known:
                self.progress.pulse()
            return GLib.SOURCE_CONTINUE

        def stop_progress(self):
            if getattr(self, 'progress_source', None):
                GLib.source_remove(self.progress_source)
                self.progress_source = None
            self.progress.set_visible(False)

    return Updater().run(sys.argv)
