# Dương — Threat Model, Result Review and Discussion Handoff

Status: working draft for team review, not the final report section.

Prepared from repository snapshot `03d0b55f3d3fbc6b3212b6ac777e920fbaf03223` on branch `test/independent-e01-e06`. The recorded RUN01 execution refers to code commit `2a1bfe475b9f22cad2eab078e48129544aca24d2`; the subsequent commit adds the result file. The results below are reviewed repository evidence, not a new execution or an independent reproduction by Dương. Team approval of the current M1 specification remains to be confirmed.

## 1. Scope and model baseline

The project simulates a first-price sealed-bid auction for one item. Its main construction is:

`c = SHA-256(Encode("CR-AUCTION-v1", A, U, "VND", b, r))`

Each field has a four-byte big-endian length prefix. The bid is an eight-byte unsigned integer; randomness is 16 raw bytes, represented as lowercase hexadecimal at the API boundary. The example price domain contains 100 values from VND 10,000 to VND 1,000,000, in steps of VND 10,000.

One commitment is accepted per eligible bidder before T1. Openings are accepted during T1 ≤ t < T2, subject to session, sender, price and hash checks. Invalid openings may be retried within the window; the first valid reveal is retained. Settlement at or after T2 selects the highest valid revealed bid, paid at its own value. Ties use the lexicographically smallest preassigned bidder ID. No valid reveal means no winner.

This handoff preserves that model. Suggested mitigations below are possible extensions, not implemented M1 features or proposed changes to the agreed experiment.

## 2. Threat model

### Assets and intended properties

- Bid confidentiality before reveal, conditional on secret, unpredictable randomness and the hash assumptions used in the security analysis.
- Binding of an opening to a fixed commitment and its auction/bidder context.
- Correct application of eligibility, deadlines, price rules and winner selection within the simulation.
- Integrity of the accepted commitment set used during verification and settlement.

### Adversaries and capabilities

| Actor | Capabilities considered | Boundary of the analysis |
|---|---|---|
| Public observer | Knows the construction, public context and price domain; observes commitments; hashes candidate openings offline | Does not initially know an honest bidder's secret r; disclosure of r is considered separately |
| Malicious eligible bidder | Chooses its own bid and randomness; submits duplicate commits, malformed or changed openings, wrong context or requests at boundary times; withholds reveal | Cannot be assumed to use honest randomness; functional tests supply simulated sender identities |
| Malicious organizer or privileged process operator | Could replace stored records, misstate time, censor requests or influence identity assignment | These actions challenge trust assumptions; the simulation does not establish protection against them |
| Colluding participants | May coordinate their bids or decisions to reveal | The current evidence does not measure collusion or establish incentive compatibility |

An attacker may inspect public protocol details; secrecy of the algorithm is not an assumption. Device compromise, real account authentication, network delivery, denial of service and payment enforcement are outside the implemented simulation.

### Required assumptions

1. Honest bidders generate fresh, independent and unpredictable 128-bit r values using the intended cryptographic generator, and keep b and r private until reveal. Fixed fixtures and weak-r configurations do not satisfy this production-style assumption.
2. Encoding is unambiguous and consistent across commitment creation and verification. Binding relies on SHA-256 collision resistance; hiding requires an additional suitable hash assumption, to be stated consistently with Công Thành's analysis. SHA-256 is not claimed to be a proven random oracle.
3. The verifier uses the correct accepted commitment and expected A/U context. The organizer preserves the frozen commitment set and follows the announced rules.
4. Scenario-provided sender identities represent eligible bidders correctly. Matching `sender_id` to `bidder_id` is a modeled check, not authentication of a real person.
5. Scenario-provided time is authoritative for the experiment. Monotonic integer timestamps model ordering; they do not supply a trusted network clock.

### What the implementation checks versus what it assumes

| Mechanism observed in source | What it supports | What it does not establish |
|---|---|---|
| Sender/eligibility comparisons | Rejects inconsistent identifiers in modeled requests | Real authentication, account security or resistance to multiple identities |
| Deadline checks and nondecreasing time | Enforces the modeled phase boundaries | Authentic receipt time, network fairness or resistance to a dishonest clock source |
| One commit per bidder; rejection after T1 | Prevents replacement through the normal submission API | Immutability against a privileged organizer altering process state |
| Hash and context verification | Checks an opening against stored commitment, A and U | Honesty of the stored commitment or authentication merely from including U |
| `secrets.token_hex(16)` for normal generation | Uses the intended cryptographic randomness API | Entropy of arbitrary caller-supplied r or secrecy on a compromised device |
| Receipt object and in-memory dictionaries | Records acceptance inside the simulation | Signed evidence, durable auditability or independent verification of history |

