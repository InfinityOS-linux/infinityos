import fcntl
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_updater import checker, upgrade_release, github_update
from test_pending_updates import pending
import launcher_backend as backend


class AuditRegressionTests(unittest.TestCase):
    def test_unsupported_pending_actions_are_kept_untouched(self):
        for action in ('Remove', 'Reason Change', 'FutureAction'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                offline = root / 'offline'
                offline.mkdir()
                original = json.dumps({'rpms': [{'nevra': 'example-1-1.x86_64', 'action': action}]})
                (offline / 'transaction.json').write_text(original)
                trigger = root / 'system-update'
                trigger.symlink_to(offline)
                with patch.object(pending, 'OFFLINE', offline), patch.object(pending, 'TRIGGER', trigger), \
                     patch.object(pending.subprocess, 'run') as run:
                    with self.assertRaisesRegex(RuntimeError, 'unsupported actions'):
                        pending.stage()
                    run.assert_not_called()
                self.assertEqual((offline / 'transaction.json').read_text(), original)
                self.assertEqual(trigger.resolve(), offline)

    def test_release_cannot_start_while_another_update_holds_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'update.lock'
            with path.open('w') as owner, patch.object(upgrade_release, 'LOCK', path), \
                 patch.object(upgrade_release.os, 'geteuid', return_value=0), \
                 patch.object(upgrade_release, 'prepare') as prepare:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    upgrade_release.main(['upgrade', '2.1', '45'])
                prepare.assert_not_called()
                fcntl.flock(owner, fcntl.LOCK_UN)
                upgrade_release.main(['upgrade', '2.1', '45'])
                prepare.assert_called_once()

    def test_pending_release_is_checked_inside_stage(self):
        with patch.object(pending.Path, 'exists', return_value=True), \
             patch.object(pending.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'release upgrade is pending'):
                pending.stage()
            run.assert_not_called()

    def test_automatic_refresh_reuses_fresh_state_but_manual_refresh_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'updates.json'
            state = {'checked_at': checker.datetime.now(checker.timezone.utc).isoformat(),
                     'updates': [], 'errors': []}
            checker.save_state(state, path)
            with patch.object(checker, 'state_path', return_value=path), \
                 patch.object(checker, 'check_updates', return_value=state) as check:
                self.assertEqual(checker.refresh_state(), state)
                check.assert_not_called()
                checker.refresh_state(force=True)
                check.assert_called_once()

    def test_github_check_stops_at_budget_and_reports_partial_result(self):
        with patch.object(github_update, '_installed', return_value={}), \
             patch.object(github_update.time, 'monotonic', side_effect=[0, 181]), \
             patch.object(github_update, 'latest_rpm_asset') as fetch:
            updates, errors = github_update.check_github_updates()
            self.assertEqual(updates, [])
            self.assertIn('timed out', errors[0])
            fetch.assert_not_called()

    def test_catalog_reads_rpm_once_and_does_not_spawn_ollama_per_model(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout='photocraft\nsteam\n')
        with patch.object(backend.subprocess, 'run', side_effect=run), \
             patch.object(backend, 'downloaded_local_models', return_value=('infinity-qwen-9b:latest',)), \
             patch.object(backend, '_driver_module_installed', return_value=False):
            _, models, states = backend.catalog_state()
        self.assertEqual(sum(args[0] == 'rpm' for args in calls), 1)
        self.assertEqual(sum(args[0] == 'flatpak' for args in calls), 2)
        self.assertFalse(any(args[0] == 'ollama' for args in calls))
        model = next(app for app in states if app.source == 'infinity-qwen-9b')
        self.assertTrue(states[model])
