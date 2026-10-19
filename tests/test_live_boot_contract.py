"""Keep the Infinity live ISO on UEFI systemd-boot without breaking Anaconda."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class LiveBootContractTests(unittest.TestCase):
    def test_infinity_live_profile_uses_systemd_boot_on_both_architectures(self):
        workstation = ET.parse(REPO / "teams/workstation.xml").getroot()
        profile = workstation.find("./profiles/profile[@name='Infinity-GNOME-Live']")
        requirements = {item.get("profile") for item in profile.findall("requires")}
        self.assertIn("InfinityLiveInstall", requirements)
        self.assertNotIn("LiveInstall", requirements)

        live = ET.parse(REPO / "components/liveinstall.xml").getroot()
        preferences = live.findall("./preferences[@profiles='InfinityLiveInstall']")
        self.assertEqual({item.get("arch") for item in preferences}, {"x86_64", "aarch64"})
        for item in preferences:
            image = item.find("type")
            self.assertEqual(image.get("firmware"), "uefi")
            self.assertGreaterEqual(int(image.get("efifatimagesize")), 512)
            self.assertEqual(image.find("bootloader").get("name"), "systemd_boot")
            # Anaconda 44 rejects inst.sdboot with a live payload. Its GRUB
            # install is converted in the required post script instead.
            self.assertNotIn("inst.sdboot", image.get("kernelcmdline", ""))

    def test_installer_must_report_failed_conversion(self):
        setup = (REPO / "config.sh").read_text()
        self.assertIn("%post --erroronfail --log=/var/log/infinityos-boot-install.log", setup)
        self.assertNotIn("Infinity OS boot setup deferred to first boot", setup)


if __name__ == "__main__":
    unittest.main()
