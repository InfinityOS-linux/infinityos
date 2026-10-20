import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "packages/infinity-config/root/usr/share/infinityos/diagnostics.py"
spec = importlib.util.spec_from_file_location("config_diagnostics", SOURCE)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class Result:
    returncode = 0
    stderr = "secret in stderr must not be saved"

    def __init__(self, stdout):
        self.stdout = stdout


class DiagnosticReportTests(unittest.TestCase):
    def test_report_contains_product_health_without_logs_or_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            (root / "etc").mkdir(parents=True)
            (root / "etc/os-release").write_text('ID=infinityos\nVERSION_ID="44"\n')
            (root / "var/lib/infinityos").mkdir(parents=True)
            (root / "var/lib/infinityos/backups-ready").touch()
            (root / "etc/infinityos").mkdir()
            (root / "etc/infinityos/refind-installed").touch()
            (root / "usr/share/infinityos").mkdir(parents=True)
            (root / "usr/share/infinityos/gnome-defaults").write_text(
                "enabled-extensions=['ding@rastersoft.com']\n")

            def run(args, **_kwargs):
                if args[0] == "gsettings":
                    return Result("['ding@rastersoft.com', 'private-user@example.org']")
                if args[0] == "findmnt":
                    return Result("btrfs")
                if args[0] == "gnome-shell":
                    return Result("GNOME Shell 50.6")
                return Result("1.0.0-1.fc44")

            output = Path(directory) / "reports/report.json"
            diagnostics.write_report(output, run, root)
            report = json.loads(output.read_text())
            self.assertEqual(report["root_filesystem"], "btrfs")
            self.assertTrue(report["backups_ready"])
            self.assertTrue(report["refind_installation_recorded"])
            self.assertNotIn("refind_boot_binary", report)
            self.assertEqual(report["enabled_packaged_extensions"], ["ding@rastersoft.com"])
            self.assertEqual(report["other_enabled_extension_count"], 1)
            self.assertNotIn("private-user@example.org", output.read_text())
            self.assertNotIn("secret", output.read_text())
            self.assertNotIn(str(Path.home()), output.read_text())
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(output.parent.stat().st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()
