import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-brand-installer"
CSS = Path(__file__).resolve().parents[1] / "root/usr/share/cockpit/anaconda-webui/infinityos-installer.css"


class InstallerBrandingTests(unittest.TestCase):
    def test_fedora_webui_90_completion_is_branded_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            webui = Path(directory)
            (webui / "VERSION.txt").write_text("90\n")
            source = (
                'y.format(jo("To begin using $0, reboot your system."),m.PRETTY_NAME)'
                'key:"reboot",onClick:kw},jo("Reboot")'
                'this.id="anaconda-screen-language",this.label=Zz("Welcome"),this.title=Zz("Welcome to Fedora Linux")'
                'this.id="anaconda-screen-date-time",this.label=q$("Date and time")'
                'this.id="anaconda-screen-method",this.label=Uet("Installation method")'
                'this.id="anaconda-screen-storage-configuration",this.label=hJ("Storage configuration"),this.title=hJ("Storage configuration")'
                'this.id="anaconda-screen-accounts",this.label=iet("Create Account")'
                'this.id="anaconda-screen-review",this.label=Pz("Review and install"),this.title=Pz("Review and install")'
                'label:cot("Storage configuration"),steps:[r]'
            )
            (webui / "index.js.gz").write_bytes(gzip.compress(source.encode()))
            (webui / "po.pl.js.gz").write_bytes(gzip.compress(
                b'cockpit.locale({"undo":[null,"cofnij"],"Quit": [\n  null,\n  "Zako\xc5\x84cz"\n ],'
                b'"Quit installer?": [null, "Zakoncz instalatora?"],'
                b'"Storage configuration": [\n  null,\n  "Konfiguracja"\n ]\n});\n'))
            (webui / "index.html").write_text("<html><head></head></html>")
            for asset in ("infinityos-installer.css", "infinityos-installer-audio.js",
                          "infinityos-installer-mark.svg", "infinityos-installer-mascot.png",
                          "infinityos-installer-music.mp3",
                          *(f"infinityos-plex-{weight}.woff2" for weight in (
                              "regular", "medium", "semibold", "bold")),
                          *(f"infinityos-step-{name}.svg" for name in (
                              "language", "time", "method", "storage", "accounts", "review"))):
                (webui / asset).write_bytes(b"test asset")
            for _ in range(2):
                subprocess.run([sys.executable, str(SCRIPT), str(webui)], check=True)
            result = gzip.decompress((webui / "index.js.gz").read_bytes()).decode()
            self.assertIn('y.spawn(["systemctl","reboot"],{superuser:"require"})', result)
            self.assertIn('jo("Reboot to installed system")+" · "+jo("Remove")+" USB"', result)
            for label in ("Language and layout", "Time and region", "Installation destination",
                          "Security", "User", "Summary"):
                self.assertIn(f'("{label}")', result)
            self.assertIn('label:cot("Security"),steps:[r]', result)
            self.assertIn('this.title=hJ("Storage configuration")', result)
            self.assertIn('this.title=Pz("Review and install")', result)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer.css"), 1)
            self.assertEqual((webui / "index.html").read_text().count("infinityos-installer-audio.js"), 1)
            locale = gzip.decompress((webui / "po.pl.js.gz").read_bytes()).decode()
            self.assertIn("Gdy rozpocznie się restart, wyjmij USB", locale)
            self.assertIn('"Quit": [\n  null,\n  "Zakończ"\n ]', locale)
            self.assertIn('"Quit installer?": [null, "Zakończyć instalację?"]', locale)
            self.assertIn('"Storage configuration": [\n  null,\n  "Konfiguracja"\n ]', locale)
            for english, polish in (
                ("Reboot to installed system", "Uruchom ponownie do zainstalowanego systemu"),
                ("Language and layout", "Język i układ"),
                ("Time and region", "Czas i region"),
                ("Installation destination", "Miejsce instalacji"),
                ("Security", "Bezpieczeństwo"),
                ("User", "Użytkownik"),
                ("Summary", "Podsumowanie"),
            ):
                self.assertEqual(locale.count(f'"{english}": [null, "{polish}"]'), 1)
            css = CSS.read_text()
            self.assertIn(".pf-v6-c-action-list__item:has(#installation-quit-btn)", css)
            self.assertIn(".pf-v6-c-action-list__item:has(#installation-next-btn)", css)
            self.assertIn("#app .anaconda-screen-progress-status .pf-v6-c-empty-state__footer .pf-v6-c-button.pf-m-link", css)

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
            (webui / "VERSION.txt").write_text("90\n")
            (webui / "infinityos-installer.css").write_text("/* style */")
            (webui / "infinityos-installer-audio.js").write_text("// controls")
            (webui / "infinityos-installer-mark.svg").write_text("<svg/>")
            (webui / "infinityos-installer-mascot.png").write_bytes(b"test asset")
            (webui / "index.html").write_text("<html><head></head></html>")
            result = subprocess.run([sys.executable, str(SCRIPT), str(webui)],
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing InfinityOS installer asset: infinityos-installer-music.mp3",
                          result.stderr)
            self.assertEqual((webui / "index.html").read_text(), "<html><head></head></html>")


if __name__ == "__main__":
    unittest.main()
