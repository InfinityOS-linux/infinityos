"""Keep dock clicks on the Shell drop-down path without changing the service."""

import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "packages/infinity-terminal/root"
DOCK = Path(__file__).resolve().parents[1] / "root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/dock.js"
TERMINAL = ROOT / "usr/bin/infinity-terminal"
EXTENSION = ROOT / "usr/share/gnome-shell/extensions/ghostty@infinityos.org"


class TerminalToggleTests(unittest.TestCase):
    def test_dock_requests_drop_down_toggle(self):
        desktop = (ROOT / "usr/share/applications/com.infinityos.GhosTTY.desktop").read_text()
        service = (ROOT / "usr/lib/systemd/user/ghostty.service").read_text()
        self.assertIn("Exec=infinity-terminal --toggle\n", desktop)
        self.assertIn("ExecStart=/usr/bin/infinity-terminal --service\n", service)

        with tempfile.TemporaryDirectory() as directory:
            mock_bin = Path(directory)
            (mock_bin / "date").write_text("#!/bin/sh\nprintf '1234567890123456789\\n'\n")
            (mock_bin / "gsettings").write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$GSETTINGS_SCHEMA_DIR\" \"$@\" > \"$TOGGLE_ARGS\"\n"
            )
            for program in ("date", "gsettings"):
                (mock_bin / program).chmod(0o755)
            output = mock_bin / "args"
            result = subprocess.run(
                [str(TERMINAL), "--toggle"],
                env={**os.environ, "PATH": f"{mock_bin}:{os.environ['PATH']}",
                     "TOGGLE_ARGS": str(output)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text().splitlines(), [
                "/usr/share/gnome-shell/extensions/ghostty@infinityos.org/schemas",
                "set", "org.infinityos.GhosTTY", "toggle-request", "1234567890123456789"
            ])

            output.unlink()
            result = subprocess.run(
                [str(TERMINAL)],
                env={**os.environ, "PATH": f"{mock_bin}:{os.environ['PATH']}",
                     "TOGGLE_ARGS": str(output)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text().splitlines()[3], "toggle-request")

    def test_shell_controller_subscribes_to_toggle_request(self):
        schema = ET.parse(EXTENSION / "schemas/org.infinityos.GhosTTY.gschema.xml")
        keys = {key.get("name"): key.get("type") for key in schema.iter("key")}
        self.assertEqual(keys["toggle-request"], "x")
        source = (EXTENSION / "extension.js").read_text()
        self.assertIn("changed::toggle-request', () => this._toggle()", source)
        self.assertIn("this._settings.disconnect(this._toggleRequestId)", source)

    def test_new_terminal_window_stays_hidden_without_toggle_request(self):
        source = (EXTENSION / "extension.js").read_text()
        track = source.split("    _track(window, fresh) {", 1)[1].split("    _place(window) {", 1)[0]
        self.assertEqual(track.count("this._reveal(window)"), 1)
        self.assertIn("if (this._pendingShow) {\n                this._pendingShow = false;\n                this._reveal(window);", track)
        self.assertIn("if (fresh && !this._pendingShow)", track)

    def test_dock_does_not_activate_the_persistent_ghostty_window(self):
        dock = DOCK.read_text()
        self.assertIn("c._appwell.app?.get_id?.() === 'com.infinityos.GhosTTY.desktop'", dock)
        self.assertIn("Gio.Subprocess.new(['/usr/bin/infinity-terminal', '--toggle']", dock)
        create = dock.split("dash._createAppItem = function (app) {", 1)[1].split(
            "this.dash = dash;", 1)[0]
        self.assertIn("item.child.activate = toggleInfinityTerminal", create)

if __name__ == "__main__":
    unittest.main()
