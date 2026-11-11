"""Exercise the actual tick callback without a display server."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos/launcher.py'


def controller(animations=True):
    tree = ast.parse(SOURCE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InfinitySetup')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_animate')
    context = {'Gtk': SimpleNamespace(Settings=SimpleNamespace(get_default=lambda: SimpleNamespace(get_property=lambda _: animations)))}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), context)
    def widget():
        w = SimpleNamespace(opacity=0)
        w.set_opacity = lambda v: setattr(w, 'opacity', v)
        w.get_opacity = lambda: w.opacity
        return w
    app = SimpleNamespace(animation_tick=0, shade=widget(), card=widget(), _finish_close=Mock(),
                          window=SimpleNamespace(add_tick_callback=Mock(return_value=7), remove_tick_callback=Mock()))
    return app, lambda opening: context['_animate'](app, opening)


class AnimationTests(unittest.TestCase):
    def test_backdrop_precedes_card_and_starts_at_first_frame(self):
        app, animate = controller()
        animate(True)
        frame = app.window.add_tick_callback.call_args.args[0]
        def tick(time):
            return frame(None, SimpleNamespace(get_frame_time=lambda: time))
        self.assertTrue(tick(10_000_000))
        self.assertEqual((app.shade.opacity, app.card.opacity), (0, 0))
        tick(10_125_000)
        self.assertGreater(app.shade.opacity, 0)
        self.assertEqual(app.card.opacity, 0)
        tick(10_410_000)
        self.assertEqual(app.shade.opacity, 1)
        self.assertGreater(app.card.opacity, 0)
        self.assertLess(app.card.opacity, 1)
        self.assertFalse(tick(10_600_000))
        self.assertEqual((app.shade.opacity, app.card.opacity), (1, 1))
        self.assertEqual(app.animation_tick, 0)

    def test_close_interrupts_open_without_flash(self):
        app, animate = controller()
        animate(True)
        app.shade.opacity, app.card.opacity = .5, .2
        animate(False)
        app.window.remove_tick_callback.assert_called_once_with(7)
        frame = app.window.add_tick_callback.call_args.args[0]
        frame(None, SimpleNamespace(get_frame_time=lambda: 1000000))
        self.assertEqual((app.shade.opacity, app.card.opacity), (.5, .2))
        self.assertFalse(frame(None, SimpleNamespace(get_frame_time=lambda: 1200000)))
        app._finish_close.assert_called_once()

    def test_reduced_motion_is_immediate(self):
        app, animate = controller(False)
        animate(True)
        self.assertEqual((app.shade.opacity, app.card.opacity), (1, 1))
        animate(False)
        app._finish_close.assert_called_once()
        app.window.add_tick_callback.assert_not_called()
