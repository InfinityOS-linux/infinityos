import importlib.util
from importlib.machinery import SourceFileLoader
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('checker')
i18n = load('i18n')
updater = load('updater')
progress = load('progress')
release = load('release')

helper_path = SOURCE.parents[2] / 'libexec/infinityos-upgrade-release'
spec = importlib.util.spec_from_loader('upgrade_release', SourceFileLoader('upgrade_release', str(helper_path)))
upgrade_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade_release)


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        current = patch.object(checker, 'installed_version', return_value=('1.0', 44))
        latest = patch.object(checker, 'load_manifest', return_value={
            'version': '1.0', 'fedora_release': 44})
        current.start()
        latest.start()
        self.addCleanup(current.stop)
        self.addCleanup(latest.stop)

    def test_checks_each_source_and_saves_state(self):
        outputs = [
            type('Result', (), {'returncode': 0, 'stdout': 'firefox|158.0|updates\n', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': 'org.gnome.Evince\t51.0\tflathub\n', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '{"Devices": []}', 'stderr': ''})(),
        ]
        with patch.object(checker, '_run', side_effect=outputs):
            state = checker.check_updates()
        self.assertEqual([item['kind'] for item in state['updates']], ['RPM', 'Flatpak system'])
        self.assertEqual(state['updates'][0]['name'], 'firefox')
        self.assertEqual(state['errors'], [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'updates.json'
            checker.save_state(state, path)
            self.assertEqual(checker.read_state(path), state)

    def test_network_monitor_distinguishes_offline_from_unknown(self):
        connectivity = SimpleNamespace(LOCAL=1, LIMITED=2, PORTAL=3, FULL=4, UNKNOWN=0)
        gio = SimpleNamespace(NetworkConnectivity=connectivity)
        monitor = SimpleNamespace(get_network_available=lambda: False,
                                  get_connectivity=lambda: connectivity.UNKNOWN)
        self.assertTrue(updater.network_is_offline(monitor, gio))
        monitor.get_network_available = lambda: True
        for status in (connectivity.LOCAL, connectivity.LIMITED, connectivity.PORTAL):
            monitor.get_connectivity = lambda status=status: status
            self.assertTrue(updater.network_is_offline(monitor, gio))
        for status in (connectivity.FULL, connectivity.UNKNOWN):
            monitor.get_connectivity = lambda status=status: status
            self.assertFalse(updater.network_is_offline(monitor, gio))

    def test_updater_offline_copy_follows_system_language(self):
        with patch.object(i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            self.assertEqual(i18n.tr('No internet connection'), 'Brak połączenia z internetem')
            self.assertEqual(i18n.tr('Connect to the internet and check again.'),
                             'Połącz się z internetem i sprawdź ponownie.')
            self.assertEqual(i18n.update_count(1), '1 dostępna aktualizacja')
            self.assertEqual(i18n.update_count(3), '3 dostępne aktualizacje')
            self.assertEqual(i18n.update_count(12), '12 dostępnych aktualizacji')
        with patch.object(i18n.locale, 'getlocale', return_value=('en_US', 'UTF-8')):
            self.assertEqual(i18n.tr('No internet connection'), 'No internet connection')
            self.assertEqual(i18n.update_count(1), '1 available update')

    def test_rpm_check_avoids_system_state_and_accepts_configured_repo_key(self):
        calls = []

        def run(args):
            calls.append(args)
            if args[0] == 'dnf':
                if not any(arg.startswith('--setopt=system_state_dir=') for arg in args):
                    return type('Result', (), {'returncode': 1, 'stdout': '',
                                               'stderr': 'Could not open packages.toml'})()
                if '--assumeyes' not in args:
                    return type('Result', (), {'returncode': 1, 'stdout': '',
                                               'stderr': 'Signing key not found'})()
            if args[0] == 'fwupdmgr':
                return type('Result', (), {'returncode': 0, 'stdout': '{"Devices": []}',
                                           'stderr': ''})()
            return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

        with patch.object(checker, '_run', side_effect=run):
            state = checker.check_updates()

        self.assertEqual(state['errors'], [])
        self.assertTrue(any(arg.startswith('--setopt=system_state_dir=') for arg in calls[0]))
        self.assertIn('--assumeyes', calls[0])

    def test_signed_new_release_is_separate_from_ordinary_updates(self):
        outputs = [
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '{"Devices": []}', 'stderr': ''})(),
        ]
        with patch.object(checker, '_run', side_effect=outputs), patch.object(
                checker, 'load_manifest', return_value={'version': '1.1', 'fedora_release': 44}):
            state = checker.check_updates()
        self.assertEqual(state['updates'], [])
        self.assertEqual(state['release'], {'version': '1.1', 'fedora_release': 44, 'supported': True})
        self.assertTrue(state['rpm_check_ok'])

    def test_release_validation_rejects_untrusted_paths_and_base_changes(self):
        self.assertIsNone(release.available_release({'version': '1.0', 'fedora_release': 44}, '1.0', 44))
        self.assertFalse(release.available_release({'version': '1.1', 'fedora_release': 45},
                                                   '1.0', 44)['supported'])
        with self.assertRaises(ValueError):
            release.repository_url('../1.1', 44, 'x86_64')
        with self.assertRaises(ValueError):
            release.repository_url('1.1', 44, 'i686')

    def test_release_helper_requires_current_packages_and_signed_target(self):
        with patch.object(upgrade_release.os, 'geteuid', return_value=0), patch.object(
                upgrade_release, 'installed_version', return_value=('1.0', 44)), patch.object(
                upgrade_release, 'load_manifest', return_value={'version': '1.1', 'fedora_release': 44}), patch.object(
                upgrade_release, 'run') as run, patch.object(
                upgrade_release.Path, 'is_file', return_value=True):
            run.side_effect = [type('R', (), {'stdout': 'btrfs\n'})(),
                               type('R', (), {'stdout': ''})(),
                               type('R', (), {'stdout': 'firefox\n'})()]
            with self.assertRaisesRegex(ValueError, 'current system package updates'):
                upgrade_release.main(['upgrader', '1.1', '44'])
            self.assertEqual([call.args[0][0] for call in run.call_args_list],
                             ['findmnt', 'mountpoint', 'dnf'])

        with patch.object(upgrade_release.os, 'geteuid', return_value=0), patch.object(
                upgrade_release, 'installed_version', return_value=('1.0', 44)), patch.object(
                upgrade_release, 'load_manifest', return_value={'version': '1.2', 'fedora_release': 44}), patch.object(
                upgrade_release, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'signed release'):
                upgrade_release.main(['upgrader', '1.1', '44'])
            run.assert_not_called()

    def test_release_helper_downloads_before_install_and_marks_success_last(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / 'os-release'
            os_release.write_text('NAME="Infinity OS"\nPRETTY_NAME="Infinity OS 44"\n'
                                  'ID=infinityos\nVERSION_ID=44\n')
            outputs = ['btrfs\n', '', '', 'x86_64\n', '17\n', '', '']
            events = []

            def run(args, **_kwargs):
                events.append(('run', args))
                return type('R', (), {'stdout': outputs.pop(0)})()

            def write(path, content):
                events.append(('write', path.name))
                if path.parent == root:
                    path.write_text(content)

            with patch.object(upgrade_release.os, 'geteuid', return_value=0), patch.object(
                    upgrade_release, 'installed_version', return_value=('1.0', 44)), patch.object(
                    upgrade_release, 'load_manifest', return_value={'version': '1.1', 'fedora_release': 44}), patch.object(
                    upgrade_release, 'run', side_effect=run), patch.object(
                    upgrade_release, 'write_atomic', side_effect=write), patch.object(
                    upgrade_release.Path, 'is_file', return_value=True), patch.object(
                    upgrade_release, 'REPO_FILE', root / 'infinityos.repo'), patch.object(
                    upgrade_release, 'MARKER', root / 'infinityos-release'), patch.object(
                    upgrade_release, 'OS_RELEASE', os_release):
                upgrade_release.main(['upgrader', '1.1', '44'])

            commands = [args for kind, args in events if kind == 'run']
            self.assertEqual(commands[4][0], 'snapper')
            self.assertIn('--downloadonly', commands[5])
            self.assertEqual(commands[6][-1], 'distro-sync')
            self.assertEqual(events[7], ('write', 'infinityos.repo'))
            self.assertEqual(events[-1], ('write', 'infinityos-release'))
            self.assertEqual((root / 'infinityos-release').read_text(), '1.1\n')
            self.assertIn('INFINITYOS_VERSION_ID=1.1', os_release.read_text())

    def test_release_helper_never_marks_a_failed_package_transaction(self):
        from subprocess import CalledProcessError
        outputs = ['btrfs\n', '', '', 'aarch64\n', '8\n', '']

        def run(args, **_kwargs):
            if args[-1] == 'distro-sync':
                raise CalledProcessError(1, args)
            return type('R', (), {'stdout': outputs.pop(0)})()

        with patch.object(upgrade_release.os, 'geteuid', return_value=0), patch.object(
                upgrade_release, 'installed_version', return_value=('1.0', 44)), patch.object(
                upgrade_release, 'load_manifest', return_value={'version': '1.1', 'fedora_release': 44}), patch.object(
                upgrade_release, 'run', side_effect=run), patch.object(
                upgrade_release, 'write_atomic') as write, patch.object(
                upgrade_release.Path, 'is_file', return_value=True):
            with self.assertRaises(CalledProcessError):
                upgrade_release.main(['upgrader', '1.1', '44'])
            write.assert_not_called()

    def test_installation_only_runs_for_sources_with_updates(self):
        commands = updater.install_commands([{'kind': 'RPM'}, {'kind': 'Flatpak user'},
                                             {'kind': 'Firmware'}])
        self.assertEqual(commands[0][1], ['pkexec', '/usr/libexec/infinityos-upgrade-system'])
        self.assertEqual(commands[1][1][:3], ['flatpak', 'update', '--user'])
        self.assertEqual(commands[2][1], ['pkexec', 'fwupdmgr', 'update', '--assume-yes',
                                          '--no-reboot-check'])
        self.assertEqual(len(commands), 3)

    def test_firmware_updates_are_listed_and_no_device_is_not_an_error(self):
        result = type('Result', (), {'stdout': '{"Devices": [{"Name": "Laptop BIOS", '
                                               '"Releases": [{"Version": "1.2", '
                                               '"RemoteId": "lvfs"}]}]}'})()
        self.assertEqual(checker.firmware_updates(result), [
            {'kind': 'Firmware', 'name': 'Laptop BIOS', 'version': '1.2', 'source': 'lvfs'}])
        self.assertEqual(checker.firmware_updates(type('Result', (),
            {'stdout': '{"Devices": []}'})()), [])

    def test_unsupported_firmware_device_does_not_raise_tray_warning(self):
        outputs = [
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 2, 'stdout': '',
                                'stderr': 'No updatable devices'})(),
        ]
        with patch.object(checker, '_run', side_effect=outputs):
            state = checker.check_updates()
        self.assertEqual(state['errors'], [])

    def test_firmware_check_failure_is_visible(self):
        outputs = [
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
            type('Result', (), {'returncode': 1, 'stdout': '',
                                'stderr': 'fwupd service unavailable'})(),
        ]
        with patch.object(checker, '_run', side_effect=outputs):
            state = checker.check_updates()
        self.assertEqual(state['errors'], ['Firmware: fwupd service unavailable'])

    def test_progress_reports_download_and_install_counts(self):
        events = []
        parser = progress.UpdateProgress('System packages', lambda *event: events.append(event))
        parser.feed('Updating and loading repositories:')
        parser.feed('\x1b[1mDownloading 5/250\x1b[0m')
        parser.feed('Installing 38/250')
        self.assertEqual(events, [
            ('System packages', 'Checking repositories', None, None),
            ('System packages', 'Downloading', 5, 250),
            ('System packages', 'Installing', 38, 250)])

    def test_progress_reports_snapshot_number_before_download(self):
        events = []
        parser = progress.UpdateProgress('System packages', lambda *event: events.append(event))
        parser.feed('Infinity OS root snapshot #17 created.')
        parser.feed('Downloading 1/2')
        self.assertEqual(events, [
            ('System packages', 'Root snapshot #17 created', None, None),
            ('System packages', 'Downloading', 1, 2)])

    def test_privileged_upgrade_creates_snapshot_before_dnf(self):
        script = (SOURCE.parents[2] / 'libexec/infinityos-upgrade-system').read_text()
        self.assertLess(script.index('number=$(snapper'), script.index('exec dnf'))
        self.assertIn('RPM upgrade stopped: could not create', script)

    def test_update_command_streams_carriage_return_progress(self):
        events = []
        command = [sys.executable, '-u', '-c',
                   'import sys; sys.stdout.write("Downloading 1/2\\rInstalling 2/2\\n")']
        result = progress.run_update_command('System packages', command,
                                             lambda *event: events.append(event))
        self.assertEqual(result.returncode, 0)
        self.assertIn(('System packages', 'Downloading', 1, 2), events)
        self.assertIn(('System packages', 'Installing', 2, 2), events)


if __name__ == '__main__':
    unittest.main()
