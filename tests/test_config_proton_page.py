from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages/infinity-setup/root/usr/share/infinityos"))
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires Fedora test environment')
class ProtonPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check():
            raise unittest.SkipTest('Run with xvfb-run')
        directory = Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/share/infinityos'
        sys.path.insert(0, str(directory))
        import config_proton_page
        cls.ui = config_proton_page

    def test_page_loads_only_when_selected_and_cannot_close_during_install(self):
        stack = Gtk.Stack()
        stack.add_named(Gtk.Box(), 'Desktop')
        app = SimpleNamespace(stack=stack, window=Gtk.Window(), status=Gtk.Label(),
                              _select_tab=lambda b,n: stack.set_visible_child_name(n) if b.get_active() else None)
        with patch.object(self.ui.backend, 'releases') as network, patch.object(self.ui.ProtonPage, 'refresh') as refresh:
            page = self.ui.ProtonPage(app, Gtk.Box(), Gtk.ToggleButton())
            network.assert_not_called()
            refresh.assert_not_called()
            stack.set_visible_child_name('Proton')
            refresh.assert_called_once()
            page.busy = True
            self.assertTrue(page.close())
            page.busy = False
            self.assertFalse(page.close())
        app.window.destroy()

    def test_existing_provider_offers_update_and_installed_version_is_disabled(self):
        page = object.__new__(self.ui.ProtonPage)
        page.install = lambda _: None
        page.rows = [{'metadata': {'provider': 'Proton-Cachy', 'digest': 'old'}, 'paths': [Path('/one'), Path('/two')]}]
        release = dict(tag='v12', provider='Proton-Cachy', digest='new')
        card, state = Gtk.Box(), Gtk.Label()
        card.append(state)
        with patch.object(self.ui.backend, 'tool_roots', return_value=[Path('/one'), Path('/two')]):
            page.release_controls(card, state, [release])
            self.assertEqual(card.get_last_child().get_label(), 'Update')
            page.rows[0]['metadata']['digest'] = 'new'
            card, state = Gtk.Box(), Gtk.Label()
            card.append(state)
            page.release_controls(card, state, [release])
            self.assertEqual(card.get_last_child().get_label(), 'Installed')
            self.assertFalse(card.get_last_child().get_sensitive())

    def test_polish_release_error(self):
        import config_proton_i18n
        page = object.__new__(self.ui.ProtonPage)
        state = Gtk.Label()
        with patch.object(config_proton_i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            page.release_controls(Gtk.Box(), state, None)
        self.assertIn('Lista wydań niedostępna', state.get_text())