## 3. Review of the existing experimental evidence

RUN01 records 37 tests, zero failures and zero errors, covering E01–E06. It includes source hashes, a clean-working-tree flag, Python 3.14.2 and Windows platform information. These fields support traceability but are not an independent timestamp or a proof that the log cannot be edited.

| Evidence | Recorded observation | Defensible interpretation and limit |
|---|---|---|
| E01-a/d | U02 wins at VND 130,000 and pays its own bid | The recorded examples follow first-price settlement; they do not demonstrate real payment |
| E02-b/c/d | Five changed-bid samples, 128 single-bit r changes and four combined changes are rejected | Specific incorrect openings were detected; this is not a proof against all collisions |
| E03-a | B0 recovers all 100 bids in the defined domain; VND 130,000 takes 13 guesses | A known small bid domain enables dictionary search against B0 without breaking SHA-256 |
| E03-b | The tested search does not recover the M1 openings | Failure of that search is not proof of hiding or a measured security level |
| E04-b | With an 8-bit experimental r domain, B1 and the context-bound construction are recovered; the recorded match takes 16,713 attempts | Predictable randomness undermines secrecy; adding A/U does not repair weak r. This is not normal M1 randomness |
| E04-c | 5,000 generated values have no duplicates; 20,000 guesses have no hits; a rate and extrapolated search time are recorded | These are configuration checks, samples and arithmetic. Neither absence of duplicates nor zero hits proves entropy or 128-bit security |
| E04-d | Disclosed r allows recovery of VND 130,000 in 13 guesses | Secret r is essential when the price domain is small and public context is known |
| E05 | Tested duplicates, incorrect context, invalid prices and phase-boundary violations are rejected | Observed rule enforcement supports functional correctness for those cases, not real identity or time guarantees |
| E06-a | If U02 withholds reveal, the winner changes from U02 to U03 at VND 120,000 | Commitments do not force disclosure; the highest committed bid need not determine the outcome |
| E06-b/c | Ties follow lexical ID ordering; no valid reveal yields no winner | Results follow the stated rules; fairness still depends on how IDs are assigned and participants reveal |

### Non-reveal and fairness

E06-a illustrates a distinction between rule correctness and participation incentives. Excluding U02 is consistent with M1, but allows the set of valid reveals, and consequently the winner and price, to change when a bidder stays silent. The experiment does not establish why U02 remained silent, whether withholding was profitable, or whether collusion occurred. Those would require additional behavioral assumptions and experiments. The safe conclusion is that M1 has no mechanism forcing reveal, not that this test proves a profitable attack.

### Disclosed randomness

E04-d shows that a public r leaves only the small bid domain to search when A, U and the encoding are known. Disclosure before reveal compromises the intended confidentiality window. Publishing r during the authorized reveal phase is expected protocol behavior, not by itself a confidentiality failure.

### Performance figures

Do not use E04-c's estimated years as the headline security claim. A measured loop rate and extrapolation are environment- and method-dependent, not a cryptographic lower bound. Before retaining performance numbers in the report, obtain the machine/CPU details, measurement repetitions and aggregation method; do not infer these from the Windows and Python version fields alone.

## 4. Five limitations and mitigation trade-offs

| Limitation | Consequence | Possible extension and trade-off |
|---|---|---|
| 1. Identity and time are modeled inputs | Checks cannot establish real authentication, trusted receipt times or fair network delivery | Authenticated channels and auditable time services add deployment, key-management and availability dependencies |
| 2. Organizer storage is trusted | A party controlling memory or logs is not constrained by normal API checks; an unsigned receipt is insufficient independent evidence | Signed receipts plus an independently witnessed append-only record improve accountability, but add key management, publication and audit requirements; signatures alone do not prevent censorship |
| 3. Secrecy depends on r generation and handling | Weak, reused in unsafe ways, predictable or prematurely leaked randomness can undermine hiding | Cryptographic generation and protected bidder-side storage reduce exposure, but depend on endpoint security and operational discipline; format checks alone are insufficient |
| 4. Reveal, availability and payment are not enforced | Withholding can change the outcome; no valid reveal can prevent sale; the simulation cannot collect payment | Deposits, penalties or escrow may alter incentives but introduce enforcement assumptions, costs and possible penalties for honest failures; none is implemented here |
| 5. Experimental coverage and fairness analysis are limited | Passing finite cases does not prove hiding, binding, collusion resistance or strategy-proofness; lexical tie-breaking depends on assigned IDs | Formal arguments, additional adversarial tests and transparent ID assignment improve assurance at the cost of analysis and governance work; they still require explicit assumptions |

