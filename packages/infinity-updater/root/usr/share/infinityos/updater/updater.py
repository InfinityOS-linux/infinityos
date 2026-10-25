import sys
import threading
from datetime import datetime

from checker import check_updates, read_state, save_state
from i18n import tr, update_count
from progress import run_update_command


STYLE = b'''
window.infinity-updater { background: #111018; color: #f4f0fa; }
.infinity-results, .infinity-results viewport { background: #111018; }
.hero { background: #1b1727; border-bottom: 1px solid #3b3152; padding: 28px; }
.hero-title { font-size: 27px; font-weight: 800; color: #ffffff; }
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
window.infinity-updater.light-mode .state-icon { color: #604583; }
'''


def network_is_offline(monitor, gio):
    """Only call a connection offline when GIO has a definite answer."""
    return (not monitor.get_network_available() or
            monitor.get_connectivity() in (gio.NetworkConnectivity.LOCAL,
                                           gio.NetworkConnectivity.LIMITED,
                                           gio.NetworkConnectivity.PORTAL))


def install_commands(updates):
    kinds = {item['kind'] for item in updates}
    commands = []
    if 'RPM' in kinds:
        commands.append(('System packages', ['pkexec', '/usr/libexec/infinityos-upgrade-system']))
    if 'Flatpak system' in kinds:
        commands.append(('System Flatpaks', ['pkexec', 'flatpak', 'update',
                                              '--system', '--noninteractive', '--assumeyes']))
    if 'Flatpak user' in kinds:
        commands.append(('Your Flatpaks', ['flatpak', 'update', '--user',
                                            '--noninteractive', '--assumeyes']))
    if 'Firmware' in kinds:
        commands.append(('Device firmware', ['pkexec', 'fwupdmgr', 'update',
                                             '--assume-yes', '--no-reboot-check']))
    return commands


