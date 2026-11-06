"""The live installer signals GNOME only while its process is alive."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-liveinst"


class InstallerDimTest(unittest.TestCase):
    def test_marker_is_removed_when_installer_exits_with_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            runtime = root / "runtime"
            bin_dir.mkdir()
            runtime.mkdir()
            (bin_dir / "gnome-extensions").write_text("#!/bin/sh\nexit 0\n")
            (bin_dir / "liveinst").write_text(
                '#!/bin/sh\nls "$XDG_RUNTIME_DIR"/infinityos-liveinst-dim-* >/dev/null\nexit 42\n')
            for name in ("gnome-extensions", "liveinst"):
                (bin_dir / name).chmod(0o755)
            env = os.environ.copy()
            env.update(PATH=f"{bin_dir}:{env['PATH']}", XDG_RUNTIME_DIR=str(runtime))
            result = subprocess.run(["bash", str(SCRIPT)], env=env, check=False)
            self.assertEqual(result.returncode, 42)
            self.assertEqual(list(runtime.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
