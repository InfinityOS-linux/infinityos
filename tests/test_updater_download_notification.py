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


class CompletionNotificationTests(unittest.TestCase):
    def method(self, name, namespace):
        method = next(node for node in ast.walk(ast.parse(SOURCE.read_text()))
                      if isinstance(node, ast.FunctionDef) and node.name == name)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        return namespace[name]

    def test_pending_restart_survives_unrelated_update_and_history_errors(self):
        from contextlib import nullcontext
        for pending in (False, True):
            for check_fails in (False, True):
                with self.subTest(pending=pending, check_fails=check_fails):
                    state = {'updates': [], 'errors': [], 'rpm_check_ok': True}
                    check = Mock(return_value=state)
                    if check_fails:
                        check.side_effect = RuntimeError('repository unavailable')
                    app = SimpleNamespace(state=state, progress=Mock(), recovery=Mock(),
                        hold=Mock(), render=Mock(), pulse_progress=Mock(), report_progress=Mock(),
                        finish_error=Mock(), finish_refresh=Mock())
                    namespace = dict(
                        offline_status=lambda: {'pending': pending}, update_rows=lambda *_: [],
                        install_commands=lambda _: [('Your Flatpaks', ['flatpak'])],
                        apply_command=lambda *_: SimpleNamespace(returncode=1, stderr='Flatpak error', stdout=''),
                        record_operation=Mock(side_effect=OSError('History unavailable')),
                        privileged_transaction=nullcontext, check_updates=check, save_state=Mock(),
                        pending_rpm_names=lambda *_: [], tr=lambda text: text,
                        threading=SimpleNamespace(Thread=lambda target, daemon: SimpleNamespace(start=target)),
                        GLib=SimpleNamespace(timeout_add=Mock(), idle_add=lambda callback, *args: callback(*args)))
                    self.method('on_apply', namespace)(app, None)
                    if check_fails:
                        app.finish_error.assert_called_once_with('repository unavailable', pending)
                    else:
                        app.finish_refresh.assert_called_once_with(state,
                            'Some updates could not be installed.', None, pending)
                        self.assertIn('Flatpak error', ' '.join(state['errors']))

    def test_error_completion_notifies_only_when_downloaded(self):
        for downloaded in (False, True):
            app = SimpleNamespace(checking=False, spinner=Mock(), stop_progress=Mock(),
                render=Mock(), release=Mock(), notify_downloaded=Mock())
            namespace = dict(read_state=lambda: {'errors': []}, GLib=SimpleNamespace(SOURCE_REMOVE=False))
            self.method('finish_error', namespace)(app, 'Check failed', downloaded)
            self.assertEqual(app.notify_downloaded.call_count, int(downloaded))
            self.assertEqual(app.state['errors'], ['Check failed'])
            self.assertFalse(app.busy)
            app.release.assert_called_once()
