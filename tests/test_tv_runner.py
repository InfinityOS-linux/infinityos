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
        self.assertIn("Requires:       dbus-daemon\n", spec)
        self.assertIn("Requires:       dbus-tools\n", spec)
        self.assertIn("Requires:       gvfs\n", spec)
        unit = (ROOT / "root/usr/lib/systemd/system/infinityos-tv@.service").read_text()
        self.assertIn("Environment=XDG_SEAT=seat0 XDG_VTNR=1", unit)
        self.assertIn("ExecStartPre=+/usr/bin/chvt 1", unit)
        self.assertIn("/usr/bin/dbus-run-session -- /usr/libexec/infinityos-tv-run %i", unit)

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
                "steam": "exit 0\n",
                "gamescope": f'printf "%s:%s\\n" "$STEAM_GAMESCOPE_FORCE_HDR_DEFAULT" "$STEAM_GAMESCOPE_FORCE_OUTPUT_TO_HDR10PQ_DEFAULT" >> "$TV_RUN_TEST_HDR"\nprintf x >> "$TV_RUN_TEST_ATTEMPTS"\n'
                             f'test -f "${{INFINITYOS_TV_EXIT_REQUEST%/*}}/mounts-ready" || exit 42\nexit {result}\n',
                "cage": 'printf "%s|%s\\n" "$WLR_RENDERER" "$*" > "$TV_RUN_TEST_LOG"\n',
                "dbus-run-session": 'exit 99\n',
                "automount": 'printf "start\\n" >> "$TV_RUN_TEST_MOUNTS"\n[ "$1" = --ready-file ] || exit 98\n'
                             ': > "$2"\nexec /bin/sleep 15\n',
                "sleep": "exit 0\n",
            }
            for name, body in commands.items():
                executable = root / name
                executable.write_text("#!/bin/sh\n" + body)
                executable.chmod(0o755)
            log = root / "cage.log"
            attempts = root / "attempts"
            mounts = root / "mounts.log"
            runner = root / "runner"
            runner.write_text(RUNNER.read_text().replace("/usr/libexec/infinityos-automount", str(root / "automount")))
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                       HOME=str(home), TV_RUN_TEST_LOG=str(log),
                       TV_RUN_TEST_ATTEMPTS=str(attempts),
                       TV_RUN_TEST_MOUNTS=str(mounts), TV_RUN_TEST_HDR=str(root / "hdr.log"))
            completed = subprocess.run(["bash", str(runner), "steam"], env=env,
                                       capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual((root / "hdr.log").read_text().splitlines(), ["0:0"] * len(attempts.read_text()))
            self.assertEqual(mounts.read_text(), "start\n")
            self.assertNotIn("(42)", completed.stderr)
            return (completed, log.read_text() if log.exists() else None,
                    str(client), attempts.read_text() if attempts.exists() else "")

    def test_early_gamescope_failure_tries_software_cage(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(1)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("gamescope exited early", completed.stderr)
        self.assertEqual(fallback,
                         "pixman|-- /usr/libexec/infinityos-tv-steam-splash /usr/libexec/infinityos-steam -gamepadui -steamos3 -steampal -steamdeck\n")
        self.assertEqual(attempts, "x")

    def test_repeated_early_successes_try_cage_instead_of_returning_to_login(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(0)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Steam exited immediately", completed.stderr)
        self.assertIsNotNone(fallback)
        self.assertEqual(attempts, "xxxxxx")

    def test_session_switch_requests_shutdown(self):
        helper = ROOT / "root/usr/libexec/infinityos-tv-steam-exit"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = root / ".local/share/Steam/steamrt64/steam"
            client.parent.mkdir(parents=True)
            client.write_text('#!/bin/sh\nprintf "%s" "$*" > "$TV_RUN_TEST_LOG"\n')
            client.chmod(0o755)
            marker = root / "exit-requested"
            log = root / "shutdown.log"
            env = dict(os.environ, HOME=str(root), INFINITYOS_TV_EXIT_REQUEST=str(marker),
                       TV_RUN_TEST_LOG=str(log))
            subprocess.run(["bash", str(helper), "plasma"], env=env, check=True)
            self.assertTrue(marker.is_file())
            self.assertEqual(log.read_text(), "-shutdown")

    def test_arm_client_uses_the_same_fallback(self):
        completed, fallback, client, attempts = self._run_with_gamescope_result(1, "aarch64")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(fallback, f"pixman|-- /usr/libexec/infinityos-tv-steam-splash {client} -gamepadui -steamos3 -steampal -steamdeck\n")
        self.assertEqual(attempts, "x")

    def test_arm_steam_restarts_after_successful_updater_exit(self):
        completed, fallback, _client, attempts = self._run_with_gamescope_result(0, "aarch64")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNotNone(fallback)
        self.assertEqual(attempts, "xxxxxx")

    def test_esde_prepares_input_and_prefers_kernel_xone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / ".local/share/infinityos/tv/ES-DE.AppImage"
            app.parent.mkdir(parents=True)
            app.touch(mode=0o755)
            for name, source in {
                "udevadm": 'printf "%s\\n" "$*"',
                "modinfo": '[ "$1" = xone_dongle ] && [ "$HAS_XONE" = 1 ]',
                "cage": 'printf "%s|%s\\n" "${SDL_JOYSTICK_HIDAPI_XBOX_ONE-unset}" "$*"',
            }.items():
                tool = root / name
                tool.write_text(f"#!/bin/sh\n{source}\n")
                tool.chmod(0o755)
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", HOME=str(root))
            env.pop("SDL_JOYSTICK_HIDAPI_XBOX_ONE", None)
            for has_xone, expected in (("1", "0"), ("0", "unset")):
                log = subprocess.check_output(["bash", str(RUNNER), "esde"],
                                              env=dict(env, HAS_XONE=has_xone), text=True)
                self.assertEqual(log.splitlines(), ["settle --timeout=3", f"{expected}|-- {app}"])


if __name__ == "__main__":
    unittest.main()
