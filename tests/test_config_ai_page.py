"""Exercise real GTK controls under Xvfb; never contact provider accounts."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/share/infinityos'
try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires the Fedora test environment')
class AiPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(DIRECTORY))
        import config_ai_page
        cls.ui = config_ai_page
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK tests need a display (use xvfb-run)")

    def test_tab_tracks_setup_and_restores_desktop_after_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / '.config/infinityos/local-ai-model'
            marker.parent.mkdir(parents=True)
            marker.write_text('custom:latest')
            window, stack, nav = Gtk.Window(), Gtk.Stack(), Gtk.Box()
            stack.add_named(Gtk.Box(), 'Desktop')
            group = Gtk.ToggleButton()
            group.connect('toggled', lambda b: stack.set_visible_child_name('Desktop') if b.get_active() else None)
            group.set_active(True)
            app = SimpleNamespace(window=window, stack=stack, status=Gtk.Label(),
                                  _select_tab=lambda b, name: stack.set_visible_child_name(name) if b.get_active() else None)
            with patch.object(self.ui, 'selected_ai', return_value=('local',)) as selected, \
                 patch.object(self.ui.Path, 'home', return_value=Path(directory)), \
                 patch.object(self.ui.AiPage, 'load'):
                page = self.ui.AiPage(app, nav, group)
                self.assertTrue(page.tab.get_visible())
                page.tab.set_active(True)
                self.assertEqual(stack.get_visible_child_name(), 'AI')
                selected.return_value = ()
                marker.unlink()
                page.poll()
                self.assertFalse(page.tab.get_visible())
                self.assertEqual(stack.get_visible_child_name(), 'Desktop')
                page.close()
            window.destroy()

    def test_blocked_close_keeps_both_pages_alive(self):
        from config import InfinityConfig
        from config_proton_page import ProtonPage
        stack = Gtk.Stack()
        stack.add_named(Gtk.Box(), 'Desktop')
        app = SimpleNamespace(window=Gtk.Window(), stack=stack, status=Gtk.Label(),
                              _select_tab=lambda *_: None)
        nav, group = Gtk.Box(), Gtk.ToggleButton()
        with patch.object(self.ui, 'selected_ai', return_value=()):
            app.proton_page = ProtonPage(app, nav, group)
            app.ai_page = self.ui.AiPage(app, nav, group)
        app.window.connect('close-request', lambda *_: InfinityConfig._close_requested(app))
        generation = app.ai_page.generation
        for ai_busy, proton_busy in ((True, False), (False, True), (True, True)):
            app.ai_page.busy = ai_busy
            app.proton_page.busy = proton_busy
            self.assertTrue(app.window.emit('close-request'))
            self.assertTrue(app.proton_page.alive)
            self.assertEqual(app.ai_page.generation, generation)
        app.ai_page.busy = app.proton_page.busy = False
        self.assertFalse(InfinityConfig._close_requested(app))
        self.assertFalse(app.proton_page.alive)
        self.assertGreater(app.ai_page.generation, generation)
        app.window.destroy()

    def test_local_controls_and_translations_render(self):
        import config_ai_i18n
        page = object.__new__(self.ui.AiPage)
        page.app = SimpleNamespace(status=Gtk.Label())
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        data = dict(model='test', models=['test', 'other'], context=4096, output=1024, temperature=0.8, storage='/mnt/models')
        with patch.object(config_ai_i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            page.local_controls(card, data, None)
        labels = []
        child = card.get_first_child()
        while child:
            if isinstance(child, (Gtk.Label, Gtk.Button)):
                labels.append(child.get_label())
            child = child.get_next_sibling()
        self.assertIn('Kontekst (tokeny)', labels)
        self.assertIn('Zastosuj ustawienia modelu', labels)

    def test_provider_limits_render_without_inventing_tokens(self):
        page = object.__new__(self.ui.AiPage)
        card, status = Gtk.Box(), Gtk.Label()
        data = {'account': {'email': 'example@example.test', 'type': 'chatgpt'},
                'limits': {'rateLimits': {'primary': {'usedPercent': 25, 'windowDurationMins': 300}}}}
        page.account_controls(card, status, 'codex', data)
        self.assertIn('75%', status.get_text())
        self.assertNotIn('Total tokens', status.get_text())
