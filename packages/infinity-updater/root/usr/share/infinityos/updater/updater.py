import subprocess
import sys
import threading
from datetime import datetime

from checker import check_updates, read_state, save_state


STYLE = b'''
window { background: #111018; color: #f4f0fa; }
.hero { background: #1b1727; border-bottom: 1px solid #3b3152; padding: 28px; }
.hero-title { font-size: 27px; font-weight: 800; color: #ffffff; }
.hero-subtitle { color: #b9adcf; }
.pill { background: #392d58; color: #e4d4ff; border-radius: 999px; padding: 5px 13px; font-weight: 700; }
.update-card { background: #201b2b; border: 1px solid #3a304d; border-radius: 13px; padding: 13px 16px; }
.update-name { font-weight: 700; color: #ffffff; }
.muted { color: #b4a9c7; }
.primary { background: #765caa; color: #ffffff; border-radius: 9px; padding: 9px 18px; font-weight: 700; }
.primary:hover { background: #8e71c6; }
.secondary { background: #322941; color: #f4edff; border-radius: 9px; padding: 9px 16px; }
.footer { background: #17131f; border-top: 1px solid #3b3152; padding: 17px 24px; }
'''


def install_commands(updates):
    kinds = {item['kind'] for item in updates}
    commands = []
    if 'RPM' in kinds:
        commands.append(('System packages', ['pkexec', 'dnf', '-y', 'upgrade', '--refresh']))
    if 'Flatpak system' in kinds:
        commands.append(('System Flatpaks', ['pkexec', 'flatpak', 'update',
                                              '--system', '--noninteractive', '--assumeyes']))
    if 'Flatpak user' in kinds:
        commands.append(('Your Flatpaks', ['flatpak', 'update', '--user',
                                            '--noninteractive', '--assumeyes']))
    return commands


def main():
    if '--check' in sys.argv:
        save_state(check_updates())
        return 0

    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gdk, GLib, Gtk, Pango

    class Updater(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='org.infinityos.Updater')
            self.state = read_state()
            self.busy = False

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
            self.window = Gtk.ApplicationWindow(application=self, title='Infinity OS Updates')
            self.window.set_default_size(700, 620)

            layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.window.set_child(layout)

            hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            hero.add_css_class('hero')
            title = Gtk.Label(label='Infinity OS Updates', xalign=0)
            title.add_css_class('hero-title')
            hero.append(title)
            subtitle = Gtk.Label(label='Infinity OS · Flathub', xalign=0)
            subtitle.add_css_class('hero-subtitle')
            hero.append(subtitle)
            layout.append(hero)

            scroll = Gtk.ScrolledWindow(vexpand=True)
            self.items = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.items.set_margin_top(22)
            self.items.set_margin_bottom(22)
            self.items.set_margin_start(24)
            self.items.set_margin_end(24)
            scroll.set_child(self.items)
            layout.append(scroll)

            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            footer.add_css_class('footer')
            self.status = Gtk.Label(xalign=0, hexpand=True)
            self.status.add_css_class('muted')
            footer.append(self.status)
            self.refresh = Gtk.Button(label='Check again')
            self.refresh.add_css_class('secondary')
            self.refresh.connect('clicked', self.on_refresh)
            footer.append(self.refresh)
            self.apply = Gtk.Button(label='Install updates')
            self.apply.add_css_class('primary')
            self.apply.connect('clicked', self.on_apply)
            footer.append(self.apply)
            layout.append(footer)
            self.render()
            self.window.present()
            self.on_refresh(None)

        def render(self):
            while child := self.items.get_first_child():
                self.items.remove(child)
            updates = self.state.get('updates', [])
            errors = self.state.get('errors', [])
            count = Gtk.Label(label=f'{len(updates)} available updates', xalign=0)
            count.add_css_class('pill')
            count_row = Gtk.Box()
            count_row.append(count)
            self.items.append(count_row)
            if not updates:
                message = ('Could not confirm whether updates are available.' if errors
                           else 'Your system is up to date.')
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
                warning = Gtk.Label(label='Some sources could not be checked:\n' + '\n'.join(errors), xalign=0)
                warning.set_wrap(True)
                warning.add_css_class('muted')
                self.items.append(warning)
            self.apply.set_sensitive(bool(updates) and not self.busy)
            self.refresh.set_sensitive(not self.busy)
            if not self.busy:
                checked_at = self.state.get('checked_at')
                if checked_at:
                    checked_at = datetime.fromisoformat(checked_at).astimezone().strftime('%d %b %Y, %H:%M')
                self.status.set_text('Last checked: ' + (checked_at or 'never'))

        def on_refresh(self, _button):
            self.busy = True
            self.hold()
            self.status.set_text('Checking for updates…')
            self.render()

            def work():
                try:
                    state = check_updates()
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    GLib.idle_add(self.finish_refresh, state)

            threading.Thread(target=work, daemon=True).start()

        def finish_refresh(self, state):
            self.state = state
            self.busy = False
            self.render()
            self.release()
            return GLib.SOURCE_REMOVE

        def finish_error(self, message):
            self.state = read_state()
            self.state['errors'] = [message] + self.state.get('errors', [])
            self.busy = False
            self.render()
            self.release()
            return GLib.SOURCE_REMOVE

        def on_apply(self, _button):
            commands = install_commands(self.state['updates'])
            if not commands:
                return
            self.busy = True
            self.hold()
            self.render()

            def work():
                errors = []
                for label, args in commands:
                    GLib.idle_add(self.status.set_text, 'Updating ' + label + '…')
                    try:
                        result = subprocess.run(args, capture_output=True, text=True, check=False)
                    except OSError as error:
                        errors.append(label + ': ' + str(error))
                        continue
                    if result.returncode:
                        errors.append(label + ': ' + (result.stderr.strip() or 'Update failed'))
                try:
                    state = check_updates()
                    state['errors'] = errors + state['errors']
                    save_state(state)
                except Exception as error:
                    GLib.idle_add(self.finish_error, str(error))
                else:
                    GLib.idle_add(self.finish_refresh, state)

            threading.Thread(target=work, daemon=True).start()

    return Updater().run(sys.argv)
