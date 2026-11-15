"""Independent reference implementation used ONLY by the independent tests.

This file deliberately does not import src.commitment. It re-implements the
documented encoding (docs/commitment-api.md, id m1-length-prefixed-be-v1) from
the written specification so that a bug in src/commitment.py cannot also hide
inside the test oracle. If the specification changes, update this file from
docs/model.md, never by copying code from src/.

Nothing here is production code. The brute-force helpers are bounded searches
over explicit, small, test-defined domains.
"""

import hashlib

TAG = b"CR-AUCTION-v1"
CURRENCY = b"VND"


def lp(value: bytes) -> bytes:
    """Four-byte big-endian length prefix followed by the bytes."""
    return len(value).to_bytes(4, "big") + value


def b0_digest(bid: int) -> str:
    """B0 = SHA-256(8-byte big-endian bid)."""
    return hashlib.sha256(bid.to_bytes(8, "big")).hexdigest()


def b1_digest(bid: int, r_hex: str) -> str:
    """B1 = SHA-256(LP(bid8) + LP(r16))."""
    data = lp(bid.to_bytes(8, "big")) + lp(bytes.fromhex(r_hex))
    return hashlib.sha256(data).hexdigest()


def m1_digest(auction: str, bidder: str, bid: int, r_hex: str) -> str:
    """M1/B2 = SHA-256(LP(tag)+LP(A)+LP(U)+LP(cur)+LP(bid8)+LP(r16))."""
    fields = (TAG, auction.encode("ascii"), bidder.encode("ascii"), CURRENCY,
              bid.to_bytes(8, "big"), bytes.fromhex(r_hex))
    return hashlib.sha256(b"".join(lp(f) for f in fields)).hexdigest()


def search_b0(target: str, domain):
    """Return (bid or None, attempts) trying each bid in order against B0."""
    attempts = 0
    for bid in domain:
        attempts += 1
        if b0_digest(bid) == target:
            return bid, attempts
    return None, attempts


def search_b1(target: str, bids, r_values):
    """Try every (r, bid) pair, r in the outer loop. Return ((bid, r) or None, attempts)."""
    attempts = 0
    for r_hex in r_values:
        for bid in bids:
            attempts += 1
            if b1_digest(bid, r_hex) == target:
                return (bid, r_hex), attempts
    return None, attempts


def search_m1(target: str, auction: str, bidder: str, bids, r_values):
    """Same as search_b1 but against the full M1 construction with known A and U."""
    attempts = 0
    for r_hex in r_values:
        for bid in bids:
            attempts += 1
            if m1_digest(auction, bidder, bid, r_hex) == target:
                return (bid, r_hex), attempts
    return None, attempts


def r_from_int(value: int) -> str:
    """32 lowercase hex digits for a small integer; used for weak-r test domains."""
    return f"{value:032x}"
