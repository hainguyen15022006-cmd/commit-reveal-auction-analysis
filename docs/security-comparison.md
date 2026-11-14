# Security comparison: B0, B1, and B2/M1

## Constructions and scope

| Variant | Construction | Added protection | Important omission |
| --- | --- | --- | --- |
| B0 | `H(encode_b0(b))` | A fixed digest can detect a changed tested bid | No randomness or context; a known small bid domain is enumerable |
| B1 | `H(Encode(b,r))` | Secret unpredictable r can enlarge the pre-reveal search space | Does not bind the auction A, bidder U, tag, or currency |
| B2/M1 | `H(Encode(tag,A,U,currency,b,r))` plus approved auction checks | Adds explicit domain/context binding and protocol admission/settlement rules | Still depends on authentication, time, storage, randomness secrecy, availability, and organizer behavior |

In the available implementation, B0 encodes b as eight unsigned big-endian
bytes; B1 length-prefixes that b and 16 raw r bytes; B2 uses
`m1-length-prefixed-be-v1` for all six fields. Thành Lê's approved
`docs/model.md` confirms this format and the 100-price example domain. “M1”
means B2 together with the separate one-commit, deadline, freeze,
reveal-validation, and settlement rules. The hash function alone is not the
complete auction.

Dương's `docs/duong-threat-model-review.md` at `1e943697…` is a working technical
reference, not a final team-approved report section. Its assumptions about
simulated identity/time, trusted in-memory records, endpoint secrecy, non-reveal,
organizer power, and finite-test limits are consistent with this analysis; no
material contradiction was found.

## Correctness

1. **Claimed property.** If an honest bidder commits and later presents exactly
   the same valid fields, verification returns true; altered fields should be
   rejected except with a hash collision or implementation/state failure. Full
   M1 correctness additionally selects the highest valid revealed bid and
   applies the tie/no-winner rules.
2. **Required assumptions.** Every party uses the same canonical encoding and
   validation policy; c is stored unchanged; expected A/U come from trusted
   auction/authentication context; deadlines and settlement are correctly
   enforced; SHA-256 and the software execute as specified.
3. **Mechanism.** The verifier canonically re-encodes the opening, hashes it, and
   compares the full digest. The coordinator must separately check auction
   state, bid policy, identity, time, duplicates, and frozen storage.
4. **Supporting evidence.** The independently recomputed 70-byte vector matches
   `7b4df9d0…2b71`. The component review passed 44 tests and 10 runner checks.
   The integrated commit passed 50 tests, including all six coordinator tests;
   E01 selected U02 at 130000 VND, and E05/E06 produced the documented boundary,
   identity, non-reveal, tie, and no-winner behavior. Chúc RUN01 independently
   passed 37/37 cases across E01-E06, with a separate specification-based oracle;
   this review reproduced the same 37/37 result from its recorded source commit.
5. **What remains unproven.** Tests cover examples, not every input,
   implementation fault, SHA-256 correctness in all environments, production
   authentication/time/storage, or organizer honesty. An independent passing
   suite improves confidence in functional behavior but is not a formal proof.

Cryptographic correctness and auction execution correctness are different
claims. The former was observed when canonical openings matched their digests;
the latter was observed for the integrated E01/E02/E05/E06 cases only under the
coordinator's simulated identity, monotonic time, and preserved in-memory state.

## Hiding

1. **Claimed property.** Before reveal, B1/B2 are intended to keep b
   computationally hidden when r is fresh, independent, uniformly sampled from
   128 bits, and secret. B0 does not hide bids drawn from the tested 100-value
   domain. B1/B2 also lose the demonstrated small-domain protection when r is
   disclosed or drawn from a known tiny domain.
2. **Required assumptions.** The observer does not learn r; the generator is an
   appropriate CSPRNG and is not reused/predictable; bidder devices and logs do
   not leak the opening; the candidate r space is genuinely large; SHA-256
   behaves suitably for this use (commonly reasoned about with a random-oracle
   or comparable preimage-resistance assumption).
3. **Mechanism.** r randomizes the hash input, forcing an observer who guesses b
   also to account for r. Context fields prevent reuse of exactly the same input
   across different A/U values but do not replace secret randomness.
