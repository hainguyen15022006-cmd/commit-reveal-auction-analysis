import hashlib
import unittest
from unittest.mock import patch

from src.commitment import (
    InvalidCommitmentData, create_b0_commitment, create_b1_commitment,
    create_commitment, encode, encode_b0, encode_b1, generate_randomness,
    prepare_commitment, validate_commitment, verify_opening,
)


class CommitmentTests(unittest.TestCase):
    # Public, patterned randomness from study guide pages 6 and 8; TEST ONLY.
    R = "00112233445566778899aabbccddeeff"
    VECTOR = "2468ab327de725704949ff21b4e58ef38cf7ee100a634951593ea494e3f2f544"
    MESSAGE = b"CR-AUCTION-v1|A01|U01|VND|100000|00112233445566778899aabbccddeeff"

    def test_published_m1_vector_and_exact_input_bytes(self):
        self.assertEqual(encode("A01", "U01", 100000, self.R), self.MESSAGE)
        self.assertEqual(create_commitment("A01", "U01", 100000, self.R), self.VECTOR)

    def test_b0_and_b1_against_independently_written_byte_strings(self):
        self.assertEqual(encode_b0(100000), b"100000")
        self.assertEqual(encode_b1(100000, self.R),
                         b"100000|00112233445566778899aabbccddeeff")
        self.assertEqual(create_b0_commitment(100000), hashlib.sha256(b"100000").hexdigest())
        self.assertEqual(create_b1_commitment(100000, self.R),
                         hashlib.sha256(b"100000|00112233445566778899aabbccddeeff").hexdigest())

    def test_deterministic_full_digest(self):
        self.assertEqual(create_commitment("A01", "U01", 100000, self.R), self.VECTOR)
        self.assertEqual(len(bytes.fromhex(self.VECTOR)), 32)

    def test_valid_opening(self):
        self.assertTrue(verify_opening(self.VECTOR, "A01", "U01", 100000, self.R))

    def test_changed_fields_fail_against_frozen_commitment(self):
        cases = [
            ("A01", "U01", 140000, self.R),
            ("A01", "U01", 100000, "10112233445566778899aabbccddeeff"),
            ("A02", "U01", 100000, self.R),
            ("A01", "U02", 100000, self.R),
        ]
        for fields in cases:
            with self.subTest(fields=fields[:3]):
                self.assertFalse(verify_opening(self.VECTOR, *fields))

    def test_delimiters_separate_ambiguous_identifier_pairs(self):
        first = encode("1", "23", 100000, self.R)
        second = encode("12", "3", 100000, self.R)
        self.assertNotEqual(first, second)
        self.assertEqual(first.split(b"|")[1:3], [b"1", b"23"])
        self.assertEqual(second.split(b"|")[1:3], [b"12", b"3"])

    def test_identifiers_are_case_sensitive(self):
        self.assertNotEqual(encode("A01", "U01", 100000, self.R),
                            encode("a01", "U01", 100000, self.R))

    def test_invalid_identifiers_are_rejected_in_both_positions(self):
        for value in ("", "A|01", " A01", "A01\n", "A\x00", "A-01", "Ａ01", "Sơn", 1, None):
            with self.subTest(value=value):
                with self.assertRaises(InvalidCommitmentData):
                    encode(value, "U01", 100000, self.R)
                with self.assertRaises(InvalidCommitmentData):
                    encode("A01", value, 100000, self.R)

    def test_price_range_policy_is_not_invented_by_crypto_module(self):
        # Positive integers outside the illustrative domain remain encodable.
        # The auction layer must enforce its actual min/max/step constraints.
        for bid in (1, 10001, 1000001):
            self.assertIn(str(bid).encode("ascii"), encode("A01", "U01", bid, self.R))

    def test_invalid_bid_types_and_values_are_rejected(self):
        for bid in (True, False, 0, -1, 100000.0, "100000", "0100000", None):
            with self.subTest(bid=bid):
                for func in (lambda: encode_b0(bid), lambda: encode_b1(bid, self.R),
                             lambda: encode("A01", "U01", bid, self.R)):
                    with self.assertRaises(InvalidCommitmentData):
                        func()

    def test_noncanonical_randomness_is_rejected(self):
        for r in ("", self.R[:-1], self.R + "0", self.R.upper(), "g" * 32,
                  "0" * 31 + "|", self.R + "\n", b"0" * 16, None, 0):
            with self.subTest(randomness_type=type(r).__name__):
                with self.assertRaises(InvalidCommitmentData):
                    encode("A01", "U01", 100000, r)
                with self.assertRaises(InvalidCommitmentData):
                    encode_b1(100000, r)

    def test_zero_fixture_is_valid_format_not_a_claim_of_entropy(self):
        self.assertTrue(encode("A01", "U01", 100000, "0" * 32).endswith(b"0" * 32))

    def test_malformed_digest_is_rejected(self):
        for digest in ("", self.VECTOR[:-1], self.VECTOR + "0", self.VECTOR.upper(),
                       "z" * 64, self.VECTOR + "\n", None, 42):
            with self.subTest(digest_type=type(digest).__name__):
                self.assertFalse(verify_opening(digest, "A01", "U01", 100000, self.R))
                with self.assertRaises(InvalidCommitmentData):
                    validate_commitment(digest)

    def test_malformed_opening_returns_false(self):
        for fields in (("A|1", "U01", 100000, self.R),
                       ("A01", "U01", True, self.R), ("A01", "U01", 100000, "bad")):
            self.assertFalse(verify_opening(self.VECTOR, *fields))

    def test_randomness_uses_secrets_with_16_bytes(self):
        with patch("src.commitment.secrets.token_hex", return_value=self.R) as generator:
            self.assertEqual(generate_randomness(), self.R)
            generator.assert_called_once_with(16)

    def test_real_randomness_has_required_format(self):
        # A structural check only, not a statistical test of entropy/security.
        r = generate_randomness()
        self.assertRegex(r, r"^[0-9a-f]{32}$")
        self.assertEqual(len(bytes.fromhex(r)), 16)

    def test_normal_preparation_generates_randomness_and_retains_opening(self):
        with patch("src.commitment.generate_randomness", return_value=self.R) as generator:
            prepared = prepare_commitment("A01", "U01", 100000)
            generator.assert_called_once_with()
        self.assertEqual(prepared.commitment, self.VECTOR)
        self.assertEqual(prepared.randomness, self.R)
        self.assertEqual(prepared.reveal_payload(), {
            "auction_id": "A01", "bidder_id": "U01", "bid": 100000, "randomness": self.R,
        })

    def test_public_payload_and_repr_do_not_disclose_opening(self):
        prepared = prepare_commitment("A01", "U01", 100000, randomness=self.R)
        self.assertEqual(prepared.public_submission(), {
            "auction_id": "A01", "bidder_id": "U01", "commitment": self.VECTOR,
        })
        self.assertNotIn(self.R, repr(prepared))
        self.assertNotIn("bid=", repr(prepared))
        self.assertNotIn("randomness=", repr(prepared))

    def test_fixture_override_does_not_generate_randomness(self):
        with patch("src.commitment.generate_randomness") as generator:
            prepared = prepare_commitment("A01", "U01", 100000, randomness=self.R)
            generator.assert_not_called()
        self.assertEqual(prepared.commitment, self.VECTOR)

    def test_invalid_fixture_does_not_silently_fall_back_to_randomness(self):
        with self.assertRaises(InvalidCommitmentData):
            prepare_commitment("A01", "U01", 100000, randomness="")


if __name__ == "__main__":
    unittest.main()
