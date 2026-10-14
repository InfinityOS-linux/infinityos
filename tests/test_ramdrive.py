import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-ramdrive"
SPEC = importlib.util.spec_from_loader("infinityos_ramdrive", importlib.machinery.SourceFileLoader("infinityos_ramdrive", str(SOURCE)))
ramdrive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ramdrive)


class RAMDriveTests(unittest.TestCase):
    def test_shutdown_guard_runs_only_while_system_is_stopping(self):
        script = SOURCE.with_name("infinityos-ramdrive-shutdown")
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory)
            log = tools / "cleared"
            (tools / "systemctl").write_text("#!/bin/sh\necho \"$SYSTEM_STATE\"\n")
            (tools / "getent").write_text("#!/bin/sh\necho 'admin:x:1000:1000::/home/admin:/bin/bash'\n")
            (tools / "runuser").write_text(f"#!/bin/sh\necho invoked > '{log}'\n")
            for command in ("systemctl", "getent", "runuser"):
                (tools / command).chmod(0o755)
            environment = {**os.environ, "PATH": f"{tools}:{os.environ['PATH']}"}
            subprocess.run(["bash", str(script)], check=True,
                           env={**environment, "SYSTEM_STATE": "running"})
            self.assertFalse(log.exists())
            subprocess.run(["bash", str(script)], check=True,
                           env={**environment, "SYSTEM_STATE": "stopping"})
            self.assertTrue(log.exists())

    def test_setup_migrates_files_and_desktop_shortcut_can_stay_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            desktop = home / "Desktop"
            desktop.mkdir()
            protected = home / ".protected" / str(os.getuid())
            protected.mkdir(parents=True)
            folder = desktop / "RAMDrive"
            folder.mkdir()
            outside = home / "keep.txt"
            outside.write_text("keep")
            (folder / "nested").mkdir()
            (folder / "nested/file.txt").write_text("recover after crash")
            (folder / "outside-link").symlink_to(outside)
            bookmark = home / ".config/gtk-3.0/bookmarks"
            bookmark.parent.mkdir(parents=True)
            bookmark.write_text(f"file:///existing Existing\n{folder.as_uri()} RAMDrive\n")

            def fake_run(command, **_kwargs):
                class Result:
                    stdout = str(desktop) + "\n"
                return Result()

            with patch.object(ramdrive.Path, "home", return_value=home), \
                 patch.object(ramdrive, "STORE_ROOT", protected.parent), \
                 patch.object(ramdrive.subprocess, "run", side_effect=fake_run):
                ramdrive.setup()
                self.assertTrue(folder.is_symlink())
                self.assertEqual(folder.resolve(), protected.resolve())
                self.assertEqual((protected / "nested/file.txt").read_text(), "recover after crash")
                self.assertTrue((protected / "outside-link").is_symlink())
                self.assertNotIn(folder.as_uri(), bookmark.read_text())
                ramdrive.setup()
                self.assertEqual(bookmark.read_text().splitlines().count(f"{protected.as_uri()} RAMDrive"), 1)
                folder.unlink()
                ramdrive.setup()
                self.assertFalse(folder.exists())
                self.assertEqual((protected / "nested/file.txt").read_text(), "recover after crash")
                ramdrive.clear()

            self.assertTrue(protected.is_dir())
            self.assertEqual(list(protected.iterdir()), [])
            self.assertEqual(outside.read_text(), "keep")

    def test_first_login_creates_shortcut_without_touching_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            desktop = home / "Desktop"
            protected = home / ".protected" / str(os.getuid())
            protected.mkdir(parents=True)
            (protected / "keep.txt").write_text("keep")

            def fake_run(_command, **_kwargs):
                class Result:
                    stdout = str(desktop) + "\n"
                return Result()

            with patch.object(ramdrive.Path, "home", return_value=home), \
                 patch.object(ramdrive, "STORE_ROOT", protected.parent), \
                 patch.object(ramdrive.subprocess, "run", side_effect=fake_run):
                ramdrive.setup()

            self.assertTrue((desktop / "RAMDrive").is_symlink())
            self.assertEqual((protected / "keep.txt").read_text(), "keep")

    def test_setup_keeps_existing_data_when_names_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            desktop = home / "Desktop"
            desktop.mkdir()
            protected = home / ".protected" / str(os.getuid())
            protected.mkdir(parents=True)
            (protected / "save.txt").write_text("already protected")
            old = desktop / "RAMDrive"
            old.mkdir()
            (old / "save.txt").write_text("on desktop")

            def fake_run(_command, **_kwargs):
                class Result:
                    stdout = str(desktop) + "\n"
                return Result()

            with patch.object(ramdrive.Path, "home", return_value=home), \
                 patch.object(ramdrive, "STORE_ROOT", protected.parent), \
                 patch.object(ramdrive.subprocess, "run", side_effect=fake_run):
                ramdrive.setup()

            self.assertEqual((protected / "save.txt").read_text(), "already protected")
            self.assertEqual((protected / "save.txt (from Desktop 1)").read_text(), "on desktop")


if __name__ == "__main__":
    unittest.main()
