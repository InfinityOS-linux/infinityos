import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "root/usr/share/infinityos/launcher_backend.py"
SPEC = importlib.util.spec_from_file_location("launcher_backend", SOURCE)
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


class LauncherBackendTests(unittest.TestCase):
    def test_architecture_and_unavailable_sources(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        photocraft = next(app for app in backend.APPS if app.name == "PhotoCraft")
        self.assertFalse(backend.available(steam, "aarch64"))
        self.assertTrue(backend.available(steam, "x86_64"))
        self.assertFalse(backend.available(photocraft, "x86_64"))

    def test_flatpak_install_starts_only_when_called(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        with patch.object(backend, "_run") as run:
            self.assertEqual(run.call_count, 0)
            backend.install(steam)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][-1], "com.valvesoftware.Steam")

    def test_cli_shortcut_is_created_after_successful_install(self):
        codex = next(app for app in backend.APPS if app.name.startswith("Codex"))
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(backend.shutil, "which", return_value="/usr/bin/npm"), patch.object(backend, "_run") as run:
                backend.install(codex, directory)
            self.assertEqual(run.call_args_list[0].args[0][-1], "@openai/codex")
            shortcut = Path(directory) / ".local/share/applications/infinityos-codex.desktop"
            self.assertIn("https://chatgpt.com/codex", shortcut.read_text())

    def test_cli_failure_does_not_create_shortcut(self):
        claude = next(app for app in backend.APPS if app.name.startswith("Claude"))
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(backend.shutil, "which", return_value="/usr/bin/npm"), patch.object(backend, "_run", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    backend.install(claude, directory)
            self.assertFalse((Path(directory) / ".local/share/applications/infinityos-claude.desktop").exists())


if __name__ == "__main__":
    unittest.main()
