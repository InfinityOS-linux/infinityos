import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]

class DesktopAdditionsTests(unittest.TestCase):
    def test_existing_account_drops_only_the_retired_system_lockscreen(self):
        funcs = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-enable-desktop-additions'))
        retired = funcs['RETIRED_LOCKSCREEN']
        settings = Mock()
        settings.get_strv.return_value = ['custom@test', retired, 'panel@test']
        gi = Mock()
        gi.Gio.Settings.new.return_value = settings
        with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules', {'gi.repository': gi}), \
                patch.dict('os.environ', {'XDG_STATE_HOME': directory, 'XDG_DATA_HOME': directory}):
            marker = Path(directory) / 'infinityos/desktop-additions-v1'
            marker.parent.mkdir()
            marker.touch()
            (marker.parent / 'media-controls-v1').touch()
            self.assertEqual(funcs['main'](), 0)
            settings.set_strv.assert_called_once_with('enabled-extensions', ['custom@test', 'panel@test'])
            gi.Gio.Settings.new.assert_called_once_with('org.gnome.shell')

            # A separately installed copy belongs to the user.
            (Path(directory) / 'gnome-shell/extensions' / retired).mkdir(parents=True)
            settings.set_strv.reset_mock()
            self.assertEqual(funcs['main'](), 0)
            settings.set_strv.assert_not_called()

    def test_media_migration_replaces_nowplay_once_and_retries_failed_write(self):
        funcs = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-enable-desktop-additions'))
        shell = Mock()
        shell.get_strv.side_effect = lambda key: enabled.copy() if key == 'enabled-extensions' else disabled.copy()
        shell.set_strv.return_value = False
        gi = Mock()
        gi.Gio.Settings.new.return_value = shell
        enabled = ['custom@test', funcs['RETIRED_MEDIA'], 'panel@test']
        disabled = []
        replacement = funcs['MEDIA_CONTROLS']

        with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules', {'gi.repository': gi}), \
                patch.dict('os.environ', {'XDG_STATE_HOME': directory, 'XDG_DATA_HOME': directory}):
            state = Path(directory) / 'infinityos'
            state.mkdir()
            (state / 'desktop-additions-v1').touch()
            marker = state / 'media-controls-v1'
            self.assertEqual(funcs['main'](), 1)
            self.assertFalse(marker.exists())

            shell.set_strv.reset_mock()
            shell.set_strv.return_value = True
            self.assertEqual(funcs['main'](), 0)
            shell.set_strv.assert_called_once_with('enabled-extensions', ['custom@test', 'panel@test', replacement])
            self.assertTrue(marker.exists())
            gi.Gio.Settings.new.assert_called_with('org.gnome.shell')

            # A later user choice to turn off the replacement stays in effect.
            enabled[:] = ['custom@test', 'panel@test']
            shell.set_strv.reset_mock()
            self.assertEqual(funcs['main'](), 0)
            shell.set_strv.assert_not_called()

            # A copy of Media Controls already disabled before upgrading stays disabled.
            marker.unlink()
            disabled.append(replacement)
            self.assertEqual(funcs['main'](), 0)
            shell.set_strv.assert_not_called()

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
        for uuid in ('media-controller@naimur', 'raccoonlauncher@shimafallah.github.io'):
            folder = ROOT / 'root/usr/share/gnome-shell/extensions' / uuid
            metadata = json.loads((folder / 'metadata.json').read_text())
            self.assertIn('51', metadata['shell-version'])
            self.assertTrue((folder / 'LICENSE').is_file())
            self.assertTrue((folder / 'schemas' / (metadata['settings-schema'] + '.gschema.xml')).is_file())
            self.assertIn('/usr/share/gnome-shell/extensions/' + uuid + '/', spec)
            self.assertIn(uuid, defaults)
        self.assertNotIn('nowplay@LalaloyXyz', defaults)
        self.assertFalse((ROOT / 'root/usr/share/gnome-shell/extensions/nowplay@LalaloyXyz').exists())
        self.assertIn('Requires:       gnome-rounded-blur', spec)
