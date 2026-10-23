import subprocess
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "root/usr/libexec/infinityos-refind-config"
THEME = ROOT / "root/usr/share/infinityos/refind-theme/theme.conf"


class RefindConfigTests(unittest.TestCase):
    def test_shared_theme_hides_optional_firmware_tool_row(self):
        theme = THEME.read_text()
        self.assertEqual([line for line in theme.splitlines() if line.startswith("showtools")],
                         ["showtools"])
        self.assertIn("include infinity-theme/theme.conf", CONFIG.read_text())
        self.assertIn("include infinity-theme/theme.conf",
                      (ROOT / "scripts/finalize-infinity-iso").read_text())

    def test_installed_menu_has_single_tool_set_and_diagnostic_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            esp = root / "esp"
            (esp / "EFI/refind").mkdir(parents=True)
            (esp / "os").mkdir()
            (esp / "os/vmlinuz-6.0.test").write_bytes(b"kernel")
            (esp / "os/initramfs-6.0.test.img").write_bytes(b"initrd")
            cmdline = root / "cmdline"
            cmdline.write_text("root=UUID=test rootflags=subvol=root rw rhgb quiet\n")
            subprocess.run(["bash", str(CONFIG), str(esp), str(cmdline),
                            str(root / "no-backups-marker")], check=True)
            menu = (esp / "EFI/refind/refind.conf").read_text()
            self.assertEqual(menu, (esp / "EFI/BOOT/refind.conf").read_text())
            self.assertNotIn("showtools", menu)
            system, recovery = menu.split('menuentry "Backups (Btrfs)"', 1)
            self.assertIn("loglevel=3", system)
            self.assertNotIn("loglevel=3", recovery)
            self.assertIn("plymouth.enable=0", recovery)
            self.assertIn("small_icon_size 32", THEME.read_text())
            self.assertIn("big_icon_size 256", THEME.read_text())
            self.assertIn("use_graphics_for linux", THEME.read_text())

    def test_infinity_boot_icons_match_their_native_menu_size(self):
        icons = ROOT / "root/usr/share/infinityos/refind-theme/icons"
        spec = (ROOT / "packages/infinity-setup/infinity-setup.spec").read_text()
        staging = (ROOT / "packages/build-rpm.sh").read_text()
        self.assertIn("/usr/share/infinityos/refind-theme/theme.conf", spec)
        self.assertIn("os_infinityos*.png", staging)
        self.assertIn("%posttrans", spec)
        self.assertIn("/boot/efi/EFI/refind/infinity-theme", spec)
        self.assertIn("/boot/efi/EFI/BOOT/infinity-theme", spec)
        for suffix in ("", "_check", "_live", "_recovery", "_safe", "_esde", "_steam"):
            with self.subTest(suffix=suffix):
                self.assertIn(f"/usr/share/infinityos/refind-theme/icons/os_infinityos{suffix}.png", spec)
                data = (icons / f"os_infinityos{suffix}.png").read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), (256, 256))
                self.assertEqual(data[25], 6)

    def test_tv_entries_only_exist_for_enabled_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            esp = root / "esp"
            icons = esp / "EFI/refind/infinity-theme/icons"
            icons.mkdir(parents=True)
            (esp / "os").mkdir()
            (esp / "os/vmlinuz-6.0.test").write_bytes(b"kernel")
            (esp / "os/initramfs-6.0.test.img").write_bytes(b"initrd")
            for mode in ("esde", "steam"):
                (icons / f"os_infinityos_{mode}.png").write_bytes(b"icon")
            modes = root / "tv-modes"
            modes.mkdir()
            (modes / "esde").write_text("1000\n")
            cmdline = root / "cmdline"
            cmdline.write_text("root=UUID=test rw quiet\n")
            command = ["bash", str(CONFIG), str(esp), str(cmdline),
                       str(root / "no-backups-marker"), str(modes)]
            subprocess.run(command, check=True)
            menu = (esp / "EFI/refind/refind.conf").read_text()
            self.assertIn('menuentry "EmulationStation"', menu)
            self.assertIn('systemd.unit=infinityos-tv@esde.target', menu)
            self.assertNotIn('menuentry "Steam Big Picture"', menu)
            (modes / "steam").write_text("1000\n")
            subprocess.run(command, check=True)
            menu = (esp / "EFI/refind/refind.conf").read_text()
            self.assertIn('systemd.unit=infinityos-tv@steam.target', menu)
            self.assertEqual(menu, (esp / "EFI/BOOT/refind.conf").read_text())
            (modes / "esde").unlink()
            subprocess.run(command, check=True)
            self.assertNotIn('menuentry "EmulationStation"',
                             (esp / "EFI/refind/refind.conf").read_text())


if __name__ == "__main__":
    unittest.main()
