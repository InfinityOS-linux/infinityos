import hashlib
import os
import subprocess
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "root/usr/libexec/infinityos-refind-config"
INSTALL = ROOT / "root/usr/libexec/infinityos-refind-install"
THEME = ROOT / "root/usr/share/infinityos/refind-theme/theme.conf"


class RefindConfigTests(unittest.TestCase):
    def test_usb_gamepad_driver_and_default_controls(self):
        driver = ROOT / "root/usr/share/infinityos/efi-drivers/x64/UsbXbox360Dxe.efi"
        data = driver.read_bytes()
        self.assertEqual(data[:2], b"MZ")
        pe_offset = struct.unpack_from("<I", data, 0x3c)[0]
        self.assertEqual(data[pe_offset:pe_offset + 4], b"PE\0\0")
        self.assertEqual(struct.unpack_from("<H", data, pe_offset + 4)[0], 0x8664)
        self.assertEqual(struct.unpack_from("<H", data, pe_offset + 24 + 68)[0], 11)
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "9651e547d2842369e69776ce5fd51e5a2562268af91ca3ccfb80bf3f492d14a2",
        )
        config = (driver.parent / "config.ini").read_text()
        for mapping in ("ButtonDpadUp=KeyUp", "ButtonDpadDown=KeyDown",
                        "ButtonDpadLeft=KeyLeft", "ButtonDpadRight=KeyRight",
                        "LeftStickMode=Keys", "ButtonA=KeyEnter"):
            self.assertIn(mapping, config)

    def test_usb_gamepad_driver_is_installed_for_both_x64_boot_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            esp = root / "esp"
            (source / "usr/share/rEFInd/refind").mkdir(parents=True)
            (source / "usr/share/rEFInd/refind/refind_x64.efi").write_bytes(b"refind")
            theme = source / "usr/share/infinityos/refind-theme"
            (theme / "icons").mkdir(parents=True)
            for name in ("", "_recovery", "_esde", "_steam"):
                (theme / "icons" / f"os_infinityos{name}.png").write_bytes(b"icon")
            (theme / "theme.conf").write_text("big_icon_size 128\n")
            driver = source / "usr/share/infinityos/efi-drivers/x64/UsbXbox360Dxe.efi"
            driver.parent.mkdir(parents=True)
            driver.write_bytes(b"MZtest-driver")
            (driver.parent / "config.ini").write_text(
                "LeftStickMode=Keys\nButtonA=KeyEnter\n")
            (esp / "EFI").mkdir(parents=True)
            bindir = root / "bin"
            bindir.mkdir()
            uname = bindir / "uname"
            uname.write_text("#!/bin/sh\necho x86_64\n")
            uname.chmod(0o755)
            env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}",
                   "INFINITYOS_ROOT": str(source)}
            subprocess.run(["bash", str(INSTALL), str(esp)], check=True, env=env)
            for path in ("refind", "BOOT"):
                target = esp / "EFI" / path / "drivers_x64/UsbXbox360Dxe.efi"
                self.assertEqual(target.read_bytes(), driver.read_bytes())
            config = esp / "EFI/Xbox360/config.ini"
            content = config.read_text()
            self.assertIn("LeftStickMode=Keys", content)
            self.assertIn("ButtonA=KeyEnter", content)
            config.write_text("# custom mapping\n")
            subprocess.run(["bash", str(INSTALL), str(esp)], check=True, env=env)
            self.assertEqual(config.read_text(), "# custom mapping\n")
            (source / "usr/share/rEFInd/refind/refind_aa64.efi").write_bytes(b"refind-arm")
            uname.write_text("#!/bin/sh\necho aarch64\n")
            arm_esp = root / "arm-esp"
            (arm_esp / "EFI").mkdir(parents=True)
            subprocess.run(["bash", str(INSTALL), str(arm_esp)], check=True, env=env)
            self.assertFalse((arm_esp / "EFI/BOOT/drivers_x64").exists())

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
            self.assertIn("big_icon_size 128", THEME.read_text())
            self.assertIn("max_tags 3", THEME.read_text())
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
                self.assertEqual(struct.unpack(">II", data[16:24]), (128, 128))
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
            self.assertEqual(
                [line for line in menu.splitlines() if line.startswith("menuentry ")],
                ['menuentry "Infinity OS" {', 'menuentry "EmulationStation" {',
                 'menuentry "Steam Big Picture" {', 'menuentry "Backups (Btrfs)" {'],
            )
            self.assertEqual(menu, (esp / "EFI/BOOT/refind.conf").read_text())
            (modes / "esde").unlink()
            subprocess.run(command, check=True)
            self.assertNotIn('menuentry "EmulationStation"',
                             (esp / "EFI/refind/refind.conf").read_text())


if __name__ == "__main__":
    unittest.main()
