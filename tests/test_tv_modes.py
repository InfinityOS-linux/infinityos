import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "packages/infinity-setup/root/usr/share/infinityos"
sys.path.insert(0, str(CATALOG))
from launcher_tv import _install_esde
import launcher_tv

CONTROL = ROOT / "root/usr/libexec/infinityos-tv-control"
SPEC = importlib.util.spec_from_loader("infinityos_tv_control", loader=None)
control = importlib.util.module_from_spec(SPEC)
exec(compile(CONTROL.read_text(), str(CONTROL), "exec"), control.__dict__)
ENTER = ROOT / "root/usr/libexec/infinityos-tv-enter"
ENTER_SPEC = importlib.util.spec_from_loader("infinityos_tv_enter", loader=None)
enter = importlib.util.module_from_spec(ENTER_SPEC)
exec(compile(ENTER.read_text(), str(ENTER), "exec"), enter.__dict__)


class TVModeTests(unittest.TestCase):
    def test_enter_policy_is_passwordless_only_for_active_sessions(self):
        policy = ET.parse(ROOT / "root/usr/share/polkit-1/actions/org.infinityos.tv-enter.policy")
        action = policy.find("./action[@id='org.infinityos.tv-modes.enter']")
        self.assertIsNotNone(action)
        self.assertEqual(action.findtext("./defaults/allow_active"), "yes")
        self.assertEqual(action.findtext("./defaults/allow_inactive"), "no")
        self.assertEqual(action.findtext("./defaults/allow_any"), "no")

    def test_enter_requires_pkexec_caller_and_uses_owner_check(self):
        request = Mock()
        with patch.object(enter.os, "geteuid", return_value=0), \
             patch.object(enter.sys, "argv", [str(ENTER), "steam"]), \
             patch.object(enter.runpy, "run_path", return_value={"request_next": request}):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(PermissionError):
                    enter.main()
            with patch.dict(os.environ, {"PKEXEC_UID": "1000"}):
                enter.main()
        request.assert_called_once_with("steam")

    def test_privileged_and_user_esde_package_lists_match(self):
        self.assertEqual(control.ESDE_PACKAGES, launcher_tv.ESDE_PACKAGES)

    def test_esde_configuration_keeps_other_user_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / "ES-DE/settings/es_settings.xml"
            settings.parent.mkdir(parents=True)
            settings.write_text('<string name="ROMDirectory" value="/old/roms" />\n'
                                '<string name="Theme" value="user-theme" />\n')
            retroarch = home / ".config/retroarch/retroarch.cfg"
            retroarch.parent.mkdir(parents=True)
            retroarch.write_text('video_fullscreen = "true"\n'
                                 'system_directory = "/old/bios"\n')
            launcher_tv._configure_esde(home)
            self.assertIn('value="/emulation/roms"', settings.read_text())
            self.assertIn('value="user-theme"', settings.read_text())
            self.assertIn('video_fullscreen = "true"', retroarch.read_text())
            self.assertIn('system_directory = "/emulation/bios"', retroarch.read_text())
            for system, label in (("nes", "Nestopia UE"), ("psx", "PCSX ReARMed")):
                gamelist = (home / f"ES-DE/gamelists/{system}/gamelist.xml").read_text()
                # ES-DE 3.4.x reads alternativeEmulator beside gameList.
                fragment = gamelist.removeprefix('<?xml version="1.0"?>\n')
                document = ET.fromstring(f"<document>{fragment}</document>")
                self.assertEqual(document.findtext("./alternativeEmulator/label"), label)
                self.assertIsNotNone(document.find("./gameList"))

    def test_esde_configuration_preserves_existing_gamelist(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            gamelist = home / "ES-DE/gamelists/nes/gamelist.xml"
            gamelist.parent.mkdir(parents=True)
            original = '<gameList><game><name>My game</name></game></gameList>\n'
            gamelist.write_text(original)
            launcher_tv._configure_esde(home)
            self.assertEqual(gamelist.read_text(), original)

    def test_esde_finish_hides_data_folder_without_changing_other_home_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            hidden = home / ".hidden"
            hidden.write_text("Documents")
            binary = home / ".local/share/infinityos/tv/ES-DE.AppImage"
            with patch.object(launcher_tv, "_install_theme"), \
                 patch.object(launcher_tv, "_configure_esde"), \
                 patch.object(launcher_tv, "_run") as run:
                launcher_tv._finish_esde(home)
                launcher_tv._finish_esde(home)
            self.assertEqual(hidden.read_text(), "Documents\nES-DE\n")
            run.assert_any_call([str(binary), "--create-system-dirs"])

    def test_pinned_esde_download_is_verified_before_install(self):
        payload = b"AppImage test content"
        metadata = ("123", len(payload), hashlib.sha256(payload).hexdigest())
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(launcher_tv.os, "uname", return_value=SimpleNamespace(machine="x86_64")), \
             patch.dict(launcher_tv.ESDE, {"x86_64": metadata}), \
             patch.object(launcher_tv.urllib.request, "urlopen", return_value=io.BytesIO(payload)):
            binary = _install_esde(Path(directory))
            self.assertEqual(binary.read_bytes(), payload)
            self.assertTrue(os.access(binary, os.X_OK))

    def test_changed_esde_download_leaves_no_binary(self):
        payload = b"changed"
        metadata = ("123", len(payload), hashlib.sha256(b"original").hexdigest())
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(launcher_tv.os, "uname", return_value=SimpleNamespace(machine="x86_64")), \
             patch.dict(launcher_tv.ESDE, {"x86_64": metadata}), \
             patch.object(launcher_tv.urllib.request, "urlopen", return_value=io.BytesIO(payload)):
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                _install_esde(Path(directory))
            self.assertFalse((Path(directory) / ".local/share/infinityos/tv/ES-DE.AppImage").exists())

    def test_theme_is_staged_beside_its_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "ES-DE/themes/canvas-es-de"

            def git(command):
                if command[:3] == ["git", "init", "-q"]:
                    source = Path(command[3])
                    self.assertEqual(source.parent.parent, target.parent)
                    (source / ".git").mkdir(parents=True)
                    (source / "theme.xml").write_text("theme")

            with patch.object(launcher_tv, "_run", side_effect=git), \
                 patch.object(launcher_tv.subprocess, "run",
                              return_value=SimpleNamespace(stdout=launcher_tv.THEME_REVISION)):
                launcher_tv._install_theme(home)
            self.assertEqual((target / "theme.xml").read_text(), "theme")

    def test_esde_enable_uses_one_privileged_command(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / ".local/share/infinityos/tv/ES-DE.AppImage"
            with patch.object(launcher_tv, "_install_esde", return_value=binary), \
                 patch.object(launcher_tv, "_missing_packages", return_value=["cage"]), \
                 patch.object(launcher_tv, "_tree_hash", return_value="theme-hash"), \
                 patch.object(launcher_tv, "_run") as run:
                launcher_tv.set_enabled("esde", True, home)
            run.assert_called_once_with(
                ["pkexec", launcher_tv.CONTROL, "activate", "esde", str(os.getuid())])
            details = json.loads(launcher_tv._manifest(home, "esde").read_text())
            self.assertEqual(details["packages"], ["cage"])
            self.assertEqual((home / "Emulation").readlink(), Path("/emulation"))

    def test_esde_enable_preserves_existing_home_emulation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            shortcut = home / "Emulation"
            shortcut.mkdir()
            (shortcut / "keep.txt").write_text("user data")
            with patch.object(launcher_tv, "_install_esde"), \
                 patch.object(launcher_tv, "_missing_packages", return_value=[]), \
                 patch.object(launcher_tv, "_run"):
                launcher_tv.set_enabled("esde", True, home)
            self.assertFalse(shortcut.is_symlink())
            self.assertEqual((shortcut / "keep.txt").read_text(), "user data")

    def test_esde_retry_keeps_packages_recorded_before_previous_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            launcher_tv._save_manifest(home, "esde", {"packages": ["cage"], "settings": {}})
            with patch.object(launcher_tv, "_install_esde"), \
                 patch.object(launcher_tv, "_missing_packages", return_value=[]), \
                 patch.object(launcher_tv, "_tree_hash", return_value="theme-hash"), \
                 patch.object(launcher_tv, "_run"):
                launcher_tv.set_enabled("esde", True, home)
            details = json.loads(launcher_tv._manifest(home, "esde").read_text())
            self.assertEqual(details["packages"], ["cage"])

    def test_esde_retry_preserves_original_settings_and_theme_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / "ES-DE/settings/es_settings.xml"
            settings.parent.mkdir(parents=True)
            settings.write_text("original setting")
            theme = home / "ES-DE/themes/canvas-es-de"

            def failed_activation(_command):
                settings.write_text("new setting")
                theme.mkdir(parents=True)
                (theme / "theme.xml").write_text("managed theme")
                raise RuntimeError("system setup failed")

            with patch.object(launcher_tv, "_install_esde"), \
                 patch.object(launcher_tv, "_missing_packages", return_value=[]), \
                 patch.object(launcher_tv, "_run", side_effect=failed_activation):
                with self.assertRaisesRegex(RuntimeError, "system setup failed"):
                    launcher_tv.set_enabled("esde", True, home)
            self.assertFalse((home / "Emulation").exists())
            with patch.object(launcher_tv, "_install_esde"), \
                 patch.object(launcher_tv, "_missing_packages", return_value=[]), \
                 patch.object(launcher_tv, "_run"):
                launcher_tv.set_enabled("esde", True, home)
            details = json.loads(launcher_tv._manifest(home, "esde").read_text())
            self.assertEqual(details["settings"]["ES-DE/settings/es_settings.xml"]["previous"],
                             "original setting")
            self.assertEqual(details["theme_hash"], launcher_tv._tree_hash(theme))

    def test_steam_enable_uses_one_privileged_command(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(launcher_tv, "installed", return_value=True), \
             patch.object(launcher_tv, "_missing_packages", return_value=["gamescope"]), \
             patch.object(launcher_tv, "_run") as run:
            launcher_tv.set_enabled("steam", True, Path(directory))
            run.assert_called_once_with(
                ["pkexec", launcher_tv.CONTROL, "activate", "steam", str(os.getuid())])

    def test_privileged_esde_activation_finishes_as_selected_user(self):
        events = []
        account = SimpleNamespace(pw_name="gamer")
        with patch.object(control, "account", return_value=account), \
             patch.object(control, "prepare_emulation",
                          side_effect=lambda uid: events.append(("prepare", uid))), \
             patch.object(control, "enable",
                          side_effect=lambda mode, uid: events.append(("enable", mode, uid))), \
             patch.object(control.subprocess, "run",
                          side_effect=lambda command, check: events.append(("run", command))):
            control.activate("esde", "1000")
        self.assertEqual(events, [
            ("run", ["dnf", "-y", "install", *control.ESDE_PACKAGES]),
            ("prepare", "1000"),
            ("run", ["runuser", "-u", "gamer", "--", "/usr/bin/python3",
                     control.USER_SETUP, "--finish-esde"]),
            ("enable", "esde", "1000"),
        ])

    def test_privileged_arm_steam_activation_installs_all_dependencies(self):
        with patch.object(control, "account", return_value=SimpleNamespace(pw_name="gamer")), \
             patch.object(control.os, "uname", return_value=SimpleNamespace(machine="aarch64")), \
             patch.object(control.subprocess, "run") as run, \
             patch.object(control, "enable") as enable:
            control.activate("steam", "1000")
        run.assert_called_once_with(
            ["dnf", "-y", "install", *control.STEAM_PACKAGES,
             *control.STEAM_ARM_PACKAGES], check=True)
        enable.assert_called_once_with("steam", "1000")

    def test_failed_esde_user_setup_does_not_enable_boot_mode(self):
        with patch.object(control, "account", return_value=SimpleNamespace(pw_name="gamer")), \
             patch.object(control, "prepare_emulation"), \
             patch.object(control.subprocess, "run",
                          side_effect=[None, subprocess.CalledProcessError(1, "runuser")]), \
             patch.object(control, "enable") as enable:
            with self.assertRaises(subprocess.CalledProcessError):
                control.activate("esde", "1000")
        enable.assert_not_called()

    def test_arm_steam_client_defers_root_dependencies_to_tv_control(self):
        steam = next(app for app in launcher_tv.APPS if app.name == "Steam")
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(launcher_tv.os, "uname", return_value=SimpleNamespace(machine="aarch64")), \
             patch.object(launcher_tv, "installed", return_value=False), \
             patch.object(launcher_tv, "install") as install_client, \
             patch.object(launcher_tv, "_missing_packages", return_value=["gamescope"]), \
             patch.object(launcher_tv, "_run") as run:
            home = Path(directory)
            launcher_tv.set_enabled("steam", True, home)
        install_client.assert_called_once_with(steam, home, defer_system_dependencies=True)
        run.assert_called_once_with(
            ["pkexec", launcher_tv.CONTROL, "activate", "steam", str(os.getuid())])

    def test_privileged_deactivation_rejects_unmanaged_packages(self):
        with patch.object(control, "disable") as disable, \
             patch.object(control.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Unknown TV mode package"):
                control.deactivate("esde", ["kernel"])
            disable.assert_not_called()
            run.assert_not_called()

    def test_disable_removes_integration_and_preserves_roms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            account = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_name="gamer", pw_dir=str(root))
            with patch.object(control, "STATE", root / "state"), \
                 patch.object(control, "NEXT", root / "next"), \
                 patch.object(control, "DROPINS", root / "dropins"), \
                 patch.object(control, "account", return_value=account), \
                 patch.object(control, "refresh_boot_menu"), \
                 patch.object(control.subprocess, "run"):
                control.enable("esde", "1000")
                rom = root / "emulation/roms/nes/game.rom"
                rom.parent.mkdir(parents=True)
                rom.write_bytes(b"user ROM")
                bios = root / "emulation/bios/user.bin"
                bios.parent.mkdir(parents=True)
                bios.write_bytes(b"user BIOS")
                control.disable("esde")
                self.assertFalse((root / "state/esde").exists())
                self.assertFalse(control.dropin("esde").exists())
                self.assertEqual(rom.read_bytes(), b"user ROM")
                self.assertEqual(bios.read_bytes(), b"user BIOS")

    def test_esde_uninstall_removes_only_managed_appimage(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher_tv, "_run"):
            home = Path(directory)
            binary = home / ".local/share/infinityos/tv/ES-DE.AppImage"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"managed application")
            saved = home / "ES-DE/gamelists/nes/gamelist.xml"
            saved.parent.mkdir(parents=True)
            saved.write_text("user metadata")
            launcher_tv.set_enabled("esde", False, home)
            self.assertFalse(binary.exists())
            self.assertEqual(saved.read_text(), "user metadata")

    def test_esde_uninstall_restores_unchanged_settings_and_keeps_user_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            theme = home / "ES-DE/themes/canvas-es-de"
            theme.mkdir(parents=True)
            (theme / "theme.xml").write_text("managed theme")
            settings = home / "ES-DE/settings/es_settings.xml"
            settings.parent.mkdir(parents=True)
            settings.write_text("managed setting")
            retroarch = home / ".config/retroarch/retroarch.cfg"
            retroarch.parent.mkdir(parents=True)
            retroarch.write_text("user changed this after setup")
            rom = home / "emulation/roms/nes/game.rom"
            rom.parent.mkdir(parents=True)
            rom.write_bytes(b"my ROM")
            launcher_tv._save_manifest(home, "esde", {
                "packages": ["cage"],
                "theme_hash": launcher_tv._tree_hash(theme),
                "settings": {
                    "ES-DE/settings/es_settings.xml": {
                        "previous": "original setting",
                        "applied": hashlib.sha256(settings.read_bytes()).hexdigest()},
                    ".config/retroarch/retroarch.cfg": {
                        "previous": "original config",
                        "applied": hashlib.sha256(b"managed config").hexdigest()},
                },
            })
            with patch.object(launcher_tv, "_run") as run, \
                 patch.object(launcher_tv, "_missing_packages", return_value=[]):
                launcher_tv.set_enabled("esde", False, home)
            self.assertFalse(theme.exists())
            self.assertEqual(settings.read_text(), "original setting")
            self.assertEqual(retroarch.read_text(), "user changed this after setup")
            self.assertEqual(rom.read_bytes(), b"my ROM")
            self.assertFalse(launcher_tv._manifest(home, "esde").exists())
            run.assert_called_once_with(
                ["pkexec", launcher_tv.CONTROL, "deactivate", "esde"])

    def test_failed_boot_menu_update_restores_enabled_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            (state / "esde").write_text("1000\n")
            with patch.object(control, "STATE", state), \
                 patch.object(control, "NEXT", root / "next"), \
                 patch.object(control, "DROPINS", root / "dropins"), \
                 patch.object(control, "refresh_boot_menu", side_effect=RuntimeError("EFI failed")), \
                 patch.object(control.subprocess, "run"):
                with self.assertRaisesRegex(RuntimeError, "EFI failed"):
                    control.disable("esde")
                self.assertEqual((state / "esde").read_text(), "1000\n")

    def test_second_account_cannot_take_over_tv_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            (state / "steam").write_text("1000\n")
            account = SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_name="second", pw_dir=str(root))
            with patch.object(control, "STATE", state), \
                 patch.object(control, "DROPINS", root / "dropins"), \
                 patch.object(control, "account", return_value=account), \
                 patch.object(control, "refresh_boot_menu") as refresh:
                with self.assertRaises(PermissionError):
                    control.enable("steam", "1001")
                self.assertEqual((state / "steam").read_text(), "1000\n")
                refresh.assert_not_called()

    def test_next_mode_is_one_shot_and_owned_by_user(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            (state / "steam").write_text("1000\n")
            dropins = root / "dropins"
            configuration = dropins / "infinityos-tv@steam.service.d/account.conf"
            configuration.parent.mkdir(parents=True)
            configuration.write_text("[Service]\nUser=gamer\n")
            with patch.object(control, "STATE", state), \
                 patch.object(control, "NEXT", root / "next"), \
                 patch.object(control, "DROPINS", dropins), \
                 patch.dict(os.environ, {"PKEXEC_UID": "1001"}), \
                 patch.object(control.subprocess, "run"):
                with self.assertRaises(PermissionError):
                    control.request_next("steam")
                self.assertFalse((root / "next").exists())
            with patch.object(control, "STATE", state), \
                 patch.object(control, "NEXT", root / "next"), \
                 patch.object(control, "DROPINS", dropins), \
                 patch.object(control, "installed_refind", return_value=True), \
                 patch.dict(os.environ, {"PKEXEC_UID": "1000"}), \
                 patch.object(control.subprocess, "run") as run:
                control.request_next("steam")
                self.assertEqual((root / "next").read_text(), "steam\n")
                self.assertEqual(run.call_args_list, [
                    call(["/usr/libexec/infinityos-refind-config"], check=True),
                    call(["systemctl", "reboot"], check=True),
                ])

    def test_explicit_boot_only_consumes_matching_one_shot_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            next_mode = Path(directory) / "next"
            next_mode.write_text("steam\n")
            with patch.object(control, "NEXT", next_mode), \
                 patch.object(control, "installed_refind", return_value=True), \
                 patch.object(control.subprocess, "run") as run:
                control.consume("esde")
                self.assertEqual(next_mode.read_text(), "steam\n")
                run.assert_not_called()
                control.consume("steam")
                self.assertFalse(next_mode.exists())
                run.assert_called_once_with(
                    ["/usr/libexec/infinityos-refind-config"], check=True)

    def test_failed_reboot_does_not_leave_new_one_shot_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            (state / "steam").write_text("1000\n")
            dropins = root / "dropins"
            configuration = dropins / "infinityos-tv@steam.service.d/account.conf"
            configuration.parent.mkdir(parents=True)
            configuration.write_text("[Service]\nUser=gamer\n")
            with patch.object(control, "STATE", state), \
                 patch.object(control, "NEXT", root / "next"), \
                 patch.object(control, "DROPINS", dropins), \
                 patch.object(control, "installed_refind", return_value=True), \
                 patch.dict(os.environ, {"PKEXEC_UID": "1000"}), \
                 patch.object(control.subprocess, "run",
                              side_effect=[None, RuntimeError("reboot failed"), None]) as run:
                with self.assertRaisesRegex(RuntimeError, "reboot failed"):
                    control.request_next("steam")
                self.assertFalse((root / "next").exists())
                self.assertEqual(run.call_args_list, [
                    call(["/usr/libexec/infinityos-refind-config"], check=True),
                    call(["systemctl", "reboot"], check=True),
                    call(["/usr/libexec/infinityos-refind-config"], check=True),
                ])

    def test_failed_default_restore_keeps_pending_tv_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            next_mode = Path(directory) / "next"
            next_mode.write_text("esde\n")
            with patch.object(control, "NEXT", next_mode), \
                 patch.object(control, "installed_refind", return_value=True), \
                 patch.object(control.subprocess, "run", side_effect=RuntimeError("ESP unavailable")):
                with self.assertRaisesRegex(RuntimeError, "ESP unavailable"):
                    control.consume("esde")
            self.assertEqual(next_mode.read_text(), "esde\n")


if __name__ == "__main__":
    unittest.main()
