# Review of Sơn's commitment component

## Scope and evidence basis

This review covers the actual remote branch `origin/feature/commitment` at commit
`0c5fe7a28ccb532df8eb6433cf0b9732ddf54e82` (14 November 2026). The branch is
three commits ahead of `origin/main` and descends from it. It was inspected by
Git reference and tested from an isolated archive; it was not merged or copied
into this branch.

The finalized PDFs named in the assignment were not available in the repository,
the supplied attachment area, or the searched Documents directory, so this
review does not claim to have inspected them. An approved `docs/model.md` is now
available on Thành Lê's `origin/codex/auction-m1` at commit
`3076239fa7f3ead86b55028e3acba05c012a41e3`. That commit directly descends from
Sơn's reviewed `0c5fe7a…` and leaves `src/commitment.py` unchanged. This review
therefore checks the component against the supplied task, README, Sơn's branch,
and the integrated M1 model and coordinator.

## M1 conformance review

The available specification-level checklist is as follows. “Observed” denotes
behavior in Thành Lê's coordinator tests rerun in this review; it is not Chúc's
independent evidence.

| M1 requirement | Review status |
| --- | --- |
| One-item, first-price sealed-bid auction | Specified in `docs/model.md`; E01 observed |
| One commitment per authenticated bidder | Coordinator accepts the first commitment and rejects a tested duplicate; identity is simulated by `sender_id` equality and eligibility |
| Commit accepted only for `t < T1` | Commit at T1 rejected as `commit_closed` |
| Accepted commitment list frozen at T1 | No commit can enter after T1; a rejected duplicate did not replace the original commitment, which later opened successfully |
| Reveal accepted only for `T1 <= t < T2` | Reveal at T1 accepted; immediately before T1 and exactly at T2 rejected |
| Valid b and correct A/U | Approved example domain is 10000..1000000 VND in steps of 10000; range/step and wrong-A/U cases observed |
| Commitment verification | Integrated coordinator calls Sơn's `verify_opening` with stored A/U; valid and altered openings observed |
| Non-reveal exclusion | Highest 130000 commitment was not revealed and did not enter settlement |
| Highest valid revealed bid wins and pays its bid | E01 selected `U02` at 130000 VND |
| Tie rule | `docs/model.md` specifies lexicographically smallest preassigned bidder ID; observed `U01` beating `U02` at equal 120000 bids |
| No valid reveal means no winner | Invalid-only reveal case produced `Settlement("no_winner")` |
| Unambiguous encoding | Model confirms `m1-length-prefixed-be-v1`; reference vector independently reproduced |
| Proper randomness | Normal API uses `secrets.token_hex(16)`; secrecy, independence, and actual runtime entropy remain operational assumptions |
| Trusted storage, timing, and authentication | Coordinator simulates monotonic time and sender identity and assumes its private records are preserved; it provides no production clock, signatures, or independent audit log |

The model, commitment API, and coordinator are internally compatible, and all
available author/integration checks passed in this rerun. It would still be
inaccurate to call this independent validation or to infer production security.

The reviewed construction is

```text
SHA-256(LP(tag) || LP(A) || LP(U) || LP(currency) || LP(b) || LP(r))
```

where `LP(x)` is a four-byte unsigned big-endian byte length followed by `x`.
The tag is the ASCII string `CR-AUCTION-v1`, the currency is `VND`, `A` and `U`
are case-sensitive ASCII alphanumeric strings, `b` is an eight-byte unsigned
big-endian integer, and `r` is 16 raw bytes represented at the API boundary as
32 lowercase hexadecimal characters. This is the documented
`m1-length-prefixed-be-v1` encoding.

| Review topic | Finding |
| --- | --- |
| SHA-256 | `create_commitment`, `create_b0_commitment`, and `create_b1_commitment` call `hashlib.sha256` on their canonical byte encodings and retain the full 256-bit digest. |
| Creation and verification | `create_commitment` hashes all M1 commitment fields. `verify_opening` validates the commitment and opening, recomputes the digest, and uses `hmac.compare_digest`. Malformed data and mismatches return `False`. |
| Field order and boundaries | The order is exactly tag, A, U, currency, b, r. Every field has a length prefix. Fixed-width b and r retain leading zero bytes. The encoding distinguishes examples such as `(A,U)=("1","23")` and `(“12”,“3”)`. |
| Input representation | A/U are nonempty ASCII letters or digits in the crypto API. Bids are Python integers in `1..2^64-1`, excluding `bool`; the coordinator further enforces the approved example domain 10000..1000000 VND in steps of 10000. Randomness and digests have strict lowercase hexadecimal forms. |
| Randomness | Normal preparation calls `secrets.token_hex(16)`, producing 16 OS-backed random bytes under Python's `secrets` contract. The optional fixed-r argument is explicitly documented as a repeatable test fixture. Format/width validation alone cannot establish entropy. |
| Secret handling | `public_submission()` omits b and r and `repr` hides them. The object still retains the opening, and explicit serialization such as `dataclasses.asdict` can disclose it. Early logging, storage, or transmission of r would permit bid-domain guessing and defeat the intended hiding benefit. |
| Changed openings | With a frozen commitment, the tested changed-bid, changed-r, wrong-A, and wrong-U examples all fail verification. These examples do not prove binding for all inputs. |
| Responsibility boundary | The module correctly states that a hash match does not authenticate U or enforce the active auction, bid policy, one-commit rule, T1/T2, frozen storage, reveal exclusion, ties, or settlement. Callers must supply the expected A/U rather than trust only values from an untrusted reveal. |
| Coordinator interface | `Auction.submit_commit` consumes `PreparedCommitment.public_submission()`. `submit_reveal` consumes `reveal_payload()` and passes the stored receipt A/U, integer bid, and lowercase-hex r to `verify_opening`; no conversion or field-order mismatch was found. |

