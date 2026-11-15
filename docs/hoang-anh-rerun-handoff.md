# Hoàng Anh — Independent Rerun Handoff (RERUN_HA01)

Status: independent reproduction of existing evidence for team review. This is
not a new experiment design and does not change M1, the tests or any result.

## 1. Scope

Rerun from a fresh clone, on a different machine from the original runs:

| Evidence reproduced | Branch @ commit | Original file | Rerun file |
|---|---|---|---|
| Chúc's independent E01–E06 suite | `test/independent-e01-e06` @ `1ebc862` | `results/independent_e01_e06_RUN01.json` | `results/independent_e01_e06_RERUN_HA01.json` |
| Thành Lê's E01 integration run | `codex/auction-m1` @ `5e05ee5` | `results/auction_e01.json` | `results/auction_e01_RERUN_HA01.json` |
| Sơn's component checks | `codex/auction-m1` @ `5e05ee5` | `results/son_checks_binary.json` | `results/son_checks_RERUN_HA01.json` |

Environment: Windows 11, Python 3.14.3, standard library only.
Run time: 2026-11-14, approximately 15:48 UTC.

## 2. Run from a fresh checkout

Commands follow the README of `codex/auction-m1` and the runner of
`test/independent-e01-e06`. Run them from the repository root.

```sh
# On test/independent-e01-e06
python -m unittest discover -s tests
python -m experiments.run_independent_tests --output results/independent_e01_e06_RERUN_HA01.json --run-id RERUN_HA01 --runner "Hoang Anh, own laptop"

# On codex/auction-m1
python -m unittest discover -s tests
python -m examples.auction_demo --output results/auction_e01_RERUN_HA01.json
python -m experiments.run_son_checks --output results/son_checks_RERUN_HA01.json
```

Outcome: 87 unit tests passed on `test/independent-e01-e06`; 50 unit tests passed on
`codex/auction-m1`; the independent runner reported 37/37 cases passed; the E01
demo reported U02 as winner at VND 130,000; the component runner reported 10/10
checks passed. No step required the original authors' machines.

`results/RERUN_HA01.sha256` lists the SHA-256 of the three rerun files as stored
in Git with LF line endings. From the repository root, check them with
`cd results && sha256sum -c RERUN_HA01.sha256` (Git Bash) before citing them.

## 3. Source consistency

SHA-256 of `src/commitment.py`, `src/auction.py`, `experiments/guessing.py` and
`docs/model.md` are identical on both branches and equal to the `source_sha256`
recorded in RUN01 and in the refreshed `results/auction_e01.json`. Between RUN01
and `5e05ee5`, `src/` is unchanged; only `examples/auction_demo.py` was modified.
The earlier E01 source-hash mismatch is resolved by commit `5e05ee5`.

## 4. Comparison with the original runs

| Case | Original | RERUN_HA01 | Same observation | Note |
|---|---|---|---|---|
| E01-a..d | pass | pass | Yes | Fixture r, so commitments match byte for byte |
| E02-a..f | pass | pass | Yes | |
| E03-a..c | pass | pass | Yes | B0 recovers 100/100 bids; VND 130,000 at attempt 13 |
| E04-a, b, d | pass | pass | Yes | 8-bit r: 16,713 attempts; disclosed r: 13 attempts |
| E04-c | pass | pass | Partly | Only the measured hash rate (409,984 vs 552,737 H/s) and the derived year estimate differ; machine-dependent |
| E05-a..n | pass | pass | Yes | |
| E06-a..f | pass | pass | Yes | E06-a: U02 silent, U03 wins at VND 120,000 |
| Thành Lê E01 | U02 / 130,000 | U02 / 130,000 | Yes | Commitments differ because the demo draws fresh r per run, as designed |
| Sơn E04 weak r | 713 attempts | 713 attempts | Yes | r restricted to 16 values |

The figures currently quoted in the shared report draft (13, 713, 16,713, 13 and
VND 120,000) match both the original logs and this rerun.

## 5. Open issues for the team

1. `main` still contains only the README. Code (`codex/auction-m1`) and tests
   (`test/independent-e01-e06`) live on separate branches. The report needs one
   official commit after they are merged.
2. Two runs share the ID RUN01: head `2a1bfe4` (09:22 UTC) and head `03d0b55`
   (09:34 UTC); the second overwrote the first. Observations are identical apart
   from timings. The report should state which one it cites (suggested: `03d0b55`).
3. E04-c rate and year estimate depend on hardware. If quoted, name the machine.

## 6. Limitations

A successful rerun shows the evidence is reproducible from the repository; it
does not add security guarantees beyond the original tests. Matching fixture
outputs confirm determinism of the tested cases only. The rerun used the same
test suite, so it cannot detect a flaw shared by the suite and the code.

## 7. Review

Reviewer for this handoff: Dương (cross-check pair Dương ↔ Hoàng Anh).
Hải Anh may cite the run ID RERUN_HA01 in section 5A of the report.
