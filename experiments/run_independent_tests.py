"""Run the independent E01-E06 tests and export traceable JSON evidence.

Run from the repository root:
    python -m experiments.run_independent_tests --output results/independent_e01_e06_RUN01.json \
        --run-id RUN01 --runner "Chuc, own laptop"

Records per README "Evidence and reporting rules": per-case outcome, observed
values, Python version, platform, code commit, whether the working tree was
dirty, and SHA-256 of the executed sources. For an official run, commit first so
that git_head names the code that ran and working_tree_dirty is false.
Random values are fixed TEST fixtures except where a case states otherwise.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from src.commitment import ENCODING_ID
from tests import test_independent_e01_e06 as suite

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("Independent functional checks and bounded experiments. E01/E05/E06 show that the "
         "simulation enforces docs/model.md; E02-E04 illustrate behavior on specific cases. "
         "None of this proves hiding or binding.")
SOURCES = ("src/commitment.py", "src/auction.py", "experiments/guessing.py", "docs/model.md",
           "tests/oracle.py", "tests/test_independent_e01_e06.py",
           "experiments/run_independent_tests.py")


def _git(*args):
    try:
        done = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _manifest():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCES if (ROOT / name).exists()}


class Collector(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = {}
        self._t0 = {}

    def startTest(self, test):
        super().startTest(test)
        self._t0[test.id()] = time.perf_counter()

    def _row(self, test, status, detail=None):
        cid = suite.case_id(test._testMethodName)
        self.rows[cid] = {
            "id": cid, "test": test.id(), "status": status,
            "seconds": round(time.perf_counter() - self._t0.get(test.id(), 0), 4),
            "observed": suite.OBSERVATIONS.get(cid, {}),
            **({"detail": detail} if detail else {}),
        }

    def addSuccess(self, test):
        super().addSuccess(test)
        self._row(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._row(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._row(test, "ERROR", self._exc_info_to_string(err, test))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", default="unnamed")
    parser.add_argument("--runner", default="", help="who ran it, e.g. 'Chuc, own laptop'")
    args = parser.parse_args(argv)

    started = datetime.now(timezone.utc).isoformat()
    tests = unittest.TestLoader().loadTestsFromModule(suite)
    result = unittest.TextTestRunner(resultclass=Collector, verbosity=1, stream=sys.stderr).run(tests)

    # Untracked source files count as dirty; only the results/ folder is ignored.
    status = _git("status", "--porcelain", "--", ".", ":(exclude)results")
    cases = [result.rows[key] for key in sorted(result.rows)]
    evidence = {
        "schema_version": 2,
        "run_id": args.run_id,
        "run_kind": "independent tests E01-E06 (oracle written separately from src/)",
        "scope_note": SCOPE,
        "run_by": args.runner,
        "run_started_at_utc": started,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "working_tree_dirty": bool(status) if status is not None else None,
        "source_sha256": _manifest(),
        "encoding_id_under_test": ENCODING_ID,
        "parameters": {"auction_id": suite.AUCTION, "T1": suite.T1, "T2": suite.T2,
                       "min_bid": suite.MIN_BID, "max_bid": suite.MAX_BID, "bid_step": suite.STEP,
                       "domain_size": len(suite.DOMAIN),
                       "source": "docs/model.md; fixed r values are test fixtures"},
        "summary": {"tests": result.testsRun, "failures": len(result.failures),
                    "errors": len(result.errors), "all_passed": result.wasSuccessful(),
                    "experiments_covered": sorted({c["id"].split("-")[0] for c in cases})},
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}", file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
