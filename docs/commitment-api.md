# Cryptographic component API

This document describes the implemented interface for Thành Lê's auction
coordinator and Chúc's independent tests. It is technical documentation, not
the report's Background section.

## Model status

This handover implements `m1-length-prefixed-be-v1`, following Thành Lê's
integration message of 14 November 2026. Each M1 field has a four-byte
big-endian byte-length prefix; the bid has eight unsigned big-endian bytes and
r has 16 raw bytes. The complete contract below fixes field order and API types.
The actual temporary auction source has not been supplied, so Thành Lê must
replace its module, compare the reference vector and rerun E01 before Chúc's
independent tests. No full-auction integration result is claimed here.

This replaces the earlier ASCII pipe encoding. Previously created commitments
are incompatible and must be recreated; the verifier does not auto-detect or
accept the old format. B0 and B1 also use the binary field representations
specified below. The 100-price example remains an experiment configuration,
not a global price rule. The team still maintains the final `docs/model.md`.

## Runtime and files

- Python 3.10+ with the standard library; no package installation is needed.
- `src/commitment.py`: cryptographic functions and private bidder state.
- `experiments/guessing.py`: bounded search of explicit experimental domains.
- `examples/commitment_demo.py`: normal generation and later explicit reveal.
- `experiments/run_son_checks.py`: repeatable synthetic checks and JSON evidence.

Run module commands from the repository root. Imports use `src.commitment`.

## Canonical data representation

| Value | Python type and format |
| --- | --- |
| `auction_id` / A | Nonempty, case-sensitive ASCII letters or digits |
| `bidder_id` / U | Same format as A; caller verifies authenticated identity |
| `bid` / b | `int` in 1..2^64-1; `bool`, floats and numeric strings are rejected |
| `randomness` / r | Exactly 32 lowercase hexadecimal digits, representing 16 bytes |
| Commitment c | Exactly 64 lowercase hexadecimal digits, the full 32-byte digest |

The tag is exactly `CR-AUCTION-v1`; the currency is exactly `VND`.

```text
LP(x) = len(x).to_bytes(4, "big", signed=False) + x
bid_bytes = b.to_bytes(8, "big", signed=False)
r_bytes = bytes.fromhex(r)

B0 input: bid_bytes
B1 input: LP(bid_bytes) + LP(r_bytes)
B2 input: LP(b"CR-AUCTION-v1") + LP(A.encode("ascii"))
        + LP(U.encode("ascii")) + LP(b"VND")
        + LP(bid_bytes) + LP(r_bytes)
```

All six M1 fields, including bid and r, have a length prefix. Text fields use
ASCII; UTF-8 produces the same bytes for the accepted ASCII identifier domain.
There are no literal pipe separators or trailing newline. Lengths count bytes,
not hexadecimal characters. The price field is always eight bytes, and leading
zero bytes in both numeric and randomness fields are retained. Field lengths
must fit unsigned 32 bits. Auction-specific price min/max/step constraints and
identifier bounds are checked by the auction coordinator.

**API boundary:** r is still a 32-character lowercase hex `str`, and c is a
64-character lowercase hex `str`. The module converts r to raw bytes internally.
If the temporary coordinator stores r as `bytes`, call with `raw_r.hex()`.
Do not pass `r.encode()` or pre-encode the bid. Generated r is also a hex string.

## Function contract

| Function | Result and purpose |
| --- | --- |
| `generate_randomness()` | `str`; calls `secrets.token_hex(16)` |
| `encode(A, U, b, r)` | Canonical M1 input `bytes` |
| `encode_b0(b)` / `encode_b1(b, r)` | Comparison input `bytes` |
| `create_commitment(A, U, b, r)` | Full M1/B2 digest `str` |
| `create_b0_commitment(b)` | Digest for guessing comparison |
| `create_b1_commitment(b, r)` | Digest for randomness comparison |
| `verify_opening(c, A, U, b, r)` | `bool`; validates format, recomputes and compares the digest |
| `prepare_commitment(A, U, b, *, randomness=None)` | Private `PreparedCommitment` containing c and its opening |
| `validate_commitment(c)` | Returns `None` for canonical c, raises on malformed c |

Creation and encoding raise `InvalidCommitmentData`, a subclass of `ValueError`,
for invalid field representations. The verifier returns `False` for malformed
fields or a mismatched hash. It performs full-length comparison with
`hmac.compare_digest`; this does not create a timing-security claim for the
entire application. It neither reads nor modifies auction state.

`prepare_commitment` generates fresh OS-backed randomness unless the caller
explicitly supplies `randomness=` for a labeled test fixture. Format checks
cannot determine whether caller-supplied randomness was generated securely.

