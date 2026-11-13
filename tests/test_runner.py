import json
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.run_son_checks import ROOT, main, run_checks
from src.commitment import prepare_commitment


class RunnerTests(unittest.TestCase):
    def test_recorded_cases_match_expectations_and_do_not_export_normal_r(self):
        secret_fixture = "f1" * 16
        prepared = prepare_commitment("A01", "U03", 120000, randomness=secret_fixture)
        with patch("experiments.run_son_checks.prepare_commitment", return_value=prepared):
            data = run_checks()
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(len(data["cases"]), 10)
        self.assertNotIn(secret_fixture, json.dumps(data))
        self.assertIn("src/commitment.py", data["source_sha256"])
        self.assertIn("experiments/guessing.py", data["source_sha256"])
        self.assertTrue(all(len(digest) == 64 for digest in data["source_sha256"].values()))

    def test_runner_cli_writes_readable_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "checks.json"
            run = subprocess.run(
                [sys.executable, "-m", "experiments.run_son_checks", "--output", str(target)],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(data["all_checks_passed"])
            self.assertIn("10/10", run.stdout)

    def test_runner_returns_failure_exit_code_for_failed_check(self):
        with patch("experiments.run_son_checks.run_checks", return_value={
            "all_checks_passed": False, "cases": [{"passed": False}],
        }), tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--output", str(Path(directory) / "failure.json")]), 1)

    def test_demo_discloses_opening_only_after_reveal_marker(self):
        run = subprocess.run([sys.executable, "-m", "examples.commitment_demo"],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        commit_section, reveal_section = run.stdout.split("REVEAL:", 1)
        self.assertNotIn('"bid":', commit_section)
        self.assertNotIn('"randomness":', commit_section)
        self.assertIn('"randomness":', reveal_section)
        self.assertIn("Hash matches the retained commitment: True", reveal_section)


if __name__ == "__main__":
    unittest.main()
