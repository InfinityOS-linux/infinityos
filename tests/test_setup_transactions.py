"""Exercise Setup transaction callbacks without installing apps or requiring GTK."""
from contextlib import nullcontext
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos/launcher.py'


def controller():
    tree = ast.parse(SOURCE.read_text())
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InfinitySetup')
    methods = [n for n in original.body if isinstance(n, ast.FunctionDef) and n.name in ('_install', '_install_work', '_installed', '_finished', '_refresh_ai', '_apply_ai_refresh', '_complete')]
    module = ast.Module(body=[ast.ClassDef(name='Callbacks', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    context = {'progress_reporting': lambda callback: nullcontext(), 'privileged_transaction': nullcontext, 'threading': SimpleNamespace(Thread=lambda target, daemon: SimpleNamespace(start=target)), 'GLib': SimpleNamespace(idle_add=lambda fn, *args: fn(*args), source_remove=Mock()),
               'tr': lambda value: value, 'install': Mock(), 'uninstall': Mock(),
               'deactivate_local_model': Mock(), 'set_tv_enabled': Mock(),
               'configured_apps': lambda **kwargs: (),
               'available': lambda app: True, 'installed': Mock(return_value=True),
               'removable': Mock(return_value=False)}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), 'exec'), context)
    app = context['Callbacks']()
    app.status = SimpleNamespace(set_text=Mock())
    app._installed = Mock()
    app._tv_applied = Mock()
    return app, context


