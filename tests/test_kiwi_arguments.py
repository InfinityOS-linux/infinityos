"""Exercise the wrapper without building an image (GNU getopt required)."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]

class KiwiArgumentTests(unittest.TestCase):
    def test_extra_arguments_survive_iso_and_isolated_builds(self):
        for isolated in (False, True):
            with self.subTest(isolated=isolated), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                log = root / "arguments"
                kiwi = root / "kiwi-ng"
                kiwi.write_text('#!/bin/bash\nprintf "%s\\0" "$@" > "$ARG_LOG"\n')
                kiwi.chmod(0o755)
                extras = ["--example=two words", "--another", "literal*value"]
                result = subprocess.run(
                    ["bash", str(REPO / "kiwi-build"), "--output-dir=" + str(root / "out"),
                     "--image-type=iso", "--image-profile=Test-Live", "--kiwi-bundle-format=iso"]
                    + (["--isolated"] if isolated else []) + ["--"] + extras,
                    cwd=REPO, env=dict(os.environ, PATH=str(root) + ":" + os.environ["PATH"], ARG_LOG=str(log)),
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                args = log.read_bytes().decode().rstrip("\0").split("\0")
                self.assertEqual(args[-5:-2], extras)
                self.assertTrue(args[-2].startswith("--set-type-attr=application_id="))
                self.assertTrue(args[-1].startswith("--set-type-attr=volid="))
