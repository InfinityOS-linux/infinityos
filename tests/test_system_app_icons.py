"""System launchers must resolve to the artwork shipped by their own RPM."""
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class SystemAppIconTests(unittest.TestCase):
    def test_desktop_icons_exist_in_package_sources(self):
        for package in ['infinity-config', 'infinity-terminal', 'infinity-updater']:
            root = ROOT / 'packages' / package / 'root'
            for desktop in (root / 'usr/share/applications').glob('*.desktop'):
                icon = next(line[5:] for line in desktop.read_text().splitlines() if line.startswith('Icon='))
                self.assertTrue(icon.startswith('/usr/share/icons/hicolor/512x512/apps/'), desktop)
                self.assertTrue((root / icon.lstrip('/')).is_file(), icon)
