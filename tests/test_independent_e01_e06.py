"""Independent tests for cases E01-E06 (Chúc).

Scope and honesty rules (see README, "Evidence and reporting rules"):
- These are functional checks and bounded experiments on specific cases. They
  do NOT prove hiding or binding of the commitment construction, and E01/E05/E06
  only show that the simulation enforces the rules written in docs/model.md.
- Expected commitment values come from tests/oracle.py, a separate
  re-implementation of the written specification. The code under test is
  src/commitment.py, src/auction.py and experiments/guessing.py. These tests do
  not use prepare_commitment() to build openings.
- Fixed random values are TEST FIXTURES. The weak 8-bit r of E04 is an
  experimental configuration, never an M1 setting. Only E01-b and E04-c draw
  fresh randomness with the secrets module.
- A failed search over a bounded domain is not evidence of security. No test
  tries to exhaust a 128-bit random space.
- Price domain and deadlines follow docs/model.md: 100 prices from 10,000 to
  1,000,000 VND in steps of 10,000; T1 = 36,000 s and T2 = 36,600 s.
- E05 expectations use the reason strings returned by src/auction.py. Where the
  code gives one reason to two situations (ineligible bidder and wrong sender
  are both "wrong_bidder") the test records exactly that.

Run from the repository root:  python -m unittest tests.test_independent_e01_e06 -v
"""

import hashlib
import re
import secrets
import time
import unittest

from experiments.guessing import (
    guess_b0, guess_b1, guess_b2_disclosed_randomness, weak_randomness_candidates,
)
from src.auction import Auction
from src.commitment import (
    InvalidCommitmentData, create_b0_commitment, create_b1_commitment,
    create_commitment, generate_randomness, prepare_commitment, verify_opening,
)
from tests import oracle

# PARAMETERS (docs/model.md) AND TEST FIXTURES -------------------------------
AUCTION = "A01"
BIDDER = "U01"
T1, T2 = 36_000, 36_600
MIN_BID, MAX_BID, STEP = 10_000, 1_000_000, 10_000
DOMAIN = range(MIN_BID, MAX_BID + 1, STEP)        # 100 permitted prices
FIXTURE_R = "a1b2c3d4e5f60718293a4b5c6d7e8f90"    # fixed fixture, not secret
FIXTURE_BID = 100_000
WEAK_R_BITS = 8                                    # 256 possible r values
WEAK_R_TRUE = 0xA7                                 # index 167 in the weak domain

# Observations are copied into the JSON evidence file by the runner.
OBSERVATIONS: dict[str, dict] = {}


def record(case_id: str, **values) -> None:
    OBSERVATIONS.setdefault(case_id, {}).update(values)


def fixture_r(bidder_id: str) -> str:
    """Deterministic TEST FIXTURE r for a bidder id (32 lowercase hex digits)."""
    digest = hashlib.sha256(b"test-fixture-r|" + bidder_id.encode()).digest()
    return digest[:16].hex()


def flip_hex_bit(r_hex: str, bit: int) -> str:
    """Return r with one bit (0 = most significant of 128) inverted."""
    return f"{int(r_hex, 16) ^ (1 << (127 - bit)):032x}"


# AUCTION TEST HARNESS -------------------------------------------------------
class Bidder:
    """Bidder side of the protocol; commitment comes from the independent oracle."""

    def __init__(self, bidder_id, bid, r=None):
        self.id, self.bid = bidder_id, bid
        self.r = r if r is not None else fixture_r(bidder_id)

    @property
    def commitment(self):
        return oracle.m1_digest(AUCTION, self.id, self.bid, self.r)

    def commit(self, auction, t, *, sender=None, auction_id=AUCTION, commitment=None):
        return auction.submit_commit(auction_id, self.id, sender or self.id,
                                     self.commitment if commitment is None else commitment, t)

    def reveal(self, auction, t, *, sender=None, auction_id=AUCTION, bid=None, r=None):
        return auction.submit_reveal(auction_id, self.id, sender or self.id,
                                     self.bid if bid is None else bid,
                                     self.r if r is None else r, t)


def make_auction(bidder_ids=("U01", "U02", "U03")):
    return Auction(AUCTION, set(bidder_ids), T1, T2,
                   min_bid=MIN_BID, max_bid=MAX_BID, bid_step=STEP)


def three_bidders(r_override=None):
    """E01 scenario: U01 100,000; U02 130,000; U03 120,000 VND."""
    prices = {"U01": 100_000, "U02": 130_000, "U03": 120_000}
    return [Bidder(u, b, None if r_override is None else r_override[u]) for u, b in prices.items()]


