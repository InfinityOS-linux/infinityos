import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
repair = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-tint-system-icons'))['repair_recoloured_glyphs']

class IconContrastUpgradeTests(unittest.TestCase):
    def test_repairs_white_overrides_recoloured_by_an_older_rpm(self):
        svg = ('<svg><path style="fill:#dbc7ff"/>'
               '<path style="fill:#443964;fill:#dbc7ff;opacity:1;fill-opacity:1;stroke-opacity:1"/>'
               '<path style="fill:#443456;opacity:1;fill-opacity:1;stroke-opacity:1"/></svg>')
        result = repair(svg)
        self.assertIn('style="fill:#dbc7ff"', result)
        self.assertIn('fill:#443964;fill:#ffffff;', result)
        self.assertIn('fill:#443456;opacity:1;', result)
        self.assertEqual(repair(result), result)
