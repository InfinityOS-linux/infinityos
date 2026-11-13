from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipUnless(Gtk, 'GTK requires Fedora and Xvfb')
class BackupsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/share/infinityos'))
        import config_backups_page
        cls.ui = config_backups_page
        if not Gtk.init_check():
            raise unittest.SkipTest('GTK needs a display')

    def setUp(self):
        self.window = Gtk.Window()
        self.addCleanup(self.window.destroy)
        self.app = SimpleNamespace(window=self.window, stack=Gtk.Stack(), status=Gtk.Label(),
                                   _select_tab=lambda b, name: self.app.stack.set_visible_child_name(name) if b.get_active() else None)
        self.app.stack.add_named(Gtk.Box(), 'Desktop')
        self.page = self.ui.BackupsPage(self.app, Gtk.Box(), Gtk.ToggleButton())

    def test_tab_loads_only_on_first_selection_and_can_refresh(self):
        with patch.object(self.page, 'load') as load:
            load.assert_not_called()
            self.page.tab.set_active(True)
            load.assert_called_once_with()
            self.page.selected()
            load.assert_called_once()
            self.page.refresh.emit('clicked')
            self.assertEqual(load.call_count, 2)

    def test_polish_empty_error_and_paired_snapshot_states(self):
        import config_backups_i18n
        with patch.object(config_backups_i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            self.page.finish({'ready': True, 'snapshots': []}, None, False)
            self.assertEqual(self.page.rows.get_first_child().get_text(), 'Nie ma jeszcze migawek.')
            self.page.finish({'ready': True, 'snapshots': [dict(number='2', date='2026-11-08', description='Before update', complete=True)]}, None, False)
            self.assertIn("Ostatnia pełna kopia", self.page.rows.get_first_child().get_text())
            row = self.page.rows.get_first_child().get_next_sibling()
            self.assertIn('/home', row.get_last_child().get_prev_sibling().get_text())
            with patch.object(self.page, 'confirm_delete') as confirm:
                row.get_last_child().emit('clicked')
                self.assertEqual(confirm.call_args.args[0]['number'], '2')
            self.page.finish(None, 'denied', False)
            self.assertTrue(self.page.body.get_sensitive())
            self.assertIn('nie powiodła', self.app.status.get_text())
            self.assertEqual(self.page.rows.get_last_child().get_child().get_text(), 'denied')

    def test_busy_backup_prevents_close_without_deactivating_other_pages(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packages/infinity-setup/root/usr/share/infinityos'))
        from config import InfinityConfig
        self.page.busy = True
        self.app.backups_page = self.page
        self.assertTrue(InfinityConfig._close_requested(self.app))
        self.assertTrue(self.page.alive)
