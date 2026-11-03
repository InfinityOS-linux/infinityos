import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "root/usr/libexec/infinityos-tint-system-icons"


class SystemIconThemeTests(unittest.TestCase):
    def test_dock_folder_icons_have_no_tile_behind_the_folder(self):
        icons = ROOT / "root/usr/share/infinityos/folder-icons"
        for name in ("folder-download", "folder-documents"):
            self.assertEqual(
                (icons / f"{name}-dock.svg").read_text(),
                (icons / f"{name}.svg").read_text(),
            )
        self.assertNotIn('id="tile"', (icons / "drive-dock.svg").read_text())

    def test_file_symbols_are_white_without_erasing_cutouts_or_captions(self):
        available = subprocess.run([sys.executable, "-c",
            "import gi; gi.require_version('Rsvg', '2.0'); from gi.repository import Rsvg"],
            capture_output=True).returncode == 0
        if not available:
            self.skipTest("librsvg introspection is required for SVG layer geometry")
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "mimetypes").mkdir()
            path = theme / "mimetypes/archive.svg"
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                '<defs><linearGradient id="tile"><stop stop-color="#222222"/>'
                '<stop offset="1" stop-color="#777777"/></linearGradient></defs>'
                '<rect x="6" y="2" width="52" height="60" fill="url(#tile)"/>'
                '<rect id="glyph" x="20" y="16" width="24" height="26" fill="#333333"/>'
                '<rect id="detail" x="30" y="18" width="4" height="20" fill="#ffffff"/>'
                '<rect id="gradient-detail" x="24" y="20" width="3" height="12" fill="url(#tile)"/>'
                '<rect id="caption" x="24" y="52" width="16" height="4" fill="#ffffff"/>'
                '<g id="faint-group" opacity=".2"><rect id="faint" x="9" y="16" width="5" height="12" fill="url(#tile)" fill-opacity=".3"/></g>'
                '</svg>')
            subprocess.run([sys.executable, str(SCRIPT), str(theme)], check=True)
            first = path.read_text()
            import xml.etree.ElementTree as ET
            tree = ET.fromstring(first)
            nodes = {node.get("id"): node for node in tree.iter() if node.get("id")}
            self.assertIn("fill:#ffffff", nodes["glyph"].get("style"))
            self.assertIn("fill:#443456", nodes["detail"].get("style"))
            self.assertIn("fill:#443456", nodes["gradient-detail"].get("style"))
            self.assertIn("fill:#ffffff", nodes["caption"].get("style"))
            self.assertIn("fill:#ffffff", nodes["faint"].get("style"))
            self.assertIn("fill-opacity:1", nodes["faint"].get("style"))
            self.assertIn("opacity:1", nodes["faint-group"].get("style"))
            self.assertIn('fill="url(#tile)"', first)
            subprocess.run([sys.executable, str(SCRIPT), str(theme)], check=True)
            self.assertEqual(first, path.read_text())

    def test_tint_is_idempotent_and_keeps_apps_and_transparency(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            for section in ("places", "actions", "mimetypes", "apps"):
                (theme / section).mkdir()
            (theme / "places/scalable").mkdir()
            original = '<svg><path fill="#0088ff"/><path style="stroke:rgb(255, 255, 255);fill:none"/></svg>'
            (theme / "places/user-documents.svg").write_text(original)
            (theme / "places/folder.svg").write_text(original)
            (theme / "actions/add.svg").symlink_to("../places/user-documents.svg")
            (theme / "apps/firefox.svg").write_text(original)
            (theme / "places/scalable/user-trash.svg").write_text('<svg><path fill="#0088ff"/></svg>')
            (theme / "mimetypes/application-msexcel.svg").write_text('<svg><path fill="#40bf4f"/></svg>')
            for _ in range(2):
                subprocess.run([sys.executable, str(SCRIPT), str(theme)], check=True)
                result = (theme / "places/user-documents.svg").read_text()
                if _ == 0:
                    first = result
            self.assertEqual(result, first)
            self.assertNotIn("#0088ff", result)
            self.assertIn("fill:none", result)
            self.assertIn("<svg><path", result)
            self.assertEqual((theme / "apps/firefox.svg").read_text(), original)
            self.assertEqual((theme / "places/folder.svg").read_text(), original)
            self.assertTrue((theme / "actions/add.svg").is_symlink())
            self.assertEqual((theme / "places/scalable/user-trash.svg").read_text().count('id="infinity-trash-detail"'), 1)
            self.assertIn('fill="#dbc7ff"', (theme / "mimetypes/application-msexcel.svg").read_text())


if __name__ == "__main__":
    unittest.main()
