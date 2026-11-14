"""Desktop and TV Steam use the same launcher without losing first-run setup."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'root/usr/libexec/infinityos-steam'
DESKTOP = ROOT / 'packages/infinity-setup/steam-desktop.desktop'


class SteamLauncherTests(unittest.TestCase):
    def test_installed_runtime_bypasses_failing_handoff_and_forwards_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            runtime = home / '.local/share/Steam/steamrt64/pv-runtime/steam-runtime-steamrt/run'
            client = home / '.local/share/Steam/steamrt64/steam'
            runtime.parent.mkdir(parents=True)
            runtime.write_text('#!/bin/sh\nprintf "%s\\n%s\\n%s\\n" "$PWD" "$STEAM_RUNTIME_RECURSION_GUARD" "$*" > "$STEAM_TEST_LOG"\n')
            runtime.chmod(0o755)
            client.write_text('#!/bin/sh\n')
            client.chmod(0o755)
            log = home / 'launch.log'
            env = dict(os.environ, HOME=str(home), STEAM_TEST_LOG=str(log))
            subprocess.run(['bash', str(LAUNCHER), '-gamepadui', 'steam://open/games'], env=env, check=True)
            self.assertEqual(log.read_text().splitlines(), [
                str(home / '.local/share/Steam'), '1',
                f'-- {client} -gamepadui steam://open/games',
            ])

    def test_first_run_falls_back_to_rpm_steam_updater(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            executable = home / 'steam'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$STEAM_TEST_LOG"\n')
            executable.chmod(0o755)
            log = home / 'launch.log'
            env = dict(os.environ, HOME=str(home), PATH=f'{home}:{os.environ["PATH"]}',
                       STEAM_TEST_LOG=str(log))
            subprocess.run(['bash', str(LAUNCHER), 'steam://open/games'], env=env, check=True)
            self.assertEqual(log.read_text(), 'steam://open/games\n')

    def test_desktop_menu_entry_uses_shared_launcher_only_when_rpm_exists(self):
        desktop = DESKTOP.read_text()
        self.assertIn('Exec=/usr/libexec/infinityos-steam %U\n', desktop)
        self.assertIn('TryExec=/usr/bin/steam\n', desktop)
        self.assertIn('Name=Steam (Desktop)\n', desktop)


if __name__ == '__main__':
    unittest.main()
