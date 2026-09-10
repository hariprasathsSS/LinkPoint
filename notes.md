# notes.md — Week 5 Error Analysis

## Seeded Random Sample

**Seed:** `42`  
**Total traces in log:** 32  
**Sample size:** 20  

---

## 20 Sampled Trace IDs

| # | trace_id | Question (truncated) |
|---|---|---|
| 01 | `5738ff25-bd9f-409f-949b-3e882fea1004` | Is a claim for water damage automatically covered... |
| 02 | `fbf1732f-05c5-40ea-ab6d-ea206ab1d2cd` | Does exclusion E-17 apply under edition 03-24 if pipe seeps three weeks? |
| 03 | `a82d6b1f-2f49-437c-85b6-50f539617c9f` | How is a covered dwelling loss settled? |
| 04 | `945623fc-38b8-40b7-b47d-368bbcc7a317` | Does E-17 apply if the leak was discovered after 12 days? |
| 05 | `58dd2eda-3f37-4a12-8efe-cc1c98401a11` | Is there a discount for bundling home and auto insurance? |
| 06 | `c6ea6f1b-87d3-46f2-8bb7-da994a3262b3` | Is mold damage covered if it results from a covered water loss? |
| 07 | `5621dcbd-24ff-49bf-a6eb-4e1ce68f9747` | Vacant 90 days, 20-day seepage — does HO-2306 cover it? |
| 08 | `1a7a3677-0872-476b-943c-b061475bac0d` | Does this policy cover auto accidents? |
| 09 | `5af77787-8683-4d16-99b6-c87327670c9d` | Does endorsement HO-2306 change how E-17 applies? |
| 10 | `ac24fbf7-8823-481e-8a65-5789299f1aa5` | What are the claimant's duties after a loss? |
| 11 | `ad0d92e2-f0c8-4ba3-94a6-de2ba2fb025e` | How much personal property coverage does this policy provide? |
| 12 | `13062e6f-1dc5-432b-aebd-fbdfdfc91968` | Is water damage covered if it's a sudden pipe burst, not a slow leak? |
| 13 | `9f2bd7ee-68d8-4e01-8695-85e9eb0c95f3` | What's the limit for other structures like a detached garage? |
| 14 | `af546424-77af-459a-ac65-86b9d59e1d25` | Is damage from a nuclear incident covered? |
| 15 | `7b60126d-f4d8-4cd2-b51c-580b3520c1ee` | Does E-17 apply under edition 03-24 if pipe seeps three weeks? (duplicate) |
| 16 | `643d69c9-dc37-45a0-979c-2cdd462e2ca8` | What's the claims phone number for Harborstone Mutual? |
| 17 | `a75fcc56-71fd-4a10-ab29-d462234f0949` | What is the total dwelling coverage limit? |
| 18 | `395c5537-289b-46ae-a102-827b54152e46` | What percentage of replacement cost must Coverage A be? |
| 19 | `9a87da24-6108-45bf-b25f-d444b36a0b24` | What does exclusion E-05 cover? |
| 20 | `c9fb6519-cc15-4c7c-89c6-fa3652b4c5b4` | Does the policy cover a claim if adjuster isn't sure which edition was in effect? |

---

## Open-Coding — One Honest Observation Per Trace

**01** `5738ff25` — The system correctly said E-17 must be checked first before covering a water-damage claim, which matches the policy.

**02** `fbf1732f` — The system correctly cited the 14-day threshold from edition 03-24 and correctly concluded 21 days exceeds it.

**03** `a82d6b1f` — The system answered correctly (replacement cost at 80% threshold) and the answer matched the Conditions section verbatim.

**04** `945623fc` — The system said "I don't have that information" for a question whose answer is in the corpus: 12 days is below the 14-day threshold in edition 03-24, so E-17 does NOT apply — the system failed to retrieve or reason from the relevant chunk.

**05** `58dd2eda` — The system correctly returned "I don't have that information" for an out-of-corpus question about bundling discounts.

**06** `c6ea6f1b` — The system said mold is covered when the underlying water loss is sudden and accidental, which is correct, but it did not mention that E-17 explicitly lists mold as excluded under continuous seepage — the more common adjuster scenario.

**07** `5621dcbd` — The system correctly answered No, citing the 60-day vacancy condition from endorsement HO-2306 — reasoning and clause citation were accurate.

