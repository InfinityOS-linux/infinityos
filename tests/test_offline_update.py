"""Offline orchestration must never install without a complete backup."""
import hashlib
import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/libexec/infinityos-offline-update'
sys.path.insert(0, str(SOURCE.parents[1] / 'share/infinityos/updater'))
spec = importlib.util.spec_from_loader('offline_update', SourceFileLoader('offline_update', str(SOURCE)))
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineTests(unittest.TestCase):
    def exercise(self, failure, previous=None, output=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            data = root / 'usr/lib/sysimage/libdnf5/offline'
            data.mkdir(parents=True)
            transaction = json.dumps({'rpms': [
                {'nevra': 'example-0:2-1.x86_64', 'action': 'Upgrade'},
                {'nevra': 'working-1-1.noarch', 'action': 'Install'},
            ]})
            (data / 'transaction.json').write_text(transaction)
            trigger = root / 'system-update'
            trigger.symlink_to(data)
            (root / 'run').mkdir()
            result_dir = root / 'var/lib/infinityos'
            result_dir.mkdir(parents=True)
            if previous:
                previous['transaction'] = hashlib.sha256(transaction.encode()).hexdigest()
                (result_dir / 'offline-update-result.json').write_text(json.dumps(previous))

            def path(value):
                return root / str(value).lstrip('/')
            commands = []
            def run(args, **kwargs):
                commands.append(args)
                if args[0] == '/usr/libexec/infinityos-backups-snapshot':
                    self.assertFalse(trigger.is_symlink())
                if '_execute' in args:
                    self.assertTrue(trigger.is_symlink())
                    self.assertEqual(json.loads((result_dir / 'offline-update-result.json').read_text())['status'],
                                     'running')
                if failure and failure in args:
                    if output:
                        kwargs['stdout'].write(output)
                    raise subprocess.CalledProcessError(1, args)
                return subprocess.CompletedProcess(args, 0, 'Create snapshot\n17\n')
            with patch.object(offline, 'Path', side_effect=path), patch.object(offline.subprocess, 'run', side_effect=run):
                code = offline.main()
            result_path = result_dir / 'offline-update-result.json'
            self.assertEqual(result_path.stat().st_mode & 0o777, 0o644)
            result = json.loads(result_path.read_text())
            return code, commands, result, trigger.is_symlink()

    def test_failed_backup_does_not_run_dnf(self):
        code, commands, result, trigger = self.exercise('/usr/libexec/infinityos-backups-snapshot')
        self.assertEqual(code, 1)
        self.assertEqual(len(commands), 1)
        self.assertFalse(trigger)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['phase'], 'backup')
        self.assertEqual({item['name'] for item in result['held_packages']}, {'example', 'working'})

    def test_failed_install_keeps_recovery_number_and_does_not_finalize_release(self):
        code, commands, result, trigger = self.exercise('_execute')
        self.assertEqual(code, 1)
        self.assertEqual(len(commands), 2)
        self.assertEqual(result['snapshot'], '17')
        self.assertEqual(result['phase'], 'transaction')
        self.assertEqual({item['name'] for item in result['held_packages']}, {'example', 'working'})
        self.assertFalse(trigger)

    def test_success_finalizes_only_after_dnf(self):
        held = {'name': 'previous', 'arch': 'x86_64', 'version': '3-1',
                'source': 'repo', 'nevra': 'previous-3-1.x86_64', 'phase': 'transaction'}
        code, commands, result, trigger = self.exercise(None, previous={'status': 'failed', 'held_packages': [held]})
        self.assertEqual(code, 0)
        self.assertEqual([a[0] for a in commands], ['/usr/libexec/infinityos-backups-snapshot',
                         '/usr/bin/dnf5', '/usr/libexec/infinityos-upgrade-release', 'systemctl'])
        self.assertEqual(result['status'], 'success')
        self.assertFalse(trigger)
        self.assertEqual(result['held_packages'], [held])

    def test_file_conflict_holds_only_the_implicated_build(self):
        code, _, result, trigger = self.exercise('_execute', output=(
            'file /example from install of example-2-1.x86_64 conflicts with file from package old-1-1.x86_64\n'))
        self.assertEqual(code, 1)
        self.assertFalse(trigger)
        self.assertEqual(result['phase'], 'file_conflict')
        self.assertEqual([item['name'] for item in result['held_packages']], ['example'])

    def test_previous_interrupted_attempt_does_not_execute_dnf_or_take_another_snapshot(self):
        previous = {'status': 'running', 'phase': 'backup', 'attempted_packages': [
            {'name': 'example', 'version': '2-1', 'arch': 'x86_64', 'source': 'repo',
             'nevra': 'example-2-1.x86_64'}]}
        code, commands, result, trigger = self.exercise(None, previous=previous)
        self.assertEqual(code, 1)
        self.assertEqual(commands, [])
        self.assertFalse(trigger)
        self.assertTrue(result['interrupted'])
        self.assertEqual(result['held_packages'][0]['name'], 'example')

    def test_changed_rpm_database_allows_a_fresh_transaction(self):
        code, _, result, trigger = self.exercise('_execute', output=(
            'The system has been modified since the offline transaction was prepared. To reschedule, run: dnf upgrade'))
        self.assertEqual(code, 1)
        self.assertFalse(trigger)
        self.assertEqual(result['phase'], 'rpmdb_changed')
        self.assertEqual(result['held_packages'], [])
