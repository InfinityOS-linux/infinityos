"""Cached results must reflect a completed offline transaction before network I/O."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('post_reboot_checker', SOURCE / 'checker.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PostRebootTests(unittest.TestCase):
    def test_cached_list_is_reconciled_before_display_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = directory / 'offline-update-result.json'
            cache = directory / 'updates.json'
            state = {'checked_at': '2026-11-17T10:00:00+00:00',
                     'updates': [{'kind': 'RPM', 'name': 'infinity-updater'},
                                 {'kind': 'Flatpak user', 'name': 'org.example.App'}],
                     'release': {'version': '2.1'}, 'errors': [], 'rpm_check_ok': True}
            checker.save_state(state, cache)
            reconcile = checker.reconcile_offline_result
            with patch.object(checker, 'reconcile_offline_result',
                              side_effect=lambda value: reconcile(value, directory)), \
                 patch.object(checker, '_run') as command:
                for status in ('failed', 'success'):
                    result.write_text(json.dumps({'status': status}))
                    os.utime(result, (1794913200, 1794913200)) # 2026-11-17 11:00 UTC
                    actual = checker.read_state(cache)
                    if status == 'failed':
                        self.assertEqual(actual, state)
                    else:
                        self.assertEqual(actual['updates'], state['updates'][1:])
                        self.assertIsNone(actual['release'])
                        self.assertFalse(checker.fresh_state(actual))
                command.assert_not_called()
                # A later scan must retain newly discovered updates.
                state['checked_at'] = '2026-11-17T12:00:00+00:00'
                checker.save_state(state, cache)
                self.assertEqual(checker.read_state(cache), state)
                # Missing or corrupt results are not evidence of installation.
                result.write_text('{')
                self.assertEqual(checker.read_state(cache), state)
                result.unlink()
                self.assertEqual(checker.read_state(cache), state)
