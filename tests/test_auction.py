"""Coordinator integration checks using Sơn's commitment API."""

import unittest

from src.auction import Auction, Settlement
from src.commitment import prepare_commitment

T1, T2 = 36_000, 36_600


class AuctionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.auction = Auction(
            "A01", {"U01", "U02", "U03"}, T1, T2,
            min_bid=10_000, max_bid=1_000_000, bid_step=10_000,
        )

    def commit(self, bidder, bid, t=T1 - 1):
        opening = prepare_commitment("A01", bidder, bid)
        decision = self.auction.submit_commit(**opening.public_submission(), sender_id=bidder, t=t)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.receipt.commitment, opening.commitment)
        self.assertEqual(decision.receipt.received_at, t)
        return opening

    def reveal(self, opening, t=T1, sender=None, **changes):
        payload = opening.reveal_payload() | changes
        return self.auction.submit_reveal(**payload, sender_id=sender or opening.bidder_id, t=t)

    def test_e01_first_price(self):
        openings = [self.commit(bidder, bid) for bidder, bid in (
            ("U01", 100_000), ("U02", 130_000), ("U03", 120_000),
        )]
        for opening in openings:
            self.assertTrue(self.reveal(opening).accepted)
        self.assertEqual(self.auction.settle(T2), Settlement("winner", "U02", 130_000))

    def test_e02_changed_price_and_randomness(self):
        opening = self.commit("U01", 100_000)
        changed_r = f"{int(opening.randomness, 16) ^ 1:032x}"
        self.assertEqual(self.reveal(opening, bid=140_000).reason, "opening_mismatch")
        self.assertEqual(self.reveal(opening, randomness=changed_r).reason, "opening_mismatch")
        self.assertTrue(self.reveal(opening).accepted)
        self.assertEqual(self.reveal(opening).reason, "already_revealed")

    def test_e05_deadlines_identity_and_duplicate_commit(self):
        opening = self.commit("U01", 100_000)
        duplicate = prepare_commitment("A01", "U01", 140_000)
        decision = self.auction.submit_commit(**duplicate.public_submission(), sender_id="U01", t=T1 - 1)
        self.assertEqual(decision.reason, "duplicate_commit")
        self.assertEqual(self.reveal(opening, T1 - 1).reason, "reveal_not_open")
        self.assertEqual(
            self.auction.submit_commit("A01", "U02", "U02", opening.commitment, T1).reason,
            "commit_closed",
        )
        self.assertEqual(self.reveal(opening, auction_id="A02").reason, "wrong_auction")
        self.assertEqual(self.reveal(opening, sender="U02").reason, "wrong_bidder")
        self.assertEqual(self.reveal(opening, bidder_id="U02", sender="U02").reason, "no_commitment")
        self.assertEqual(self.reveal(opening, bidder_id="U04", sender="U04").reason, "wrong_bidder")
        self.assertTrue(self.reveal(opening, T2 - 1).accepted)
        self.assertEqual(self.auction.settle(T2 - 1).status, "pending")
        self.assertEqual(self.reveal(opening, T2).reason, "reveal_closed")

    def test_e05_price_range_and_step(self):
        openings = [self.commit("U01", 10_000), self.commit("U02", 1_000_000)]
        for bid in (9_999, 1_010_000, 10_001, True, 10_000.0):
            with self.subTest(bid=bid):
                self.assertEqual(self.reveal(openings[0], bid=bid).reason, "invalid_bid")
        for opening in openings:
            self.assertTrue(self.reveal(opening).accepted)

    def test_e06_non_reveal_and_tie(self):
        second = self.commit("U02", 120_000)
        first = self.commit("U01", 120_000)
        self.commit("U03", 130_000)
        self.assertTrue(self.reveal(second).accepted)
        self.assertTrue(self.reveal(first).accepted)
        self.assertEqual(self.auction.settle(T2), Settlement("winner", "U01", 120_000))

    def test_e06_no_valid_reveal(self):
        opening = self.commit("U01", 100_000)
        self.assertEqual(self.reveal(opening, bid=140_000).reason, "opening_mismatch")
        self.assertEqual(self.auction.settle(T2), Settlement("no_winner"))