4. **Supporting evidence.** B0 recovered 130000 from 100 bids on attempt 13. A
   16-value weak-r B1 case recovered the opening on attempt 713; disclosed-r B1
   and B2 recovered the bid on attempt 13. Normal preparation used
   `secrets.token_hex(16)`, produced 16 bytes, omitted b/r from the public
   payload, and later opened correctly. Independently, RUN01 recovered B1 and M1
   under a different 256-value weak-r domain on attempt 16713 and recovered a
   disclosed-r bid on attempt 13. Its bounded normal-r samples found no hits, a
   result explicitly treated as non-proof.
5. **What remains unproven.** The normal structural check does not measure
   entropy, exclude side channels, or prove hiding. No exhaustive 128-bit search
   was attempted, and failing to find a candidate would not itself prove
   security. SHA-256 has not been proven to be an ideal random oracle.

Collision resistance alone does not imply hiding: deterministic B0 uses
SHA-256 yet is guessable because its input domain is small.

The weak-r results are not interchangeable complexity estimates. Sơn's true
r=7 in a 16-value domain gives `7*100+13 = 713`; Chúc's true r=167 in a
256-value domain gives `167*100+13 = 16713`. Both show that encoded 128-bit width
does not create entropy when selection comes from a small known set.

## Binding

1. **Claimed property.** After c is fixed, a bidder should not be able to find
   two distinct valid openings accepted for the same expected M1 context.
2. **Required assumptions.** Encoding is injective over accepted field tuples;
   the complete digest is checked; SHA-256 collision/second-preimage attacks are
   computationally infeasible; the original commitment and acceptance record
   cannot be replaced; the coordinator uses the intended frozen A/U context.
3. **Mechanism.** Canonical length-prefixed encoding maps distinct accepted field
   tuples to distinct bytes, after which opening c in two ways would require
   finding distinct accepted inputs with the same digest. Including A/U binds
   the bytes to a context; trusted storage binds the protocol to the originally
   accepted c.
4. **Supporting evidence.** The implementation distinguishes ambiguous field
   pairs and rejects tested changes to b, r, A, and U. The source uses the full
   SHA-256 digest and strict representations. In integration, a duplicate commit
   was rejected and the original stored commitment subsequently opened
   successfully, while no commit was accepted at or after T1. RUN01 independently
   rejected five changed-bid samples, 128 single-bit r changes, four combined
   changes, four context changes, and cross-submitted openings; its duplicate
   case also retained and later accepted the first opening.
5. **What remains unproven.** A finite test set does not prove binding or the
   absence of collisions. No formal reduction, cryptanalysis, persistent
   immutable database, or independent audit mechanism was evaluated. Binding
   does not imply authentication: an attacker may submit or replace records if
   the surrounding system permits it.

## Small-domain guessing and randomness

B0's work factor is bounded by the known bid candidates. In E03 the thirteenth
ascending candidate matched; no property of SHA-256 was broken. B1 protects
against that direct table only to the extent r is unknown and unpredictable.
The weak experiment deliberately stores r in a 128-bit-wide field but selects it
from 16 known values, so its entropy is at most four bits. Encoded width and
entropy are different quantities. If r is disclosed early, B1 and B2 reduce to
one hash comparison per bid candidate for a known context. A secure normal M1
run therefore needs independent CSPRNG output for every commitment and secrecy
until the reveal phase.

Reusing the same r does not necessarily reveal b immediately, but it violates
the independent-freshness assumption and can enable correlation or amortized
guessing. The safe rule is a fresh r per commitment.

## Context binding, authentication, and replay

B1 does not include A or U. Its same `(b,r)` opening produces the same digest
across auctions and bidders, allowing cross-context correlation and possible
replay wherever the coordinator fails to add its own binding. B2 changes the
digest when A or U changes and therefore makes a captured opening invalid under
a different expected A/U in the tested examples.

This is context binding, not authentication. The coordinator must authenticate
the caller, derive expected U from that authenticated session, select expected A
from the active auction, and compare claimed fields. If it simply accepts A/U
from an untrusted payload, including them in the hash does not establish who
sent the commitment. B2 also cannot stop replay into a coordinator that reuses
identifiers or fails to enforce one commitment and unique auction lifecycle.
The fixed tag and currency provide domain separation only when all parties use
and validate their exact agreed values.

## Trusted storage and deadlines

Binding at the hash level assumes the accepted c is fixed. M1 therefore needs an
auditable one-commit rule and a frozen list at T1. Database immutability is not a
consequence of SHA-256: an organizer who can replace or delete stored records
can change which commitment is later checked without finding a collision.

