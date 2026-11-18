import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'root/usr/libexec/infinityos-theme-sync'


class CursorMigrationTests(unittest.TestCase):
    def test_default_is_migrated_once_and_custom_themes_are_preserved(self):
        for current in ('Bibata-Modern-Ice', 'MyCustomTheme'):
            with self.subTest(theme=current), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                bin_dir = home / 'bin'
                bin_dir.mkdir()
                command = bin_dir / 'gsettings'
                command.write_text('''#!/bin/sh
case "$1:$3" in
  get:cursor-theme) printf "'%s'\\n" "$TEST_CURSOR_THEME" ;;
  get:color-scheme) echo "'prefer-dark'" ;;
  set:cursor-theme) echo "$4" >> "$XDG_STATE_HOME/cursor-changes" ;;
  monitor:*) exit 0 ;;
esac
''')
                command.chmod(0o755)
                env = {**os.environ, 'HOME': str(home), 'XDG_STATE_HOME': str(home),
                       'TEST_CURSOR_THEME': current, 'PATH': f'{bin_dir}:{os.environ["PATH"]}'}
                for _ in range(2):
                    subprocess.run(['bash', str(SCRIPT)], env=env, check=True, timeout=10)
                changed = home / 'cursor-changes'
                if current == 'Bibata-Modern-Ice':
                    self.assertEqual(changed.read_text().splitlines(), ['InfinityOS-Modern-Ice'])
                else:
                    self.assertFalse(changed.exists())
