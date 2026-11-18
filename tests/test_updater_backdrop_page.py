import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'


class UpdaterBackdropTests(unittest.TestCase):
    def sync(self, state=None, owner=True, fail=False):
        tree = ast.parse(SOURCE.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == '_sync_shell_backdrop')
        class BusError(Exception):
            pass
        proxy = Mock()
        proxy.get_name_owner.return_value = ':1.1' if owner else None
        proxy.call_sync.return_value.unpack.return_value = ({'state': state},)
        if fail:
            proxy.call_sync.side_effect = BusError('Shell unavailable')
        app = SimpleNamespace(_shell_proxy=proxy, window=Mock())
        namespace = {'Gio': SimpleNamespace(DBusCallFlags=SimpleNamespace(NONE=0)),
                     'GLib': SimpleNamespace(Variant=lambda *_: None, Error=BusError)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        namespace['_sync_shell_backdrop'](app)
        return app.window

    def test_only_an_active_extension_makes_gtk_transparent(self):
        window = self.sync(1)
        window.add_css_class.assert_called_once_with('shell-backdrop')
        for state in (None, 2, 3, 4, 5, 6, 99):
            with self.subTest(state=state):
                self.sync(state).remove_css_class.assert_called_once_with('shell-backdrop')
        variant = SimpleNamespace(unpack=lambda: 1)
        self.sync(variant).add_css_class.assert_called_once_with('shell-backdrop')

    def test_shell_loss_and_bus_errors_restore_the_opaque_fallback(self):
        self.sync(1, owner=False).remove_css_class.assert_called_once_with('shell-backdrop')
        self.sync(1, fail=True).remove_css_class.assert_called_once_with('shell-backdrop')
