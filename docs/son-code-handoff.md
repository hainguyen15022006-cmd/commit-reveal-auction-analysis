# Sơn code handover

## Delivered scope

- `src/commitment.py`: canonical encoding, secure randomness, B0/B1/B2 creation,
  M1 opening verification and private bidder state with a public commit payload.
- `experiments/guessing.py`: bounded B0 guessing, weak/disclosed-r B1 search and
  disclosed-r B2 search using explicit candidate domains.
- `tests/`: author component checks, including the guide's reference vector,
  malformed inputs, changed openings, search budgets and evidence output.
- `examples/commitment_demo.py`: executable normal-generation integration example.
- `experiments/run_son_checks.py`: synthetic vector, encoding, E02, E03 and E04
  component checks with expected and observed results in JSON.
- `docs/commitment-api.md`: exact byte format, input/output and responsibility boundaries.

The report has not been written or changed as part of this code delivery.

## Run from a fresh checkout

Use Python 3.10+; no third-party packages are required. From the repository root:

```sh
python -m unittest discover -s tests -v
python -m examples.commitment_demo
python -m experiments.run_son_checks --output results/son_checks.json
```

The tests must finish with exit status 0. The component runner returns 0 only
when all expected results match; a mismatch returns 1 and remains visible in
the JSON. Run with a different output filename to preserve earlier evidence.

Local validation completed on Windows with Python 3.13.2 and Python 3.12.14:
all 40 unit tests passed in both environments. The recorded component run has
10 passing checks. A second local run reproduced the same case inputs and
outputs; this is not an independent rerun by another team member.

The recorded example domain is 10,000 to 1,000,000 VND inclusive, step 10,000.
The weak-r example uses the 16 integers 0 through 15 encoded in a 128-bit-wide
hexadecimal field. The real generator is checked for format and opening
correctness only. No run attempts exhaustive search of its 128-bit space.

## Evidence and limitations

`results/son_checks.json` records inputs, target commitments, expected outputs,
actual outputs, attempt counts, UTC run time, Python/platform, Git HEAD,
working-tree status and SHA-256 hashes of source files. If HEAD names the base
documentation commit while the tree is dirty, the source manifest identifies
the executed implementation bytes; HEAD alone does not identify that code.
If Git is unavailable or refuses repository access, its metadata is `null`;
the source manifest is still recorded. The saved run includes the actual base
commit and dirty-state flag as observed before committing this delivery.

Only public synthetic opening values are stored in the fixed-fixture results.
The normal-r check does not export its generated opening. Source files and
inputs must be retained along with any result cited later in the report.
The unit-test transcript is in `results/son_unit_tests.txt`.

These are author-run checks. They do not substitute for Chúc's independently
designed E01-E06 suite, Hoàng Anh's independent rerun, a complete auction
simulation or cryptographic security arguments.

## Integration points for the team

1. Hải Anh and Thành Lê provide the approved `docs/model.md`. Compare its Encode
   and price rules against this module before official experiments. Current
   code follows the existing study guide and keeps price-policy checks outside
   the crypto layer.
2. Thành Lê imports the functions instead of duplicating the hash formula. He
   retains the accepted c, supplies expected A/U to verification and independently
   checks identity, time, price and frozen state. `public_submission()` is the
   commit-phase payload; private bidder state remains outside the coordinator.
3. Công Thành reviews the reference vector and assumptions, and approves the
   experimental domains for E03/E04. Failing to find a candidate is not a proof
   of hiding; 32 hex digits alone do not establish 128 bits of entropy.
4. Chúc tests the module independently, reports reproducible defects and reruns
   affected cases after Sơn fixes them. Full E01/E05/E06 need Thành Lê's auction
   coordinator; they are not claimed by this delivery.
5. Hoàng Anh reruns the commands and retains original outputs. Use reviewed
   results when the team later prepares the report.

The local implementation branch is `feature/commitment`. Its changes can be
submitted for review without modifying the shared `main` branch.
