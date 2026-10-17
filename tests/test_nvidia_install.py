import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "root/usr/libexec/infinityos-install-nvidia"
CATALOG = ROOT / "root/usr/share/infinityos/nvidia-legacy-gpus.json"
LOADER = importlib.machinery.SourceFileLoader("infinityos_install_nvidia", str(SOURCE))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
installer = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(installer)


def card(sysfs, name, device, boot=False):
    slot = sysfs / name
    slot.mkdir()
    (slot / "vendor").write_text("0x10de\n")
    (slot / "class").write_text("0x030000\n")
    (slot / "device").write_text(f"0x{device}\n")
    (slot / "boot_vga").write_text("1\n" if boot else "0\n")


class NvidiaInstallerTests(unittest.TestCase):
    def test_official_pci_catalog_selects_each_driver_branch(self):
        data = json.loads(CATALOG.read_text())
        for device, branch in (("1E84", "current"), ("1B80", "580"),
                               ("0FC6", "470"), ("06C0", "390")):
            with self.subTest(device=device):
                self.assertEqual(installer.driver_branch([(device, True)], data), branch)
        self.assertEqual(installer.driver_branch([], data), "none")
        self.assertEqual(installer.driver_branch([("0020", True)], data), "unsupported")

    def test_boot_gpu_is_selected_when_more_than_one_nvidia_card_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            sysfs = Path(directory)
            card(sysfs, "0000:01:00.0", "1B80")
            card(sysfs, "0000:02:00.0", "1E84", boot=True)
            self.assertEqual(installer.detected_cards(sysfs)[0], ("1E84", True))

    def test_legacy_install_replaces_preloaded_current_driver(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sysfs = root / "sys"
            sysfs.mkdir()
            card(sysfs, "0000:01:00.0", "1B80", boot=True)
            with patch.object(installer, "installed", return_value=False), \
                 patch.object(installer, "dnf", return_value=True) as dnf:
                self.assertTrue(installer.configure(root, sysfs, CATALOG))
            self.assertEqual(dnf.call_args.args[1:],
                             ("install", "--allowerasing", "akmod-nvidia-580xx",
                              "xorg-x11-drv-nvidia-580xx"))
            self.assertEqual((root / installer.MARKER).read_text(), "580\n")

    def test_failed_legacy_download_removes_incompatible_driver_for_nouveau(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sysfs = root / "sys"
            sysfs.mkdir()
            card(sysfs, "0000:01:00.0", "0FC6", boot=True)
            with patch.object(installer, "installed", side_effect=lambda _, package: package in installer.CURRENT), \
                 patch.object(installer, "dnf", side_effect=(False, True)) as dnf:
                self.assertFalse(installer.configure(root, sysfs, CATALOG))
            self.assertEqual(dnf.call_args_list[1].args[1:],
                             ("remove", "akmod-nvidia", "xorg-x11-drv-nvidia"))
            self.assertFalse((root / installer.MARKER).exists())

    def test_non_nvidia_machine_does_not_install_driver(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sysfs = root / "sys"
            sysfs.mkdir()
            with patch.object(installer, "installed", return_value=False), \
                 patch.object(installer, "dnf", return_value=True) as dnf:
                self.assertTrue(installer.configure(root, sysfs, CATALOG))
            dnf.assert_not_called()
            self.assertEqual((root / installer.MARKER).read_text(), "none\n")


if __name__ == "__main__":
    unittest.main()