## 5. Organizer tampering and the missing trust anchor

No separate log-tampering experiment was found in the reviewed snapshot. M1 explicitly states that signed receipts and an independent audit record are absent. Therefore, resistance to a malicious organizer remains unresolved.

If a demonstration is later added, retain the original commitment record and the altered record, identify who controls each copy, and explain why an observer should trust the original. Comparing two editable files proves only that they differ. Recomputing a hash against a substituted commitment does not prove that the commitment is the one accepted before T1. A hash chain kept entirely by the same adversarial organizer likewise needs an independently anchored checkpoint to make rewriting detectable to outsiders.

Any future demonstration must distinguish an ordinary API request being rejected from privileged storage manipulation. Its outcome must be recorded before being described as experimental evidence.

## 6. Review notes for the B0/B1/B2 comparison

| Variant | Appropriate description | Claims to avoid |
|---|---|---|
| B0 | Hashes only the bid; tested small-domain recovery succeeds | “SHA-256 was broken” |
| B1 | Adds r to the encoded bid; confidentiality depends on randomness and hash assumptions; lacks explicit A/U context | “Any 128-bit-looking string guarantees hiding” |
| B2 / normal M1 | Adds explicit context and auction-layer checks; retains assumptions about secret randomness, identity, time and storage | “Context binding authenticates users” or “M1 is secure because all tests passed” |

Weak-r variants must be labeled experimental configurations. A table cell marked “supported” or “passed” should identify whether its basis is a specific test, a code observation or a conditional theoretical argument. Do not treat a functional refusal to replace a commit as the cryptographic proof of binding.

## 7. Handoff and pending team review

| Owner | Request | Status in this handoff |
|---|---|---|
| Hải Anh | Confirm that the reviewed `docs/model.md` is the team-approved M1, including retry and tie rules | Pending confirmation |
| Công Thành | Supply or review Security analysis, hash assumptions and experiment-design rationale; align the B0/B1/B2 claims | Not found as a separate analysis document in the reviewed snapshot |
| Chúc | Confirm RUN01 as the selected evidence run; provide measurement details if timing numbers are retained; supply any separate tampering evidence | RUN01 available; additional items pending |
| Hoàng Anh | Map final tables to case IDs and run/commit; provide independent rerun record | Final tables and rerun record not found in the reviewed snapshot |
| Dương | Reconcile comments, preserve five limitations, and condense the approved material into Threat model + Discussion | This working handoff prepared; final approval pending |

The report should be drafted alongside this review, then finalized after these dependencies are resolved. The allocation of about 0.55 page for Dương is an editing target, not a reason to omit assumptions or present unverified claims. This longer handoff is supporting material and should not be pasted wholesale into the under-five-page report.

## 8. Source register

All repository links are pinned to the reviewed snapshot so later branch changes do not silently change the evidence.

- [M1 specification](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/docs/model.md): construction, rules, assumptions and organizer limitations.
- [Auction implementation](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/src/auction.py): sender, time, storage, reveal and settlement behavior.
- [Commitment implementation](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/src/commitment.py): encoding, randomness generation, input validation and B0/B1/B2 construction.
- [Chúc's RUN01 evidence](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/results/independent_e01_e06_RUN01.json): recorded cases, observations and execution metadata.
- [Sơn's English Background](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/report/background_en.md): available team draft for terminology alignment; external references cited there still require direct verification before final use.
- [Protocol Description](https://github.com/hainguyen15022006-cmd/commit-reveal-auction-analysis/blob/03d0b55f3d3fbc6b3212b6ac777e920fbaf03223/report/protocol_description_en.md): team description of phases and settlement.
- Assignment document supplied by Dương: `04_Phan_cong_bo_sung_code_giu_nguyen_M1.pdf`, especially pages 4–7, for responsibilities, review requirements and report allocation.

This handoff provides scoped interpretation and review material, not a replacement for Công Thành's formal security argument or Chúc's independent testing.

...
