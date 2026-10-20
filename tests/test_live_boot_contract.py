"""Keep the live installer bootable and require systemd-boot on the target."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class LiveBootContractTests(unittest.TestCase):
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
            # Anaconda 44 rejects inst.sdboot with a live payload. Its GRUB
            # install is converted in the required post script instead.
            self.assertNotIn("inst.sdboot", image.get("kernelcmdline", ""))

    def test_installer_must_report_failed_conversion(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("%post --erroronfail --log=/var/log/infinityos-boot-install.log", setup)
        self.assertIn("cat >> /usr/share/anaconda/interactive-defaults.ks <<'BOOT_POST_EOF'", setup)
        self.assertIn("cat >> /usr/share/anaconda/interactive-defaults.ks <<'NVIDIA_POST_EOF'", setup)
        self.assertNotIn("cat > /usr/share/anaconda/post-scripts/91-infinityos-boot.ks", setup)
        self.assertNotIn("Infinity OS boot setup deferred to first boot", setup)

    def test_installer_creates_branded_efi_directory(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn('EFI_HOME=$2', setup)
        self.assertIn('mkdir -p "$EFI_HOME"', setup)

    def test_boot_entry_reads_partition_number_without_padding(self):
        installer = (REPO / "root/usr/libexec/infinityos-liveinstall-boot-setup").read_text()
        self.assertIn('lsblk -nr -o PARTN "$esp_device"', installer)

    def test_live_installer_disables_extensions(self):
        setup = (REPO / "config.sh").read_text()
        wrapper = (REPO / "root/usr/libexec/infinityos-liveinst").read_text()
        self.assertIn("installer_desktop=/usr/share/applications/liveinst.desktop", setup)
        self.assertIn("Exec=/usr/libexec/infinityos-liveinst", setup)
        self.assertIn("disable-user-extensions true", wrapper)

    def test_live_power_settings_reach_account_created_on_first_boot(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("/etc/skel/.config/autostart/infinityos-live-power.desktop", setup)
        self.assertNotIn("/home/liveuser/.config/autostart/infinityos-live-power.desktop", setup)

    def test_release_has_an_installed_system_audit(self):
        audit = (REPO / "root/usr/libexec/infinityos-audit-install").read_text()
        image_check = (REPO / "scripts/verify-infinity-iso").read_text()
        self.assertIn("BootCurrent:", audit)
        self.assertIn("/etc/infinityos/liveinstall-systemd-boot", audit)
        self.assertIn("/var/lib/infinityos/backups-ready", audit)
        self.assertIn("infinityos-audit-install", image_check)


if __name__ == "__main__":
    unittest.main()
