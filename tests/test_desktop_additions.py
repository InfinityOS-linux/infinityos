import json
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DesktopAdditionsTests(unittest.TestCase):
    def test_migration_is_additive_and_does_not_replace_custom_shortcuts(self):
        funcs = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-enable-desktop-additions'))
        current = ['ghostty@infinityos.org']
        updated = funcs['with_extensions'](current)
        self.assertEqual(updated[0], current[0])
        self.assertEqual(funcs['with_extensions'](updated), updated)
        shortcuts = ['<Super>space', '<Alt>F2']
        self.assertEqual(funcs['without_launcher_conflict'](shortcuts), ['<Super><Alt>space', '<Alt>F2'])
        self.assertEqual(funcs['without_launcher_conflict'](['<Control>space']), ['<Control>space'])

    def test_both_extensions_are_bundled_and_packaged_with_schemas_and_licenses(self):
        spec = (ROOT / 'packages/infinityos-shell-extensions/infinityos-shell-extensions.spec').read_text()
        defaults = (ROOT / 'root/usr/share/infinityos/gnome-defaults').read_text()
        for uuid in ('nowplay@LalaloyXyz', 'raccoonlauncher@shimafallah.github.io'):
            folder = ROOT / 'root/usr/share/gnome-shell/extensions' / uuid
            metadata = json.loads((folder / 'metadata.json').read_text())
            self.assertIn('51', metadata['shell-version'])
            self.assertTrue((folder / 'LICENSE').is_file())
            self.assertTrue((folder / 'schemas' / (metadata['settings-schema'] + '.gschema.xml')).is_file())
            self.assertIn('/usr/share/gnome-shell/extensions/' + uuid + '/', spec)
            self.assertIn(uuid, defaults)
        self.assertIn('Requires:       gnome-rounded-blur', spec)
