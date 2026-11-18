import ast
import sys
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
    def test_blurred_surface_and_button_states_do_not_paint_shadow_rectangles(self):
        if not Gtk.init_check():
            self.skipTest('GTK needs a display')
        import cairo
        gi.require_foreign('cairo')
        from gi.repository import Gdk
        repo = Path(__file__).resolve().parents[1]
        source = repo / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
        tree = ast.parse(source.read_text())
        style = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STYLE' for t in node.targets))
        display = Gdk.Display.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(style)
        theme = Gtk.CssProvider()
        window = Gtk.Window(decorated=False)
        for name in ('infinity-updater', 'csd', 'shell-backdrop', 'motion-enabled'):
            window.add_css_class(name)
        button = Gtk.Button(label='Install updates')
        window.set_child(button)

        def alpha(widget, x, y):
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 208, 104)
            context = cairo.Context(surface)
            Gtk.render_background(widget.get_style_context(), context, 24, 24, 160, 56)
            Gtk.render_frame(widget.get_style_context(), context, 24, 24, 160, 56)
            surface.flush()
            pixel = bytes(surface.get_data()[y * surface.get_stride() + x * 4:
                                             y * surface.get_stride() + x * 4 + 4])
            return int.from_bytes(pixel, sys.byteorder) >> 24

        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        Gtk.StyleContext.add_provider_for_display(display, theme, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        try:
            for light in (False, True):
                theme.load_from_path(str(repo / 'root/usr/share/themes' /
                                         f'Orchis-Purple-{"Light" if light else "Dark"}-Compact/gtk-4.0/gtk.css'))
                if light:
                    window.add_css_class('light-mode')
                for state in (Gtk.StateFlags.NORMAL, Gtk.StateFlags.PRELIGHT,
                              Gtk.StateFlags.ACTIVE | Gtk.StateFlags.PRELIGHT,
                              Gtk.StateFlags.FOCUSED | Gtk.StateFlags.FOCUS_VISIBLE,
                              Gtk.StateFlags.BACKDROP, Gtk.StateFlags.INSENSITIVE):
                    window.set_state_flags(state, True)
                    self.assertEqual(alpha(window, 100, 20), 0, (light, state, 'above title'))
                    self.assertEqual(alpha(window, 100, 50), 0, (light, state, 'window surface'))
                    for name in ('primary', 'secondary', 'restart'):
                        with self.subTest(light=light, state=state, button=name):
                            button.add_css_class(name)
                            button.set_state_flags(state, True)
                            self.assertEqual(alpha(button, 20, 50), 0, 'shadow left of button')
                            self.assertEqual(alpha(button, 100, 20), 0, 'shadow above button')
                            self.assertEqual(alpha(button, 24, 24), 0, 'square button corner')
                            self.assertGreater(alpha(button, 100, 50), 240, 'button stays opaque')
                            button.remove_css_class(name)
        finally:
            window.destroy()
            Gtk.StyleContext.remove_provider_for_display(display, provider)
            Gtk.StyleContext.remove_provider_for_display(display, theme)

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
        for ready, visible in ((False, True), (True, False), (True, True), (False, False), (False, True)):
            app.restart_ready = ready
            app.apply.set_visible(visible)
            app.layout_actions()
            app.actions.allocate(900, 60, -1, None)
            left = (app.apply if visible else app.history_button) if ready else app.refresh
            right = app.refresh if ready else app.apply if visible else app.history_button
            self.assertIs(app.actions.get_start_widget(), left)
            self.assertIs(app.actions.get_center_widget(), app.history_button if visible else None)
            self.assertIs(app.actions.get_end_widget(), right)
            self.assertEqual(left.get_allocation().x, 0)
            allocation = right.get_allocation()
            self.assertEqual(allocation.x + allocation.width, 900)
            if visible:
                allocation = app.history_button.get_allocation()
                self.assertAlmostEqual(allocation.x + allocation.width / 2, 450, delta=1)

    def test_updater_stylesheet_parses_in_gtk(self):
        source = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
        tree = ast.parse(source.read_text())
        style = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STYLE' for t in node.targets))
        errors = []
        provider = Gtk.CssProvider()
        provider.connect('parsing-error', lambda _provider, _section, error: errors.append(str(error)))
        provider.load_from_data(style)
        self.assertEqual(errors, [])

    def test_action_labels_keep_readable_theme_colors(self):
        if not Gtk.init_check():
            self.skipTest('GTK needs a display')
        from gi.repository import Gdk
        source = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
        tree = ast.parse(source.read_text())
        style = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STYLE' for t in node.targets))
        provider = Gtk.CssProvider()
        provider.load_from_data(style)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        user_theme = Gtk.CssProvider()
        user_theme.load_from_data(b'button { background: #181624; color: #151025; } button label { color: #151025; }')
        Gtk.StyleContext.add_provider_for_display(display, user_theme, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        window = Gtk.Window()
        window.add_css_class('infinity-updater')
        button = Gtk.Button(label='Install updates')
        window.set_child(button)
        try:
            for light in (False, True):
                if light:
                    window.add_css_class('light-mode')
                for name in ('primary', 'restart'):
                    button.add_css_class(name)
                    for sensitive in (True, False):
                        button.set_sensitive(sensitive)
                        color = button.get_child().get_style_context().get_color()
                        brightness = (color.red + color.green + color.blue) / 3
                        if light:
                            self.assertLess(brightness, 0.5)
                        else:
                            self.assertGreater(brightness, 0.7)
                    button.remove_css_class(name)
        finally:
            window.destroy()
            Gtk.StyleContext.remove_provider_for_display(display, provider)
            Gtk.StyleContext.remove_provider_for_display(display, user_theme)
