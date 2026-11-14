# Experiment plan for M1

## Evidence status and common setup

M1 is a first-price sealed-bid auction for one item. One commitment per
authenticated bidder is accepted only for `t < T1`; the accepted list freezes at
T1. Reveals are accepted only for `T1 <= t < T2` after checking bid validity,
expected A/U, and the frozen commitment. Non-reveals and invalid reveals are
excluded. The highest valid revealed bid wins and pays its bid; `docs/model.md`
specifies lexicographic ordering by preassigned bidder ID, smallest first, for a
tie. No valid reveal means no winner.

The commitment is M1/B2:

```text
c = SHA-256(Encode("CR-AUCTION-v1", A, U, "VND", b, r))
```

The integrated model confirms `Encode` is `m1-length-prefixed-be-v1` as reviewed
in `commitment-review.md`. Fixed r values below are public test fixtures; normal
M1 execution requires a fresh, independent, secret 128-bit r.

Status labels are deliberately strict:

- **Observed (review rerun):** executed from the isolated Sơn source at commit
  `0c5fe7a…` on Python 3.13.15/Windows 11.
- **Observed (Sơn author evidence):** present in
  `results/son_checks_binary.json` on `origin/feature/commitment`; not an
  independent group execution.
- **Observed (Thành Lê integration rerun):** executed from an isolated archive
  of `origin/codex/auction-m1` commit `3076239…` on Python 3.13.15/Windows 11;
  this is coordinator/integration evidence, not Chúc's independent execution.
- **Planned:** designed but not independently executed by Chúc.

Evidence categories are kept separate: **A** is Sơn's cryptographic component
tests and guessing runner; **B** is Thành Lê's coordinator/integration tests and
demo; **C** would be Chúc's independent suite, which is not currently available;
and **D** is the conditional theoretical reasoning in `security-comparison.md`.
Passing A or B is never reported as C or as proof of D.

The approved M1 example uses 100 permitted bids from 10000 through 1000000 VND
in increments of 10000. The coordinator enforces this range and step. E03/E04
use that exact domain; it remains a simulation parameter rather than a claim
about all real auctions.

## E01 — Valid auction

- **Objective:** Check the complete happy path and first-price settlement.
- **Model/variant:** Full M1/B2 with coordinator rules.
- **Inputs:** Auction `A01`; authenticated bidders `U01`, `U02`, `U03`; bids
  100000, 130000, 120000 VND respectively; three independently generated secret
  r values; valid commit times before T1 and reveal times in `[T1,T2)`.
- **Assumptions/preconditions:** A/U authentication, trusted phase clock,
  immutable frozen commitments, agreed bid policy, and integrated
  `m1-length-prefixed-be-v1` APIs.
- **Procedure:** Prepare each commitment; submit only A, U, and c before T1;
  reject no valid submission; freeze at T1; submit all three openings during the
  reveal interval; verify each against its frozen c and expected A/U; settle at
  or after T2.
- **Expected result:** All openings are valid. `U02` wins at 130000 VND and pays
  130000 VND.
- **Actual result:** **Observed (Thành Lê integration rerun):** all three commits
  at `T1-1` and reveals at T1 were accepted; settlement at T2 returned
  `Settlement("winner", "U02", 130000)`. The full suite and six-test coordinator
  module passed, and `python -m examples.auction_demo` independently reproduced
  the same outcome with newly generated r values.
- **Security interpretation:** Confirms functional composition for one valid
  scenario, not hiding/binding proofs or production fairness.
- **Limitations:** Does not exercise invalid timing, storage tampering,
  authentication failure, collusion, payment, or availability. Two source hashes
  in the committed E01 JSON reflect CRLF bytes while the Git commit stores LF;
  the text is equivalent and the exact committed source was rerun successfully,
  but the recorded byte-level provenance is imperfect.
- **Executor/evidence source:** Thành Lê integration test
  `test_e01_first_price`, demo, and committed `results/auction_e01.json`, plus
  this review rerun at `3076239…`. Chúc's independent evidence is unavailable.

## E02 — Invalid opening

- **Objective:** Check that a fixed commitment does not accept the tested altered
  bid or altered randomness.
- **Model/variant:** M1/B2 component verification and coordinator integration.
- **Inputs:** Frozen reference commitment
  `7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71`
  for A=`A01`, U=`U01`, b=100000, r=`00112233445566778899aabbccddeeff`.
  Negative openings independently change b to 140000 or change r to
  `10112233445566778899aabbccddeeff`.
- **Assumptions/preconditions:** The original c is frozen and the verifier uses
  the expected A/U plus the reviewed canonical encoding.
- **Procedure:** Call `verify_opening` for the original opening, then for each
  one-field modification while keeping c unchanged.
- **Expected result:** Original opening returns `True`; each alteration returns
  `False`.
