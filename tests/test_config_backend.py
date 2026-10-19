"""Infinity Config percentage controls preserve the Infinity OS defaults."""

import importlib.util
import unittest
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] /
          "packages/infinity-config/root/usr/share/infinityos/config_backend.py")
spec = importlib.util.spec_from_file_location("config_backend", SOURCE)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ConfigBackendTests(unittest.TestCase):
    def test_slider_endpoints_and_center(self):
        self.assertEqual([config.slider_to_percent(x) for x in (0, 50, 100)],
                         [20, 100, 200])
        self.assertEqual([config.percent_to_slider(x) for x in (20, 100, 200)],
                         [0, 50, 100])

    def test_defaults_are_100_percent(self):
        self.assertEqual(config.dock_percent(config.DOCK_DEFAULT), 100)
        self.assertEqual(config.cursor_percent(config.CURSOR_DEFAULT), 100)
        self.assertAlmostEqual(config.dock_size(100), config.DOCK_DEFAULT)
        self.assertEqual(config.cursor_size(100), config.CURSOR_DEFAULT)

    def test_limits(self):
        self.assertAlmostEqual(config.dock_size(20), config.DOCK_DEFAULT * .2)
        self.assertAlmostEqual(config.dock_size(200), config.DOCK_DEFAULT * 2)
        self.assertEqual(config.cursor_size(200), 48)
        self.assertEqual(config.cursor_percent(config.cursor_size(20)), 20)


if __name__ == "__main__":
    unittest.main()