def main():
    if '--check' in sys.argv:
        save_state(check_updates())
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

        def do_activate(self):
            if getattr(self, 'window', None):
                self.window.present()
                if not self.busy:
                    self.on_refresh(None)
                return
            css = Gtk.CssProvider()
            css.load_from_data(STYLE)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.window = Gtk.ApplicationWindow(application=self, title=tr('Infinity OS Updates'))
            self.window.add_css_class('infinity-updater')
            self.color_settings = Gio.Settings.new('org.gnome.desktop.interface')
            self.color_settings.connect('changed::color-scheme', self._sync_color_scheme)
            self._sync_color_scheme()
            self.window.set_default_size(700, 620)

            layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.window.set_child(layout)

            hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            hero.add_css_class('hero')
            title = Gtk.Label(label=tr('Infinity OS Updates'), xalign=0)
            title.add_css_class('hero-title')
            hero.append(title)
            subtitle = Gtk.Label(label=tr('System packages · Flatpaks · Device firmware'), xalign=0)
            subtitle.add_css_class('hero-subtitle')
            hero.append(subtitle)
            layout.append(hero)

            self.content = Gtk.Stack(vexpand=True)
            self.content.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.content.set_transition_duration(260)
            scroll = Gtk.ScrolledWindow(vexpand=True)
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
            checking.append(self.spinner)
            checking_title = Gtk.Label(label=tr('Checking for updates…'))
            checking_title.add_css_class('state-title')
            checking.append(checking_title)
            detail = Gtk.Label(label=tr('Checking package repositories and other sources.'))
            detail.add_css_class('muted')
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
            offline.append(hint)
            self.content.add_named(offline, 'offline')
            layout.append(self.content)

            footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            footer.add_css_class('footer')
            self.progress = Gtk.ProgressBar()
            self.progress.add_css_class('update-progress')
            self.progress.set_visible(False)
            footer.append(self.progress)
            self.recovery = Gtk.Label(xalign=0)
            self.recovery.add_css_class('muted')
            self.recovery.set_wrap(True)
            self.recovery.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.recovery.set_max_width_chars(80)
            self.recovery.set_visible(False)
            footer.append(self.recovery)
            self.status = Gtk.Label(xalign=0, hexpand=True)
            self.status.add_css_class('muted')
            self.status.set_wrap(True)
            self.status.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.status.set_max_width_chars(80)
            footer.append(self.status)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                              halign=Gtk.Align.END)
            self.refresh = Gtk.Button(label=tr('Check again'))
            self.refresh.add_css_class('secondary')
            self.refresh.connect('clicked', self.on_refresh)
            actions.append(self.refresh)
            self.apply = Gtk.Button(label=tr('Install updates'))
            self.apply.add_css_class('primary')
            self.apply.connect('clicked', self.on_apply)
            actions.append(self.apply)
            self.release_apply = Gtk.Button(label=tr('Upgrade Infinity OS'))
            self.release_apply.add_css_class('primary')
            self.release_apply.connect('clicked', self.on_release)
            actions.append(self.release_apply)
            footer.append(actions)
            layout.append(footer)
            self.on_refresh(None)
            self.window.present()

        def _sync_color_scheme(self, *_args):
            if self.color_settings.get_string('color-scheme') == 'prefer-dark':
                self.window.remove_css_class('light-mode')
            else:
                self.window.add_css_class('light-mode')

        def render(self):
            if self.checking:
                self.content.set_visible_child_name('checking')
                self.apply.set_sensitive(False)
                self.release_apply.set_visible(False)
                self.refresh.set_sensitive(False)
                return
            if self.offline:
                self.content.set_visible_child_name('offline')
                self.apply.set_sensitive(False)
                self.release_apply.set_visible(False)
                self.refresh.set_sensitive(True)
                self.status.set_text(tr('No internet connection'))
                return
            self.content.set_visible_child_name('results')
            while child := self.items.get_first_child():
                self.items.remove(child)
            updates = self.state.get('updates', [])
            errors = self.state.get('errors', [])
            release = self.state.get('release')
            if release:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                card.add_css_class('update-card')
                title = Gtk.Label(label=tr('Infinity OS {version} is available').format(
                    version=release['version']), xalign=0)
                title.add_css_class('update-name')
                card.append(title)
                message = (tr('First install current system packages, then download and install the new release. '
                              'A Btrfs recovery snapshot is created before each system transaction.')
                           if release.get('supported') else
                           tr('This release changes the Fedora base and needs a dedicated migration path.'))
                detail = Gtk.Label(label=message, xalign=0, wrap=True)
                detail.add_css_class('muted')
                card.append(detail)
                self.items.append(card)
            count = Gtk.Label(label=update_count(len(updates)), xalign=0)
            count.add_css_class('pill')
            count_row = Gtk.Box()
            count_row.append(count)
            self.items.append(count_row)
            if not updates:
                message = (tr('Could not confirm whether updates are available.') if errors
                           else tr('Your system is up to date.'))
                empty = Gtk.Label(label=message, xalign=0)
                empty.set_margin_top(24)
                self.items.append(empty)
            for item in updates:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                card.add_css_class('update-card')
                name = Gtk.Label(label=item['name'], xalign=0)
                name.add_css_class('update-name')
                card.append(name)
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
            self.apply.set_sensitive(bool(updates) and not self.busy)
            self.release_apply.set_visible(bool(release))
            self.release_apply.set_sensitive(bool(release and release.get('supported')) and not self.busy)
            self.refresh.set_sensitive(not self.busy)
            if not self.busy:
                checked_at = self.state.get('checked_at')
                if checked_at:
                    checked_at = datetime.fromisoformat(checked_at).astimezone().strftime('%d %b %Y, %H:%M')
                self.status.set_text(tr('Last checked: ') + (checked_at or tr('never')))

        def on_refresh(self, _button):
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
                    state = check_updates()
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    GLib.idle_add(self.finish_refresh, state)

            threading.Thread(target=work, daemon=True).start()

        def finish_refresh(self, state, notice=None, recovery=None):
            if self.checking and network_is_offline(self.network_monitor, Gio):
                return self.finish_offline()
            if self.checking:
                try:
                    save_state(state)
                except OSError as error:
                    state['errors'].append(str(error))
            self.state = state
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
            self.busy = False
            self.checking = False
            self.offline = True
            self.spinner.stop()
            self.stop_progress()
            self.render()
            self.release()
            return GLib.SOURCE_REMOVE

        def on_apply(self, _button):
            commands = install_commands(self.state['updates'])
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
                completed_system_updates = False
                snapshot = None

                def report(label, phase, current, total):
                    nonlocal snapshot
                    if label == 'System packages' and phase.startswith('Root snapshot #'):
                        snapshot = phase.partition('#')[2].partition(' ')[0]
                    self.report_progress(label, phase, current, total)

                for label, args in commands:
                    result = run_update_command(label, args, report)
                    if result.returncode:
                        errors.append(label + ': ' + (result.stderr.strip() or
                                                      result.stdout.strip() or 'Update failed'))
                    elif label in ('System packages', 'Device firmware'):
                        completed_system_updates = True
                self.report_progress('Remaining updates', 'Checking', None, None)
                try:
                    state = check_updates()
                    state['errors'] = errors + state['errors']
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    notice = (tr('Some updates could not be installed.') if errors else
                              tr('System updates installed. Restart may be required.')
                              if completed_system_updates else tr('Updates installed.'))
                    recovery = (f'Root snapshot #{snapshot} is available in Backups (Btrfs) in rEFInd. '
                                '/home, /var and device firmware are not part of this snapshot.'
                                if snapshot else None)
                    GLib.idle_add(self.finish_refresh, state, notice, recovery)

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
                snapshot = None

                def report(label, phase, current, total):
                    nonlocal snapshot
                    if phase.startswith('Root snapshot #'):
                        snapshot = phase.partition('#')[2].partition(' ')[0]
                    self.report_progress(label, phase, current, total)

                try:
                    # The privileged release helper repeats the signed-manifest
                    # and pending-RPM checks before switching repositories.
                    current = run_update_command('Current system packages',
                                                 ['pkexec', '/usr/libexec/infinityos-upgrade-system'], report)
                    if current.returncode:
                        raise RuntimeError(current.stderr.strip() or current.stdout.strip() or
                                           'Current package update failed')
                    self.report_progress('Current system packages', 'Checking', None, None)
                    state = check_updates()
                    if not state.get('rpm_check_ok') or any(item['kind'] == 'RPM' for item in state['updates']):
                        raise RuntimeError('Current RPM updates are still pending; release upgrade stopped')
                    installed = run_update_command(f'Infinity OS {version}',
                                                   ['pkexec', '/usr/libexec/infinityos-upgrade-release',
                                                    version, str(fedora)], report)
                    if installed.returncode:
                        raise RuntimeError(installed.stderr.strip() or installed.stdout.strip() or
                                           'Release upgrade failed')
                    state = check_updates()
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    recovery = (f'Root snapshot #{snapshot} is available in Backups (Btrfs) in rEFInd. '
                                '/home, /var and device firmware are not part of this snapshot.'
                                if snapshot else None)
                    GLib.idle_add(self.finish_refresh, state,
                                  tr('Infinity OS {version} installed. Restart to use the new release.').format(
                                      version=version), recovery)

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
