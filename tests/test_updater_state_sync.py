import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
method = next(node for node in ast.walk(ast.parse(SOURCE.read_text()))
              if isinstance(node, ast.FunctionDef) and node.name == 'on_state_changed')


class UpdaterStateSyncTests(unittest.TestCase):
    def sync(self, app, state, filename="updates.json"):
        read = Mock(return_value=state)
        namespace = {'read_state': read}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        namespace['on_state_changed'](app, None, SimpleNamespace(get_basename=lambda: filename), None, None)
        return read

    def test_background_results_replace_open_drawer_state_in_both_directions(self):
        app = SimpleNamespace(busy=False, state={'updates': []}, offline=True, render=Mock())
        found = {'updates': [{'name': 'infinity-updater'}]}
        self.sync(app, found)
        self.assertEqual(app.state, found)
        self.assertFalse(app.offline)
        self.sync(app, {'updates': []})
        self.assertEqual(app.state, {'updates': []})
        self.assertEqual(app.render.call_count, 2)

    def test_background_result_does_not_interrupt_active_operation(self):
        app = SimpleNamespace(busy=True, state={'updates': []}, render=Mock())
        read = self.sync(app, {'updates': [{'name': 'infinity-updater'}]})
        read.assert_not_called()
        app.render.assert_not_called()

    def test_duplicate_directory_events_do_not_redraw(self):
        state = {'updates': [{'name': 'infinity-updater'}]}
        app = SimpleNamespace(busy=False, state=state, offline=False, render=Mock())
        self.sync(app, dict(state))
        app.render.assert_not_called()

    def test_operation_completion_uses_latest_published_result(self):
        completion = next(node for node in ast.walk(ast.parse(SOURCE.read_text()))
                          if isinstance(node, ast.FunctionDef) and node.name == 'finish_refresh')
        published = {'updates': [{'name': 'new-background-result'}], 'errors': []}
        namespace = {'read_state': Mock(return_value=published), 'save_state': Mock(),
                     'GLib': SimpleNamespace(SOURCE_REMOVE=False)}
        exec(compile(ast.Module(body=[completion], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        app = SimpleNamespace(checking=False, busy=True, spinner=Mock(), stop_progress=Mock(),
                              render=Mock(), release=Mock())
        namespace['finish_refresh'](app, {'updates': []})
        self.assertEqual(app.state, published)
        self.assertFalse(app.busy)
        app.render.assert_called_once()
        app.release.assert_called_once()


    def test_unrelated_cache_changes_preserve_local_error_details(self):
        app = SimpleNamespace(busy=False, state={'updates': [], 'errors': ['local error']}, render=Mock())
        read = self.sync(app, {'updates': []}, filename='launcher.json')
        read.assert_not_called()
        app.render.assert_not_called()
