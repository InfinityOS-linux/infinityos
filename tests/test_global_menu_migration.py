"""Preserve existing GNOME extensions when enabling Global Menu."""

import runpy
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-enable-global-menu"


class GlobalMenuMigrationTests(unittest.TestCase):
    def test_append_once_without_changing_existing_extensions(self):
        module = runpy.run_path(str(SCRIPT))
        update = module["with_global_menu"]
        current = ["ghostty@infinityos.org", "wack-shell@rinzler69-wastaken.github.com"]
        expected = [*current, module["UUID"]]
        self.assertEqual(update(current), expected)
        self.assertEqual(update(expected), expected)


if __name__ == "__main__":
    unittest.main()
