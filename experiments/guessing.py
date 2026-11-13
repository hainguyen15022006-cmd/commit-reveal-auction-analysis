"""Bounded guessing utilities for E03/E04, with explicit candidate domains.

Weak randomness here is an experimental configuration, never an M1 default.
No function attempts an exhaustive search of a secret 128-bit random space.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
import hmac
from typing import Literal

from src.commitment import (
    create_b0_commitment, create_b1_commitment, create_commitment,
    validate_commitment,
)


@dataclass(frozen=True)
class GuessResult:
    """The first matching candidate and number of hashes actually evaluated.

    A match need not identify a unique opening over arbitrary domains. A budget
    stop or exhausted domain without a match is not evidence of hiding security.
    """

    status: Literal["match", "domain_exhausted", "budget_exhausted"]
    attempts: int
    bid: int | None = None
    randomness: str | None = field(default=None, repr=False)


def _search(
    commitment: str,
    candidates: Iterable[tuple[int, str | None]],
    make_digest: Callable[[int, str | None], str],
    max_attempts: int,
) -> GuessResult:
    validate_commitment(commitment)
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer, excluding bool.")
    attempts = 0
    for bid, randomness in candidates:
        if attempts >= max_attempts:
            return GuessResult("budget_exhausted", attempts)
        candidate = make_digest(bid, randomness)
        attempts += 1
        if hmac.compare_digest(commitment, candidate):
            return GuessResult("match", attempts, bid, randomness)
    return GuessResult("domain_exhausted", attempts)


def guess_b0(
    commitment: str, bids: Iterable[int], *, max_attempts: int = 100_000
) -> GuessResult:
    """Try bids in supplied order, stopping at the first match or budget limit."""
    return _search(commitment, ((b, None) for b in bids),
                   lambda b, r: create_b0_commitment(b), max_attempts)


def guess_b1(
    commitment: str, bids: Sequence[int], randomness_candidates: Iterable[str],
    *, max_attempts: int = 1_000_000,
) -> GuessResult:
    """Try each candidate r against every bid, in supplied order.

    bids must be a finite, reusable sequence (e.g. range or tuple), not a
    one-shot iterator. No enormous candidate list is constructed internally.
    For disclosed randomness, supply a one-element randomness_candidates list.
    """
    if not isinstance(bids, Sequence):
        raise TypeError("bids must be a reusable sequence, such as range or tuple.")
    candidates = ((b, r) for r in randomness_candidates for b in bids) if bids else ()
    return _search(commitment, candidates,
                   lambda b, r: create_b1_commitment(b, r), max_attempts)


def guess_b2_disclosed_randomness(
    commitment: str, auction_id: str, bidder_id: str, bids: Iterable[int],
    disclosed_randomness: str, *, max_attempts: int = 100_000,
) -> GuessResult:
    """Illustrate small-domain guessing when an M1 opening's randomness leaks."""
    return _search(
        commitment, ((b, disclosed_randomness) for b in bids),
        lambda b, r: create_commitment(auction_id, bidder_id, b, r), max_attempts,
    )


def weak_randomness_candidates(count: int = 10_000) -> Iterable[str]:
    """Experimental values 0..count-1, each encoded as 32 lowercase hex digits.

    At most 10,000 distinct values are allowed by this fixture generator. Each
    has the M1 field width but comes from a deliberately small public domain.
    This is not a random generator and must not be used for normal commitments.
    """
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 10_000:
        raise ValueError("Experimental count must be an integer between 1 and 10000.")
    return (f"{value:032x}" for value in range(count))
