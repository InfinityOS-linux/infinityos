import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'


class DownloadNotificationTests(unittest.TestCase):
    def setUp(self):
        methods = [node for node in ast.walk(ast.parse(SOURCE.read_text()))
                   if isinstance(node, ast.FunctionDef)
                   and node.name in ('notify_downloaded', 'on_restart_downloaded')]
        self.pending = True
        self.notification = Mock()
        self.process = Mock()
        self.gio = SimpleNamespace(Notification=SimpleNamespace(new=Mock(return_value=self.notification)),
            ThemedIcon=SimpleNamespace(new=Mock()),
            Subprocess=SimpleNamespace(new=Mock(return_value=self.process)),
            SubprocessFlags=SimpleNamespace(NONE=0))
        self.namespace = dict(Gio=self.gio, GLib=SimpleNamespace(Error=RuntimeError),
                              tr=lambda text: text, offline_status=lambda: {'pending': self.pending})
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE), 'exec'), self.namespace)
        self.app = SimpleNamespace(busy=False, send_notification=Mock(), withdraw_notification=Mock(),
                                   hold=Mock(), release=Mock())

    def test_ready_notification_has_restart_action(self):
        self.namespace['notify_downloaded'](self.app)
        self.gio.Notification.new.assert_called_once_with('Updates downloaded')
        self.notification.add_button.assert_called_once_with('Restart to install', 'app.restart-downloaded')
        self.app.send_notification.assert_called_once_with('updates-downloaded', self.notification)

    def test_no_download_notification_without_pending_transaction(self):
        self.pending = False
        self.namespace['notify_downloaded'](self.app)
        self.app.send_notification.assert_not_called()

    def test_stale_notification_does_not_restart(self):
        self.pending = False
        self.namespace['on_restart_downloaded'](self.app, None, None)
        self.gio.Subprocess.new.assert_not_called()
        self.app.withdraw_notification.assert_called_once_with('updates-downloaded')

    def test_restart_works_without_window_and_holds_app_until_completed(self):
        self.namespace['on_restart_downloaded'](self.app, None, None)
        self.gio.Subprocess.new.assert_called_once_with(['/usr/bin/systemctl', 'reboot'], 0)
        self.app.hold.assert_called_once()
        self.app.release.assert_not_called()
        self.namespace['on_restart_downloaded'](self.app, None, None)
        self.assertEqual(self.gio.Subprocess.new.call_count, 1)
        callback = self.process.wait_check_async.call_args.args[1]
        callback(self.process, object())
        self.app.release.assert_called_once()
        self.app.withdraw_notification.assert_called_once_with('updates-downloaded')

    def test_failed_restart_is_reported_and_can_be_retried(self):
        self.namespace['on_restart_downloaded'](self.app, None, None)
        self.process.wait_check_finish.side_effect = RuntimeError('denied')
        self.process.wait_check_async.call_args.args[1](self.process, object())
        self.assertFalse(self.app._notification_restarting)
        self.app.release.assert_called_once()
        self.app.send_notification.assert_called_once()
        self.app.withdraw_notification.assert_not_called()
