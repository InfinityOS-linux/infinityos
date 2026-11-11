import configparser
from pathlib import Path
import runpy
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class BinIdentityTests(unittest.TestCase):
    def test_names_cover_desktop_languages_and_packaged_launcher(self):
        source = ROOT / 'root/usr/share/infinityos/bin.desktop'
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str
        config.read(source)
        names = config['Desktop Entry']
        self.assertEqual(names['Name'], 'Bin')
        self.assertEqual(names['Name[pl]'], 'Kosz')
        locales = ROOT / 'root/usr/share/gnome-shell/extensions/ding@rastersoft.com/locale'
        for locale in locales.iterdir():
            self.assertTrue(names.get(f'Name[{locale.name}]'), locale.name)
        self.assertIn('infinityos/bin.desktop', (ROOT / 'packages/build-rpm.sh').read_text())
        self.assertIn('/usr/share/infinityos/bin.desktop', (ROOT / 'packages/infinityos-shell-extensions/infinityos-shell-extensions.spec').read_text())

    def test_both_bin_states_have_the_same_body_and_distinct_contents(self):
        icon = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-tint-system-icons'))['trash_icon']
        empty, full = ET.fromstring(icon(False)), ET.fromstring(icon(True))
        paper = next(node for node in full if node.get('id') == 'infinity-trash-paper')
        full.remove(paper)
        self.assertEqual(ET.tostring(empty), ET.tostring(full))
        self.assertIn('#221b30', icon(False))
        self.assertIn('#f8f5ff', icon(False))
