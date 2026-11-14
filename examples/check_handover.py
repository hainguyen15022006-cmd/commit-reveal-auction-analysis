"""Known-answer smoke check, runnable in the repo or standalone handover folder."""

if __package__ == "examples":
    from src.commitment import create_commitment, encode, prepare_commitment, verify_opening
else:
    from commitment import create_commitment, encode, prepare_commitment, verify_opening


def main() -> None:
    # PUBLIC TEST FIXTURE ONLY. Normal runs must generate fresh randomness.
    r = "00112233445566778899aabbccddeeff"
    expected = "7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71"
    expected_bytes = bytes.fromhex(
        "0000000d43522d41554354494f4e2d7631"
        "00000003413031" "00000003553031" "00000003564e44"
        "0000000800000000000186a0"
        "0000001000112233445566778899aabbccddeeff"
    )
    c = create_commitment("A01", "U01", 100000, r)
    checks = {
        "exact 70-byte encoding": encode("A01", "U01", 100000, r) == expected_bytes,
        "SHA-256 reference": c == expected,
        "valid opening": verify_opening(c, "A01", "U01", 100000, r),
        "changed bid rejected": not verify_opening(c, "A01", "U01", 140000, r),
        "changed randomness rejected": not verify_opening(c, "A01", "U01", 100000, "10" * 16),
        "wrong auction rejected": not verify_opening(c, "A02", "U01", 100000, r),
        "wrong bidder rejected": not verify_opening(c, "A01", "U02", 100000, r),
    }
    normal = prepare_commitment("A01", "U02", 130000)
    checks["normal random opening"] = verify_opening(
        normal.commitment, "A01", "U02", 130000, normal.randomness)
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    print("Reference commitment:", c)
    print("These are component checks; run E01 in the auction coordinator separately.")
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
