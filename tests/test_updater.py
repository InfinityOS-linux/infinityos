import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('checker')
updater = load('updater')
progress = load('progress')


class UpdaterTests(unittest.TestCase):
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

    def test_installation_only_runs_for_sources_with_updates(self):
        commands = updater.install_commands([{'kind': 'RPM'}, {'kind': 'Flatpak user'},
                                             {'kind': 'Firmware'}])
        self.assertEqual(commands[0][1], ['pkexec', 'dnf', '-y', 'upgrade', '--refresh'])
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
