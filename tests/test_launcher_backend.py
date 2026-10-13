import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "packages/infinity-launcher/root/usr/share/infinityos/launcher_backend.py"
SPEC = importlib.util.spec_from_file_location("launcher_backend", SOURCE)
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


class LauncherBackendTests(unittest.TestCase):
    def test_architecture_and_unavailable_sources(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        photocraft = next(app for app in backend.APPS if app.name == "PhotoCraft")
        self.assertFalse(backend.available(steam, "aarch64"))
        self.assertTrue(backend.available(steam, "x86_64"))
        self.assertTrue(backend.available(photocraft, "aarch64"))

    def test_flatpak_install_starts_only_when_called(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        with patch.object(backend, "_run") as run:
            self.assertEqual(run.call_count, 0)
            backend.install(steam)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][-1], "com.valvesoftware.Steam")

    def test_cli_shortcut_is_created_after_successful_install(self):
        codex = next(app for app in backend.APPS if "Codex CLI" in app.name)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(backend.shutil, "which", return_value="/usr/bin/npm"), patch.object(backend, "_run") as run:
                backend.install(codex, directory)
            self.assertEqual(run.call_args_list[0].args[0][-1], "@openai/codex")
            shortcut = Path(directory) / ".local/share/applications/infinityos-codex.desktop"
            self.assertIn("https://chatgpt.com/codex", shortcut.read_text())

    def test_cli_failure_does_not_create_shortcut(self):
        claude = next(app for app in backend.APPS if "Claude Code CLI" in app.name)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(backend.shutil, "which", return_value="/usr/bin/npm"), patch.object(backend, "_run", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    backend.install(claude, directory)
            self.assertFalse((Path(directory) / ".local/share/applications/infinityos-claude.desktop").exists())

    def test_latest_storytold_rpm_uses_target_arch_and_checks_size(self):
        app = next(app for app in backend.APPS if app.name == "PhotoCraft")
        release = {"assets": [{"name": "photocraft-1-linux-aarch64.rpm", "size": 3,
                               "browser_download_url": "https://github.com/storytold/photocraft/releases/download/v1/photocraft-1-linux-aarch64.rpm"},
                              {"name": "photocraft-1-linux-x86_64.rpm", "size": 4,
                               "browser_download_url": "https://github.com/storytold/photocraft/releases/download/v1/photocraft-1-linux-x86_64.rpm"}]}
        responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(b"rpm"))
        with tempfile.TemporaryDirectory() as directory, patch.object(backend.urllib.request, "urlopen", side_effect=responses):
            package = backend._latest_rpm(app, "aarch64", directory)
            self.assertEqual(package.name, "photocraft-1-linux-aarch64.rpm")
            self.assertEqual(package.read_bytes(), b"rpm")

    def test_openlogi_arm_release_asset(self):
        app = next(app for app in backend.APPS if app.name == "OpenLogi")
        release = {"assets": [{"name": "openlogi-v1-linux-arm64.rpm", "size": 3,
                               "browser_download_url": "https://github.com/AprilNEA/OpenLogi/releases/download/v1/openlogi-v1-linux-arm64.rpm"}]}
        responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(b"rpm"))
        with tempfile.TemporaryDirectory() as directory, patch.object(backend.urllib.request, "urlopen", side_effect=responses):
            package = backend._latest_rpm(app, "aarch64", directory)
            self.assertEqual(package.name, "openlogi-v1-linux-arm64.rpm")

    def test_temporary_dns_failure_is_actionable(self):
        result = type("Result", (), {"returncode": 1, "stdout": "npm ERR! EAI_AGAIN registry.npmjs.org"})()
        with patch.object(backend.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "press APPLY to retry"):
                backend._run(["npm", "install"])


if __name__ == "__main__":
    unittest.main()