Likewise, `t<T1` and `T1<=t<T2` require a trusted clock, consistent boundary
handling, and authorization. A hash function cannot reject a late commit or an
early/late reveal. The coordinator tests observed the specified boundaries,
duplicate rejection, and preservation of the original in-memory commitment.
However, `sender_id` and event time are trusted scenario inputs, `_advance`
models only monotonic seconds within one day, and the private dictionaries are
not a tamper-resistant or independently auditable store. Because `_advance(t)`
precedes the later request checks, even a rejected request advances simulation
time; this is safe only under the stated trusted-scenario assumption and would
be an availability risk if callers controlled t.

Dương's review likewise found no separate privileged log-tampering experiment,
signed receipt, or independently anchored audit record. Ordinary API rejection
of a duplicate is therefore evidence about the coordinator path, not evidence
that a malicious organizer cannot rewrite memory or history.

## Non-reveal, fairness, and availability limits

A valid commitment does not force its owner to reveal. Under M1 a non-revealer
is excluded, allowing the highest remaining valid reveal to win, but strategic
withholding can still affect the outcome. The commitment also does not compel
payment, prevent collusion, guarantee bidder participation, or hide metadata.
The preannounced tie rule provides determinism, not economic fairness.

RUN01 E06-a observed the winner changing from U02 to U03 when U02 stayed silent.
As Dương notes, this demonstrates rule behavior and lack of forced reveal; it
does not establish why the bidder withheld, whether withholding was profitable,
or whether collusion occurred.

An organizer or network can censor commits/reveals, delay messages across a
deadline, delete records, refuse settlement, or make the service unavailable.
Local SHA-256 verification does not solve these availability and governance
problems. Production guarantees would require mechanisms outside this
educational model.

## Theoretical reasoning versus observed results

### Theoretical security reasoning

- B0 is vulnerable to enumeration when b comes from a known small domain.
- B1/B2 hiding depends on secret, unpredictable, independent r and an explicit
  assumption about SHA-256's preimage-like behavior; collision resistance alone
  is insufficient.
- Canonical injective encoding plus a collision/second-preimage assumption
  supports computational binding to the encoded fields.
- B2 binds A/U into the hashed bytes, while authentication, frozen storage,
  deadlines, and settlement remain separate trusted protocol mechanisms.

These are conditional arguments, not formal proofs of SHA-256, the Python
runtime, or the complete auction.

### Observed test results

- Independent assembly reproduced the 70-byte vector and documented digest.
- The reviewed 44-test suite passed; the component runner passed 10/10 cases.
- Specific altered b/r/A/U openings were rejected.
- B0, weak-r B1, disclosed-r B1, and disclosed-r B2 produced the documented
  recovery attempts; normal generation produced a correctly structured opening
  and public payload.
- The integrated 50-test suite passed, including six coordinator tests. E01
  selected U02 at 130000 VND; E05 observed price, duplicate, identity, deadline,
  and pending-settlement rules; E06 observed non-reveal exclusion,
  lexicographic tie-breaking, and no winner after no valid reveal.
- Chúc RUN01 recorded 37/37 independent passes (E01=4, E02=6, E03=3, E04=4,
  E05=14, E06=6), zero failures and zero errors at clean source commit
  `2a1bfe4…`. Its seven-file SHA-256 manifest matched that commit byte-for-byte,
  and the documented command reproduced 37/37 passes in this review.

The first four observations are component-level reviewer/Sơn evidence; the
50-test result is Thành Lê coordinator/integration evidence; RUN01 is Chúc's
independent evidence. The committed E01 JSON's auction/demo source hashes reflect CRLF
bytes rather than the LF-normalized commit, but rerunning the exact commit
reproduced its settlement result.

## Supported conclusions and pending dependencies

The available evidence supports the exact encoding/vector, component behavior,
the small-domain/weak-r conclusions, and functional M1 execution for the tested
E01/E02/E05/E06 cases. The accessible approved model confirms the binary
encoding, example price domain, boundaries, and tie rule. It does not support a
claim that hiding or binding has been proven, that simulated records are
immutable, or that the auction is fair and available in production. The
component, integration, independent-test, and threat-model evidence needed
for technical report preparation is now available. This does not remove the
conditional assumptions or replace final team review; the finalized PDFs also
remain unavailable for direct cross-checking.

