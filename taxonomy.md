# taxonomy.md — Failure Mode Taxonomy
## LinkPoint Insurance RAG · Week 5 Error Analysis
**Sample:** 20 traces · Seed: 42 · Date: 2026-09-11

---

## Failure Mode Table

| Mode | Count | Freq % | Severity | Example trace_id |
|---|---|---|---|---|
| **Answer present in corpus but system returns "I don't have that information"** | 1 | 5% | High — adjuster gets no guidance on a question the policy actually answers, may make wrong call | `945623fc` |
| **Confirms yes/no correctly but omits the critical qualifying condition** | 2 | 10% | High — adjuster acts on partial information; may approve or deny without knowing the full rule | `c6ea6f1b`, `5af77787` |
| **Retrieves wrong context and answers a different question than was asked** | 1 | 5% | High — answer is confidently wrong; adjuster could cite the wrong clause | `c9fb6519` |
| **Out-of-corpus question answered correctly with "I don't know"** | 4 | 20% | Low — system behaves correctly; no action needed | `58dd2eda`, `08`, `16`, and one more |
| **Factual lookup answered correctly from table/conditions** | 12 | 60% | None — working as intended | `a82d6b1f`, `ac24fbf7`, `ad0d92e2`, etc. |

---

## Mode Descriptions

### Mode 1 — Answer in corpus but system says it doesn't know
**Count:** 1 / 20 (5%)  
**Severity:** High — wrongly denies information to an adjuster who needs it  
**Example:** `945623fc` — Asked "Does E-17 apply if the leak was discovered after 12 days?" The answer is in the policy (12 < 14-day threshold in edition 03-24, so NO, E-17 does not apply), but the system returned "I don't have that information." The relevant chunk was not retrieved or not ranked highly enough.

---

### Mode 2 — Partial answer: correct direction, missing the key condition
**Count:** 2 / 20 (10%)  
**Severity:** High — answer is not wrong enough to be obviously wrong, so adjuster may not check further  
**Examples:**  
- `c6ea6f1b` — Said mold is covered when water loss is sudden/accidental, but did not mention that E-17 explicitly excludes mold under continuous seepage (the more common scenario).  
- `5af77787` — Said HO-2306 amends E-17, but gave no detail on the 30-day seepage limit and 60-day vacancy condition — the exact numbers an adjuster needs to make a decision.

---

### Mode 3 — Wrong-context retrieval: answers a different question
**Count:** 1 / 20 (5%)  
**Severity:** High — adjuster could cite wrong clause and expose the insurer to bad-faith risk  
**Example:** `c9fb6519` — Asked "Does the policy cover a claim if the adjuster isn't sure which form edition was in effect at loss date?" The system responded by describing HO-2306's seepage provision, which is completely unrelated to the question about edition-date uncertainty.

---

### Mode 4 — Out-of-corpus question correctly deflected
**Count:** 4 / 20 (20%)  
**Severity:** None — working correctly  
**Examples:** `58dd2eda` (bundling discount), `1a7a3677` (auto accidents), `643d69c9` (phone number)  
The system correctly returned "I don't have that information" for questions with no answer in the corpus.

---

### Mode 5 — Correct factual retrieval from tables and conditions
**Count:** 12 / 20 (60%)  
**Severity:** None — working correctly  
**Examples:** Coverage limits, duties after loss, settlement percentage, exclusion descriptions — all retrieved and answered accurately.

---

## Dated Prediction (committed to git before any fix)

**Date:** 2026-09-11  
**Target mode:** Mode 2 — Partial answer: correct direction, missing the key condition  
**Specific change:** Add a metadata field `section_type` (values: `exclusion`, `endorsement`, `conditions`, `coverage`) to each chunk at ingest time, and at prompt-build time, for any query that matches an exclusion keyword (E-17, seepage, mold), force inclusion of at least one chunk tagged `endorsement` alongside the exclusion chunks.  
**Predicted delta:** Mode 2 drops from 10% (2/20) to under 3% (0-1/20) in the next 20-trace sample, because the endorsement's qualifying conditions will always appear in the context window when an exclusion is discussed.

> See git commit for exact hash — run `git log --oneline -1` after commit.

---

## Notes
- Zero code changes were made during open-coding. All 20 traces were read from the log as-is.
- Traces 02 and 15 are duplicate questions; both gave the same correct answer, confirming retrieval stability for that query.
- The dominant pattern (60% correct factual retrieval) shows the system works well for simple lookups but degrades on nuanced conditional reasoning.
