"""Exercise the standalone Steam session fallback without a graphical VM."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "root/usr/libexec/infinityos-tv-run"


class TVRunnerTests(unittest.TestCase):
    def test_cage_fallback_is_available_after_setup_upgrade(self):
        spec = (ROOT / "packages/infinity-setup/infinity-setup.spec").read_text()
        self.assertIn("Requires:       cage\n", spec)

    def _run_with_gamescope_result(self, result, arch="x86_64"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            client = home / ".local/share/Steam/steamrtarm64/steam"
            client.parent.mkdir(parents=True)
            client.write_text("#!/bin/sh\nexit 0\n")
            client.chmod(0o755)
            commands = {
                "uname": f"printf '{arch}\\n'\n",
                "flatpak": "if [ \"$1\" = info ]; then exit 0; fi\n",
                "gamescope": f'printf x >> "$TV_RUN_TEST_ATTEMPTS"\nexit {result}\n',
                "cage": 'printf "%s|%s\\n" "$WLR_RENDERER" "$*" > "$TV_RUN_TEST_LOG"\n',
            }
            for name, body in commands.items():
                executable = root / name
                executable.write_text("#!/bin/sh\n" + body)
                executable.chmod(0o755)
            log = root / "cage.log"
            attempts = root / "attempts"
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                       HOME=str(home), TV_RUN_TEST_LOG=str(log),
                       TV_RUN_TEST_ATTEMPTS=str(attempts))
            completed = subprocess.run(["bash", str(RUNNER), "steam"], env=env,
                                       capture_output=True, text=True, check=False)
            return (completed, log.read_text() if log.exists() else None,
                    str(client), attempts.read_text() if attempts.exists() else "")

    def test_early_gamescope_failure_tries_software_cage(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(1)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("gamescope exited early", completed.stderr)
        self.assertEqual(fallback,
                         "pixman|-- flatpak run --user com.valvesoftware.Steam -gamepadui\n")
        self.assertEqual(attempts, "x")

    def test_successful_gamescope_does_not_start_fallback(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(0)
        self.assertEqual(completed.returncode, 0)
        self.assertIsNone(fallback)
        self.assertEqual(attempts, "xx")

    def test_arm_client_uses_the_same_fallback(self):
        completed, fallback, client, attempts = self._run_with_gamescope_result(1, "aarch64")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(fallback, f"pixman|-- {client} -gamepadui\n")
        self.assertEqual(attempts, "x")

    def test_arm_steam_restarts_after_successful_updater_exit(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(0, "aarch64")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(fallback)
        self.assertEqual(attempts, "xx")


if __name__ == "__main__":
    unittest.main()