## Integration example

```python
from src.commitment import prepare_commitment, verify_opening

# Bidder device, before the commit deadline; do not send private_state.
private_state = prepare_commitment("A01", "U01", 100000)
submission = private_state.public_submission()
# {'auction_id': 'A01', 'bidder_id': 'U01', 'commitment': '...'}
# auction.submit_commit(...) authenticates U, checks A/time/duplicates, then
# retains this commitment. It must not obtain b or r during the commit phase.
frozen_commitment = submission["commitment"]

# Only after the coordinator opens the reveal phase:
opening = private_state.reveal_payload()
# Derive expected A/U from the active auction and authenticated caller.
expected_auction = "A01"
authenticated_bidder = "U01"
hash_matches = verify_opening(
    frozen_commitment,
    expected_auction,
    authenticated_bidder,
    opening["bid"],
    opening["randomness"],
)
# The coordinator additionally checks the request's claimed A/U, bid bounds,
# phase and deadline. A True hash result alone does not accept the reveal.
```

`PreparedCommitment.public_submission()` deliberately omits bid and randomness.
Its `repr` also hides them. `reveal_payload()` explicitly discloses them; it does
not check a clock. Do not log or serialize all private attributes (for example
with `dataclasses.asdict`) during commit. No component function logs secrets.

## Reference vector and negative samples

The input values reuse the public fixture from study guide pages 6 and 8, but
the binary encoding produces a NEW digest. Its patterned randomness is for
tests only. The digest has been cross-checked using Python and .NET SHA-256.

```text
A = A01
U = U01
b = 100000
r = 00112233445566778899aabbccddeeff
tag = CR-AUCTION-v1
currency = VND
input length = 70 bytes
input hex (join the following lines without spaces):
0000000d43522d41554354494f4e2d7631
00000003413031
00000003553031
00000003564e44
0000000800000000000186a0
0000001000112233445566778899aabbccddeeff
c = 7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71
```

The same c opens successfully with these fields. Keeping c fixed and changing
b to `140000`, r to `10112233445566778899aabbccddeeff`, A to `A02`, or U to `U02`
fails in the tested samples. These examples are functional checks, not proofs
that collisions are impossible.

## Guessing utilities

```python
from experiments.guessing import (
    guess_b0, guess_b1, guess_b2_disclosed_randomness,
    weak_randomness_candidates,
)
from src.commitment import create_b0_commitment, create_b1_commitment

# Explicit example configuration, not an implicit price rule in commitment.py.
bids = range(10000, 1000001, 10000)
b0_result = guess_b0(create_b0_commitment(130000), bids, max_attempts=100)

# TEST ONLY: one of 16 publicly defined possible values, despite 32 hex digits.
weak_r = "00000000000000000000000000000007"
b1_result = guess_b1(
    create_b1_commitment(130000, weak_r), bids,
    weak_randomness_candidates(16), max_attempts=1600,
)
```

Each function returns `GuessResult(status, attempts, bid, randomness)`:

- `match`: the first matching candidate in the supplied enumeration order.
- `domain_exhausted`: all supplied candidates were evaluated without a match.
- `budget_exhausted`: the hash-attempt limit was reached with candidates left.

`attempts` counts hashes actually evaluated, including the matching attempt.
The match need not be unique over arbitrary domains. B0 and disclosed-r B2
iterate bids in order. B1 iterates r in the outer loop and the bid sequence in
the inner loop. Therefore the examples above take 13 and 713 attempts.
Empty domains produce zero attempts. Duplicate candidates count as additional
attempts; these functions do not silently change the supplied domain.

B1 bids must be a reusable finite sequence, such as `range`, list or tuple.
Randomness candidates can be an iterator. For known r, use `guess_b1(c, bids,
[r])` or `guess_b2_disclosed_randomness(c, A, U, bids, r)`. The latter requires
the correct known context. Candidate domains and budgets are explicit inputs;
there is no brute-force 128-bit generator. `weak_randomness_candidates(count)`
supports 1 to 10,000 deterministic test values and is not a random generator.

## Ownership and remaining integration

Sơn owns these crypto functions, input/output documentation, fixture checks and
guessing support. Thành Lê owns authentication simulation, current auction and
price validation, deadlines, frozen storage, duplicate submissions, tie rules
and winner selection. Công Thành reviews cryptographic assumptions and the
experiment design; Chúc independently tests and executes the agreed cases.
Hoàng Anh reruns the documented commands on another environment.

The original study guide, the group's README and the supplementary assignment
define the conceptual scope. Thành Lê's integration message supplies the new
binary encoding. This document records the exact interface for integration;
it does not claim the full E01-E06 auction suite has been completed.
