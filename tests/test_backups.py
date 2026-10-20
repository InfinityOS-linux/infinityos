import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FSTAB = ROOT / "root/usr/libexec/infinityos-backups-fstab"
CONFIG = ROOT / "root/usr/libexec/infinityos-refind-config"


class BackupsTests(unittest.TestCase):
    def test_fstab_uses_default_root_and_persistent_snapshot_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fstab"
            path.write_text(
                "UUID=abc / btrfs compress=zstd:1,defaults,subvol=root 0 1\n"
                "UUID=abc /home btrfs subvol=home 0 0\n"
                "UUID=abc /.snapshots btrfs subvol=old 0 0\n"
            )
            subprocess.run([FSTAB, path, "abc"], check=True)
            result = path.read_text()
            self.assertIn("/ btrfs compress=zstd:1,defaults", result)
            self.assertNotIn("subvol=root", result)
            self.assertIn("/home btrfs subvol=home", result)
            self.assertEqual(result.count("/.snapshots btrfs"), 1)
            self.assertIn("subvol=infinityos-snapshots", result)
            subprocess.run([FSTAB, path, "abc"], check=True)
            self.assertEqual(path.read_text(), result)

    def test_refind_entries_track_kernel_and_default_btrfs_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            esp = Path(tmp) / "esp"
            (esp / "EFI/refind").mkdir(parents=True)
            (esp / "os").mkdir()
            (esp / "os/vmlinuz-1").write_bytes(b"kernel")
            (esp / "os/initramfs-1.img").write_bytes(b"initrd")
            cmdline = Path(tmp) / "cmdline"
            cmdline.write_text("rootflags=subvol=root rhgb quiet root=UUID=abc\n")
            ready = Path(tmp) / "backups-ready"
            subprocess.run([CONFIG, esp, cmdline, ready], check=True)
            result = esp / "EFI/refind/refind.conf"
            content = result.read_text()
            self.assertIn('menuentry "Infinity OS"', content)
            self.assertIn('menuentry "Backups (Btrfs)"', content)
            self.assertIn('loader /os/vmlinuz-1', content)
            self.assertIn('initrd /os/initramfs-1.img', content)
            self.assertIn('icon /EFI/refind/infinity-theme/icons/os_infinityos.png', content)
            self.assertIn('rootflags=subvol=root', content)
            self.assertIn('systemd.unit=infinityos-backups.target', content)
            ready.touch()
            subprocess.run([CONFIG, esp, cmdline, ready], check=True)
            content = result.read_text()
            self.assertNotIn('rootflags=subvol=root', content)
            timestamp = result.stat().st_mtime_ns
            subprocess.run([CONFIG, esp, cmdline, ready], check=True)
            self.assertEqual(result.stat().st_mtime_ns, timestamp)


if __name__ == "__main__":
    unittest.main()
