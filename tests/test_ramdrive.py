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

    def test_setup_preserves_files_and_clear_removes_only_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            desktop = home / "Desktop"
            desktop.mkdir()
            outside = home / "keep.txt"
            outside.write_text("keep")
            bookmark = home / ".config/gtk-3.0/bookmarks"
            bookmark.parent.mkdir(parents=True)
            bookmark.write_text("file:///existing Existing")

            def fake_run(command, **_kwargs):
                class Result:
                    stdout = str(desktop) + "\n"
                return Result()

            with patch.object(ramdrive.Path, "home", return_value=home), patch.object(ramdrive.subprocess, "run", side_effect=fake_run):
                ramdrive.setup()
                folder = desktop / "RAMDrive"
                (folder / "nested").mkdir()
                (folder / "nested/file.txt").write_text("recover after crash")
                (folder / "outside-link").symlink_to(outside)
                ramdrive.setup()
                self.assertEqual((folder / "nested/file.txt").read_text(), "recover after crash")
                self.assertEqual(bookmark.read_text().splitlines().count(f"{folder.as_uri()} RAMDrive"), 1)
                ramdrive.clear()

            self.assertTrue(folder.is_dir())
            self.assertEqual(list(folder.iterdir()), [])
            self.assertEqual(outside.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
