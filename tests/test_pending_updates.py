import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE.parents[5] / 'infinity-setup/root/usr/share/infinityos'))
import pending
import updater


def package(name='example', version='1-1', arch='x86_64', **extra):
    return dict(kind='RPM', name=name, version=version, arch=arch, source='repo',
                nevra=f'{name}-{version}.{arch}', path='', **extra)


def compare(a, b):
    return (a > b) - (a < b)


class PendingUpdatesTests(unittest.TestCase):
    def test_newer_versions_replace_pending_while_exact_versions_have_restart_marker(self):
        queued = [package(), package('other'), package('withdrawn')]
        rows = updater.update_rows([package(version='2-1'), package('other'),
                                    dict(kind='Flatpak user', name='chat', version='1', source='flathub')],
                                   dict(pending=True, packages=queued))
        self.assertEqual([(r['name'], r['pending']) for r in rows],
                         [('example', False), ('other', True), ('chat', False), ('withdrawn', True)])
        self.assertEqual(len(updater.update_rows([], dict(pending=False, packages=queued))), 0)

    def test_multilib_and_epoch_matching(self):
        rows = updater.update_rows([package(version='0:1-1'), package(arch='i686')],
                                   dict(pending=True, packages=[package()]))
        self.assertEqual([r['pending'] for r in rows], [True, False])
        self.assertEqual(pending.evr_tuple('2:1.5-3.fc45'), ('2', '1.5', '3.fc45'))

    def test_refresh_keeps_cached_packages_when_repo_drops_them(self):
        with tempfile.TemporaryDirectory() as directory:
            rpm = Path(directory).resolve() / 'old.rpm'
            rpm.touch()
            old = package()
            old['path'] = str(rpm)
            self.assertEqual(pending.refresh_specs([old], [], compare), [str(rpm)])
            self.assertEqual(pending.refresh_specs([old], [package(version='2-1')], compare),
                             ['example-2-1.x86_64'])
            self.assertEqual(pending.refresh_specs([old], [package(version='0-1')], compare), [str(rpm)])
            self.assertEqual(pending.refresh_specs([old], [], compare, ('example', 'x86_64')), [])

    def test_missing_cache_fails_before_touching_pending_transaction(self):
        with self.assertRaisesRegex(RuntimeError, 'pending update was kept'):
            pending.refresh_specs([package()], [], compare)

    def exercise(self, fail):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            data = root / 'offline'
            data.mkdir()
            original = json.dumps({'rpms': [dict(nevra='example-0:1-1.x86_64', action='Upgrade', repo_id='repo', reason='Dependency')]})
            (data / 'transaction.json').write_text(original)
            (data / 'offline-transaction-state.toml').write_text('original-state')
            trigger = root / 'system-update'
            trigger.symlink_to(data)
            commands = []
            def run(args, **kwargs):
                commands.append(args)
                if 'repoquery' in args:
                    return SimpleNamespace(stdout='example|x86_64|2-1\n')
                self.assertFalse(trigger.is_symlink())
                if 'reboot' in args:
                    trigger.symlink_to(data)
                    return SimpleNamespace(returncode=0)
                (data / 'transaction.json').write_text(json.dumps({'rpms': [
                    dict(nevra='example-2-1.x86_64', action='Upgrade', reason='User')]}))
                (data / 'offline-transaction-state.toml').write_text('new-state')
                if fail:
                    raise subprocess.CalledProcessError(1, args)
                return SimpleNamespace(returncode=0)
            with patch.object(pending, 'OFFLINE', data), patch.object(pending, 'TRIGGER', trigger), \
                 patch.object(pending.subprocess, 'run', side_effect=run), \
                 patch.dict(sys.modules, {'rpm': SimpleNamespace(labelCompare=compare)}):
                if fail:
                    with self.assertRaises(subprocess.CalledProcessError):
                        pending.stage()
                    self.assertEqual((data / 'transaction.json').read_text(), original)
                    self.assertEqual((data / 'offline-transaction-state.toml').read_text(), 'original-state')
                else:
                    pending.stage()
                    self.assertIn('example-2-1.x86_64', commands[1])
                    self.assertIn('--action=upgrade', commands[1])
                    self.assertIn('--offline', commands[1])
                    self.assertEqual(json.loads((data / 'transaction.json').read_text())['rpms'][0]['reason'],
                                     'Dependency')
                self.assertEqual(trigger.resolve(), data)

    def test_failed_refresh_restores_original_batch_and_restart_trigger(self):
        self.exercise(True)

    def test_success_refreshes_queue_and_rearms_restart_without_installing_live(self):
        self.exercise(False)

    def test_foreign_updater_trigger_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            trigger = Path(directory).resolve() / 'system-update'
            trigger.symlink_to('/another-updater')
            with patch.object(pending, 'TRIGGER', trigger):
                with self.assertRaisesRegex(RuntimeError, 'Another updater'):
                    pending.stage()
            self.assertEqual(str(trigger.readlink()), '/another-updater')

    def test_empty_upgrade_does_not_arm_a_nonexistent_offline_transaction(self):
        for empty_file in (False, True):
            with self.subTest(empty_file=empty_file), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if empty_file:
                    (root / 'transaction.json').write_text('{"rpms": []}')
                trigger = root / 'system-update'
                with patch.object(pending, 'OFFLINE', root), patch.object(pending, 'TRIGGER', trigger), \
                     patch.object(pending.subprocess, 'run') as run:
                    pending.stage()
                    run.assert_called_once()
                    self.assertIn('upgrade', run.call_args.args[0])
                    self.assertFalse(trigger.exists())
