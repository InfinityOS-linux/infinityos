"""Keep the renamed application and its RPM upgrade path consistent."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages/infinity-setup"


class SetupIdentityTests(unittest.TestCase):
    def test_desktop_files_and_application_id_match(self):
        app = (PACKAGE / "root/usr/share/infinityos/launcher.py").read_text()
        desktop = (PACKAGE / "root/usr/share/infinityos/launcher.desktop").read_text()
        autostart = (PACKAGE / "root/usr/share/infinityos/launcher-autostart.desktop").read_text()
        self.assertIn('application_id="org.infinityos.Setup"', app)
        self.assertIn('title="InfinitySetup"', app)
        self.assertIn("Name=InfinitySetup\n", desktop)
        self.assertIn("Exec=infinity-setup\n", desktop)
        self.assertIn("Icon=infinity-setup\n", desktop)
        self.assertIn("Exec=infinity-setup --first-run\n", autostart)
        self.assertTrue((PACKAGE / "root/usr/share/infinityos/launcher-icons/infinity-setup.svg").is_file())
        self.assertNotIn("NEXT_START", app)
        self.assertNotIn("Run at next startup", app)
        self.assertIn("MARKER.exists()", app)
        self.assertIn("MARKER.touch()", app)
        self.assertNotIn("self.applied", app)

    def test_upgrade_keeps_first_run_state_and_old_favorites(self):
        app = (PACKAGE / "root/usr/share/infinityos/launcher.py").read_text()
        spec = (PACKAGE / "infinity-setup.spec").read_text()
        builder = (ROOT / "packages/build-rpm.sh").read_text()
        alias = (PACKAGE / "legacy.desktop").read_text()
        self.assertIn('".config/infinityos/launcher-complete"', app)
        self.assertIn("Obsoletes:      infinity-launcher < 1.0.1", spec)
        self.assertIn("Provides:       infinity-launcher", spec)
        for old_id in ("infinity-launcher.desktop", "org.infinityos.Launcher.desktop"):
            with self.subTest(old_id=old_id):
                self.assertIn(f"/usr/share/applications/{old_id}", spec)
                self.assertIn(f"/usr/share/applications/{old_id}", builder)
        self.assertIn("Name=InfinitySetup\n", alias)
        self.assertIn("Exec=infinity-setup\n", alias)
        self.assertIn("NoDisplay=true\n", alias)


if __name__ == "__main__":
    unittest.main()
