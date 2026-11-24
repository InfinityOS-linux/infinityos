import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

source = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
methods = [node for node in ast.walk(ast.parse(source.read_text()))
           if isinstance(node, ast.FunctionDef) and node.name in {'on_close_request', 'do_activate', 'on_refresh'}]
namespace = {}
exec(compile(ast.Module(body=methods, type_ignores=[]), str(source), 'exec'), namespace)


class UpdaterCloseTests(unittest.TestCase):
    def test_idle_close_uses_normal_application_shutdown(self):
        app = SimpleNamespace(busy=False, remove_window=Mock())
        window = Mock()
        self.assertFalse(namespace['on_close_request'](app, window))
        app.remove_window.assert_not_called()

    def test_busy_close_hides_window_without_interrupting_operation(self):
        app = SimpleNamespace(busy=True, remove_window=Mock(), quit=Mock(), release=Mock())
        window = Mock()
        self.assertTrue(namespace['on_close_request'](app, window))
        window.set_visible.assert_called_once_with(False)
        app.remove_window.assert_called_once_with(window)
        app.quit.assert_not_called()
        app.release.assert_not_called()

    def test_reopening_background_operation_reattaches_window_without_new_check(self):
        app = SimpleNamespace(busy=True, window=Mock(), add_window=Mock(), on_refresh=Mock())
        namespace['do_activate'](app)
        app.add_window.assert_called_once_with(app.window)
        app.window.present.assert_called_once()
        app.on_refresh.assert_not_called()


    def test_repeated_activation_with_staged_updates_keeps_restart_available(self):
        staged = {'pending': True}
        namespace.update(offline_status=lambda: staged, restart_ready=lambda state: state['pending'],
                         read_state=lambda: {'updates': []})
        app = SimpleNamespace(busy=False, checking=False, offline=True, render=Mock(), hold=Mock(),
                              window=Mock(), add_window=Mock())
        app.on_refresh = lambda *args, **kwargs: namespace['on_refresh'](app, *args, **kwargs)
        for _ in range(3):
            namespace['do_activate'](app)
        self.assertFalse(app.checking)
        self.assertFalse(app.busy)
        self.assertFalse(app.offline)
        self.assertEqual(app.render.call_count, 3)
        app.hold.assert_not_called()