**08** `1a7a3677` — The system correctly said it doesn't have that information for an out-of-corpus question about auto accidents.

**09** `5af77787` — The system confirmed HO-2306 amends E-17 but gave no detail on how it changes it (the 30-day seepage limit and 60-day vacancy condition), which is the key information an adjuster actually needs.

**10** `ac24fbf7` — The system correctly listed all three claimant duties (prompt notice, protect property, cooperate) verbatim from the Conditions section.

**11** `ad0d92e2` — The system correctly answered $175,000 from the Coverage C limit table.

**12** `13062e6f` — The system correctly identified the "Sudden and Accidental Discharge" peril and said yes, water damage from a burst pipe is covered.

**13** `9f2bd7ee` — The system correctly answered $35,000 for other structures (Coverage B limit).

**14** `af546424` — The system correctly said nuclear incidents are not covered (exclusion E-20).

**15** `7b60126d` — The system gave the same correct answer as trace 02 for an identical question, confirming stable retrieval for this specific query.

**16** `643d69c9` — The system correctly returned "I don't have that information" for an out-of-corpus question about a phone number.

**17** `a75fcc56` — The system correctly answered $350,000 for the total dwelling coverage limit (Coverage A).

**18** `395c5537` — The system correctly answered 80% for the replacement cost threshold.

**19** `9a87da24` — The system correctly described E-05 as earth movement (earthquakes, landslides, mudflows, sinkhole collapse).

**20** `c9fb6519` — The system answered the question "what if the adjuster isn't sure which form edition was in effect" by citing endorsement HO-2306's seepage provision, which is the wrong context — the question is about edition-date uncertainty and the system pulled an irrelevant chunk.

---

## Replay Evidence

**Chosen trace:** `fbf1732f-05c5-40ea-ab6d-ea206ab1d2cd`  
**Reason chosen:** First trace in the sample; involves the core E-17 / edition logic.

**Original answer (stored in log):**
> Yes. In Form HO-0304 (Edition 03-24) Exclusion E-17 states that "Water Damage, Continuous Seepage — Water/steam seeping 14+ days, including resulting mold or rot" is excluded. A pipe that seeps for three weeks (21 days) exceeds the 14-day threshold, so the exclusion would apply under the base policy.

**Replay:** `POST /query` with `{"query": "Does exclusion E-17 apply under form HO-0304 edition 03-24 if a pipe seeps for three weeks?", "top_k": 3}`

**Replayed answer:**
> Yes. Under Form HO-0304, Edition 03-24, Exclusion E-17 covers "Water Damage, Continuous Seepage" when water or steam has been seeping for 14 days or more (including resulting mold or rot). A pipe that has been seeping for three weeks (21 days) exceeds the 14-day threshold, so the exclusion applies.

**Result:** Semantically identical. Core fact (14-day threshold, 21 > 14, exclusion applies) reproduced correctly. Minor wording variation expected at temperature=0.2.

**All required fields confirmed present:** trace_id ✅ · timestamp ✅ · question ✅ · prompt_version ✅ · retrieved chunk_ids+scores ✅ · model ✅ · generation_params ✅ · answer ✅

---

## PII Redaction Confirmation

Claimant identifiers are redacted **before** the trace is written, not after.  
In `app/utils/trace_logger.py`, `redact(question)` and `redact(answer)` are called inside `log_trace()` before the `entry` dict is serialised to JSON. The `redact()` function runs `_NAME_PATTERN.sub("[REDACTED_NAME]", text)` and `_CLAIM_NUMBER_PATTERN.sub("[REDACTED_CLAIM_NO]", text)` on the raw strings. The log file never contains the unredacted text.

---

## 3 Sentences: Why a Public Benchmark Would Not Have Surfaced These Modes

Public benchmarks like MMLU or RAGAS measure performance on generic or synthetic question-answer pairs drawn from diverse open-domain corpora, so they have no coverage of proprietary insurance form editions, inter-edition threshold differences (14 vs 10 days), or endorsement interaction logic specific to this corpus. The "incomplete but confident" mode (trace 09) and the "wrong-context retrieval" mode (trace 20) both require knowing the correct answer from the actual source document — a capability benchmarks cannot verify without a matching ground-truth corpus built from the same PDFs. Benchmark scores reward average correctness across many topics, which means a system that gets 95% of generic facts right but consistently fails on the one critical policy-edition distinction an adjuster needs will score well on benchmarks while producing dangerous outputs in production.
