"""Conditional AI page for InfinityConfig."""
from datetime import datetime
from pathlib import Path
import subprocess
import threading

from gi.repository import GLib, Gtk
from config_ai import (selected_ai, provider_status, provider_command, local_status,
                       select_local, import_model)
from config_ai_i18n import tr

STORAGE = '/usr/libexec/infinity-ai-storage'


def text(value):
    widget = Gtk.Label(label=value, xalign=0, wrap=True, selectable=True)
    return widget


def button(title, callback):
    widget = Gtk.Button(label=tr(title))
    widget.connect('clicked', lambda _button: callback())
    return widget


class AiPage:
    def __init__(self, app, nav, group):
        self.app = app
        self.selection = None
        self.local_model = None
        self.busy = False
        self.generation = 0
        self.tab = Gtk.ToggleButton(hexpand=True)
        tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tab_content.set_halign(Gtk.Align.CENTER)
        tab_content.append(Gtk.Image.new_from_icon_name('utilities-terminal-symbolic'))
        tab_content.append(Gtk.Label(label='AI'))
        self.tab.set_child(tab_content)
        self.tab.add_css_class('infinity-tab')
        self.tab.set_group(group)
        self.tab.connect('toggled', app._select_tab, 'AI')
        self.group = group
        nav.append(self.tab)
        self.page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ('start', 'end', 'top', 'bottom'):
            getattr(self.page, 'set_margin_' + side)(24)
        scroller = Gtk.ScrolledWindow(vexpand=True, min_content_height=280)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.page)
        app.stack.add_named(scroller, 'AI')
        self.poll()
        self.timer = GLib.timeout_add_seconds(2, self.poll)

    def close(self, *_args):
        GLib.source_remove(self.timer)
        self.generation += 1
        return False

    def poll(self):
        try:
            selection = selected_ai()
            local_model = (Path.home() / '.config/infinityos/local-ai-model').read_text() if 'local' in selection else None
        except OSError:
            return True
        self.tab.set_visible(bool(selection))
        if not selection and self.tab.get_active():
            self.group.set_active(True)
        if (selection != self.selection or local_model != self.local_model) and not self.busy:
            self.selection = selection
            self.local_model = local_model
            self.refresh()
        return True

    def job(self, work, done):
        if self.busy:
            return
        self.busy = True
        self.page.set_sensitive(False)
        self.app.status.set_text(tr('Working…'))
        generation = self.generation

        def finish(result, failed):
            self.busy = False
            if generation != self.generation:
                return False
            self.page.set_sensitive(True)
            self.app.status.set_text(tr('Operation failed. Check the provider or local service and try again.') if failed
                                     else tr('Saved. New settings apply to new AI sessions.'))
            if not failed:
                done(result)
            return False

        def worker():
            try:
                result = work()
            except Exception:
                GLib.idle_add(finish, None, True)
            else:
                GLib.idle_add(finish, result, False)
        threading.Thread(target=worker, daemon=True).start()

    def refresh(self, imported=None):
        if self.busy:
            return
        self.generation += 1
        generation = self.generation
        while self.page.get_first_child():
            self.page.remove(self.page.get_first_child())
        self.page.append(text(tr('Accounts and local models')))
        self.page.append(button('Refresh', self.refresh))
        selection = self.selection
        for provider in selection:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class('infinity-row')
            card.append(text(tr('Local model') if provider == 'local' else provider.capitalize()))
            status = text(tr('Loading…'))
            card.append(status)
            self.page.append(card)
            threading.Thread(target=self.load, args=(provider, card, status, generation, imported), daemon=True).start()

    def load(self, provider, card, status, generation, imported):
        try:
            data = local_status() if provider == 'local' else provider_status(provider)
            if provider == 'local':
                try:
                    data['storage'] = subprocess.run([STORAGE, '--show'], check=True, capture_output=True,
                                                     text=True, timeout=10).stdout.strip()
                except (OSError, subprocess.SubprocessError):
                    data['storage'] = tr('Storage unavailable')
        except Exception:
            data = None

        def render():
            if generation != self.generation:
                return False
            if provider == 'local':
                if data is None:
                    status.set_text(tr('Status unavailable. Check the connection and refresh.'))
                else:
                    card.remove(status)
                    self.local_controls(card, data, imported)
            else:
                self.account_controls(card, status, provider, data)
            return False
        GLib.idle_add(render)

    def terminal(self, command):
        try:
            subprocess.Popen(['infinity-terminal', '-e', *command], start_new_session=True)
        except OSError:
            self.app.status.set_text(tr('Operation failed. Check the provider or local service and try again.'))

    def account_controls(self, card, status, provider, data):
        account = data.get('account') if data else None
        lines = [tr('Status unavailable. Check the connection and refresh.') if data is None else
                 tr('Signed in as: {account}').format(account=account.get('email') or account.get('type') or provider)
                 if account else tr('Not signed in')]
        if account and account.get('planType'):
            lines.append(tr('Plan: {plan}').format(plan=account['planType']))
        limits = (data or {}).get('limits', {})
        buckets = limits.get('rateLimitsByLimitId') or {'Codex': limits.get('rateLimits', {})}
        has_usage = False
        for name, bucket in buckets.items():
            for key in ('primary', 'secondary'):
                window = (bucket or {}).get(key)
                if window and isinstance(window.get('usedPercent'), (int, float)):
                    has_usage = True
                    lines.append(tr('{name}: {left}% remaining ({minutes} min window)').format(
                        name=name, left=round(max(0, 100-window['usedPercent']), 1), minutes=window.get('windowDurationMins', '?')))
                    if window.get('resetsAt'):
                        lines.append(tr('Resets: {time}').format(time=datetime.fromtimestamp(window['resetsAt']).strftime('%x %X')))
            credits = (bucket or {}).get('credits') or {}
            if credits.get('unlimited'):
                lines.append(tr('Unlimited credits'))
                has_usage = True
            elif credits.get('balance') is not None:
                lines.append(tr('Credits: {balance}').format(balance=credits['balance']))
                has_usage = True
        tokens = ((data or {}).get('usage', {}).get('summary') or {}).get('lifetimeTokens')
        if tokens is not None:
            lines.append(tr('Total tokens used: {tokens}').format(tokens=tokens))
            has_usage = True
        if not has_usage:
            lines.append(tr('Usage unavailable through the provider CLI.'))
        status.set_text('\n'.join(lines))
        card.append(button('Sign in', lambda: self.terminal(provider_command(provider, 'login'))))
        if account:
            card.append(button('Sign out', lambda: self.logout(provider)))
        url = 'https://chatgpt.com/codex/settings/usage' if provider == 'codex' else 'https://claude.ai/settings/usage'
        card.append(Gtk.LinkButton(uri=url, label=tr('Provider usage')))
        card.append(text(tr('Use /model in the provider terminal to select its model.')))
        card.append(button('Choose model in terminal', lambda: self.terminal([str(Path.home() / f'.local/bin/{provider}')])) )

    def logout(self, provider):
        dialog = Gtk.MessageDialog(transient_for=self.app.window, modal=True,
                                   text=tr('Sign out of {provider}?').format(provider=provider.capitalize()),
                                   secondary_text=tr('Other sessions using this account may also be signed out.'))
        dialog.add_button(tr('Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(tr('Sign out'), Gtk.ResponseType.OK)
        def response(dialog, answer):
            dialog.destroy()
            if answer == Gtk.ResponseType.OK:
                self.job(lambda: subprocess.run(provider_command(provider, 'logout'), check=True,
                                                capture_output=True, timeout=20), lambda _: self.refresh())
        dialog.connect('response', response)
        dialog.present()

    def local_controls(self, card, data, imported):
        names = list(dict.fromkeys([data['model'], *data['models']]))
        dropdown = Gtk.DropDown.new_from_strings(names)
        if imported in names:
            dropdown.set_selected(names.index(imported))
        card.append(text(tr('Model')))
        card.append(dropdown)
        controls = []
        for title, key, low, high, step in (
            ('Context (tokens)', 'context', 512, 262144, 512),
            ('Maximum response (tokens)', 'output', 1, 262144, 256),
            ('Temperature', 'temperature', 0, 2, 0.1),
        ):
            card.append(text(tr(title)))
            spin = Gtk.SpinButton.new_with_range(low, high, step)
            spin.set_value(data[key])
            card.append(spin)
            controls.append(spin)
        def apply():
            context, output = (c.get_value_as_int() for c in controls[:2])
            if output > context:
                self.app.status.set_text(tr('Response length must not exceed context size.'))
                return
            model = names[dropdown.get_selected()]
            temperature = controls[2].get_value()
            self.job(lambda: select_local(model, context, output, temperature), lambda _: self.refresh())
        card.append(button('Apply model settings', apply))
        card.append(button('Import GGUF…', self.choose_model))
        card.append(text(tr('Model storage') + ': ' + data['storage']))
        card.append(text(tr('Copies all models and restarts Ollama. Old files are kept. Administrator authentication is required.')))
        card.append(button('Copy models to another folder…', self.choose_storage))

    def chooser(self, title, action, callback):
        dialog = Gtk.FileChooserNative(title=tr(title), transient_for=self.app.window,
                                       action=action, accept_label=tr('Choose'), cancel_label=tr('Cancel'))
        if action == Gtk.FileChooserAction.OPEN:
            file_filter = Gtk.FileFilter()
            file_filter.set_name('GGUF')
            file_filter.add_pattern('*.gguf')
            dialog.add_filter(file_filter)
        def response(dialog, answer):
            selected = dialog.get_file()
            dialog.destroy()
            if answer == Gtk.ResponseType.ACCEPT and selected and selected.get_path():
                callback(selected.get_path())
        dialog.connect('response', response)
        dialog.show()

    def choose_model(self):
        self.chooser('Choose a GGUF model', Gtk.FileChooserAction.OPEN,
                     lambda path: self.job(lambda: import_model(path), self.refresh))

    def choose_storage(self):
        self.chooser('Choose an empty folder accessible to the Ollama service.', Gtk.FileChooserAction.SELECT_FOLDER,
                     lambda path: self.job(lambda: subprocess.run(['pkexec', STORAGE, path], check=True,
                                                                  capture_output=True, timeout=3700), lambda _: self.refresh()))
