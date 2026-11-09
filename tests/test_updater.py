import importlib.util
import hashlib
from importlib.machinery import SourceFileLoader
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE.parents[5] / 'infinity-setup/root/usr/share/infinityos'))


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
github_update = load('github_update')

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
        github = patch.object(checker, 'check_github_updates', return_value=([], []))
        github.start()
        self.addCleanup(github.stop)

    def test_check_reports_source_before_running_it(self):
        sources = []
        def run(args):
            expected = {'dnf': 'System packages', 'fwupdmgr': 'Device firmware'}
            if args[0] == 'flatpak':
                expected['flatpak'] = 'System Flatpaks' if '--system' in args else 'Your Flatpaks'
            self.assertEqual(sources[-1], expected[args[0]])
            return SimpleNamespace(returncode=0, stdout='{"Devices": []}', stderr='')
        with patch.object(checker, '_run', side_effect=run):
            checker.check_updates(sources.append)
        self.assertEqual(sources, ['System packages', 'InfinitySetup apps',
            'System Flatpaks', 'Your Flatpaks', 'Device firmware', 'Infinity OS releases'])
        with patch.object(i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            self.assertEqual(i18n.tr('Checking: {source}').format(
                source=i18n.tr('System packages')), 'Sprawdzanie: Pakiety systemowe')

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

    def test_extension_rpms_use_system_updates_and_require_session_restart(self):
        for package in ('infinityos-shell-extensions', 'infinity-terminal', 'infinity-updater'):
            updates = [{'kind': 'RPM', 'name': package, 'version': '1', 'source': 'infinityos'}]
            self.assertTrue(updater.includes_extension_update(updates))
            self.assertEqual(updater.install_commands(updates), [
                ('System packages', ['pkexec', '/usr/libexec/infinityos-upgrade-system'])])
        self.assertFalse(updater.includes_extension_update([
            {'kind': 'Flatpak user', 'name': 'infinity-terminal'}]))
        with patch.object(i18n.locale, 'getlocale', return_value=('pl_PL', 'UTF-8')):
            self.assertEqual(i18n.tr('Sign out and back in to use updated extensions.'),
                             'Wyloguj się i zaloguj ponownie, aby korzystać ze zaktualizowanych rozszerzeń.')

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
            self.assertEqual(i18n.tr('RPM updates waiting for compatible dependencies: {packages}').format(
                packages='libheif'), 'Aktualizacje RPM czekają na zgodne zależności: libheif')
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
            transaction = root / 'transaction.json'
            transaction.write_text('transaction')
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
                    upgrade_release, 'OS_RELEASE', os_release), patch.object(
                    upgrade_release, 'PENDING', root / 'pending.json'), patch.object(
                    upgrade_release, 'TRANSACTION', transaction):
                upgrade_release.main(['upgrader', '1.1', '44'])
                self.assertFalse((root / 'infinityos-release').exists())
                import hashlib
                digest = hashlib.sha256(transaction.read_bytes()).hexdigest()
                with patch.object(upgrade_release.Path, 'read_text', side_effect=[
                        (root / 'pending.json').read_text(), digest, os_release.read_text()]):
                    upgrade_release.finish()

            commands = [args for kind, args in events if kind == 'run']
            self.assertIn('--offline', commands[4])
            self.assertEqual(commands[5][-2:], ['offline', 'reboot'])
            self.assertEqual(events[-1], ('write', 'infinityos-release'))
            self.assertEqual((root / 'infinityos-release').read_text(), '1.1\n')
            self.assertIn('INFINITYOS_VERSION_ID=1.1', os_release.read_text())

    def test_release_helper_never_marks_a_failed_package_transaction(self):
        from subprocess import CalledProcessError
        outputs = ['btrfs\n', '', '', 'aarch64\n', '8\n', '']

        def run(args, **_kwargs):
            if 'distro-sync' in args:
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
        self.assertEqual(commands[2][1], ['pkexec', '/usr/bin/fwupdmgr', 'update', '--assume-yes',
                                          '--no-reboot-check'])
        self.assertEqual(len(commands), 3)

    def test_pending_rpm_updates_are_not_reported_as_installed(self):
        before = [{'kind': 'RPM', 'name': 'libheif'},
                  {'kind': 'RPM', 'name': 'libheif-ffmpeg'},
                  {'kind': 'Flatpak user', 'name': 'org.example.App'}]
        after = [{'kind': 'RPM', 'name': 'libheif-ffmpeg'},
                 {'kind': 'Flatpak user', 'name': 'org.example.App'}]
        self.assertEqual(updater.pending_rpm_names(before, after), ['libheif-ffmpeg'])
        self.assertEqual(updater.pending_rpm_names(before, []), [])

    def test_installed_setup_rpm_appears_and_uses_verified_update_path(self):
        app = next(app for app in github_update.APPS if app.name == 'PhotoCraft')
        with patch.object(github_update, '_installed', return_value={'photocraft': ('0.17.0', '1')}), \
             patch.object(github_update, 'latest_rpm_asset', return_value=({'tag_name': 'v0.18.0'}, {})), \
             patch.object(github_update, '_newer', return_value=True):
            updates, errors = github_update.check_github_updates()
        self.assertEqual(errors, [])
        self.assertEqual(updates, [{'kind': 'InfinitySetup RPM', 'name': 'PhotoCraft',
                                    'version': 'v0.18.0', 'source': app.source}])
        self.assertEqual(updater.install_commands(updates), [
            ('PhotoCraft', ['python3', '/usr/share/infinityos/updater/github_update.py',
                            app.source])])

    def test_new_craft_rpms_are_tracked_by_infinity_updater(self):
        installed = {name: ('0.1.0', '1') for name in
                     ('craft-anything', 'materialcraft', 'solidcraft', 'texturecraft')}
        with patch.object(github_update, '_installed', return_value=installed), \
             patch.object(github_update, 'latest_rpm_asset',
                          return_value=({'tag_name': 'v0.2.0'}, {})), \
             patch.object(github_update, '_newer', return_value=True):
            updates, errors = github_update.check_github_updates()
        self.assertEqual(errors, [])
        self.assertEqual({item['name'] for item in updates},
                         {'Craft Anything', 'MaterialCraft', 'SolidCraft', 'TextureCraft'})
        self.assertEqual(len(updater.install_commands(updates)), 4)

    def test_setup_rpm_version_comparison_uses_rpm_ordering(self):
        rpm = SimpleNamespace(labelCompare=Mock(return_value=1))
        with patch.dict(sys.modules, {'rpm': rpm}):
            self.assertTrue(github_update._newer('v0.18.0', ('0.17.0', '1')))
            with self.assertRaisesRegex(ValueError, 'Unrecognized release version'):
                github_update._newer('release-latest', ('0.17.0', '1'))
        rpm.labelCompare.assert_called_once_with(('0', '0.18.0', '0'),
                                                  ('0', '0.17.0', '1'))

    def test_setup_rpm_update_rejects_wrong_downloaded_package(self):
        def download(_app, _arch, directory):
            path = Path(directory) / 'photocraft.rpm'
            path.write_bytes(b'rpm')
            return path

        with patch.object(github_update, '_installed', return_value={'photocraft': ('0.17.0', '1')}), \
             patch.object(github_update, '_latest_rpm', side_effect=download), \
             patch.object(github_update.subprocess, 'run', return_value=SimpleNamespace(
                 stdout='different|0.18.0|1|aarch64')) as run, \
             patch.object(github_update.os, 'uname', return_value=SimpleNamespace(machine='aarch64')):
            with self.assertRaisesRegex(ValueError, 'identity or architecture'):
                github_update.install_github_update('storytold/photocraft')
        self.assertEqual(run.call_count, 1)

    def test_setup_rpm_update_installs_newer_matching_package(self):
        def download(_app, _arch, directory):
            path = Path(directory) / 'photocraft.rpm'
            path.write_bytes(b'rpm')
            return path

        with patch.object(github_update, '_installed', return_value={'photocraft': ('0.17.0', '1')}), \
             patch.object(github_update, '_latest_rpm', side_effect=download), \
             patch.object(github_update, '_newer', return_value=True), \
             patch.object(github_update.subprocess, 'run', side_effect=[
                 SimpleNamespace(stdout='photocraft|0.18.0|1|aarch64'),
                 SimpleNamespace(returncode=0)]) as run, \
             patch.object(github_update.os, 'uname', return_value=SimpleNamespace(machine='aarch64')):
            github_update.install_github_update('storytold/photocraft')
        self.assertEqual(run.call_args.args[0][:3],
                         ['pkexec', '/usr/libexec/infinityos-upgrade-system', '--local-rpm'])

    def test_twindesk_appimage_update_is_found_and_installed_by_updater(self):
        app = next(app for app in github_update.APPS if app.name == 'TwinDesk')
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary, desktop = github_update.appimage_paths(app, home)
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'old appimage')
            desktop.parent.mkdir(parents=True)
            desktop.write_text('[Desktop Entry]\nName=TwinDesk\n')
            release = {'tag_name': 'v2.4.0'}
            asset = {'digest': 'sha256:' + hashlib.sha256(b'new appimage').hexdigest()}
            with patch.object(github_update, '_installed', return_value={}), \
                 patch.object(github_update, 'latest_appimage_asset',
                              return_value=(release, asset)), \
                 patch.object(github_update.os, 'uname',
                              return_value=SimpleNamespace(machine='x86_64')):
                updates, errors = github_update.check_github_updates(home)
                self.assertEqual(errors, [])
                self.assertEqual(updates, [{'kind': 'InfinitySetup AppImage',
                    'name': 'TwinDesk', 'version': 'v2.4.0', 'source': app.source}])
                self.assertEqual(updater.install_commands(updates), [
                    ('TwinDesk', ['python3', '/usr/share/infinityos/updater/github_update.py',
                                  app.source])])
                with patch.object(github_update, 'install') as install:
                    github_update.install_github_update(app.source, home)
                install.assert_called_once_with(app, home)

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

    def test_privileged_upgrade_prepares_offline_without_installing_live(self):
        script = (SOURCE.parents[2] / 'libexec/infinityos-upgrade-system').read_text()
        self.assertIn('dnf -y upgrade --offline', script)
        self.assertIn('DNF_SYSTEM_UPGRADE_NO_REBOOT=1', script)
        self.assertNotIn('snapper -c', script)
        self.assertNotIn('--allowerasing', script)

    def test_offline_failure_and_pending_state_are_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trigger = root / 'trigger'
            (root / 'offline-update-result.json').write_text('{"status":"failed","snapshot":"17"}')
            (root / 'offline-update.log').write_text('Transaction failed')
            result = checker.offline_status(root, trigger)
            self.assertEqual(result['snapshot'], '17')
            self.assertEqual(result['log'], 'Transaction failed')
            (root / 'offline-update.log').unlink()
            self.assertEqual(checker.offline_status(root, trigger)['status'], 'failed')
            trigger.symlink_to(root)
            self.assertEqual(checker.offline_status(root, trigger), {'pending': True})

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
