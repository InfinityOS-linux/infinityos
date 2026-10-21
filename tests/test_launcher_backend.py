import importlib.util
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "packages/infinity-launcher/root/usr/share/infinityos/launcher_backend.py"
SPEC = importlib.util.spec_from_file_location("launcher_backend", SOURCE)
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


class LauncherBackendTests(unittest.TestCase):
    def test_gaming_launchers_follow_steam(self):
        names = [app.name for app in backend.APPS if app.category == "Gaming"]
        self.assertEqual(names[:3], ["Steam", "Epic Games Launcher", "Blizzard Battle.net"])
        self.assertNotIn("GOG Galaxy", names)
        epic = next(app for app in backend.APPS if app.name == "Epic Games Launcher")
        self.assertEqual(epic.website, "https://launcher.epicgames.com/")
        self.assertFalse(backend.available(epic, "aarch64"))

    def test_epic_appimage_uses_official_download_and_creates_launcher(self):
        epic = next(app for app in backend.APPS if app.name == "Epic Games Launcher")
        response = io.BytesIO(b"\x7fELF\x02\x01\x01\x00AI\x02" + b"0" * 4096)
        response.geturl = lambda: "https://content-download-egs.distro.on.epicgames.com/EpicGamesLauncher-x86_64.AppImage"
        response.headers = {"Content-Length": str(len(response.getvalue()))}
        with tempfile.TemporaryDirectory() as directory, patch.object(backend.urllib.request, "urlopen", return_value=response):
            home = Path(directory)
            self.assertFalse(backend.installed(epic, home))
            backend.install(epic, home)
            self.assertTrue(backend.installed(epic, home))
            self.assertIn("EpicGamesLauncher.AppImage", (home / ".local/share/applications/epic-games-launcher.desktop").read_text())

    def test_epic_incomplete_download_does_not_install(self):
        epic = next(app for app in backend.APPS if app.name == "Epic Games Launcher")
        response = io.BytesIO(b"\x7fELF\x02\x01\x01\x00AI\x02" + b"0" * 4096)
        response.geturl = lambda: "https://content-download-egs.distro.on.epicgames.com/EpicGamesLauncher-x86_64.AppImage"
        response.headers = {"Content-Length": str(len(response.getvalue()) + 1)}
        with tempfile.TemporaryDirectory() as directory, patch.object(backend.urllib.request, "urlopen", return_value=response):
            home = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "size did not match"):
                backend.install(epic, home)
            self.assertFalse(backend.installed(epic, home))

    def test_battlenet_opens_system_lutris_installer(self):
        battlenet = next(app for app in backend.APPS if app.name == "Blizzard Battle.net")
        with patch.object(backend.shutil, "which", return_value="/usr/bin/lutris"), \
             patch.object(backend.subprocess, "Popen") as popen:
            backend.open_lutris_installer(battlenet)
        self.assertEqual(popen.call_args.args[0], ["/usr/bin/lutris", "lutris:install/battlenet-standard"])

    def test_architecture_and_unavailable_sources(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        photocraft = next(app for app in backend.APPS if app.name == "PhotoCraft")
        self.assertFalse(backend.available(steam, "aarch64"))
        self.assertTrue(backend.available(steam, "x86_64"))
        self.assertTrue(backend.available(photocraft, "aarch64"))

    def test_new_catalog_entries_and_order(self):
        gaming = [app.name for app in backend.APPS if app.category == "Gaming"]
        office = [app.name for app in backend.APPS if app.category == "Office"]
        creative = [app.name for app in backend.APPS if app.category == "Creative"]
        self.assertEqual(gaming[gaming.index("OpenGamepadUI") + 1], "ProtonPlus")
        self.assertEqual(office[office.index("WordCraft") + 1], "GridCraft")
        self.assertIn("SoundCraft", creative)
        self.assertIn("FigCraft", creative)
        self.assertNotIn("ArtCraft Launcher", creative)
        for name in ("GridCraft", "SoundCraft", "FigCraft", "ProtonPlus"):
            app = next(app for app in backend.APPS if app.name == name)
            self.assertTrue(backend.available(app, "aarch64"))

    def test_controller_install_uses_packaged_root_helper(self):
        app = next(app for app in backend.APPS if app.source == "xone")
        with patch.object(backend, "_run") as run:
            backend.install(app)
        self.assertEqual(run.call_args.args[0][-2:], ["--install-driver", "xone"])
        self.assertEqual(run.call_args.args[0][:2], ["pkexec", "/usr/bin/python3"])

    def test_controller_is_available_before_dkms_is_installed(self):
        app = next(app for app in backend.APPS if app.source == "xpadneo")
        with patch.object(backend.shutil, "which", return_value=None):
            self.assertFalse(backend.installed(app))

    def test_controller_source_checksum_and_safe_extraction(self):
        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            data = b"driver source"
            info = tarfile.TarInfo("xone-pinned/install.sh")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        archive_bytes = archive_buffer.getvalue()
        pinned = ("medusalix/xone", "pinned", hashlib.sha256(archive_bytes).hexdigest(), "xone", "v0.3")
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(backend.DRIVERS, {"xone": pinned}), \
             patch.object(backend.urllib.request, "urlopen", return_value=io.BytesIO(archive_bytes)):
            source = backend._verified_driver_source("xone", directory)
            self.assertEqual((source / "install.sh").read_bytes(), b"driver source")
        bad_pin = (*pinned[:2], "0" * 64, *pinned[3:])
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(backend.DRIVERS, {"xone": bad_pin}), \
             patch.object(backend.urllib.request, "urlopen", return_value=io.BytesIO(archive_bytes)):
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                backend._verified_driver_source("xone", directory)

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
            with patch.object(backend.shutil, "which", side_effect=lambda name: "/usr/bin/npm" if name == "npm" else None), patch.object(backend, "_run") as run:
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

    def test_eurooffice_release_and_installed_package_name(self):
        app = next(app for app in backend.APPS if app.name == "EuroOffice")
        release = {"assets": [{"name": "euro-office-euro-office-9.3.5-2.aarch64.rpm", "size": 3,
                               "browser_download_url": "https://github.com/Euro-Office/DesktopEditors/releases/download/v9.3.5-2/euro-office-euro-office-9.3.5-2.aarch64.rpm"}]}
        responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(b"rpm"))
        with tempfile.TemporaryDirectory() as directory, patch.object(backend.urllib.request, "urlopen", side_effect=responses):
            package = backend._latest_rpm(app, "aarch64", directory)
        self.assertEqual(package.name, "euro-office-euro-office-9.3.5-2.aarch64.rpm")
        with patch.object(backend.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(backend.installed(app))
        self.assertEqual(run.call_args.args[0], ["rpm", "-q", "euro-office-euro-office"])

    def test_openrazer_uses_its_repo_and_driver_packages(self):
        app = next(app for app in backend.APPS if app.name == "OpenRazer")
        with patch.object(backend, "_run") as run:
            backend.install(app)
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["pkexec", "dnf", "config-manager", "addrepo", "--from-repofile=https://openrazer.github.io/hardware:razer.repo"],
            ["pkexec", "dnf", "-y", "install", "kernel-devel", "openrazer-meta"],
            ["pkexec", "groupadd", "-f", "plugdev"],
            ["pkexec", "gpasswd", "-a", backend.pwd.getpwuid(backend.os.getuid()).pw_name, "plugdev"],
        ])

    def test_temporary_dns_failure_is_actionable(self):
        result = type("Result", (), {"returncode": 1, "stdout": "npm ERR! EAI_AGAIN registry.npmjs.org"})()
        with patch.object(backend.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "press APPLY to retry"):
                backend._run(["npm", "install"])

    def test_terminal_control_codes_are_removed_from_install_error(self):
        result = SimpleNamespace(returncode=1, stdout="Download failed\x1b[?25h\x07")
        with patch.object(backend.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "^Download failed$"):
                backend._run(["flatpak", "install"])

    def test_local_model_install_configures_runtime_and_activates_after_check(self):
        app = next(app for app in backend.APPS if app.source == "infinity-qwen-9b")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / ".local/bin/opencode"
            binary.parent.mkdir(parents=True)
            binary.touch()

            def which(command):
                return "/usr/local/bin/ollama" if command == "ollama" else None

            with patch.object(backend.shutil, "which", side_effect=which), \
                 patch.object(backend.shutil, "disk_usage", return_value=SimpleNamespace(free=50_000_000_000)), \
                 patch.object(backend.subprocess, "run", return_value=SimpleNamespace(returncode=1)), \
                 patch.object(backend.urllib.request, "urlopen", return_value=io.BytesIO(b"#!/bin/sh\n")), \
                 patch.object(backend, "_run") as run:
                backend.install(app, home)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertTrue(any(command[:2] == ["pkexec", "sh"] for command in commands))
            self.assertIn(["pkexec", "systemctl", "enable", "--now", "ollama.service"], commands)
            self.assertIn(["/usr/local/bin/ollama", "pull", backend.LOCAL_MODELS[app.source].remote], commands)
            self.assertTrue(any(command[:3] == ["/usr/local/bin/ollama", "create", app.source]
                                for command in commands))
            self.assertIn(["/usr/bin/infinity-local-ai", "--check"], commands)
            self.assertEqual(backend.active_local_model(home), app.source)

    def test_local_model_insufficient_disk_does_not_install_tools(self):
        app = next(app for app in backend.APPS if app.source == "infinity-qwen-9b")
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(backend.shutil, "which", return_value=None), \
             patch.object(backend.shutil, "disk_usage", return_value=SimpleNamespace(free=1_000_000_000)), \
             patch.object(backend, "_run") as run:
            with self.assertRaisesRegex(RuntimeError, "10 GB"):
                backend.install(app, directory)
            run.assert_not_called()

    def test_local_model_failed_ready_check_restores_previous_choice(self):
        app = next(app for app in backend.APPS if app.source == "infinity-qwen-9b")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/infinityos/local-ai-model"
            config.parent.mkdir(parents=True)
            config.write_text("infinity-gemma-12b\n")
            binary = home / ".local/bin/opencode"
            binary.parent.mkdir(parents=True)
            binary.touch()

            def run(command):
                if command == ["/usr/bin/infinity-local-ai", "--check"]:
                    raise RuntimeError("agent unavailable")

            with patch.object(backend.shutil, "which", side_effect=lambda name: "/usr/local/bin/ollama" if name == "ollama" else None), \
                 patch.object(backend.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                 patch.object(backend, "_run", side_effect=run):
                with self.assertRaisesRegex(RuntimeError, "agent unavailable"):
                    backend.install(app, home)
            self.assertEqual(config.read_text(), "infinity-gemma-12b\n")


if __name__ == "__main__":
    unittest.main()
