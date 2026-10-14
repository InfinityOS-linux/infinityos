import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FSTAB = ROOT / "root/usr/libexec/infinityos-backups-fstab"
ENTRY = ROOT / "root/usr/libexec/infinityos-backups-entry"


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

    def test_boot_entry_uses_matching_kernel_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            esp = Path(tmp)
            (esp / "loader/entries").mkdir(parents=True)
            (esp / "os").mkdir()
            (esp / "os/vmlinuz-1").write_bytes(b"kernel")
            (esp / "os/initramfs-1.img").write_bytes(b"initrd")
            (esp / "loader/entries/infinityos.conf").write_text(
                "title Infinity OS 44\n"
                "options rootflags=subvol=root rhgb quiet root=UUID=abc\n"
                "linux os/vmlinuz-1\n"
                "initrd os/initramfs-1.img\n"
            )
            subprocess.run([ENTRY, esp], check=True)
            result = esp / "loader/entries/infinityos-backups.conf"
            content = result.read_text()
            self.assertIn("title Backups", content)
            self.assertIn("linux os/vmlinuz-1", content)
            self.assertIn("systemd.unit=infinityos-backups.target", content)
            self.assertNotIn(" rhgb", content)
            self.assertNotIn(" quiet", content)
            timestamp = result.stat().st_mtime_ns
            subprocess.run([ENTRY, esp], check=True)
            self.assertEqual(result.stat().st_mtime_ns, timestamp)


if __name__ == "__main__":
    unittest.main()