class SetupTransactionsTests(unittest.TestCase):
    def test_deactivation_preserves_downloaded_model_in_installed_filter(self):
        from collections import namedtuple
        app, _context = controller()
        item = namedtuple('Model', 'kind')('local-model')
        app.notes = {item: Mock()}
        app.initial_active = {item: True}
        app.catalog_status = {item: True}
        type(app)._installed(app, item, False)
        self.assertTrue(app.catalog_status[item])
        self.assertFalse(app.initial_active[item])
        app.notes[item].set_text.assert_called_once_with('Downloaded; inactive')

    def test_stop_finishes_current_operation_and_leaves_next_pending(self):
        app, context = controller()
        first = SimpleNamespace(kind='flatpak', source='first', name='First')
        second = SimpleNamespace(kind='flatpak', source='second', name='Second')
        app._finished = Mock()
        def stop_after_install(item):
            app.stop_requested = True
        context['install'].side_effect = stop_after_install
        app._install([(first, True), (second, True)], [])
        context['install'].assert_called_once_with(first)
        app._installed.assert_called_once_with(first, True)
        self.assertIn('Queue stopped', app._finished.call_args.args[0][0])

    def test_steam_tv_enable_does_not_start_steam_behind_the_desktop(self):
        for enabled, failure in ((True, False), (True, True), (False, False)):
            with self.subTest(enabled=enabled, failure=failure):
                app, context = controller()
                app._finished = Mock()
                if failure:
                    context['set_tv_enabled'].side_effect = RuntimeError('failed')
                app._install([], [('steam', enabled)])
                self.assertEqual(app._finished.call_args.args[1], enabled and not failure)

    def test_successful_steam_tv_install_asks_for_desktop_first_launch(self):
        app, context = controller()
        app._finished = Mock()
        app._install([], [('steam', True)])
        app._tv_applied.assert_called_once_with('steam', True)
        app._complete(app._finished.call_args.args[1])
        self.assertIn('Open Steam from the desktop', app.status.set_text.call_args.args[0])

    def test_steam_then_tv_mode_does_not_reinstall_steam(self):
        app, context = controller()
        app._finished = Mock()
        app._install([], [('steam', True)])
        context['install'].assert_not_called()
        context['set_tv_enabled'].assert_called_once_with('steam', True)

    def test_steam_and_tv_mode_in_one_apply_install_client_first(self):
        app, context = controller()
        app._finished = Mock()
        steam = SimpleNamespace(kind='dnf', source='com.valvesoftware.Steam', name='Steam')
        events = []
        context['install'].side_effect = lambda *_args, **_kwargs: events.append('steam')
        context['set_tv_enabled'].side_effect = lambda *_args: events.append('tv')
        app._install([(steam, True)], [('steam', True)])
        self.assertEqual(events, ['steam', 'tv'])
        context['install'].assert_called_once_with(steam, defer_system_dependencies=True)

    def test_disabling_tv_mode_precedes_steam_removal(self):
        app, context = controller()
        app._finished = Mock()
        steam = SimpleNamespace(kind='dnf', source='com.valvesoftware.Steam', name='Steam')
        events = []
        context['set_tv_enabled'].side_effect = lambda *_args: events.append('tv')
        context['uninstall'].side_effect = lambda *_args: events.append('steam')
        app._install([(steam, False)], [('steam', False)])
        self.assertEqual(events, ['tv', 'steam'])

    def test_failed_tv_disable_keeps_steam_installed(self):
        app, context = controller()
        app._finished = Mock()
        steam = SimpleNamespace(kind='dnf', source='com.valvesoftware.Steam', name='Steam')
        context['set_tv_enabled'].side_effect = RuntimeError('TV disable failed')
        app._install([(steam, False)], [('steam', False)])
        context['uninstall'].assert_not_called()
        self.assertIn('Steam was left installed', app._finished.call_args.args[0][1])

    def test_completion_reports_success_without_closing(self):
        app, _context = controller()
        app._begin_close = Mock()
        app._complete()
        app.status.set_text.assert_called_once_with('Installation complete.')
        app._begin_close.assert_not_called()

    def test_external_ai_selection_refreshes_only_ai_rows(self):
        app, context = controller()
        ai = ('old',)
        context['selected_ai'] = lambda: ('local',)
        context['active_local_model'] = lambda: 'custom'
        context['downloaded_local_models'] = lambda: ('custom',)
        context['SECTIONS'] = [('AI', 'icon', 'description')]
        app.window = SimpleNamespace(is_active=lambda: True)
        app.busy = app.closing = False
        app.catalog_status = {}
        app.ai_models = ()
        app.ai_selection = (ai, 'old', ())
        from collections import namedtuple
        Item = namedtuple('Item', 'category')
        old, other = Item('AI'), Item('System')
        app.switches = {old: object(), other: object()}
        app.initial_active = {old: True, other: False}
        app.notes = {old: object(), other: object()}
        app.stack = SimpleNamespace(get_visible_child_name=lambda: 'ai',
                                    get_child_by_name=lambda _: 'old-page',
                                    remove=Mock(), add_named=Mock(), set_visible_child_name=Mock())
        app._page = Mock(return_value='new-page')
        app._refresh_ai()
        self.assertNotIn(old, app.switches)
        self.assertIn(other, app.switches)
        self.assertEqual(app.ai_selection, (('local',), 'custom', ('custom',)))
        app.stack.add_named.assert_called_once_with('new-page', 'ai')
        app._refresh_ai()
        app._page.assert_called_once()

    def test_failed_replacement_keeps_previous_local_ai_active(self):
        app, context = controller()
        old = SimpleNamespace(name='Old model', source='old', kind='local-model')
        new = SimpleNamespace(name='New model', source='new', kind='local-model')
        context['install'].side_effect = RuntimeError('download failed')
        app._finished = Mock()
        app._install([(old, False), (new, True)], [])
        context['deactivate_local_model'].assert_not_called()
        app._installed.assert_not_called()
        self.assertIn('download failed', app._finished.call_args.args[0][0])

    def test_successful_replacement_updates_old_and_new_selection(self):
        app, context = controller()
        old = SimpleNamespace(name='Old model', source='old', kind='local-model')
        new = SimpleNamespace(name='New model', source='new', kind='local-model')
        app._finished = Mock()
        app._install([(old, False), (new, True)], [])
        context['deactivate_local_model'].assert_not_called()
        app._installed.assert_any_call(old, False)
        app._installed.assert_any_call(new, True)

    def test_explicit_local_ai_removal_still_deactivates(self):
        app, context = controller()
        app._finished = Mock()
        app._install([(SimpleNamespace(name='Model', source='old', kind='local-model'), False)], [])
        context['deactivate_local_model'].assert_called_once()

    def test_failed_partial_install_remains_retryable(self):
        app, context = controller()
        item = type('App', (), {'kind': 'driver'})()
        switch = SimpleNamespace(set_sensitive=Mock())
        app.switches = {item: switch}
        app.initial_active = {item: False}
        app.progress_source = 0
        app.progress = SimpleNamespace(set_visible=Mock())
        app.suite_switch = SimpleNamespace(set_sensitive=Mock())
        app.save_button = SimpleNamespace(set_sensitive=Mock(), set_label=Mock())
        app.tv_switches = {}
        app.installer_buttons = []
        app._finished(['last installation step failed'])
        switch.set_sensitive.assert_called_once_with(True)
        context['installed'].assert_not_called()
        app.save_button.set_label.assert_called_once_with('Retry pending changes')
