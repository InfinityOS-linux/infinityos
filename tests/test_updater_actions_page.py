import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires Fedora and Xvfb')
class UpdaterActionsTests(unittest.TestCase):
    def test_actions_move_between_edges_and_center_when_install_visibility_changes(self):
        if not Gtk.init_check():
            self.skipTest('GTK needs a display')
        source = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
        tree = ast.parse(source.read_text())
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        app = SimpleNamespace(on_refresh_action=Mock(), show_history=Mock(), on_apply=Mock())
        namespace = {'Gtk': Gtk, 'self': app, 'tr': lambda text: text}
        exec(compile(ast.Module(body=[methods['layout_actions']], type_ignores=[]), str(source), 'exec'), namespace)
        app.layout_actions = lambda *args: namespace['layout_actions'](app)
        body = methods['do_activate'].body
        start = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign)
                     and ast.unparse(node.targets[0]) == 'self.actions')
        end = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign)
                   and ast.unparse(node.targets[0]) == 'self.release_apply')
        exec(compile(ast.Module(body=body[start:end], type_ignores=[]), str(source), 'exec'), namespace)
        for visible in (True, False, True, False):
            app.apply.set_visible(visible)
            app.actions.allocate(900, 60, -1, None)
            self.assertIs(app.actions.get_start_widget(), app.refresh)
            self.assertIs(app.actions.get_center_widget(), app.history_button if visible else None)
            right = app.apply if visible else app.history_button
            self.assertIs(app.actions.get_end_widget(), right)
            self.assertEqual(app.refresh.get_allocation().x, 0)
            allocation = right.get_allocation()
            self.assertEqual(allocation.x + allocation.width, 900)
            if visible:
                allocation = app.history_button.get_allocation()
                self.assertAlmostEqual(allocation.x + allocation.width / 2, 450, delta=1)
