"""Keep the live installer bootable and publish rEFInd media."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from struct import unpack


REPO = Path(__file__).resolve().parents[1]


class LiveBootContractTests(unittest.TestCase):
    def test_disk_profile_does_not_request_grub_firmware_packages(self):
        boot = ET.parse(REPO / "components/boot.xml").getroot()
        profile = boot.find("./profiles/profile[@name='InfinityBootDiskCore']")
        requirements = {item.get("profile") for item in profile.findall("requires")}
        self.assertIn("InfinityBootCore", requirements)
        self.assertNotIn("BootCore", requirements)
        image = boot.find("./preferences[@profiles='InfinityBootDiskCore']/type")
        self.assertEqual(image.find("bootloader").get("name"), "custom")
        packages = [
            package.get("name")
            for group in boot.findall("./packages")
            if "InfinityBootCore" in group.get("profiles", "").split(",")
            for package in group.findall("package")
        ]
        self.assertFalse(any(name.startswith("grub2-") for name in packages))
        self.assertNotIn("systemd-boot-unsigned", packages)

    def test_infinity_live_profile_uses_supported_iso_bootloader(self):
        workstation = ET.parse(REPO / "teams/workstation.xml").getroot()
        profile = workstation.find("./profiles/profile[@name='Infinity-GNOME-Live']")
        requirements = {item.get("profile") for item in profile.findall("requires")}
        self.assertIn("LiveInstall", requirements)

        live = ET.parse(REPO / "components/liveinstall.xml").getroot()
        preferences = live.findall("./preferences[@profiles='LiveInstall']")
        self.assertTrue({"x86_64", "aarch64"}.issubset({item.get("arch") for item in preferences}))
        for item in preferences:
            if item.get("arch") not in ("x86_64", "aarch64"):
                continue
            image = item.find("type")
            self.assertEqual(image.get("firmware"), "uefi")
            self.assertLessEqual(int(image.get("efifatimagesize")), 31)
            self.assertEqual(image.find("bootloader").get("name"), "grub2")
            # KIWI composes with GRUB, then the ISO finalizer replaces its
            # EFI boot image with rEFInd before release.
            self.assertNotIn("inst.sdboot", image.get("kernelcmdline", ""))

    def test_installer_must_report_failed_conversion(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("%post --erroronfail --log=/var/log/infinityos-boot-install.log", setup)
        # Anaconda's automatic partitioning omits the ESP when its bootloader
        # is disabled, so conversion must run after normal UEFI partitioning.
        self.assertNotIn("bootloader --location=none", setup)
        verifier = (REPO / "scripts/verify-infinity-iso").read_text()
        self.assertIn("if grep -Fqx 'bootloader --location=none'", verifier)
        self.assertIn("cat >> /usr/share/anaconda/interactive-defaults.ks <<'BOOT_POST_EOF'", setup)
        self.assertIn("cat >> /usr/share/anaconda/interactive-defaults.ks <<'NVIDIA_POST_EOF'", setup)
        self.assertNotIn("cat > /usr/share/anaconda/post-scripts/91-infinityos-boot.ks", setup)
        self.assertNotIn("Infinity OS boot setup deferred to first boot", setup)

    def test_installer_creates_branded_efi_directory(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn('EFI_HOME=$2', setup)
        self.assertIn('mkdir -p "$EFI_HOME"', setup)

    def test_boot_entry_reads_partition_number_without_padding(self):
        installer = (REPO / "root/usr/libexec/infinityos-refind-install").read_text()
        self.assertIn('lsblk -nr -o PARTN "$esp_device"', installer)

    def test_live_installer_keeps_dock_active(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("installer_desktop=/usr/share/applications/liveinst.desktop", setup)
        self.assertIn("grep -qx 'Exec=liveinst'", setup)
        self.assertIn("Icon=infinity-installer", setup)
        icon = REPO / "root/usr/share/icons/hicolor/256x256/apps/infinity-installer.png"
        self.assertTrue(icon.is_file())
        data = icon.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(unpack(">II", data[16:24]), (256, 256))
        self.assertEqual(data[25], 6)  # RGBA
        self.assertNotIn("disable-user-extensions", setup)
        self.assertFalse((REPO / "root/usr/libexec/infinityos-liveinst").exists())

    def test_mascot_is_used_by_installer_and_boot_animation(self):
        source = REPO / "assets/infinityos-mascot.png"
        frame = REPO / "root/usr/share/plymouth/themes/infinityos/throbber-0001.png"
        for path in (source, frame):
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(data[25], 6)  # RGBA
        self.assertFalse((REPO / "root/usr/share/icons/hicolor/scalable/apps/infinity-installer.svg").exists())

    def test_welcome_uses_mascot_and_refind_uses_original_symbol(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("iconName: 'infinity-installer'", setup)
        self.assertIn("Icon=infinityos-logo", setup)
        verifier = (REPO / "scripts/verify-infinity-iso").read_text()
        self.assertIn("iconName: 'infinity-installer'", verifier)
        generator = (REPO / "scripts/generate-mascot-assets.py").read_text()
        self.assertNotIn("refind-theme", generator)
        refind_generator = (REPO / "scripts/generate-refind-icons.sh").read_text()
        generated_names = refind_generator.split("for name in ", 1)[1].split("; do", 1)[0].split()
        for name in ("infinityos", "infinityos-live"):
            self.assertTrue((REPO / f"assets/refind-icons/{name}.svg").is_file())
            self.assertIn(name, generated_names)

    def test_live_session_settings_reach_account_created_on_first_boot(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("/etc/skel/.config/autostart/infinityos-live-power.desktop", setup)
        self.assertNotIn("/home/liveuser/.config/autostart/infinityos-live-power.desktop", setup)
        self.assertIn("system-db:infinityos-live", setup)
        self.assertIn("idle-delay=uint32 0", setup)
        self.assertIn("idle-activation-enabled=false", setup)
        self.assertIn("sleep-inactive-ac-type='nothing'", setup)
        self.assertIn("sleep-inactive-battery-type='nothing'", setup)
        self.assertIn("disabled-extensions=['ghostty@infinityos.org']", setup)
        target_setup = (REPO / "root/usr/libexec/infinityos-liveinstall-boot-setup").read_text()
        self.assertIn("printf 'user-db:user\\nsystem-db:local\\n' > /etc/dconf/profile/user", target_setup)
        self.assertIn("rm -f /etc/dconf/db/infinityos-live", target_setup)
        self.assertIn("rm -f /etc/skel/.config/autostart/infinityos-live-power.desktop", target_setup)

    def test_release_has_an_installed_system_audit(self):
        audit = (REPO / "root/usr/libexec/infinityos-audit-install").read_text()
        image_check = (REPO / "scripts/verify-infinity-iso").read_text()
        self.assertIn("active_infinity_boot", audit)
        self.assertIn("EFI/refind/refind_", audit)
        self.assertIn("/etc/infinityos/refind-installed", audit)
        self.assertIn("/var/lib/infinityos/backups-ready", audit)
        self.assertIn("infinityos-audit-install", image_check)
        builder = (REPO / "kiwi-build").read_text()
        finalizer = (REPO / "scripts/finalize-infinity-iso").read_text()
        self.assertIn("scripts/finalize-infinity-iso", builder)
        self.assertIn('install -m 0644 "$kernel" "$efi_mount/os/linux"', finalizer)
        self.assertIn("menuentry \"Infinity OS Live\"", finalizer)
        for label in ("live", "check", "safe"):
            self.assertIn(f"icon /EFI/BOOT/infinity-theme/icons/os_infinityos_{label}.png", finalizer)
        self.assertIn("-rm_r /boot/grub2", finalizer)


if __name__ == "__main__":
    unittest.main()
