import importlib.util
import hashlib
import io
import json
import stat
import tarfile
import tempfile
import unittest
from xml.etree import ElementTree
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "packages/infinity-setup/root/usr/share/infinityos/launcher_backend.py"
SPEC = importlib.util.spec_from_file_location("launcher_backend", SOURCE)
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)
CATALOG_DIR = SOURCE.parent
I18N_SPEC = importlib.util.spec_from_file_location("launcher_i18n", CATALOG_DIR / "launcher_i18n.py")
i18n = importlib.util.module_from_spec(I18N_SPEC)
I18N_SPEC.loader.exec_module(i18n)


class LauncherBackendTests(unittest.TestCase):
    def test_every_catalog_description_has_a_polish_translation(self):
        missing = [app.name for app in backend.APPS if app.description not in i18n.POLISH]
        self.assertEqual(missing, [])
        winboat = next(app for app in backend.APPS if app.name == "WinBoat")
        self.assertEqual(i18n.POLISH[winboat.description],
                         "Uruchom w łatwy sposób Windowsa na tym systemie.")

    def test_game_store_brands_have_bundled_icons(self):
        icons = CATALOG_DIR / "launcher-icons"
        for name in ("Epic Games Launcher", "Blizzard Battle.net"):
            app = next(app for app in backend.APPS if app.name == name)
            with self.subTest(name=name):
                icon = icons / f"{app.icon}.svg"
                self.assertTrue(icon.is_file())
                self.assertEqual(ElementTree.parse(icon).getroot().tag,
                                 "{http://www.w3.org/2000/svg}svg")

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
        self.assertTrue(backend.available(steam, "aarch64"))
        self.assertTrue(backend.available(steam, "x86_64"))
        self.assertFalse(backend.available(steam, "riscv64"))
        self.assertTrue(backend.available(photocraft, "aarch64"))

    def test_arm_steam_uses_valve_manifest_and_verified_archive(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        archive = io.BytesIO()
        with __import__("zipfile").ZipFile(archive, "w") as client:
            client.writestr("steamrtarm64/steam", b"native arm client")
            client.writestr("steamrtarm64\\libs\\libcurl.so", b"runtime library")
            link = __import__("zipfile").ZipInfo("steamrtarm64\\libs\\libcurl.so.4")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o755) << 16
            client.writestr(link, "libcurl.so")
        payload = archive.getvalue()
        filename = "bins_linuxarm64_linuxarm64.zip." + "a" * 40
        digest = hashlib.sha256(payload).hexdigest()
        manifest = (f'"bins_linuxarm64_linuxarm64"\n{{\n"file" "{filename}"\n'
                    f'"size" "{len(payload)}"\n"sha2" "{digest}"\n}}').encode()
        download = io.BytesIO(payload)
        download.geturl = lambda: f"https://client-update.steamstatic.com/{filename}"
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(backend.os, "uname", return_value=SimpleNamespace(machine="aarch64")), \
             patch.object(backend.urllib.request, "urlopen", side_effect=[io.BytesIO(manifest), download]), \
             patch.object(backend, "_run") as run:
            home = Path(directory)
            self.assertFalse(backend.installed(steam, home))
            backend.install(steam, home)
            self.assertTrue(backend.installed(steam, home))
            client = home / ".local/share/Steam/steamrtarm64/steam"
            client.chmod(0o644)
            self.assertFalse(backend.installed(steam, home))
            client.chmod(0o755)
            self.assertEqual((home / ".local/share/Steam/steamrtarm64/libs/libcurl.so").read_bytes(),
                             b"runtime library")
            self.assertTrue((home / ".local/share/Steam/steamrtarm64/libs/libcurl.so.4").is_symlink())
            self.assertTrue((home / ".local/share/Steam/steamrtarm64/steam").stat().st_mode & stat.S_IXUSR)
            self.assertIn("Steam ARM64", (home / ".local/share/applications/steam-arm64.desktop").read_text())
        run.assert_called_once_with(["pkexec", "dnf", "-y", "install", "libva", "libvpx", "ibus-libs"])

    def test_arm_steam_rejects_changed_archive_before_installing_packages(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        payload = b"not the declared archive"
        filename = "bins_linuxarm64_linuxarm64.zip." + "a" * 40
        zero_digest = "0" * 64
        manifest = (f'"bins_linuxarm64_linuxarm64"\n{{\n"file" "{filename}"\n'
                    f'"size" "{len(payload)}"\n"sha2" "{zero_digest}"\n}}').encode()
        download = io.BytesIO(payload)
        download.geturl = lambda: f"https://client-update.steamstatic.com/{filename}"
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(backend.os, "uname", return_value=SimpleNamespace(machine="aarch64")), \
             patch.object(backend.urllib.request, "urlopen", side_effect=[io.BytesIO(manifest), download]), \
             patch.object(backend, "_run") as run:
            home = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                backend.install(steam, home)
            self.assertFalse(backend.installed(steam, home))
        run.assert_not_called()

    def test_live_image_keeps_steam_and_lutris_optional(self):
        image = Path(__file__).resolve().parents[1] / "teams/workstation.xml"
        root = ElementTree.parse(image).getroot()
        packages = root.find("./packages[@profiles='Infinity-GNOME-Live,Infinity-GNOME-Disk']")
        self.assertIsNotNone(packages)
        self.assertFalse({"steam", "lutris"} & {item.get("name") for item in packages.findall("package")})

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

    def test_winboat_is_x86_only_and_installs_runtime_with_rpm(self):
        app = next(app for app in backend.APPS if app.name == "WinBoat")
        self.assertFalse(backend.available(app, "aarch64"))
        self.assertTrue(backend.available(app, "x86_64"))
        self.assertEqual((app.category, app.group), ("System", "Windows apps"))
        self.assertNotIn(app, [item for item in backend.APPS if item.category == "Gaming"])
        with patch.object(backend, "_latest_rpm", return_value=Path("/tmp/winboat-0.9.2-x86_64.rpm")) as latest, \
             patch.object(backend, "_run") as run:
            backend.install(app)
        self.assertEqual(latest.call_args.args[0], app)
        self.assertEqual(run.call_args.args[0], [
            "pkexec", "dnf", "-y", "install", "podman", "podman-compose", "freerdp",
            "/tmp/winboat-0.9.2-x86_64.rpm"])

    def test_winboat_release_asset_matches_upstream_rpm_name(self):
        app = next(app for app in backend.APPS if app.name == "WinBoat")
        release = {"assets": [{"name": "winboat-0.9.2-x86_64.rpm", "size": 3,
                               "browser_download_url": "https://github.com/winboat-org/winboat/releases/download/v0.9.2/winboat-0.9.2-x86_64.rpm"}]}
        responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(b"rpm"))
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(backend.urllib.request, "urlopen", side_effect=responses):
            package = backend._latest_rpm(app, "x86_64", directory)
            self.assertEqual(package.name, "winboat-0.9.2-x86_64.rpm")

    def test_safe_disk_cleaner_release_on_both_architectures(self):
        app = next(app for app in backend.APPS if app.name == "Safe Disk Cleaner")
        self.assertEqual((app.category, app.group), ("System", "System maintenance"))
        for arch, machine in (("x86_64", 62), ("aarch64", 183)):
            with self.subTest(arch=arch):
                payload = (b"\x7fELF\x02\x01\x01\x00AI\x02" + b"\x00" * 7 +
                           machine.to_bytes(2, "little") + b"\x00" * 4096)
                name = f"Safe_Disk_Cleaner-1.1.1-{arch}.AppImage"
                release = {"assets": [{"name": name, "size": len(payload),
                                       "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
                                       "browser_download_url": f"https://github.com/{app.source}/releases/download/v1.1.1/{name}"}]}
                responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(payload))
                with tempfile.TemporaryDirectory() as directory, \
                     patch.object(backend.urllib.request, "urlopen", side_effect=responses):
                    package = backend._latest_appimage(app, arch, directory)
                    self.assertEqual(package.read_bytes(), payload)
                release["assets"][0]["digest"] = "sha256:" + "0" * 64
                responses = (io.BytesIO(json.dumps(release).encode()), io.BytesIO(payload))
                with tempfile.TemporaryDirectory() as directory, \
                     patch.object(backend.urllib.request, "urlopen", side_effect=responses):
                    with self.assertRaisesRegex(RuntimeError, "checksum"):
                        backend._latest_appimage(app, arch, directory)

    def test_safe_disk_cleaner_install_creates_desktop_entry(self):
        app = next(app for app in backend.APPS if app.name == "Safe Disk Cleaner")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = home / "source.AppImage"
            source.write_bytes(b"appimage")
            with patch.object(backend, "_latest_appimage", return_value=source):
                backend.install(app, home)
            self.assertTrue(backend.installed(app, home))
            desktop = home / ".local/share/applications/io.github.cyb3rl00m.SafeDiskCleaner.desktop"
            self.assertIn("APPIMAGE_EXTRACT_AND_RUN=1", desktop.read_text())

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
        pinned = ("dlundqvist/xone", "pinned", hashlib.sha256(archive_bytes).hexdigest(), "xone", "0.5.8")
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

    def test_xone_old_version_requires_upgrade(self):
        app = next(app for app in backend.APPS if app.source == "xone")
        status = "xone/v0.3, 6.0.0, x86_64: installed\n"
        with patch.object(backend.shutil, "which", return_value="/usr/bin/dkms"), \
             patch.object(backend.os, "uname", return_value=SimpleNamespace(release="6.0.0")), \
             patch.object(backend.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=status)):
            self.assertFalse(backend.installed(app))
            self.assertEqual(backend._old_xone_versions(), ["v0.3"])
        status = "xone/0.5.8, 6.0.0, x86_64: installed\n"
        with patch.object(backend.shutil, "which", return_value="/usr/bin/dkms"), \
             patch.object(backend.os, "uname", return_value=SimpleNamespace(release="6.0.0")), \
             patch.object(backend.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=status)):
            self.assertTrue(backend._driver_module_installed("xone", "0.5.8"))

    def test_xone_requires_all_new_dongle_firmware_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(backend.XONE_FIRMWARES, clear=True):
            backend.XONE_FIRMWARES.update({
                "02e6": ("https://example.com/02e6.cab", "firmware.bin", hashlib.sha256(b"first").hexdigest()),
                "02fe": ("https://example.com/02fe.cab", "firmware.bin", hashlib.sha256(b"second").hexdigest()),
            })
            firmware_dir = Path(directory) / "firmware"
            self.assertFalse(backend._xone_firmware_valid(firmware_dir))
            responses = (io.BytesIO(b"cab1"), io.BytesIO(b"cab2"))
            outputs = (SimpleNamespace(returncode=0, stdout=b"first"),
                       SimpleNamespace(returncode=0, stdout=b"second"))
            with patch.object(backend.urllib.request, "urlopen", side_effect=responses), \
                 patch.object(backend.subprocess, "run", side_effect=outputs):
                backend._install_xone_firmware(directory, firmware_dir)
            self.assertTrue(backend._xone_firmware_valid(firmware_dir))

    def test_flatpak_install_starts_only_when_called(self):
        steam = next(app for app in backend.APPS if app.name == "Steam")
        with patch.object(backend, "_run") as run:
            self.assertEqual(run.call_count, 0)
            backend.install(steam)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][-1], "com.valvesoftware.Steam")

    def test_catalog_reads_flatpak_installations_once_per_scope(self):
        vlc = next(app for app in backend.APPS if app.name == "VLC")
        responses = (
            SimpleNamespace(returncode=0, stdout="org.videolan.VLC\n"),
            SimpleNamespace(returncode=0, stdout="org.gimp.GIMP\n"),
        )
        with patch.object(backend.subprocess, "run", side_effect=responses) as run:
            installed_ids = backend.installed_flatpaks()
            self.assertTrue(backend.installed(vlc, flatpak_ids=installed_ids))
            self.assertFalse(backend.installed(vlc._replace(source="org.videolan.Other"),
                                               flatpak_ids=installed_ids))
        self.assertEqual(run.call_count, 2)

    def test_flatpak_catalog_falls_back_to_individual_checks_on_list_error(self):
        vlc = next(app for app in backend.APPS if app.name == "VLC")
        with patch.object(backend.subprocess, "run", side_effect=[
                SimpleNamespace(returncode=1, stdout=""),
                SimpleNamespace(returncode=0)]) as run:
            self.assertIsNone(backend.installed_flatpaks())
            self.assertTrue(backend.installed(vlc))
        self.assertEqual(run.call_count, 2)

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

    def test_user_cli_can_be_removed_without_touching_system_install(self):
        claude = next(app for app in backend.APPS if "Claude Code CLI" in app.name)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / ".local/bin/claude"
            binary.parent.mkdir(parents=True)
            binary.touch()
            shortcut = home / ".local/share/applications/infinityos-claude.desktop"
            shortcut.parent.mkdir(parents=True)
            shortcut.touch()
            self.assertTrue(backend.removable(claude, home))
            with patch.object(backend, "_run") as run, \
                 patch.object(backend.shutil, "which", return_value=None):
                backend.uninstall(claude, home)
            self.assertEqual(run.call_args.args[0], ["npm", "uninstall", "--global",
                                                     "--prefix", str(home / ".local"), claude.source])
            self.assertFalse(shortcut.exists())
            binary.unlink()
            with self.assertRaises(ValueError):
                backend.uninstall(claude, home)

    def test_local_model_can_be_deselected_without_deleting_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/infinityos/local-ai-model"
            config.parent.mkdir(parents=True)
            config.write_text("infinity-qwen-9b\n")
            with patch.object(backend.shutil, "which", return_value=None):
                backend.deactivate_local_model(home)
            self.assertIsNone(backend.active_local_model(home))

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
