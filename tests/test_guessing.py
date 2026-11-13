import unittest

from experiments.guessing import (
    guess_b0, guess_b1, guess_b2_disclosed_randomness, weak_randomness_candidates,
)
from src.commitment import create_b0_commitment, create_b1_commitment, create_commitment


class GuessingTests(unittest.TestCase):
    BIDS = range(10000, 1000001, 10000)  # Illustrative domain, not global M1 policy.

    def test_b0_recovers_bid_with_known_attempt_count(self):
        result = guess_b0(create_b0_commitment(130000), self.BIDS)
        self.assertEqual((result.status, result.bid, result.attempts), ("match", 130000, 13))

    def test_domain_endpoints_are_included(self):
        for bid, attempts in ((10000, 1), (1000000, 100)):
            result = guess_b0(create_b0_commitment(bid), self.BIDS)
            self.assertEqual((result.bid, result.attempts), (bid, attempts))

    def test_absent_bid_exhausts_domain(self):
        result = guess_b0(create_b0_commitment(1000001), self.BIDS)
        self.assertEqual((result.status, result.attempts, result.bid), ("domain_exhausted", 100, None))

    def test_budget_stops_before_matching_candidate(self):
        result = guess_b0(create_b0_commitment(130000), self.BIDS, max_attempts=12)
        self.assertEqual((result.status, result.attempts, result.bid), ("budget_exhausted", 12, None))

    def test_match_on_last_allowed_attempt(self):
        result = guess_b0(create_b0_commitment(130000), self.BIDS, max_attempts=13)
        self.assertEqual((result.status, result.attempts), ("match", 13))

    def test_exact_budget_equal_to_domain_reports_exhaustion_correctly(self):
        result = guess_b0(create_b0_commitment(1000001), self.BIDS, max_attempts=100)
        self.assertEqual((result.status, result.attempts), ("domain_exhausted", 100))

    def test_empty_domain_has_zero_attempts(self):
        result = guess_b0(create_b0_commitment(1), [])
        self.assertEqual((result.status, result.attempts), ("domain_exhausted", 0))

    def test_one_shot_b0_candidate_iterator_is_supported(self):
        result = guess_b0(create_b0_commitment(2), iter([1, 2]))
        self.assertEqual((result.bid, result.attempts), (2, 2))

    def test_weak_r_uses_explicit_small_domain_and_search_order(self):
        r = "00000000000000000000000000000007"
        target = create_b1_commitment(130000, r)
        result = guess_b1(target, self.BIDS, weak_randomness_candidates(16))
        self.assertEqual((result.status, result.bid, result.randomness, result.attempts),
                         ("match", 130000, r, 713))

    def test_missing_r_candidate_exhausts_pairs(self):
        target = create_b1_commitment(130000, "f" * 32)
        result = guess_b1(target, self.BIDS, weak_randomness_candidates(16))
        self.assertEqual((result.status, result.attempts), ("domain_exhausted", 1600))

    def test_disclosed_b1_r_reduces_search_to_bid_domain(self):
        r = "00112233445566778899aabbccddeeff"
        result = guess_b1(create_b1_commitment(130000, r), self.BIDS, [r])
        self.assertEqual((result.bid, result.attempts), (130000, 13))

    def test_disclosed_b2_r_requires_matching_context(self):
        r = "00112233445566778899aabbccddeeff"
        target = create_commitment("A01", "U02", 130000, r)
        found = guess_b2_disclosed_randomness(target, "A01", "U02", self.BIDS, r)
        wrong = guess_b2_disclosed_randomness(target, "A02", "U02", self.BIDS, r)
        self.assertEqual((found.bid, found.attempts), (130000, 13))
        self.assertEqual((wrong.status, wrong.attempts), ("domain_exhausted", 100))

    def test_weak_fixture_generation_is_bounded_and_repeatable(self):
        self.assertEqual(list(weak_randomness_candidates(2)), ["0" * 32, "0" * 31 + "1"])
        for count in (0, -1, 10001, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                weak_randomness_candidates(count)

    def test_invalid_budget_and_target_are_rejected(self):
        target = create_b0_commitment(1)
        for budget in (0, -1, True, 1.5):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                guess_b0(target, [1], max_attempts=budget)
        with self.assertRaises(ValueError):
            guess_b0("invalid", [1])

    def test_b1_requires_reusable_bid_sequence(self):
        with self.assertRaises(TypeError):
            guess_b1(create_b1_commitment(1, "0" * 32), iter([1]), ["0" * 32])

    def test_empty_b1_bid_domain_does_not_consume_randomness_iterator(self):
        def should_not_be_read():
            raise AssertionError("Empty bid domain must not consume the randomness domain")
            yield "0" * 32
        result = guess_b1(create_b1_commitment(1, "0" * 32), [], should_not_be_read())
        self.assertEqual((result.status, result.attempts), ("domain_exhausted", 0))


if __name__ == "__main__":
    unittest.main()
