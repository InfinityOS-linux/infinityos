import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-brand-installer"
CSS = Path(__file__).resolve().parents[1] / "root/usr/share/cockpit/anaconda-webui/infinityos-installer.css"


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
            (webui / "po.pl.js.gz").write_bytes(gzip.compress(
                b'cockpit.locale({"undo":[null,"cofnij"],"Quit": [\n  null,\n  "Zako\xc5\x84cz"\n ]\n});\n'))
            (webui / "index.html").write_text("<html><head></head></html>")
            for asset in ("infinityos-installer.css", "infinityos-installer-audio.js",
                          "infinityos-installer-mark.svg", "infinityos-installer-music.mp3",
                          *(f"infinityos-plex-{weight}.woff2" for weight in (
                              "regular", "medium", "semibold", "bold")),
                          *(f"infinityos-step-{name}.svg" for name in (
                              "language", "time", "method", "storage", "accounts", "review"))):
                (webui / asset).write_bytes(b"test asset")
            for _ in range(2):
                subprocess.run([sys.executable, str(SCRIPT), str(webui)], check=True)
            result = gzip.decompress((webui / "index.js.gz").read_bytes()).decode()
            self.assertIn('Y.spawn(["systemctl","reboot"],{superuser:"require"})', result)
            self.assertIn('Yo("Reboot to installed system")+" · "+Yo("Remove")+" USB"', result)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer.css"), 1)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer-audio.js"), 1)
            locale = gzip.decompress((webui / "po.pl.js.gz").read_bytes()).decode()
            self.assertIn("Gdy rozpocznie się restart, wyjmij USB", locale)
            self.assertIn('"Quit": [\n  null,\n  "Przerwij"\n ]', locale)
            css = CSS.read_text()
            self.assertIn(".pf-v6-c-action-list__item:has(#installation-quit-btn)", css)
            self.assertIn(".pf-v6-c-action-list__item:has(#installation-next-btn)", css)

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
            (webui / "infinityos-installer-mark.svg").write_text("<svg/>")
            (webui / "index.html").write_text("<html><head></head></html>")
            result = subprocess.run([sys.executable, str(SCRIPT), str(webui)],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing InfinityOS installer asset: infinityos-installer-music.mp3",
                          result.stderr)
            self.assertEqual((webui / "index.html").read_text(), "<html><head></head></html>")


if __name__ == "__main__":
    unittest.main()
