"""Keep Infinity OS settings overlays compatible with GNOME Control Center 51."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


OVERLAYS = Path(__file__).resolve().parents[1] / "root/usr/share/infinityos/settings-overlays"


class Gnome51OverlayTests(unittest.TestCase):
    def test_about_page_retains_new_template_bindings(self):
        root = ET.parse(OVERLAYS / "system/about/cc-about-page.ui").getroot()
        ids = {node.get("id") for node in root.iter("object")}
        self.assertTrue({"toast_overlay", "gnome_version_row", "os_name_row",
                         "os_build_row", "os_logo"} <= ids)
        self.assertNotIn("Support GNOME", [node.text for node in root.iter("property")])

    def test_background_and_window_keep_infinity_defaults(self):
        background = ET.parse(OVERLAYS / "background/cc-background-panel.ui").getroot()
        self.assertEqual(background.find(".//object[@id='default_label']/property[@name='label']").text,
                         "_Light")
        self.assertEqual(background.find(".//object[@id='accent_box']/property[@name='visible']").text,
                         "false")
        window = ET.parse(OVERLAYS / "gtk/cc-window.ui").getroot()
        self.assertIsNone(window.find("./menu[@id='primary_menu']"))
        self.assertIsNotNone(window.find(".//object[@id='search_button']"))


if __name__ == "__main__":
    unittest.main()
