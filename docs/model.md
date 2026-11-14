# M1 — First-price sealed-bid auction

M1 models one item in a first-price sealed-bid auction. The organizer publishes a unique auction ID `A`, eligible bidder IDs `U`, bid rules in integer VND, the deadlines `T1 < T2`, and the tie-breaking rule before accepting commitments. Equal bids are ordered lexicographically by the preassigned bidder ID, smallest first.

## Commitment

`c = SHA-256(Encode("CR-AUCTION-v1", A, U, "VND", b, r))`

The B2 encoding follows [the commitment API](commitment-api.md). Six fields appear in the order above, each with a four-byte unsigned big-endian length. Identifiers contain ASCII letters or digits. The bid is an eight-byte unsigned big-endian integer, and the opening randomness is 16 raw bytes in the encoding. The API carries the digest and randomness as lowercase hex strings. The bidder generates fresh randomness with a cryptographic random generator and keeps it secret until reveal.

## Auction rules

1. **Commit, `t < T1`.** The organizer checks the session and sender against `A` and `U`. It accepts the first well-formed commitment per eligible bidder and issues a receipt with `A`, `U`, `c` and receipt time. Bid and randomness stay with the bidder.
2. **Freeze, `t = T1`.** The accepted commitment set becomes fixed. The simulation enforces this by advancing time monotonically and rejecting every commit at or after `T1`.
3. **Reveal, `T1 ≤ t < T2`.** The bidder submits `b,r` for the same `A,U`. The organizer verifies the session, sender, price, and hash against the stored commitment. The first valid reveal is retained. The simulation allows a rejected opening to be retried while this window remains open.
4. **Settle, `t ≥ T2`.** Only valid reveals count. The highest bid wins and pays its own bid. Apply the announced ID ordering to a tie. An empty set of valid reveals yields no winner.

## Simulation parameters and assumptions

The example uses 100 permitted prices from 10,000 through 1,000,000 VND in increments of 10,000 VND. The illustrative deadlines on one hypothetical day are 10:00 and 10:10 Vietnam time. The runner represents them as integer seconds from midnight (36,000 and 36,600).

Sender identity and receipt time come from the scenario. The model assumes the organizer preserves the frozen commitments. The receipt records acceptance within the simulation. Organizer tampering remains a limitation because the model provides neither signed receipts nor an independent audit record.

If two different openings validate against one fixed commitment for the same session and bidder, unambiguous encoding gives two distinct byte strings with the same SHA-256 digest. Finding such a pair would yield a collision. Binding therefore relies on collision resistance and preserving the commitment used for verification.
