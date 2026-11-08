"""The build-time patch must fail safely when Anaconda changes its layout."""
import runpy
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
patch = runpy.run_path(str(REPO / 'root/usr/libexec/infinityos-patch-welcome'))['patch']


class WelcomeAnimationTests(unittest.TestCase):
    def test_patch_is_idempotent_and_keeps_welcome_actions(self):
        source = "iconName: 'infinityos-welcome'\n        this.content.set_child(statusPage);\ninstallButton.connect();"
        result = patch(source)
        self.assertEqual(patch(result), result)
        self.assertIn('installButton.connect();', result)
        self.assertIn('return frame < 89;', result)
        self.assertIn('Gdk.Texture.new_from_filename', result)

    def test_unknown_layout_fails_instead_of_silently_losing_animation(self):
        with self.assertRaises(ValueError):
            patch('new upstream layout')
