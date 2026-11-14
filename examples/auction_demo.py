"""Run E01 with three bidders and print a JSON record of the simulation."""

import json
from dataclasses import asdict

from src.auction import Auction
from src.commitment import prepare_commitment

AUCTION_ID = "A01"
T1, T2 = 36_000, 36_600
BIDS = {"U01": 100_000, "U02": 130_000, "U03": 120_000}


def main() -> None:
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
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