def run_flow(bidders, revealers=None, ids=None):
    """Commit at 35,000+10i, reveal at T1+100i. Returns (auction, commits, reveals)."""
    auction = make_auction(ids or [b.id for b in bidders])
    commits = {b.id: b.commit(auction, 35_000 + 10 * i) for i, b in enumerate(bidders)}
    reveals = {b.id: b.reveal(auction, T1 + 100 * i) for i, b in enumerate(bidders)
               if revealers is None or b.id in revealers}
    return auction, commits, reveals


# ============================== E01 =========================================
class E01ValidFlow(unittest.TestCase):
    """E01: valid three-bidder first-price auction from commit to settlement."""

    def test_E01_a_valid_flow_fixture_r(self):
        bidders = three_bidders()
        auction, commits, reveals = run_flow(bidders)
        for i, b in enumerate(bidders):
            decision = commits[b.id]
            self.assertTrue(decision.accepted, (b.id, decision.reason))
            receipt = decision.receipt
            self.assertEqual((receipt.auction_id, receipt.bidder_id, receipt.received_at),
                             (AUCTION, b.id, 35_000 + 10 * i))
            self.assertEqual(receipt.commitment, b.commitment)
            self.assertNotIn(b.r, repr(decision), "commit receipt must not expose r")
            self.assertTrue(reveals[b.id].accepted, (b.id, reveals[b.id].reason))
        self.assertEqual(auction.settle(T2 - 1).status, "pending")
        final = auction.settle(T2)
        self.assertEqual((final.status, final.winner_id, final.price), ("winner", "U02", 130_000))
        record("E01-a", commitments={b.id: b.commitment for b in bidders},
               winner=final.winner_id, price=final.price, settle_before_T2="pending")

    def test_E01_b_valid_flow_fresh_secure_r(self):
        fresh = {u: secrets.token_hex(16) for u in ("U01", "U02", "U03")}
        for r in fresh.values():
            self.assertEqual(len(bytes.fromhex(r)) * 8, 128)
        bidders = three_bidders(r_override=fresh)
        auction, commits, reveals = run_flow(bidders)
        self.assertTrue(all(d.accepted for d in commits.values()))
        self.assertTrue(all(d.accepted for d in reveals.values()))
        final = auction.settle(T2)
        self.assertEqual((final.winner_id, final.price), ("U02", 130_000))
        fixture_commitments = {b.id: b.commitment for b in three_bidders()}
        for b in bidders:
            self.assertNotEqual(b.commitment, fixture_commitments[b.id])
        record("E01-b", winner=final.winner_id, price=final.price,
               commitments_differ_from_fixture_run=True)

    def test_E01_c_same_inputs_reproduce_same_result(self):
        first_auction, first_commits, _ = run_flow(three_bidders())
        second_auction, second_commits, _ = run_flow(three_bidders())
        self.assertEqual({u: d.receipt for u, d in first_commits.items()},
                         {u: d.receipt for u, d in second_commits.items()})
        self.assertEqual(first_auction.settle(T2), second_auction.settle(T2))
        record("E01-c", reproduced=True)

    def test_E01_d_winner_pays_own_bid_not_second_price(self):
        auction, _, _ = run_flow(three_bidders())
        final = auction.settle(T2)
        self.assertEqual(final.price, 130_000)
        self.assertNotEqual(final.price, 120_000)
        record("E01-d", price=final.price, second_highest_bid=120_000)


