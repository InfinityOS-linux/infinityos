import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-theme-sync"


class ThemeSyncTests(unittest.TestCase):
    def test_switches_orchis_variants_without_replacing_custom_gtk_css(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            state = home / "color-scheme"
            state.write_text("'prefer-dark'")
            gtk = home / ".config/gtk-4.0"
            gtk.mkdir(parents=True)
            custom_css = gtk / "gtk.css"
            custom_css.write_text("/* keep me */")
            (gtk / "assets").symlink_to("/usr/share/themes/Orchis-Purple-Dark-Compact/gtk-4.0/assets")
            (gtk / "gtk-dark.css").symlink_to("/usr/share/themes/Orchis-Purple-Dark-Compact/gtk-4.0/gtk-dark.css")
            gsettings = bin_dir / "gsettings"
            gsettings.write_text(
                '#!/bin/sh\n'
                'case "$1" in\n'
                '  get) cat "$HOME/color-scheme" ;;\n'
                '  set) echo "$2 $3 $4" >> "$HOME/changes" ;;\n'
                '  monitor) echo "\'default\'" > "$HOME/color-scheme"; echo changed ;;\n'
                'esac\n'
            )
            gsettings.chmod(0o755)
            subprocess.run(
                [str(SCRIPT)], check=True, timeout=10,
                env={**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}"},
            )
            changes = (home / "changes").read_text()
            self.assertIn("gtk-theme Orchis-Purple-Dark-Compact", changes)
            self.assertIn("gtk-theme Orchis-Purple-Light-Compact", changes)
            self.assertIn("name Orchis-Purple-Light-Compact", changes)
            self.assertEqual(custom_css.read_text(), "/* keep me */")
            self.assertFalse((gtk / "assets").is_symlink())
            self.assertFalse((gtk / "gtk-dark.css").is_symlink())


if __name__ == "__main__":
    unittest.main()
