"""Hash commitments for the group's M1 model and B0/B1 comparisons.

This module verifies hash openings, not auction admission. The auction layer
must independently check identity, session, bid range, deadlines and frozen state.
The binary encoding follows the integration format described by Thành Lê:
four-byte big-endian lengths, an eight-byte unsigned bid and 16 raw random bytes.
See docs/commitment-api.md for the complete interface and migration notes.
"""

from dataclasses import dataclass, field
import hashlib
import hmac
import re
import secrets

TAG = "CR-AUCTION-v1"
CURRENCY = "VND"
RANDOMNESS_BYTES = 16
MAX_BID = (1 << 64) - 1
ENCODING_ID = "m1-length-prefixed-be-v1"
_IDENTIFIER = re.compile(r"[A-Za-z0-9]+", re.ASCII)
_RANDOMNESS = re.compile(r"[0-9a-f]{32}", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)


class InvalidCommitmentData(ValueError):
    """An input violates the canonical data representation."""


def generate_randomness() -> str:
    """Return 16 secret random bytes represented by 32 lowercase hex digits.

    A fresh value is generated for each call. Keep it private until reveal.
    Length alone does not establish entropy for caller-supplied values.
    """
    return secrets.token_hex(RANDOMNESS_BYTES)


def _validate_identifier(value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise InvalidCommitmentData("Identifiers must be nonempty ASCII letters/digits.")


def _bid_bytes(bid: int) -> bytes:
    # bool is a subclass of int, but is not an admissible price representation.
    if isinstance(bid, bool) or not isinstance(bid, int) or not 1 <= bid <= MAX_BID:
        raise InvalidCommitmentData("Bid must be an integer in 1..2^64-1, excluding bool.")
    return bid.to_bytes(8, "big", signed=False)


def _validate_randomness(randomness: str) -> None:
    if not isinstance(randomness, str) or _RANDOMNESS.fullmatch(randomness) is None:
        raise InvalidCommitmentData("Randomness must be exactly 32 lowercase hex digits.")


def validate_commitment(commitment: str) -> None:
    """Require a full SHA-256 digest in canonical lowercase hexadecimal form."""
    if not isinstance(commitment, str) or _DIGEST.fullmatch(commitment) is None:
        raise InvalidCommitmentData("Commitment must be exactly 64 lowercase hex digits.")


def encode_b0(bid: int) -> bytes:
    """B0 hashes only the eight-byte unsigned big-endian bid, with no prefix."""
    return _bid_bytes(bid)


def _length_prefix(value: bytes) -> bytes:
    if len(value) >= 1 << 32:
        raise InvalidCommitmentData("Field length must fit an unsigned four-byte prefix.")
    return len(value).to_bytes(4, "big", signed=False) + value


def encode_b1(bid: int, randomness: str) -> bytes:
    """B1 uses length-prefixed bid bytes and raw randomness, in that order."""
    bid_bytes = _bid_bytes(bid)
    _validate_randomness(randomness)
    return _length_prefix(bid_bytes) + _length_prefix(bytes.fromhex(randomness))


def encode(auction_id: str, bidder_id: str, bid: int, randomness: str) -> bytes:
    """Encode tag,A,U,currency,b,r; prefix EVERY field with its four-byte length.

    Lengths count bytes and use unsigned big-endian representation. Text fields
    are ASCII; b is eight unsigned big-endian bytes; r is 16 raw bytes decoded
    from the API's lowercase hex string. No pipe delimiters or final newline.
    A/U remain case-sensitive ASCII alphanumeric identifiers. Auction-specific
    bid bounds and increments belong to the auction layer.
    """
    _validate_identifier(auction_id)
    _validate_identifier(bidder_id)
    bid_bytes = _bid_bytes(bid)
    _validate_randomness(randomness)
    fields = (TAG.encode("ascii"), auction_id.encode("ascii"), bidder_id.encode("ascii"),
              CURRENCY.encode("ascii"), bid_bytes, bytes.fromhex(randomness))
    return b"".join(_length_prefix(value) for value in fields)


def create_commitment(auction_id: str, bidder_id: str, bid: int, randomness: str) -> str:
    """Create the full M1/B2 hash commitment; the caller retains the opening."""
    return hashlib.sha256(encode(auction_id, bidder_id, bid, randomness)).hexdigest()


def create_b0_commitment(bid: int) -> str:
    """Hash the bid alone, intentionally exposing a small bid domain to guessing."""
    return hashlib.sha256(encode_b0(bid)).hexdigest()


def create_b1_commitment(bid: int, randomness: str) -> str:
    """Hash length-prefixed b,r; this does not bind an auction or bidder context."""
    return hashlib.sha256(encode_b1(bid, randomness)).hexdigest()


def verify_opening(
    commitment: str, auction_id: str, bidder_id: str, bid: int, randomness: str
) -> bool:
    """Return False for malformed data or a mismatch, True only for hash equality.

    Pass the auction and bidder identifiers expected by the auction layer, not
    unchecked identifiers taken solely from an untrusted reveal request.
    True does not mean that the auction must accept this reveal.
    """
    try:
        validate_commitment(commitment)
        candidate = create_commitment(auction_id, bidder_id, bid, randomness)
    except ValueError:
        return False
    return hmac.compare_digest(commitment, candidate)


@dataclass(frozen=True)
class PreparedCommitment:
    """Bidder-side state: do not serialize this object into a public commit log.

    repr hides bid and randomness to reduce accidental exposure. Explicitly
    serializing every attribute (e.g. dataclasses.asdict) still exposes them.
    """

    auction_id: str
    bidder_id: str
    commitment: str
    bid: int = field(repr=False)
    randomness: str = field(repr=False)

    def public_submission(self) -> dict[str, str]:
        """The commit-phase payload contains no bid or opening randomness."""
        return {"auction_id": self.auction_id, "bidder_id": self.bidder_id,
                "commitment": self.commitment}

    def reveal_payload(self) -> dict[str, str | int]:
        """Explicitly disclose the opening; call only during the reveal phase."""
        return {"auction_id": self.auction_id, "bidder_id": self.bidder_id,
                "bid": self.bid, "randomness": self.randomness}


def prepare_commitment(
    auction_id: str, bidder_id: str, bid: int, *, randomness: str | None = None
) -> PreparedCommitment:
    """Prepare private bidder state, generating secure randomness by default.

    The randomness override is for explicitly labeled repeatable test fixtures.
    A caller-supplied value can pass format checks while being easy to guess.
    """
    if randomness is None:
        randomness = generate_randomness()
    commitment = create_commitment(auction_id, bidder_id, bid, randomness)
    return PreparedCommitment(auction_id, bidder_id, commitment, bid, randomness)