- **Actual result:** **Observed (review rerun):** exactly the expected booleans;
  the 44-test suite and the 10-case runner both exited 0. **Observed (Sơn author
  evidence):** the same two E02 cases passed in the recorded JSON. **Observed
  (Thành Lê integration rerun):** `test_e02_changed_price_and_randomness`
  returned `opening_mismatch` for each alteration, then accepted the correct
  opening and rejected its repeat as `already_revealed`.
- **Security interpretation:** Demonstrates mismatch detection for these inputs.
  It does not prove that no alternative opening or SHA-256 collision exists.
- **Limitations:** These are specific examples; they do not prove binding or
  exercise a production authentication/storage system.
- **Executor/evidence source:** Security-analysis review rerun plus Sơn's
  author-run component evidence and Thành Lê's integration test. None is marked
  as Chúc's execution.

## E03 — Small-domain guessing against B0

- **Objective:** Show that `B0 = H(b)` exposes a bid selected from a known small
  domain to enumeration without breaking SHA-256.
- **Model/variant:** B0 using the component's canonical eight-byte unsigned
  big-endian representation of b.
- **Inputs:** Target b=130000 VND; candidates
  `range(10000, 1000001, 10000)`; target digest
  `953c19a5fd430675a06a0a6e5151f90679db3067c08dd6b0ac854fd048d3a84b`;
  maximum 100 attempts.
- **Assumptions/preconditions:** The observer knows the exact representation and
  candidate domain, and 130000 belongs to that domain.
- **Procedure:** Search bids in ascending order. For each candidate, compute its
  B0 commitment and compare the full digest; stop at the first match.
- **Expected result:** Candidates 10000, 20000, ..., 130000 are tried; the first
  match is b=130000 on attempt 13.
- **Actual result:** **Observed (review rerun):** status `match`, attempt count
  13, recovered bid 130000. **Observed (Sơn author evidence):** identical.
- **Security interpretation:** The work factor follows the small input domain;
  this is an input-guessing demonstration, not a SHA-256 break.
- **Limitations:** The domain is the approved M1 example configuration, not a
  universal real-auction policy. A match is not generally guaranteed unique
  over arbitrary domains.
- **Executor/evidence source:** Security-analysis review rerun plus Sơn's
  author-run component evidence; no Chúc result is available.

## E04 — Impact of randomness

- **Objective:** Compare absent, weak, disclosed, and normal secret randomness.
- **Model/variant:** B0 for no r; B1 for weak/disclosed r; B2/M1 for disclosed
  and normally generated r.
- **Inputs:** b=130000 and the same 100-bid domain as E03. Weak r is integer 7
  encoded as `00000000000000000000000000000007`; its public candidate domain is
  integers 0..15, each encoded as a 32-hex-character field. Disclosed r is
  `00112233445566778899aabbccddeeff`. Normal M1 calls
  `secrets.token_hex(16)` and does not export r in the commit payload.
- **Assumptions/preconditions:** Candidate formats and search order are known.
  For the normal case, the OS CSPRNG supplies uniform, independent randomness
  and the bidder keeps r secret until reveal.
- **Procedure:** (1) Use the E03 B0 enumeration for no r. (2) For weak B1, try r
  in order 0..15 as the outer loop and all ascending bids as the inner loop, up
  to 1600 pairs. (3) With disclosed r, try the 100 bids for B1 and B2 with known
  correct A/U. (4) For normal B2, prepare a commitment, check r decodes to 16
  bytes, check the public payload omits b/r, and verify the retained opening. Do
  not enumerate the 128-bit space.
- **Expected result:** No-r B0 recovers b on attempt 13. Weak-r B1 recovers
  `(b,r)` on attempt `7*100+13 = 713`. Disclosed-r B1 and B2 recover b on
  attempt 13. Normal B2 has a 16-byte r, a public payload containing only A/U/c,
  and a valid retained opening; no recovery claim is expected or attempted.
- **Actual result:** **Observed (review rerun):** all expected outputs occurred;
  target weak-B1 digest was `f88110ec…5558836`, disclosed-B1 was
  `3e8e4a85…aef3624`, and disclosed-B2 was `8a93bd62…981e4c`.
  The runner reported 16 bytes, a valid opening, and public fields A/U/c for the
  normal configuration. **Observed (Sơn author evidence):** identical expected
  comparisons passed. The unchanged component runner also passed 10/10 when
  rerun from Thành Lê's integrated commit.
- **Security interpretation:** A 128-bit field can have only four bits of entropy
  in the 16-value weak experiment. Disclosure removes r from the observer's
  search. With a uniform, independent, secret 128-bit r, exhaustive joint search
  is intended to be infeasible, but the structural check does not measure
  entropy or prove hiding.
- **Limitations:** No full-space search or statistical CSPRNG evaluation was run.
  Hiding also depends on the hash-function model and secrecy of the opening.
