"""Exercise target kernel recovery without accessing the host boot files."""

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-liveinstall-boot-setup"


class LiveInstallKernelTests(unittest.TestCase):
    def run_kernel_setup(self, root):
        source = SCRIPT.read_text().split("source_entry=\n", 1)[1].split(
            '[[ -s $initrd ]] || dracut', 1)[0]
        source = "set -eu\nsource_entry=\n" + source
        for path in ("/boot", "/usr/lib/modules"):
            source = source.replace(path, str(root) + path)
        return subprocess.run(["bash", "-c", source], capture_output=True, text=True)

    def test_recovers_matching_kernel_with_or_without_boot_entry(self):
        for entry in (False, True):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "boot/loader/entries").mkdir(parents=True)
                for version in ("6.18.1", "6.18.2"):
                    kernel = root / f"usr/lib/modules/{version}/vmlinuz"
                    kernel.parent.mkdir(parents=True)
                    kernel.write_text(version)
                if entry:
                    (root / "boot/loader/entries/os.conf").write_text("version 6.18.1\n")
                result = self.run_kernel_setup(root)
                self.assertEqual(result.returncode, 0, result.stderr)
                version = "6.18.1" if entry else "6.18.2"
                self.assertEqual((root / f"boot/vmlinuz-{version}").read_text(), version)

    def test_missing_matching_kernel_fails_without_using_another_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "boot/loader/entries").mkdir(parents=True)
            (root / "boot/loader/entries/os.conf").write_text("version 6.18.1\n")
            kernel = root / "usr/lib/modules/6.18.2/vmlinuz"
            kernel.parent.mkdir(parents=True)
            kernel.write_text("different kernel")
            result = self.run_kernel_setup(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Kernel is missing", result.stderr)
            self.assertFalse((root / "boot/vmlinuz-6.18.1").exists())


if __name__ == "__main__":
    unittest.main()
