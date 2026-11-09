# Commit–Reveal Auction Analysis

**Security Analysis of Commit–Reveal Protocols for Sealed-Bid Online Auctions**

Group project for *Introduction to Cryptography*. We study a hash-based
commit–reveal protocol through a small Python simulation, controlled experiments,
and a written security analysis.

## Project status

This repository currently contains project documentation and Git configuration.
The simulation, tests, and experimental results are **not implemented yet**.
The directory layout below is a plan; run instructions will be added when the
corresponding commands have been implemented and verified.

## Research questions

1. Under which assumptions does a commitment hide a bid before the reveal phase?
2. What prevents a bidder from opening a fixed commitment to a different bid?
3. Which fairness, availability, and organizer-trust problems remain outside
   the protection provided by the commitment?

## Scope and protocol model

The main model, **M1**, is a first-price sealed-bid auction for one item.
Each authenticated bidder may submit one commitment. Among valid reveals,
the highest bid wins and pays its own bid. The finalized M1 document will be
maintained in `docs/model.md` as the team's shared specification.

The commitment construction is:

```text
c = SHA-256(Encode(tag, A, U, currency, b, r))

tag      = "CR-AUCTION-v1"
A        = auction identifier
U        = authenticated bidder identifier
currency = "VND"
b        = integer bid amount
r        = independent 128-bit random value, secret until reveal
```

`Encode` must represent the fields unambiguously. Including `U` in the hash
does not authenticate the sender by itself. The team must use one agreed encoding
and the same price constraints throughout the simulation and report.

The protocol has five stages:

1. **Setup:** publish the auction rules, eligible bidders, and deadlines `T1 < T2`.
2. **Commit:** accept commitments while `t < T1`; do not collect bids or `r` early.
3. **Freeze:** fix the accepted commitment set at `T1`.
4. **Reveal:** accept openings while `T1 <= t < T2`; check identity, auction,
   bid validity, and commitment equality.
5. **Settle:** at or after `T2`, select the highest valid revealed bid.

Later commitments from the same bidder are rejected. Missing or invalid reveals
are excluded. Ties use the preannounced ordering of bidder identifiers; if no
valid reveal exists, there is no winner. The detailed rules must match the
team-approved M1 specification.

This is an educational simulation. Identities, time, and storage are modeled;
the project does not implement production authentication, a trusted clock,
distributed consensus, or real payments.

## Planned comparisons and experiments

| Variant | Construction | Purpose |
| --- | --- | --- |
| B0 | `H(b)` | Illustrate guessing attacks against a small bid space |
| B1 | `H(Encode(b, r))` | Examine the role of secret randomness |
| B2 | The M1 construction plus auction checks | Bind the opening to its auction and bidder context |

Planned scenarios include:

- A valid auction with three bidders.
- An altered bid or random value during reveal.
- Exhaustive guessing within a small, explicitly defined B0 bid domain.
- Missing, weak, or disclosed randomness compared with the M1 configuration.
- Duplicate commitments, wrong auction/bidder identifiers, and deadline boundaries.
- Non-reveal, ties, and auctions with no valid reveals.

The weak-randomness configurations are experimental variants, not changes to M1.
We will not attempt to exhaust a 128-bit random space or treat an unsuccessful
search as proof of security.

## Planned repository layout

```text
.
├── README.md
├── .gitignore
├── src/
│   ├── commitment.py       # Encoding, randomness, commitment creation/verification
│   └── auction.py          # Auction state and rule enforcement
├── tests/                  # Independent functional and boundary tests
├── experiments/            # Reproducible experiment configurations and runners
├── results/                # Selected raw results and report-ready summaries
├── docs/
│   ├── model.md            # Approved M1 specification
│   ├── experiment-plan.md  # Inputs, assumptions, expected behavior, limitations
│   └── references.md       # Shared source notes and bibliography
└── report/                 # Report source and figures
```

## Team responsibilities

| Member | Primary responsibility |
| --- | --- |
| **Hải Anh** | Coordination, report integration, introduction/conclusion, final submission |
| Sơn | Cryptographic functions, randomness, guessing utilities, background |
| Thành Lê | Auction workflow, code integration, protocol description and diagrams |
| Công Thành | Experiment design, B0/B1/B2 comparison, security arguments |
| Chúc | Independent tests, experiment execution, raw results and methodology |
| Dương | Threat model, interpretation of findings, limitations and discussion |
| Hoàng Anh | Result tables/figures, independent reruns, references and PDF checks |

Review pairs: Sơn ↔ Công Thành, Thành Lê ↔ Chúc, Dương ↔ Hoàng Anh.
Hoàng Anh reviews Hải Anh's writing; Hải Anh checks consistency across the report.

## Collaboration workflow

1. Agree on M1, function interfaces, and experiment inputs before implementation.
2. Work on a descriptive branch, such as `feature/commitment`, `feature/auction`,
   `test/auction-cases`, or `docs/security-analysis`.
3. Open a pull request describing the change and how it was checked.
4. Request review from the responsible reviewer before merging into `main`.
5. Report progress briefly: completed work, link, next deliverable, and blockers.

Keep one authoritative M1 document and one main report. Changes to assumptions
or rules must be reviewed before updating code, tests, and conclusions.

## Evidence and reporting rules

- Preserve raw outputs used in the report, along with inputs, Python version,
  relevant environment information, and the code commit used for the run.
- Label fixed random values as test fixtures; normal simulation runs must use
  cryptographically appropriate randomness.
- Label hypothetical examples separately from executed experiments.
- Functional tests demonstrate observed behavior for specific cases; they do
  not prove the security of the complete protocol.
- Collision resistance alone does not establish hiding. State randomness and
  hash-model assumptions explicitly.
- Commitments do not force revelation or payment, prevent all collusion, or
  independently guarantee an honest organizer and immutable records.
- Do not commit credentials, real personal data, or real secret keys. Synthetic
  opening values may be stored in clearly labeled experimental fixtures.

The report must follow the instructor's requirements, including the previously
communicated limit of fewer than five content pages and the course policy on AI
use. According to the team's current understanding, the report is the submission
artifact; retain code and evidence for reproducibility and explanation.

## Reading starting points

- [NIST FIPS 180-4: Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- [CMU: Introduction to Cryptography lecture notes](https://www.cs.cmu.edu/~goyal/15356/lecture_notes.pdf)
- [MIT 6.5610: Recitation 6, Hash functions](https://65610.csail.mit.edu/2023/rec/rec6.pdf)
- [ETH Zürich: Cryptography, commitment schemes](https://disco.ethz.ch/courses/coti/lecturenotes/chapter3.pdf)
- [Solidity 0.8.27: Blind Auction example](https://docs.soliditylang.org/en/v0.8.27/solidity-by-example.html#blind-auction)

These sources provide background, not certification of our model. Verify the
relevant sections before citing them. The Solidity example uses Keccak-256 in
a smart-contract setting; this project uses SHA-256 in a local simulation.