- **Executor/evidence source:** Security-analysis review rerun plus Sơn's
  author-run component evidence; no Chúc result is available.

## E05 — Protocol-rule tests

- **Objective:** Check coordinator rules that are not enforced by the hash module.
- **Model/variant:** Full M1/B2 coordinator.
- **Inputs:** One valid baseline opening plus these isolated variants:
  duplicate commitment by the same authenticated U; commit exactly at T1;
  reveal immediately before T1; reveal exactly at T2; reveal under wrong A; and
  reveal under wrong U.
- **Assumptions/preconditions:** Exact boundary convention is `commit: t<T1` and
  `reveal: T1<=t<T2`; the accepted commitment set is frozen at T1; the
  coordinator obtains authenticated U and active A from trusted context.
- **Procedure:** Begin from a fresh auction for each case. Submit the event at
  the stated boundary/context, retain state before and after, and record both
  return status and reason. For wrong A/U, also recompute against the expected
  context so the cryptographic mismatch is observable.
- **Expected result:** All six variants are rejected. The first duplicate does
  not replace the frozen c; commit at T1 is late; pre-T1 reveal is early; reveal
  at T2 is late; wrong A/U fail context and commitment checks.
- **Actual result:** **Observed (Thành Lê integration rerun):** the grouped E05
  test passed with these reasons: duplicate=`duplicate_commit`, reveal at
  `T1-1`=`reveal_not_open`, commit at T1=`commit_closed`, wrong A=`wrong_auction`,
  mismatched sender=`wrong_bidder`, eligible U without a commitment=`no_commitment`,
  ineligible U=`wrong_bidder`, and reveal at T2=`reveal_closed`. The original
  commitment still opened at `T2-1` after the rejected duplicate, giving
  simulation evidence that the duplicate did not replace it. Settlement before
  T2 was `pending`. A separate price test accepted both endpoints and rejected
  9999, 1010000, 10001, `True`, and `10000.0` as `invalid_bid`.
- **Security interpretation:** These checks protect protocol state and context;
  they are distinct from SHA-256's properties.
- **Limitations:** A simulated clock/authentication/storage layer does not prove
  production trustworthiness or resistance to rollback and denial of service.
  The implementation advances its shared clock before later request checks, so
  timestamps must remain trusted scenario inputs rather than caller-controlled
  production data.
- **Executor/evidence source:** Thành Lê's
  `test_e05_deadlines_identity_and_duplicate_commit` and
  `test_e05_price_range_and_step`, rerun at commit `3076239…`. Chúc's
  independent evidence remains unavailable.

## E06 — Settlement edge cases

- **Objective:** Check deterministic settlement when reveals are missing, tied,
  or absent.
- **Model/variant:** Full M1 settlement rules.
- **Inputs:** (a) Highest committed bidder does not reveal while lower valid bids
  do; (b) at least two equal highest valid revealed bids with bidder IDs chosen
  so ascending identifier order is unambiguous; (c) no valid reveal, including
  separate subcases of no reveal and only invalid reveals.
- **Assumptions/preconditions:** Commitments are frozen, reveal validity is
  already determined, and the approved tie rule is the preannounced ordering of
  bidder identifiers stated in the README.
- **Procedure:** Run a fresh auction per case through settlement at or after T2;
  retain accepted/rejected reveal records and selected winner/payment.
- **Expected result:** (a) The non-revealer is excluded and the highest remaining
  valid reveal wins. (b) The tied bidder first in the preannounced identifier
  order wins and pays the tied bid. (c) The result has no winner.
- **Actual result:** **Observed (Thành Lê integration rerun):** U03 committed
  130000 but did not reveal; U01 and U02 both revealed 120000, and settlement
  selected lexicographically smaller `U01` at 120000. In the no-valid-reveal
  test, an altered bid was rejected as `opening_mismatch` and settlement returned
  `Settlement("no_winner")`. Both tests passed.
- **Security interpretation:** Defines deterministic availability/fairness
  behavior but does not compel revelation or payment and does not prevent a
  bidder from strategically withholding an opening.
- **Limitations:** The accessible `docs/model.md` confirms the identifier order,
  but the finalized PDFs remain unavailable. Production liveness, storage
  tampering, and economic incentives are outside this functional test.
- **Executor/evidence source:** Thành Lê's `test_e06_non_reveal_and_tie` and
  `test_e06_no_valid_reveal`, rerun at commit `3076239…`. Chúc's independent
  evidence remains unavailable.

## Execution handoff

E01, E02, E05, and E06 now have reproducible Thành Lê integration evidence;
E02-E04 also have repeatable Sơn component/reviewer evidence. The complete
integrated suite ran 50 tests successfully, including six coordinator tests.
These results remain author/integration evidence, not Chúc's independent
execution. Future independent evidence should record the exact command,
coordinator and commitment revisions, Python/platform, full synthetic inputs,
expected and actual outputs, exit status, and unmodified logs.

