import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-brand-installer"


class InstallerBrandingTests(unittest.TestCase):
    def test_fedora_webui_68_completion_is_branded_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            webui = Path(directory)
            (webui / "VERSION.txt").write_text("68\n")
            source = (
                'Y.format(Yo("To begin using $0, reboot your system."),p.PRETTY_NAME)'
                'Yo(d?"Reboot to installed system":"Exit to live desktop")'
                'secondary:e==="success"&&Le.default.createElement(it,{onClick:Qp}'
            )
            (webui / "index.js.gz").write_bytes(gzip.compress(source.encode()))
            (webui / "po.pl.js.gz").write_bytes(gzip.compress(b'cockpit.locale({"undo":[null,"cofnij"]\n});\n'))
            (webui / "index.html").write_text("<html><head></head></html>")
            for asset in ("infinityos-installer.css", "infinityos-installer-audio.js",
                          "infinityos-installer-music.mp3"):
                (webui / asset).write_bytes(b"test asset")
            for _ in range(2):
                subprocess.run([sys.executable, str(SCRIPT), str(webui)], check=True)
            result = gzip.decompress((webui / "index.js.gz").read_bytes()).decode()
            self.assertIn('Y.spawn(["systemctl","reboot"],{superuser:"require"})', result)
            self.assertIn('Yo("Reboot to installed system")+" · "+Yo("Remove")+" USB"', result)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer.css"), 1)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer-audio.js"), 1)
            self.assertIn("Gdy rozpocznie się restart, wyjmij USB", gzip.decompress(
                (webui / "po.pl.js.gz").read_bytes()).decode())

    def test_unknown_webui_version_is_rejected_before_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            webui = Path(directory)
            (webui / "VERSION.txt").write_text("69\n")
            result = subprocess.run([sys.executable, str(SCRIPT), str(webui)],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsupported Anaconda WebUI version", result.stderr)

    def test_missing_music_fails_before_branding(self):
        with tempfile.TemporaryDirectory() as directory:
            webui = Path(directory)
            (webui / "VERSION.txt").write_text("68\n")
            (webui / "infinityos-installer.css").write_text("/* style */")
            (webui / "infinityos-installer-audio.js").write_text("// controls")
            (webui / "index.html").write_text("<html><head></head></html>")
            result = subprocess.run([sys.executable, str(SCRIPT), str(webui)],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing InfinityOS installer asset: infinityos-installer-music.mp3",
                          result.stderr)
            self.assertEqual((webui / "index.html").read_text(), "<html><head></head></html>")


if __name__ == "__main__":
    unittest.main()
