"""Exercise the ISO publication gate with an isolated GitHub CLI fixture."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ensure-iso-rpms"
SHA = "a" * 40


def run_record(event="push", status="completed", conclusion="success", **extra):
    return dict(id=10, head_sha=SHA, head_branch="main", event=event,
                status=status, conclusion=conclusion, html_url="https://example.test/run", **extra)


class IsoRpmGateTests(unittest.TestCase):
    def gate(self, responses, *, main_sha=SHA, ref="refs/heads/main", api_failure=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.json").write_text(json.dumps({
                "responses": responses, "main_sha": main_sha, "api_failure": api_failure,
            }))
            gh = root / "gh"
            gh.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ["GATE_FIXTURE"])
fixture = json.loads((root / "fixture.json").read_text())
with (root / "calls").open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "workflow":
    sys.exit(0)
if fixture["api_failure"]:
    sys.exit(1)
if "/git/ref/" in sys.argv[2]:
    print(fixture["main_sha"])
else:
    counter = root / "counter"
    index = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(index + 1))
    responses = fixture["responses"]
    print(json.dumps({"workflow_runs": responses[min(index, len(responses) - 1)]}))
''')
            gh.chmod(0o755)
            sleep = root / "sleep"
            sleep.write_text("#!/bin/sh\nexit 0\n")
            sleep.chmod(0o755)
            result = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True,
                                    timeout=30, env={**os.environ,
                "PATH": f"{root}{os.pathsep}{os.environ['PATH']}", "GATE_FIXTURE": str(root),
                "GITHUB_SHA": SHA, "GITHUB_REF": ref, "GITHUB_REPOSITORY": "test/repo",
            })
            calls = [json.loads(line) for line in (root / "calls").read_text().splitlines()] \
                if (root / "calls").exists() else []
            return result, [call for call in calls if call[0] == "workflow"]

    def test_successful_push_or_manual_publication_is_accepted(self):
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event):
                result, dispatches = self.gate([[run_record(event)]])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(dispatches, [])

    def test_missing_publication_is_dispatched_once_and_waits_for_completion(self):
        result, dispatches = self.gate([[], [], [run_record("workflow_dispatch", "in_progress", None)],
                                       [run_record("workflow_dispatch")]])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(dispatches, [["workflow", "run", "publish-rpm.yml", "--repo", "test/repo", "--ref", "main"]])

    def test_pr_other_sha_and_other_branch_cannot_satisfy_gate(self):
        wrong_sha = {**run_record(), "head_sha": "b" * 40}
        wrong_branch = {**run_record(), "head_branch": "review/test"}
        result, dispatches = self.gate([[run_record("pull_request"), wrong_sha, wrong_branch],
                                       [run_record("workflow_dispatch")]])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(dispatches), 1)

    def test_existing_pending_run_is_not_duplicated(self):
        result, dispatches = self.gate([[run_record(status="queued", conclusion=None)], [run_record()]])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(dispatches, [])

    def test_failed_or_cancelled_publication_stops_iso(self):
        for conclusion in ("failure", "cancelled", "timed_out", "skipped"):
            with self.subTest(conclusion=conclusion):
                result, dispatches = self.gate([[run_record(conclusion=conclusion)]])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(conclusion, result.stderr)
                self.assertEqual(dispatches, [])

    def test_old_run_does_not_dispatch_for_new_main(self):
        result, dispatches = self.gate([[]], main_sha="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("main has moved", result.stderr)
        self.assertEqual(dispatches, [])

    def test_non_main_iso_is_rejected(self):
        result, dispatches = self.gate([[run_record()]], ref="refs/heads/review/test")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(dispatches, [])

    def test_api_failure_does_not_trigger_publication(self):
        result, dispatches = self.gate([[]], api_failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(dispatches, [])


if __name__ == "__main__":
    unittest.main()
