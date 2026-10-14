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


class UpdaterTests(unittest.TestCase):
    def test_checks_each_source_and_saves_state(self):
        outputs = [
            type('Result', (), {'returncode': 0, 'stdout': 'firefox|158.0|updates\n', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': 'org.gnome.Evince\t51.0\tflathub\n', 'stderr': ''})(),
            type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})(),
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

    def test_rpm_check_does_not_read_system_dnf_state(self):
        calls = []

        def run(args):
            calls.append(args)
            if args[0] == 'dnf' and not any(arg.startswith('--setopt=system_state_dir=') for arg in args):
                return type('Result', (), {'returncode': 1, 'stdout': '',
                                           'stderr': 'Could not open packages.toml'})()
            return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

        with patch.object(checker, '_run', side_effect=run):
            state = checker.check_updates()

        self.assertEqual(state['errors'], [])
        self.assertTrue(any(arg.startswith('--setopt=system_state_dir=') for arg in calls[0]))

    def test_installation_only_runs_for_sources_with_updates(self):
        commands = updater.install_commands([{'kind': 'RPM'}, {'kind': 'Flatpak user'}])
        self.assertEqual(commands[0][1][:3], ['pkexec', 'dnf', '-y'])
        self.assertEqual(commands[1][1][:3], ['flatpak', 'update', '--user'])
        self.assertEqual(len(commands), 2)


if __name__ == '__main__':
    unittest.main()
