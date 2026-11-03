import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "root/usr/libexec/infinityos-tint-system-icons"


class SystemIconThemeTests(unittest.TestCase):
    def test_tint_is_idempotent_and_keeps_apps_and_transparency(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            for section in ("places", "actions", "apps"):
                (theme / section).mkdir()
            original = '<svg><path fill="#0088ff"/><path style="stroke:rgb(255, 255, 255);fill:none"/></svg>'
            (theme / "places/folder.svg").write_text(original)
            (theme / "actions/add.svg").symlink_to("../places/folder.svg")
            (theme / "apps/firefox.svg").write_text(original)
            for _ in range(2):
                subprocess.run([sys.executable, str(SCRIPT), str(theme)], check=True)
                result = (theme / "places/folder.svg").read_text()
                if _ == 0:
                    first = result
            self.assertEqual(result, first)
            self.assertNotIn("#0088ff", result)
            self.assertIn("fill:none", result)
            self.assertIn("<svg><path", result)
            self.assertEqual((theme / "apps/firefox.svg").read_text(), original)
            self.assertTrue((theme / "actions/add.svg").is_symlink())


if __name__ == "__main__":
    unittest.main()
