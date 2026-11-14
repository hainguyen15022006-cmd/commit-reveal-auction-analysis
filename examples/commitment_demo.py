"""Show a normal bidder-side commitment and its later opening, without a clock.

This is an API demonstration, not a complete auction or a test of its deadlines.
"""

import json

from src.commitment import prepare_commitment, verify_opening


def main() -> None:
    private_state = prepare_commitment("A01", "U01", 100000)
    public_record = private_state.public_submission()
    print("COMMIT: only this payload is sent to the auction coordinator")
    print(json.dumps(public_record, indent=2))

    # In the full application, the auction coordinator opens the reveal phase
    # after freezing commitments. This example illustrates only the crypto API.
    opening = private_state.reveal_payload()
    print("REVEAL: the opening is now explicitly disclosed")
    print(json.dumps(opening, indent=2))
    matches = verify_opening(public_record["commitment"], "A01", "U01",
                             opening["bid"], opening["randomness"])
    print(f"Hash matches the retained commitment: {matches}")
    print("The auction coordinator must still check identity, session, price and deadlines.")


if __name__ == "__main__":
    main()