No material compatibility defect was found between the reviewed cryptographic
component and coordinator. This statement is limited to the reviewed source and
executed examples; it is not a cryptographic proof or production approval.

## Independent reference-vector check

The supplied vector was recomputed without importing Sơn's implementation. A
small one-line Python calculation used `struct.pack(">I", len(x))` for each
length, `struct.pack(">Q", 100000)` for b, raw bytes for r, and
`hashlib.sha256` only after independently assembling the message.

```text
A = A01
U = U01
b = 100000
r = 00112233445566778899aabbccddeeff
encoded length = 70 bytes
SHA-256 = 7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71
```

The independently assembled bytes were:

```text
0000000d43522d41554354494f4e2d7631
00000003413031
00000003553031
00000003564e44
0000000800000000000186a0
0000001000112233445566778899aabbccddeeff
```

The length and digest match the documented vector.

## Executed checks

Environment: Windows 11 (`Windows-11-10.0.26200-SP0`), Python 3.13.15, standard
library only. The original component review used an isolated archive of
`0c5fe7a28ccb532df8eb6433cf0b9732ddf54e82`; the integration review used an
isolated archive of `3076239fa7f3ead86b55028e3acba05c012a41e3`. The archives
intentionally contained no `.git` directory, so source revisions are pinned by
the archived refs rather than runner `git_head`. The source manifest in Sơn's
recorded `results/son_checks_binary.json` was compared with the final component
branch files and every hash matched.

| Command | Expected | Actual | Result |
| --- | --- | --- | --- |
| `python -m unittest discover -s tests -v` | Exit 0; all component tests pass | Exit 0; 44 tests ran and all passed in 0.433 s | Pass |
| `python -m experiments.run_son_checks --output <temporary-path>/independent-son-checks.json` | Exit 0; 10/10 expected component checks pass | Exit 0; 10/10 passed | Pass |
| Independent `struct`/`hashlib` vector calculation | 70 bytes and documented digest | 70 bytes and `7b4df9d0…2b71` | Pass |
| `python -m unittest discover -s tests -q` at integrated commit | Exit 0; component and coordinator tests pass | Exit 0; 50 tests ran and all passed in 0.442 s | Pass |
| `python -m unittest tests.test_auction -v` | Exit 0; six coordinator tests pass | Exit 0; 6/6 passed in 0.001 s | Pass |
| `python -m examples.auction_demo` | Exit 0; three valid reveals and first-price winner | Exit 0; `U02` won at 130000 VND | Pass |
| `python -m examples.check_handover` | Exit 0; eight handover checks pass | Exit 0; 8/8 `PASS` lines | Pass |
| `python -m experiments.run_son_checks --output <temporary-path>/son-checks.json` at integrated commit | Exit 0; 10/10 component checks pass | Exit 0; 10/10 passed | Pass |

The rerun observed a valid opening, rejection of a modified bid and modified r,
distinct encoding of ambiguous identifier pairs, B0 recovery of 130000 VND on
attempt 13, weak-r recovery on attempt 713, disclosed-r recovery on attempt 13,
and correct structure/opening for a freshly generated 16-byte r. Full details
and limitations are recorded in `experiment-plan.md`.

Sơn's committed evidence on `origin/feature/commitment` is explicitly author-run: Python 3.13.2 on Windows 11,
44/44 tests and 10/10 component checks. Its JSON records base HEAD
`5fe97906e5c88d1afab0d5c70c244b071e8e0271` with a dirty tree, but its recorded
source manifest matches the final files at `0c5fe7a…`. This is traceable
component evidence, not Chúc's independent execution.

The integration evidence locations are `tests/test_auction.py`,
`examples/auction_demo.py`, and `results/auction_e01.json` on
`origin/codex/auction-m1`. The committed E01 JSON records the expected winner and
price, and the current demo independently reproduced them with new random
openings. Its recorded SHA-256 for `src/commitment.py` matches the committed
file. The recorded hashes for `src/auction.py` and `examples/auction_demo.py` do
not match the LF-normalized committed bytes: they exactly match CRLF versions of
the same text. This is a line-ending provenance defect, not an observed logic
difference; the result is therefore supported primarily by the successful rerun
from commit `3076239…`, not by claiming all recorded byte hashes match.

## Background consistency

`report/background_en.md` is technically consistent with the reviewed M1
construction: it distinguishes commitments from encryption and signatures,
does not claim collision resistance provides hiding, explains the B0
small-domain attack, requires unpredictable secret r, and ties binding to
unambiguous encoding plus a fixed commitment record and a hash assumption. Its
random-oracle statement is presented as an assumption, not as a proof that
SHA-256 is an ideal random oracle. No rewrite was made. This review did not
independently audit the bibliographic references.

## Limits and open dependencies

- The finalized PDFs remain unavailable and were not inspected. The accessible
  approved `docs/model.md` nevertheless confirms the binary format, example
  price domain, boundaries, settlement, and trust assumptions used here.
- Authentication and time are scenario inputs, while frozen-record preservation
  is assumed. The coordinator has no production identity system, trusted clock,
  signed receipt, persistence layer, or independent audit record.
- `_advance(t)` runs before request validity checks, so even a subsequently
  rejected request advances the shared simulated clock. This is consistent only
  with the documented assumption that timestamps come from a trusted scenario;
  exposing caller-chosen t would create an availability/deadline risk.
- The committed E01 evidence has the CRLF/LF source-hash discrepancy described
  above; the session rerun from the exact committed ref passed.
- No evidence from Chúc's independent suite or Hoàng Anh's rerun is available.
- Passing examples support functional correctness for those inputs. They do not
  prove hiding, binding, collision resistance, entropy, or end-to-end fairness.

