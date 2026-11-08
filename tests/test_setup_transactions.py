"""Exercise Setup transaction callbacks without installing apps or requiring GTK."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos/launcher.py'


def controller():
    tree = ast.parse(SOURCE.read_text())
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InfinitySetup')
    methods = [n for n in original.body if isinstance(n, ast.FunctionDef) and n.name in ('_install', '_finished', '_refresh_ai')]
    module = ast.Module(body=[ast.ClassDef(name='Callbacks', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    context = {'GLib': SimpleNamespace(idle_add=lambda fn, *args: fn(*args), source_remove=Mock()),
               'tr': lambda value: value, 'install': Mock(), 'uninstall': Mock(),
               'deactivate_local_model': Mock(), 'set_tv_enabled': Mock(),
               'available': lambda app: True, 'installed': Mock(return_value=True),
               'removable': Mock(return_value=False)}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), 'exec'), context)
    app = context['Callbacks']()
    app.status = SimpleNamespace(set_text=Mock())
    app._installed = Mock()
    app._tv_applied = Mock()
    return app, context


class SetupTransactionsTests(unittest.TestCase):
    def test_external_ai_selection_refreshes_only_ai_rows(self):
        app, context = controller()
        ai = ('old',)
        context['selected_ai'] = lambda: ('local',)
        context['active_local_model'] = lambda: 'custom'
        context['downloaded_local_models'] = lambda: ('custom',)
        context['SECTIONS'] = [('AI', 'icon', 'description')]
        app.window = SimpleNamespace(is_active=lambda: True)
        app.busy = app.closing = False
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
