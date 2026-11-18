import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater/updater.py'
METHOD = next(node for node in ast.walk(ast.parse(SOURCE.read_text()))
              if isinstance(node, ast.FunctionDef) and node.name == 'on_apply')


class CancelledInstallTests(unittest.TestCase):
    def exercise(self, codes):
        items = [dict(kind='RPM', name='infinity-updater')]
        app = SimpleNamespace(state={'updates': items}, hold=Mock(), progress=Mock(),
                              recovery=Mock(), pulse_progress=Mock(), render=Mock(),
                              report_progress=Mock(), finish_error=Mock(), finish_refresh=Mock())
        check = Mock(return_value={'updates': [], 'errors': [], 'rpm_check_ok': True})
        save = Mock()
        namespace = {
            'update_rows': lambda updates, offline: updates,
            'offline_status': lambda: {},
            'install_commands': lambda updates: [(f'Command {i}', ['pkexec', 'test']) for i in range(len(codes))],
            'apply_command': Mock(side_effect=[SimpleNamespace(returncode=code, stdout='',
                                stderr='Authorization was cancelled or failed.' if code else '') for code in codes]),
            'privileged_transaction': nullcontext, 'record_operation': Mock(),
            'check_updates': check, 'save_state': save, 'pending_rpm_names': lambda *args: [],
            'tr': lambda text: text,
            'GLib': SimpleNamespace(timeout_add=lambda *args: 1,
                                    idle_add=lambda callback, *args: callback(*args)),
            'threading': SimpleNamespace(Thread=lambda target, **kwargs: SimpleNamespace(start=target)),
        }
        exec(compile(ast.Module(body=[METHOD], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        namespace['on_apply'](app, None)
        return app, check, save

    def test_cancelled_or_denied_authorization_keeps_updates_without_recheck(self):
        for code in (1, 126, 127):
            with self.subTest(code=code):
                app, check, save = self.exercise([code])
                check.assert_not_called()
                save.assert_not_called()
                self.assertEqual(app.state['updates'][0]['name'], 'infinity-updater')
                app.finish_error.assert_called_once()
                app.finish_refresh.assert_not_called()

    def test_all_failed_commands_do_not_publish_an_empty_list(self):
        app, check, save = self.exercise([1, 1])
        check.assert_not_called()
        save.assert_not_called()
        app.finish_error.assert_called_once()

    def test_success_and_partial_success_still_refresh_real_remaining_updates(self):
        for codes in ([0], [1, 0]):
            with self.subTest(codes=codes):
                app, check, save = self.exercise(codes)
                check.assert_called_once()
                save.assert_called_once()
                app.finish_refresh.assert_called_once()
                app.finish_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