# ============================== E02 =========================================
class E02WrongOpening(unittest.TestCase):
    """E02: keep c fixed, change the opening, expect the verifier to say no."""

    @classmethod
    def setUpClass(cls):
        cls.c = oracle.m1_digest(AUCTION, BIDDER, FIXTURE_BID, FIXTURE_R)

    def verify(self, bid=FIXTURE_BID, r=FIXTURE_R, a=AUCTION, u=BIDDER):
        return verify_opening(self.c, a, u, bid, r)

    def test_E02_a_control_correct_opening_accepted(self):
        self.assertEqual(create_commitment(AUCTION, BIDDER, FIXTURE_BID, FIXTURE_R), self.c)
        self.assertTrue(self.verify())
        record("E02-a", commitment=self.c, accepted=True)

    def test_E02_b_changed_bid_rejected_r_unchanged(self):
        changed = [FIXTURE_BID + 1, FIXTURE_BID - 1, 1, 130_000, 2**64 - 1]
        outcomes = {}
        for bid in changed:
            self.assertNotEqual(oracle.m1_digest(AUCTION, BIDDER, bid, FIXTURE_R), self.c,
                                f"oracle says bid {bid} collides: invalid sample")
            outcomes[bid] = self.verify(bid=bid)
        self.assertFalse(any(outcomes.values()), outcomes)
        record("E02-b", samples=len(changed), accepted_count=sum(outcomes.values()),
               note="specific samples only; not a proof against all collisions")

    def test_E02_c_changed_r_rejected_bid_unchanged(self):
        accepted = []
        for bit in range(128):
            r_changed = flip_hex_bit(FIXTURE_R, bit)
            self.assertNotEqual(oracle.m1_digest(AUCTION, BIDDER, FIXTURE_BID, r_changed), self.c)
            if self.verify(r=r_changed):
                accepted.append(bit)
        self.assertEqual(accepted, [], f"single-bit r changes accepted at bits {accepted}")
        record("E02-c", samples=128, accepted_count=0,
               note="each of the 128 single-bit flips of r tried once")

    def test_E02_d_changed_bid_and_r_rejected(self):
        samples = [(130_000, flip_hex_bit(FIXTURE_R, 0)),
                   (FIXTURE_BID + 1, flip_hex_bit(FIXTURE_R, 127)),
                   (1, "00" * 16), (2**64 - 1, "ff" * 16)]
        accepted = [s for s in samples if self.verify(bid=s[0], r=s[1])]
        self.assertEqual(accepted, [])
        record("E02-d", samples=len(samples), accepted_count=0)

    def test_E02_e_context_change_rejected_supplementary(self):
        """Hash-level context binding (A, U). The auction layer's own A/U checks are E05."""
        outcomes = {
            "other_auction": self.verify(a="A02"),
            "other_bidder": self.verify(u="U02"),
            "swapped_A_U": self.verify(a=BIDDER, u=AUCTION),
            "case_changed_A": self.verify(a="a01"),
        }
        self.assertFalse(any(outcomes.values()), outcomes)
        record("E02-e", outcomes=outcomes)

    def test_E02_f_malformed_openings_return_false_not_exception(self):
        bad_calls = {
            "r_uppercase": dict(r=FIXTURE_R.upper()),
            "r_31_digits": dict(r=FIXTURE_R[:-1]),
            "r_34_digits": dict(r=FIXTURE_R + "00"),
            "r_not_hex": dict(r="z" * 32),
            "bid_bool": dict(bid=True),
            "bid_float": dict(bid=float(FIXTURE_BID)),
            "bid_str": dict(bid=str(FIXTURE_BID)),
            "bid_zero": dict(bid=0),
            "bid_negative": dict(bid=-1),
            "bid_2_pow_64": dict(bid=2**64),
            "u_empty": dict(u=""),
            "u_symbol": dict(u="U_1"),
        }
        results = {}
        for name, kwargs in bad_calls.items():
            try:
                results[name] = self.verify(**kwargs)
            except Exception as exc:  # the contract says False, never an exception
                self.fail(f"{name}: verify_opening raised {exc!r}")
        self.assertFalse(any(results.values()), results)
        for c_bad in (self.c.upper(), self.c[:-1], self.c + "0", "", "g" * 64):
            self.assertFalse(verify_opening(c_bad, AUCTION, BIDDER, FIXTURE_BID, FIXTURE_R))
        record("E02-f", rejected=len(bad_calls) + 5)


# ============================== E03 =========================================
class E03GuessB0(unittest.TestCase):
    """E03: a hash of the bid alone can be recovered when the price domain is small."""

    def test_E03_a_b0_recovers_every_bid_in_domain(self):
        rows = {}
        for index, bid in enumerate(DOMAIN, start=1):
            target = oracle.b0_digest(bid)
            self.assertEqual(create_b0_commitment(bid), target)
            found, attempts = oracle.search_b0(target, DOMAIN)
            self.assertEqual((found, attempts), (bid, index))
            tool = guess_b0(target, DOMAIN)
            self.assertEqual((tool.status, tool.bid, tool.attempts), ("match", bid, index))
            rows[bid] = attempts
        self.assertEqual(len(rows), 100)
        record("E03-a", domain_size=len(DOMAIN), recovered=len(rows),
               attempts_for_130000=rows[130_000], worst_case_attempts=max(rows.values()),
               note="illustrates risk for a small known domain; not a claim about M1")

    def test_E03_b_same_search_fails_against_m1_commitments(self):
        """Attacker knows the domain and the A,U context but not r."""
        outcomes = []
        for bid in DOMAIN:
            c_m1 = oracle.m1_digest(AUCTION, BIDDER, bid, secrets.token_hex(16))
            found, attempts = oracle.search_b0(c_m1, DOMAIN)
            tool = guess_b0(c_m1, DOMAIN)
            self.assertEqual((found, attempts), (None, 100))
            self.assertEqual((tool.status, tool.attempts, tool.bid), ("domain_exhausted", 100, None))
            outcomes.append(found)
        target = oracle.m1_digest(AUCTION, BIDDER, 130_000, secrets.token_hex(16))
        wrong_guess, attempts = oracle.search_m1(target, AUCTION, BIDDER, DOMAIN, ["00" * 16])
        self.assertIsNone(wrong_guess)
        record("E03-b", commitments_tried=len(outcomes), recovered=0, wrong_r_attempts=attempts,
               note="no match is NOT a proof of hiding; r secrecy/entropy is the assumption")

    def test_E03_c_result_depends_on_domain_and_budget(self):
        target = oracle.b0_digest(130_000)
        outside = oracle.b0_digest(130_005)  # not a multiple of 10,000
        found_outside, attempts_outside = oracle.search_b0(outside, DOMAIN)
        self.assertEqual((found_outside, attempts_outside), (None, 100))
        short = guess_b0(target, DOMAIN, max_attempts=12)
        exact = guess_b0(target, DOMAIN, max_attempts=13)
        self.assertEqual((short.status, short.attempts), ("budget_exhausted", 12))
        self.assertEqual((exact.status, exact.attempts, exact.bid), ("match", 13, 130_000))
        record("E03-c", outside_domain="domain_exhausted after 100",
               budget_12="budget_exhausted", budget_13="match")


