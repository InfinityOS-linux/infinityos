import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'


class UpdaterBackdropTests(unittest.TestCase):
    def sync(self, ready=None, owner=True, fail=False):
        tree = ast.parse(SOURCE.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == '_sync_shell_backdrop')
        class BusError(Exception):
            pass
        proxy = Mock()
        proxy.get_name_owner.return_value = ':1.1' if owner else None
        proxy.get_cached_property.return_value = None if ready is None else SimpleNamespace(unpack=lambda: ready)
        if fail:
            proxy.get_cached_property.side_effect = BusError('Shell unavailable')
        app = SimpleNamespace(_shell_proxy=proxy, window=Mock())
        namespace = {'Gio': SimpleNamespace(DBusCallFlags=SimpleNamespace(NONE=0)),
                     'GLib': SimpleNamespace(Variant=lambda *_: None, Error=BusError)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        namespace['_sync_shell_backdrop'](app)
        return app.window

    def test_only_a_ready_backdrop_makes_gtk_transparent(self):
        window = self.sync(True)
        window.add_css_class.assert_called_once_with('shell-backdrop')
        for ready in (None, False, 1, 'true'):
            with self.subTest(ready=ready):
                self.sync(ready).remove_css_class.assert_called_once_with('shell-backdrop')

    def test_shell_loss_and_bus_errors_restore_the_opaque_fallback(self):
        self.sync(True, owner=False).remove_css_class.assert_called_once_with('shell-backdrop')
        self.sync(True, fail=True).remove_css_class.assert_called_once_with('shell-backdrop')

    def test_a_late_property_change_recovers_from_an_initial_missing_backdrop(self):
        # The same callback is used for the initial proxy load and every
        # PropertiesChanged notification, without a blocking Shell RPC.
        self.sync(None).remove_css_class.assert_called_once_with('shell-backdrop')
        self.sync(True).add_css_class.assert_called_once_with('shell-backdrop')
        self.sync(False).remove_css_class.assert_called_once_with('shell-backdrop')
