import hashlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "packages/infinity-setup/root/usr/share/infinityos"
sys.path.insert(0, str(CATALOG))
from launcher_tv import _install_esde
import launcher_tv

CONTROL = ROOT / "root/usr/libexec/infinityos-tv-control"
SPEC = importlib.util.spec_from_loader("infinityos_tv_control", loader=None)
control = importlib.util.module_from_spec(SPEC)
exec(compile(CONTROL.read_text(), str(CONTROL), "exec"), control.__dict__)


class TVModeTests(unittest.TestCase):
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
            self.assertEqual(
                ET.parse(home / "ES-DE/gamelists/nes/gamelist.xml")
                  .findtext("./alternativeEmulator/label"), "Nestopia UE")
            self.assertEqual(
                ET.parse(home / "ES-DE/gamelists/psx/gamelist.xml")
                  .findtext("./alternativeEmulator/label"), "PCSX ReARMed")

    def test_esde_configuration_preserves_existing_gamelist(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            gamelist = home / "ES-DE/gamelists/nes/gamelist.xml"
            gamelist.parent.mkdir(parents=True)
            original = '<gameList><game><name>My game</name></game></gameList>\n'
            gamelist.write_text(original)
            launcher_tv._configure_esde(home)
            self.assertEqual(gamelist.read_text(), original)

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
            self.assertEqual(run.call_args_list[-1].args[0],
                             ["pkexec", "dnf", "-y", "remove", "cage"])

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
                 patch.dict(os.environ, {"PKEXEC_UID": "1000"}), \
                 patch.object(control.subprocess, "run") as run:
                control.request_next("steam")
                self.assertEqual((root / "next").read_text(), "steam\n")
                run.assert_called_once_with(["systemctl", "reboot"], check=True)

    def test_explicit_boot_only_consumes_matching_one_shot_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            next_mode = Path(directory) / "next"
            next_mode.write_text("steam\n")
            with patch.object(control, "NEXT", next_mode):
                control.consume("esde")
                self.assertEqual(next_mode.read_text(), "steam\n")
                control.consume("steam")
                self.assertFalse(next_mode.exists())

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
                 patch.dict(os.environ, {"PKEXEC_UID": "1000"}), \
                 patch.object(control.subprocess, "run", side_effect=RuntimeError("reboot failed")):
                with self.assertRaisesRegex(RuntimeError, "reboot failed"):
                    control.request_next("steam")
                self.assertFalse((root / "next").exists())


if __name__ == "__main__":
    unittest.main()