# ============================== E04 =========================================
class E04RoleOfRandomness(unittest.TestCase):
    """E04: compare no r, weak r, secret 128-bit r and disclosed r."""

    def test_E04_a_without_r_equal_bids_give_equal_commitments(self):
        self.assertEqual(oracle.b0_digest(130_000), oracle.b0_digest(130_000))
        self.assertEqual(create_b0_commitment(130_000), create_b0_commitment(130_000))
        m1_one = oracle.m1_digest(AUCTION, "U01", 130_000, secrets.token_hex(16))
        m1_two = oracle.m1_digest(AUCTION, "U02", 130_000, secrets.token_hex(16))
        m1_again = oracle.m1_digest(AUCTION, "U01", 130_000, secrets.token_hex(16))
        self.assertNotEqual(m1_one, m1_two)
        self.assertNotEqual(m1_one, m1_again)  # same A, U, b but fresh r
        found, attempts = oracle.search_b0(create_b0_commitment(130_000), DOMAIN)
        self.assertEqual((found, attempts), (130_000, 13))
        record("E04-a", b0_equal_bids_equal_commitments=True, m1_equal_bids_equal_commitments=False,
               b0_attempts=attempts)

    def test_E04_b_weak_8_bit_r_is_found_in_bounded_search(self):
        weak_domain = [oracle.r_from_int(v) for v in range(1 << WEAK_R_BITS)]
        true_r = oracle.r_from_int(WEAK_R_TRUE)
        expected_attempts = WEAK_R_TRUE * len(DOMAIN) + 13  # r outer loop, bid inner loop
        total_space = len(weak_domain) * len(DOMAIN)

        c_b1 = create_b1_commitment(130_000, true_r)
        self.assertEqual(c_b1, oracle.b1_digest(130_000, true_r))
        found, attempts = oracle.search_b1(c_b1, DOMAIN, weak_domain)
        self.assertEqual((found, attempts), ((130_000, true_r), expected_attempts))
        tool = guess_b1(c_b1, DOMAIN, weak_randomness_candidates(1 << WEAK_R_BITS),
                        max_attempts=total_space)
        self.assertEqual((tool.status, tool.bid, tool.randomness, tool.attempts),
                         ("match", 130_000, true_r, expected_attempts))

        # M1 with the same weak r and a known A,U context is just as exposed.
        c_m1 = create_commitment(AUCTION, BIDDER, 130_000, true_r)
        found_m1, attempts_m1 = oracle.search_m1(c_m1, AUCTION, BIDDER, DOMAIN, weak_domain)
        self.assertEqual((found_m1, attempts_m1), ((130_000, true_r), expected_attempts))
        record("E04-b", r_bits=WEAK_R_BITS, search_space=total_space,
               attempts_to_match=expected_attempts, b1_recovered=True, m1_with_weak_r_recovered=True,
               note="weak r is an experimental configuration; binding A,U does not repair it")

    def test_E04_c_128_bit_r_configuration_only_no_exhaustive_search(self):
        values = [generate_randomness() for _ in range(5000)]
        for r in values:
            self.assertRegex(r, r"^[0-9a-f]{32}$")
            self.assertEqual(len(bytes.fromhex(r)) * 8, 128)
        self.assertEqual(len(set(values)), len(values), "duplicate r among 5,000 draws")

        one = prepare_commitment(AUCTION, BIDDER, 130_000)
        two = prepare_commitment(AUCTION, BIDDER, 130_000)
        self.assertNotEqual(one.randomness, two.randomness)
        self.assertNotEqual(one.commitment, two.commitment)

        # r that is not exactly 128 bits / canonical hex must be refused at creation.
        for bad_r in (one.randomness[:-1], one.randomness + "0", one.randomness.upper(), "zz" * 16):
            with self.assertRaises(InvalidCommitmentData):
                create_commitment(AUCTION, BIDDER, 130_000, bad_r)

        # The provided weak-r generator refuses to build a large domain.
        with self.assertRaises(ValueError):
            weak_randomness_candidates(10_001)

        # Arithmetic only: how long would 2**128 hashes take at this machine's measured rate?
        start = time.perf_counter()
        n = 50_000
        for v in range(n):
            oracle.m1_digest(AUCTION, BIDDER, 130_000, oracle.r_from_int(v))
        rate = n / (time.perf_counter() - start)
        years = (2**128 / rate) / (365.25 * 24 * 3600)
        self.assertGreater(years, 1e12)

        # Small bounded random sample against a secret-r M1 commitment (NOT a security proof).
        target = oracle.m1_digest(AUCTION, BIDDER, 130_000, secrets.token_hex(16))
        sample = 20_000
        hits = sum(oracle.m1_digest(AUCTION, BIDDER, 130_000, secrets.token_hex(16)) == target
                   for _ in range(sample))
        self.assertEqual(hits, 0)
        record("E04-c", r_bits=128, draws=len(values), duplicates=0,
               measured_hashes_per_second=round(rate),
               estimated_years_for_2_pow_128=f"{years:.3e}", random_guesses=sample, hits=hits,
               note="configuration check and arithmetic; no exhaustive search attempted and "
                    "zero hits in a small sample is not a proof of security")

    def test_E04_d_disclosed_r_allows_small_domain_recovery(self):
        r = oracle.r_from_int(0xDEADBEEF)  # stands for a leaked r (fixture)
        target = oracle.m1_digest(AUCTION, BIDDER, 130_000, r)
        self.assertEqual(create_commitment(AUCTION, BIDDER, 130_000, r), target)
        found, attempts = oracle.search_m1(target, AUCTION, BIDDER, DOMAIN, [r])
        self.assertEqual((found, attempts), ((130_000, r), 13))
        tool = guess_b2_disclosed_randomness(target, AUCTION, BIDDER, DOMAIN, r)
        self.assertEqual((tool.status, tool.bid, tool.attempts), ("match", 130_000, 13))
        wrong = guess_b2_disclosed_randomness(target, AUCTION, BIDDER, DOMAIN, oracle.r_from_int(1))
        wrong_context = guess_b2_disclosed_randomness(target, AUCTION, "U02", DOMAIN, r)
        self.assertEqual(wrong.status, "domain_exhausted")
        self.assertEqual(wrong_context.status, "domain_exhausted")
        record("E04-d", attempts_with_disclosed_r=attempts, recovered_bid=130_000,
               wrong_r_status=wrong.status, wrong_context_status=wrong_context.status,
               note="secrecy of r until reveal is a required assumption, not a guarantee")


