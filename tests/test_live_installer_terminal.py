"""InfinityTerminal remains available around a live installation."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


WRAPPER = Path(__file__).resolve().parents[1] / "root/usr/libexec/infinityos-liveinst"
EXTENSION = "ghostty@infinityos.org"


class LiveInstallerTerminalTests(unittest.TestCase):
    def test_terminal_state_is_restored_after_installer_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            terminal_state = root / "terminal-state"
            events = root / "events"
            extensions = root / "gnome-extensions"
            extensions.write_text("""#!/bin/sh
case "$1" in
  list) cat "$TEST_STATE" ;;
  disable) printf 'disable\n' >> "$TEST_LOG"; : > "$TEST_STATE" ;;
  enable) printf 'enable\n' >> "$TEST_LOG"; printf '%s\n' "$2" > "$TEST_STATE" ;;
esac
""")
            extensions.chmod(0o755)
            installer = root / "liveinst"
            installer.write_text("""#!/bin/sh
test ! -s "$TEST_STATE" || exit 90
printf 'liveinst\n' >> "$TEST_LOG"
exit "$TEST_INSTALLER_STATUS"
""")
            installer.chmod(0o755)
            environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                               TEST_STATE=str(terminal_state), TEST_LOG=str(events))

            for initially_enabled, installer_status, expected_events in (
                (True, 7, ["disable", "liveinst", "enable"]),
                (False, 0, ["liveinst"]),
            ):
                with self.subTest(initially_enabled=initially_enabled):
                    terminal_state.write_text(f"{EXTENSION}\n" if initially_enabled else "")
                    events.write_text("")
                    environment["TEST_INSTALLER_STATUS"] = str(installer_status)
                    result = subprocess.run([str(WRAPPER)], env=environment, check=False)
                    self.assertEqual(result.returncode, installer_status)
                    self.assertEqual(events.read_text().splitlines(), expected_events)
                    self.assertEqual(terminal_state.read_text(),
                                     f"{EXTENSION}\n" if initially_enabled else "")


if __name__ == "__main__":
    unittest.main()
