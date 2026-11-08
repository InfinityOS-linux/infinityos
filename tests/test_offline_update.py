"""Offline orchestration must never install without a complete backup."""
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/libexec/infinityos-offline-update'
spec = importlib.util.spec_from_loader('offline_update', SourceFileLoader('offline_update', str(SOURCE)))
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineTests(unittest.TestCase):
    def exercise(self, failure):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            data = root / 'usr/lib/sysimage/libdnf5/offline'
            data.mkdir(parents=True)
            (data / "transaction.json").write_text("transaction")
            trigger = root / 'system-update'
            trigger.symlink_to(data)
            (root / 'run').mkdir()
            def path(value):
                return root / str(value).lstrip('/')
            commands = []
            def run(args, **kwargs):
                commands.append(args)
                if failure and failure in args:
                    raise subprocess.CalledProcessError(1, args)
                return subprocess.CompletedProcess(args, 0, 'Create snapshot\n17\n')
            with patch.object(offline, 'Path', side_effect=path), patch.object(offline.subprocess, 'run', side_effect=run):
                code = offline.main()
            import json
            result = json.loads((root / 'var/lib/infinityos/offline-update-result.json').read_text())
            return code, commands, result, trigger.is_symlink()

    def test_failed_backup_does_not_run_dnf(self):
        code, commands, result, trigger = self.exercise('/usr/libexec/infinityos-backups-snapshot')
        self.assertEqual(code, 1)
        self.assertEqual(len(commands), 1)
        self.assertFalse(trigger)
        self.assertEqual(result['status'], 'failed')

    def test_failed_install_keeps_recovery_number_and_does_not_finalize_release(self):
        code, commands, result, trigger = self.exercise('_execute')
        self.assertEqual(code, 1)
        self.assertEqual(len(commands), 2)
        self.assertEqual(result['snapshot'], '17')
        self.assertFalse(trigger)

    def test_success_finalizes_only_after_dnf(self):
        code, commands, result, _ = self.exercise(None)
        self.assertEqual(code, 0)
        self.assertEqual([a[0] for a in commands], ['/usr/libexec/infinityos-backups-snapshot',
                         '/usr/bin/dnf5', '/usr/libexec/infinityos-upgrade-release', 'systemctl'])
        self.assertEqual(result['status'], 'success')