# ============================== E05 =========================================
class E05SessionRules(unittest.TestCase):
    """E05: acceptance and rejection rules, with the exact reason returned."""

    def assertRejected(self, decision, reason):
        self.assertFalse(decision.accepted, f"expected rejection {reason!r}, got acceptance")
        self.assertEqual(decision.reason, reason)

    def assertAccepted(self, decision):
        self.assertTrue(decision.accepted, f"expected acceptance, got {decision.reason!r}")

    def test_E05_a_duplicate_commit_rejected_first_commit_kept(self):
        auction = make_auction()
        original = Bidder("U01", 100_000)
        duplicate = Bidder("U01", 120_000, r=oracle.r_from_int(77))
        self.assertAccepted(original.commit(auction, 35_000))
        self.assertRejected(duplicate.commit(auction, 35_010), "duplicate_commit")
        # The duplicate's opening must not match: the stored commitment is the first one.
        self.assertRejected(duplicate.reveal(auction, T1), "opening_mismatch")
        self.assertAccepted(original.reveal(auction, T1 + 10))
        record("E05-a", second_commit="duplicate_commit", reveal_of_second_opening="opening_mismatch",
               reveal_of_first_opening="accepted")

    def test_E05_b_commit_at_T1_rejected(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        self.assertRejected(bidder.commit(auction, T1), "commit_closed")
        self.assertRejected(bidder.commit(auction, T1 + 1), "commit_closed")
        self.assertRejected(bidder.reveal(auction, T1 + 2), "no_commitment")
        record("E05-b", commit_at_T1="commit_closed", commit_at_T1_plus_1="commit_closed",
               reveal_after_rejected_commit="no_commitment")

    def test_E05_c_commit_one_second_before_T1_accepted(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        decision = bidder.commit(auction, T1 - 1)
        self.assertAccepted(decision)
        self.assertEqual(decision.receipt.received_at, T1 - 1)
        self.assertAccepted(bidder.reveal(auction, T1))
        record("E05-c", commit_at_T1_minus_1="accepted", receipt_time=T1 - 1)

    def test_E05_d_reveal_before_T1_rejected_then_retry_accepted(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        self.assertAccepted(bidder.commit(auction, 35_000))
        self.assertRejected(bidder.reveal(auction, T1 - 1), "reveal_not_open")
        self.assertAccepted(bidder.reveal(auction, T1))
        record("E05-d", reveal_at_T1_minus_1="reveal_not_open", retry_at_T1="accepted")

    def test_E05_e_reveal_exactly_at_T1_accepted(self):
        auction = make_auction()
        bidder = Bidder("U02", 130_000)
        self.assertAccepted(bidder.commit(auction, 35_000))
        self.assertAccepted(bidder.reveal(auction, T1))
        record("E05-e", reveal_at_T1="accepted")

    def test_E05_f_reveal_at_T2_rejected_T2_minus_1_accepted(self):
        auction = make_auction()
        early, late = Bidder("U01", 100_000), Bidder("U02", 130_000)
        self.assertAccepted(early.commit(auction, 35_000))
        self.assertAccepted(late.commit(auction, 35_010))
        self.assertAccepted(early.reveal(auction, T2 - 1))
        self.assertRejected(late.reveal(auction, T2), "reveal_closed")
        final = auction.settle(T2)
        self.assertEqual((final.status, final.winner_id, final.price), ("winner", "U01", 100_000))
        record("E05-f", reveal_at_T2_minus_1="accepted", reveal_at_T2="reveal_closed",
               winner_after_late_reveal=final.winner_id)

    def test_E05_g_wrong_auction_id_rejected(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        self.assertRejected(bidder.commit(auction, 35_000, auction_id="A02"), "wrong_auction")
        self.assertAccepted(bidder.commit(auction, 35_010))  # first attempt left no state
        self.assertRejected(bidder.reveal(auction, T1, auction_id="A02"), "wrong_auction")
        self.assertAccepted(bidder.reveal(auction, T1 + 1))
        record("E05-g", commit_wrong_A="wrong_auction", reveal_wrong_A="wrong_auction",
               later_correct_commit_and_reveal="accepted")

    def test_E05_h_wrong_sender_or_cross_submitted_opening_rejected(self):
        auction = make_auction()
        u1, u2 = Bidder("U01", 100_000), Bidder("U02", 130_000)
        self.assertRejected(u1.commit(auction, 35_000, sender="U02"), "wrong_bidder")
        self.assertAccepted(u1.commit(auction, 35_010))
        self.assertAccepted(u2.commit(auction, 35_020))
        self.assertRejected(u1.reveal(auction, T1, sender="U02"), "wrong_bidder")
        # U02 submits U01's opening under U02's own identity: hash is bound to U.
        cross = auction.submit_reveal(AUCTION, "U02", "U02", u1.bid, u1.r, T1 + 1)
        self.assertRejected(cross, "opening_mismatch")
        self.assertAccepted(u1.reveal(auction, T1 + 2))
        self.assertAccepted(u2.reveal(auction, T1 + 3))
        record("E05-h", commit_sender_mismatch="wrong_bidder", reveal_sender_mismatch="wrong_bidder",
               cross_submitted_opening="opening_mismatch")

    def test_E05_i_ineligible_bidder_rejected(self):
        auction = make_auction()
        outsider = Bidder("U99", 100_000)
        self.assertRejected(outsider.commit(auction, 35_000), "wrong_bidder")
        self.assertRejected(outsider.reveal(auction, T1), "wrong_bidder")
        record("E05-i", commit="wrong_bidder", reveal="wrong_bidder",
               note="code uses the same reason for ineligible bidder and sender mismatch")

    def test_E05_j_reveal_without_commitment_rejected(self):
        auction = make_auction()
        never_committed = Bidder("U03", 120_000)
        self.assertRejected(never_committed.reveal(auction, T1), "no_commitment")
        record("E05-j", reveal="no_commitment")

    def test_E05_k_invalid_bid_rejected_even_with_matching_commitment(self):
        outcomes = {}
        for bid in (5_000, 125_000, 1_010_000):  # below min, off the step grid, above max
            auction = make_auction()
            bidder = Bidder("U01", bid)
            self.assertAccepted(bidder.commit(auction, 35_000))  # commit phase does not see b
            self.assertRejected(bidder.reveal(auction, T1), "invalid_bid")
            outcomes[bid] = "invalid_bid"
        for bad_type in (True, 130_000.0, "130000"):
            auction = make_auction()
            bidder = Bidder("U01", 130_000)
            self.assertAccepted(bidder.commit(auction, 35_000))
            self.assertRejected(bidder.reveal(auction, T1, bid=bad_type), "invalid_bid")
            outcomes[repr(bad_type)] = "invalid_bid"
        record("E05-k", outcomes=outcomes)

    def test_E05_l_malformed_commitment_rejected_and_not_stored(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        good = bidder.commitment
        malformed = {"uppercase": good.upper(), "too_short": good[:-1], "too_long": good + "0",
                     "empty": "", "not_hex": "g" * 64}
        for name, bad in malformed.items():
            self.assertRejected(bidder.commit(auction, 35_000, commitment=bad), "invalid_commitment")
        self.assertAccepted(bidder.commit(auction, 35_010))  # earlier rejections left no record
        record("E05-l", rejected_forms=sorted(malformed), later_valid_commit="accepted")

    def test_E05_m_failed_reveal_can_be_retried_first_valid_reveal_kept(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        self.assertAccepted(bidder.commit(auction, 35_000))
        self.assertRejected(bidder.reveal(auction, T1, r=flip_hex_bit(bidder.r, 5)), "opening_mismatch")
        self.assertAccepted(bidder.reveal(auction, T1 + 1))
        self.assertRejected(bidder.reveal(auction, T1 + 2), "already_revealed")
        self.assertRejected(bidder.reveal(auction, T1 + 3, bid=500_000), "already_revealed")
        final = auction.settle(T2)
        self.assertEqual((final.winner_id, final.price), ("U01", 100_000))
        record("E05-m", wrong_r="opening_mismatch", correct_retry="accepted",
               second_reveal="already_revealed", settled_price=final.price)

    def test_E05_n_time_and_configuration_guards_raise(self):
        auction = make_auction()
        bidder = Bidder("U01", 100_000)
        self.assertAccepted(bidder.commit(auction, 35_000))
        with self.assertRaises(ValueError):          # time moving backwards
            bidder.commit(auction, 34_999)
        with self.assertRaises(ValueError):          # outside the day
            auction.settle(86_400)
        for t1, t2 in ((T1, T1), (T2, T1), (-1, T2), (T1, 86_400)):
            with self.assertRaises(ValueError, msg=f"T1={t1}, T2={t2}"):
                Auction(AUCTION, {"U01"}, t1, t2, min_bid=MIN_BID, max_bid=MAX_BID, bid_step=STEP)
        for kwargs in (dict(min_bid=0, max_bid=MAX_BID, bid_step=STEP),
                       dict(min_bid=MAX_BID, max_bid=MIN_BID, bid_step=STEP),
                       dict(min_bid=MIN_BID, max_bid=MAX_BID, bid_step=0)):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                Auction(AUCTION, {"U01"}, T1, T2, **kwargs)
        record("E05-n", backwards_time="ValueError", time_outside_day="ValueError",
               invalid_T1_T2_and_price_parameters="ValueError")


# ============================== E06 =========================================
class E06NonRevealTiesNoWinner(unittest.TestCase):
    """E06: missing reveals, ties and auctions with no valid reveal."""

    def test_E06_a_highest_bidder_does_not_reveal_winner_changes(self):
        bidders = three_bidders()
        full, _, _ = run_flow(bidders)
        with_u2_silent, _, reveals = run_flow(bidders, revealers={"U01", "U03"})
        self.assertNotIn("U02", reveals)
        self.assertEqual(full.settle(T2).winner_id, "U02")
        final = with_u2_silent.settle(T2)
        self.assertEqual((final.status, final.winner_id, final.price), ("winner", "U03", 120_000))
        record("E06-a", winner_if_all_reveal="U02", winner_if_U02_silent=final.winner_id,
               price_if_U02_silent=final.price,
               note="a commitment does not force reveal; the silent top bidder just drops out")

    def test_E06_b_tie_resolved_by_id_not_arrival_order(self):
        # U02 commits and reveals first, yet the smaller id U01 wins the tie.
        bidders = [Bidder("U02", 130_000), Bidder("U01", 130_000), Bidder("U03", 100_000)]
        auction, _, reveals = run_flow(bidders, ids=["U01", "U02", "U03"])
        self.assertTrue(all(d.accepted for d in reveals.values()))
        final = auction.settle(T2)
        self.assertEqual((final.winner_id, final.price), ("U01", 130_000))
        # Lexicographic order: "U10" sorts before "U2".
        lex = [Bidder("U2", 200_000), Bidder("U10", 200_000), Bidder("U3", 100_000)]
        auction2, _, reveals2 = run_flow(lex)
        self.assertTrue(all(d.accepted for d in reveals2.values()))
        final2 = auction2.settle(T2)
        self.assertEqual((final2.winner_id, final2.price), ("U10", 200_000))
        record("E06-b", tie_winner_U01_vs_U02="U01", arrival_order="U02 first",
               tie_winner_U10_vs_U2=final2.winner_id, rule="smallest id lexicographically")

    def test_E06_c_no_valid_reveal_means_no_winner(self):
        bidders = three_bidders()
        nobody, _, _ = run_flow(bidders, revealers=set())
        silent = nobody.settle(T2)
        self.assertEqual((silent.status, silent.winner_id, silent.price), ("no_winner", None, None))

        # Everybody reveals, but every opening is wrong: still no winner.
        auction = make_auction()
        for i, b in enumerate(bidders):
            self.assertTrue(b.commit(auction, 35_000 + i).accepted)
        for i, b in enumerate(bidders):
            decision = b.reveal(auction, T1 + i, r=flip_hex_bit(b.r, 0))
            self.assertEqual(decision.reason, "opening_mismatch")
        wrong = auction.settle(T2)
        self.assertEqual((wrong.status, wrong.winner_id, wrong.price), ("no_winner", None, None))
        record("E06-c", nobody_reveals=silent.status, all_openings_wrong=wrong.status)

    def test_E06_d_single_valid_reveal_wins_and_pays_own_bid(self):
        bidders = three_bidders()
        auction, _, reveals = run_flow(bidders, revealers={"U01"})
        self.assertEqual(list(reveals), ["U01"])
        final = auction.settle(T2)
        self.assertEqual((final.status, final.winner_id, final.price), ("winner", "U01", 100_000))
        record("E06-d", winner=final.winner_id, price=final.price,
               note="no reserve price in M1 beyond the minimum permitted bid")

    def test_E06_e_settlement_timing_and_late_reveal_changes_nothing(self):
        bidders = three_bidders()
        auction = make_auction()
        for i, b in enumerate(bidders):
            self.assertTrue(b.commit(auction, 35_000 + i).accepted)
        self.assertEqual(auction.settle(T1).status, "pending")        # reveal phase just opened
        self.assertTrue(bidders[0].reveal(auction, T1).accepted)       # U01
        self.assertTrue(bidders[1].reveal(auction, T1 + 50).accepted)  # U02
        self.assertEqual(auction.settle(T2 - 1).status, "pending")
        final = auction.settle(T2)
        self.assertEqual((final.winner_id, final.price), ("U02", 130_000))
        late = bidders[2].reveal(auction, T2)                          # U03 reveals too late
        self.assertFalse(late.accepted)
        self.assertEqual(late.reason, "reveal_closed")
        self.assertEqual(auction.settle(T2 + 10), final)
        record("E06-e", settle_at_T1="pending", settle_at_T2_minus_1="pending",
               settle_at_T2=final.winner_id, late_reveal=late.reason, settlement_unchanged=True)

    def test_E06_f_wrong_opening_never_corrected_counts_as_non_reveal(self):
        bidders = three_bidders()
        auction = make_auction()
        for i, b in enumerate(bidders):
            self.assertTrue(b.commit(auction, 35_000 + i).accepted)
        bad = bidders[1].reveal(auction, T1, r=flip_hex_bit(bidders[1].r, 64))  # U02, wrong r
        self.assertEqual(bad.reason, "opening_mismatch")
        self.assertTrue(bidders[0].reveal(auction, T1 + 1).accepted)
        self.assertTrue(bidders[2].reveal(auction, T1 + 2).accepted)
        final = auction.settle(T2)
        self.assertEqual((final.winner_id, final.price), ("U03", 120_000))
        record("E06-f", U02_reveal="opening_mismatch", winner=final.winner_id, price=final.price)


CASE_ID = re.compile(r"test_(E\d\d)_([a-z])")


def case_id(test_name: str) -> str:
    match = CASE_ID.match(test_name)
    return f"{match.group(1)}-{match.group(2)}" if match else test_name


if __name__ == "__main__":
    unittest.main()
