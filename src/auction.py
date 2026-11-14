"""First-price sealed-bid auction with simulated identities and time."""

from dataclasses import dataclass
from typing import Literal

from src.commitment import MAX_BID, InvalidCommitmentData, validate_commitment, verify_opening


@dataclass(frozen=True)
class Receipt:
    auction_id: str
    bidder_id: str
    commitment: str
    received_at: int


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str | None = None
    receipt: Receipt | None = None


@dataclass(frozen=True)
class Settlement:
    status: Literal["pending", "winner", "no_winner"]
    winner_id: str | None = None
    price: int | None = None


class Auction:
    def __init__(
        self,
        auction_id: str,
        bidders: set[str],
        t1: int,
        t2: int,
        *,
        min_bid: int,
        max_bid: int,
        bid_step: int,
    ):
        if type(t1) is not int or type(t2) is not int or not 0 <= t1 < t2 < 86400:
            raise ValueError("expected 0 <= T1 < T2 < 86400")
        if not all(type(value) is int for value in (min_bid, max_bid, bid_step)):
            raise ValueError("price limits and step must be integers")
        if not 1 <= min_bid <= max_bid <= MAX_BID or bid_step <= 0:
            raise ValueError("invalid bid range or step")
        self.auction_id = auction_id
        self.bidders = frozenset(bidders)
        self.t1 = t1
        self.t2 = t2
        self.min_bid = min_bid
        self.max_bid = max_bid
        self.bid_step = bid_step
        self._time = 0
        # Once time reaches T1, submit_commit cannot change this record.
        self._commits: dict[str, Receipt] = {}
        self._reveals: dict[str, int] = {}

    def _advance(self, t: int) -> None:
        if type(t) is not int or not self._time <= t < 86400:
            raise ValueError("expected nondecreasing integer seconds within the same day")
        self._time = t

    def _check_sender(self, auction_id: str, bidder_id: str, sender_id: str) -> str | None:
        if auction_id != self.auction_id:
            return "wrong_auction"
        if bidder_id != sender_id or bidder_id not in self.bidders:
            return "wrong_bidder"
        return None

    def submit_commit(
        self, auction_id: str, bidder_id: str, sender_id: str, commitment: str, t: int
    ) -> Decision:
        self._advance(t)
        if t >= self.t1:
            return Decision(False, "commit_closed")
        reason = self._check_sender(auction_id, bidder_id, sender_id)
        if reason:
            return Decision(False, reason)
        if bidder_id in self._commits:
            return Decision(False, "duplicate_commit")
        try:
            validate_commitment(commitment)
        except InvalidCommitmentData:
            return Decision(False, "invalid_commitment")
        receipt = Receipt(auction_id, bidder_id, commitment, t)
        self._commits[bidder_id] = receipt
        return Decision(True, receipt=receipt)

    def submit_reveal(
        self, auction_id: str, bidder_id: str, sender_id: str, bid: int, randomness: str, t: int
    ) -> Decision:
        self._advance(t)
        if t < self.t1:
            return Decision(False, "reveal_not_open")
        if t >= self.t2:
            return Decision(False, "reveal_closed")
        reason = self._check_sender(auction_id, bidder_id, sender_id)
        if reason:
            return Decision(False, reason)
        receipt = self._commits.get(bidder_id)
        if receipt is None:
            return Decision(False, "no_commitment")
        if bidder_id in self._reveals:
            return Decision(False, "already_revealed")
        if (
            type(bid) is not int
            or not self.min_bid <= bid <= self.max_bid
            or (bid - self.min_bid) % self.bid_step
        ):
            return Decision(False, "invalid_bid")
        if not verify_opening(receipt.commitment, receipt.auction_id, receipt.bidder_id, bid, randomness):
            return Decision(False, "opening_mismatch")
        self._reveals[bidder_id] = bid
        return Decision(True)

    def settle(self, t: int) -> Settlement:
        self._advance(t)
        if t < self.t2:
            return Settlement("pending")
        if not self._reveals:
            return Settlement("no_winner")
        bidder_id, price = min(self._reveals.items(), key=lambda item: (-item[1], item[0]))
        return Settlement("winner", bidder_id, price)
