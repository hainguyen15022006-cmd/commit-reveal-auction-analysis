"""Run Sơn's controlled crypto checks and export traceable JSON evidence.

Run from the repository root: python -m experiments.run_son_checks --output PATH
These are author-run component checks, not Chúc's independent full-auction suite.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from experiments.guessing import guess_b0, guess_b1, guess_b2_disclosed_randomness, weak_randomness_candidates
from src.commitment import (
    ENCODING_ID, RANDOMNESS_BYTES, create_b0_commitment, create_b1_commitment,
    create_commitment, encode, prepare_commitment, verify_opening,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_R = "00112233445566778899aabbccddeeff"
REFERENCE_DIGEST = "7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71"


def _git(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def source_manifest() -> dict[str, str]:
    """Pin executed source bytes even when the working tree is not committed."""
    paths = sorted(p for folder in ("src", "experiments", "tests", "examples")
                   for p in (ROOT / folder).rglob("*.py"))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def run_checks() -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    bids = range(10000, 1000001, 10000)
    cases = []

    def record(case_id, purpose, inputs, expected, actual, limitation):
        cases.append({"id": case_id, "purpose": purpose, "inputs": inputs,
                      "expected": expected, "actual": actual,
                      "passed": actual == expected, "limitation": limitation})

    commitment = create_commitment("A01", "U01", 100000, FIXTURE_R)
    opening = {"auction_id": "A01", "bidder_id": "U01", "bid": 100000,
               "randomness": FIXTURE_R, "randomness_kind": "public fixed TEST fixture"}
    record("C01-vector", "Check the binary integration SHA-256 reference vector", opening,
           {"digest": REFERENCE_DIGEST}, {"digest": commitment},
           "A known-answer check verifies one encoding/hash vector, not protocol security.")
    for case_id, bid, r, expected in (
        ("C02-valid-opening", 100000, FIXTURE_R, True),
        ("E02-changed-bid", 140000, FIXTURE_R, False),
        ("E02-changed-r", 100000, "10112233445566778899aabbccddeeff", False),
    ):
        record(case_id, "Compare an opening with the fixed reference commitment",
               {**opening, "bid": bid, "randomness": r, "frozen_commitment": REFERENCE_DIGEST},
               {"hash_matches": expected},
               {"hash_matches": verify_opening(REFERENCE_DIGEST, "A01", "U01", bid, r)},
               "Hash matching alone does not admit a bid; auction rules are a separate layer.")

    record("C03-field-boundaries", "Distinguish records that naive concatenation confuses",
           {"identifier_pairs": [["1", "23"], ["12", "3"]], "bid": 100000,
            "randomness": FIXTURE_R, "randomness_kind": "public fixed TEST fixture"},
           {"encoded_records_differ": True},
           {"encoded_records_differ": encode("1", "23", 100000, FIXTURE_R) !=
                                      encode("12", "3", 100000, FIXTURE_R)},
           "This example illustrates field separation; accepted input rules define the encoding.")

    domain = {"minimum": 10000, "maximum_inclusive": 1000000, "step": 10000, "size": len(bids),
              "status": "illustrative experiment domain; not a new M1 price rule"}
    target_b0 = create_b0_commitment(130000)
    record("E03-b0-guessing", "Enumerate a known small bid domain", {"bid_domain": domain,
           "true_bid": 130000, "target": target_b0, "max_attempts": 100},
           {"status": "match", "attempts": 13, "bid": 130000, "randomness": None},
           asdict(guess_b0(target_b0, bids, max_attempts=100)),
           "This is an input-guessing demonstration, not a break of SHA-256.")

    weak_r = "00000000000000000000000000000007"
    target_weak = create_b1_commitment(130000, weak_r)
    record("E04-weak-r", "Enumerate a deliberately small randomness domain in B1",
           {"bid_domain": domain, "true_bid": 130000, "target": target_weak,
            "fixture_r": weak_r, "r_domain": "integers 0..15 encoded as 32 lowercase hex digits",
            "randomness_kind": "weak public-domain TEST configuration, not normal M1",
            "search_order": "r outer loop, ascending bids inner loop", "max_attempts": 1600},
           {"status": "match", "attempts": 713, "bid": 130000, "randomness": weak_r},
           asdict(guess_b1(target_weak, bids, weak_randomness_candidates(16), max_attempts=1600)),
           "Field width remains 128 bits, but only 16 candidate values are possible here.")

    target_b1 = create_b1_commitment(130000, FIXTURE_R)
    record("E04-disclosed-r-b1", "Guess B1 bids after randomness disclosure",
           {"bid_domain": domain, "true_bid": 130000, "target": target_b1,
            "disclosed_r": FIXTURE_R, "randomness_kind": "public fixed TEST fixture", "max_attempts": 100},
           {"status": "match", "attempts": 13, "bid": 130000, "randomness": FIXTURE_R},
           asdict(guess_b1(target_b1, bids, [FIXTURE_R], max_attempts=100)),
           "Publishing r early removes its protection against this small-domain search.")

    target_b2 = create_commitment("A01", "U02", 130000, FIXTURE_R)
    record("E04-disclosed-r-b2", "Guess a context-bound bid when r is known",
           {"bid_domain": domain, "true_bid": 130000, "target": target_b2,
            "auction_id": "A01", "bidder_id": "U02", "disclosed_r": FIXTURE_R,
            "randomness_kind": "public fixed TEST fixture", "max_attempts": 100},
           {"status": "match", "attempts": 13, "bid": 130000, "randomness": FIXTURE_R},
           asdict(guess_b2_disclosed_randomness(target_b2, "A01", "U02", bids, FIXTURE_R,
                                               max_attempts=100)),
           "Context binding does not restore hiding if opening randomness is disclosed.")

    prepared = prepare_commitment("A01", "U03", 120000)
    actual = {"random_bytes": len(bytes.fromhex(prepared.randomness)),
              "opening_matches": verify_opening(prepared.commitment, "A01", "U03", 120000,
                                                 prepared.randomness),
              "public_payload_fields": sorted(prepared.public_submission())}
    record("E04-normal-r-configuration", "Check normal generation and the public payload",
           {"generator": "secrets.token_hex(16)", "auction_id": "A01", "bidder_id": "U03",
            "bid": 120000, "randomness_kind": "fresh OS-backed randomness; opening not exported"},
           {"random_bytes": RANDOMNESS_BYTES, "opening_matches": True,
            "public_payload_fields": ["auction_id", "bidder_id", "commitment"]}, actual,
           "Length and a successful opening do not measure entropy or prove hiding. "
           "2^128 possible r values assumes uniform independent generation; no exhaustive search is run.")

    status = _git("status", "--porcelain")
    return {
        "schema_version": 1,
        "run_kind": "author component checks using synthetic data; not independent E01-E06 validation",
        "run_started_at_utc": started_at,
        "python_version": platform.python_version(), "platform": platform.platform(),
        "git_head": _git("rev-parse", "HEAD"),
        "working_tree_dirty": None if status is None else bool(status),
        "source_sha256": source_manifest(), "encoding_id": ENCODING_ID,
        "reference_vector_source": "docs/commitment-api.md; binary vector independently checked with .NET SHA-256",
        "model_status": ("docs/model.md exists; its approval and conformance require team review."
                         if (ROOT / "docs/model.md").is_file() else
                         "Binary handover format implemented from the integration message; docs/model.md is not yet present."),
        "model_sha256": (hashlib.sha256((ROOT / "docs/model.md").read_bytes()).hexdigest()
                         if (ROOT / "docs/model.md").is_file() else None),
        "all_checks_passed": all(case["passed"] for case in cases), "cases": cases,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON evidence; otherwise print it.")
    args = parser.parse_args(argv)
    result = run_checks()
    text = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"{sum(c['passed'] for c in result['cases'])}/{len(result['cases'])} checks passed. "
              f"Evidence: {args.output}")
    else:
        sys.stdout.write(text)
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
