"""Prevent images assembled from old prepared roots or old Infinity RPMs."""

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE_REVISION = REPO / "scripts/infinityos-source-revision"
VERIFY_ROOT = REPO / "root/usr/libexec/infinityos-verify-build-root"
PACKAGES = (
    "infinity-config",
    "infinity-setup",
    "infinity-terminal",
    "infinity-updater",
    "infinityos-repos",
    "infinityos-wallpapers",
    "infinityos-ramdrive",
    "infinityos-shell-extensions",
)


class ImageProvenanceTests(unittest.TestCase):
    def test_source_revision_rejects_uncommitted_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "source").write_text("first\n")
            subprocess.run(["git", "-C", str(repo), "add", "source"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.org",
                 "commit", "-qm", "initial"],
                check=True,
            )
            clean = subprocess.run([str(SOURCE_REVISION), str(repo)], capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(len(clean.stdout.strip()), 40)

            (repo / "source").write_text("changed\n")
            dirty = subprocess.run([str(SOURCE_REVISION), str(repo)], capture_output=True, text=True)
            self.assertNotEqual(dirty.returncode, 0)
            self.assertIn("uncommitted", dirty.stderr)

            (repo / "source").write_text("first\n")
            (repo / "new-file").write_text("new\n")
            untracked = subprocess.run([str(SOURCE_REVISION), str(repo)], capture_output=True, text=True)
            self.assertNotEqual(untracked.returncode, 0)

    def test_root_rejects_missing_and_stale_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision = "a" * 40
            build = root / "usr/share/infinityos"
            markers = build / "build-revisions"
            markers.mkdir(parents=True)
            (build / "build-revision").write_text(revision + "\n")
            (build / "required-rpms").write_text("\n".join(PACKAGES) + "\n")
            for package in PACKAGES:
                (markers / package).write_text(revision + "\n")
            gdm_defaults = root / "etc/dconf/db/gdm.d/00-infinityos"
            gdm_defaults.parent.mkdir(parents=True)
            gdm_defaults.write_text(
                "picture-uri='file:///usr/share/backgrounds/infinityos/infinityos-login.png'\n"
                "picture-uri-dark='file:///usr/share/backgrounds/infinityos/infinityos-login.png'\n"
                "picture-options='zoom'\n"
            )
            expected_files = (
                "usr/bin/infinity-config",
                "usr/bin/infinity-setup",
                "usr/bin/infinity-terminal",
                "usr/bin/infinity-updater",
                "usr/share/backgrounds/infinityos/infinityos-dark.png",
                "usr/share/backgrounds/infinityos/infinityos-login.png",
                "usr/share/gnome-shell/extensions/ghostty@infinityos.org/extension.js",
                "usr/share/gnome-shell/extensions/infinity-updater@infinityos.org/extension.js",
            )
            for name in expected_files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            result = subprocess.run([str(VERIFY_ROOT), str(root), revision], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            login_background = root / "usr/share/backgrounds/infinityos/infinityos-login.png"
            login_background.unlink()
            missing_background = subprocess.run(
                [str(VERIFY_ROOT), str(root), revision], capture_output=True, text=True)
            self.assertNotEqual(missing_background.returncode, 0)
            self.assertIn("infinityos-login.png", missing_background.stderr)
            login_background.touch()

            (markers / "infinity-updater").write_text("b" * 40 + "\n")
            stale = subprocess.run([str(VERIFY_ROOT), str(root), revision], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("infinity-updater", stale.stderr)

            (markers / "infinity-updater").unlink()
            missing = subprocess.run([str(VERIFY_ROOT), str(root), revision], capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)

            (markers / "infinity-updater").write_text(revision + "\n")
            (root / "usr/bin/infinity-terminal").unlink()
            missing_app = subprocess.run([str(VERIFY_ROOT), str(root), revision], capture_output=True, text=True)
            self.assertNotEqual(missing_app.returncode, 0)
            self.assertIn("infinity-terminal", missing_app.stderr)


if __name__ == "__main__":
    unittest.main()
