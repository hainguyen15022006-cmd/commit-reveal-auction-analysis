"""Run E01 with three bidders and print a JSON record of the simulation."""

import argparse
import hashlib
import json
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.auction import Auction
from src.commitment import prepare_commitment

AUCTION_ID = "A01"
T1, T2 = 36_000, 36_600
BIDS = {"U01": 100_000, "U02": 130_000, "U03": 120_000}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write E01 evidence as UTF-8 JSON.")
    args = parser.parse_args()
    auction = Auction(
        AUCTION_ID, set(BIDS), T1, T2,
        min_bid=10_000, max_bid=1_000_000, bid_step=10_000,
    )
    openings = [prepare_commitment(AUCTION_ID, bidder, bid) for bidder, bid in BIDS.items()]
    commits = {}
    for opening in openings:
        decision = auction.submit_commit(
            **opening.public_submission(), sender_id=opening.bidder_id, t=T1 - 1,
        )
        commits[opening.bidder_id] = asdict(decision)
    reveals = {}
    for opening in openings:
        decision = auction.submit_reveal(
            **opening.reveal_payload(), sender_id=opening.bidder_id, t=T1,
        )
        reveals[opening.bidder_id] = {"bid": opening.bid, "received_at": T1, **asdict(decision)}
    result = {
        "case": "E01",
        "T1": T1,
        "T2": T2,
        "commits": commits,
        "reveals": reveals,
        "settlement": asdict(auction.settle(T2)),
    }
    expected = {"status": "winner", "winner_id": "U02", "price": 130_000}
    root = Path(__file__).resolve().parents[1]
    try:
        git_head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL, timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        git_head = None
    result.update({
        "run_kind": "author integration check",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "config": {"min_bid": 10_000, "max_bid": 1_000_000, "bid_step": 10_000},
        "randomness": "fresh secret 128-bit randomness per bidder",
        "expected_settlement": expected,
        "all_checks_passed": (
            all(record["accepted"] for record in commits.values())
            and all(record["accepted"] for record in reveals.values())
            and result["settlement"] == expected
        ),
        "source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("src/commitment.py", "src/auction.py", "examples/auction_demo.py")
        },
    })
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(output.encode("utf-8"))
    else:
        print(output, end="")
    if not result["all_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
