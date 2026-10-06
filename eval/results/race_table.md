# Race table - single agent vs claims squad

Cases (identical for both arms, judge_v1): case_01, case_02, case_03, case_04, case_05, case_06, case_07, case_08, case_09, case_10
Cost model: $0.0005/1K prompt tokens, $0.0015/1K completion tokens (same constants both arms). Judge tokens excluded.
p99 uses nearest-rank on 10 samples, i.e. equals the slowest case.

| Metric | Single agent | Multi-agent squad |
|---|---|---|
| Pass rate | 8/10 (80%) | 6/10 (60%) |
| p50 latency (s) | 16.17 | 35.46 |
| p99 latency (s) | 47.22 | 48.20 |
| Total tokens | 25979 | 53173 |
| Cost per claim ($) | 0.00208 | 0.00484 |

**Context re-send multiplier: 2.0x** (53173 multi tokens / 25979 single tokens). Dominant hand-off: **manager -> coverage_worker, 37% of all multi-agent tokens**.

## Per-case verdicts
| Case | Single | Multi | Multi judge reason |
|---|---|---|---|
| case_01 | PASS | PASS | The answer correctly states that E‑17 must be checked first and includes the HO‑2306 conditions for seepage under 30 days with a vacancy limit of 60 consecutive days. |
| case_02 | PASS | PASS | The answer correctly states that E‑17 applies because the leak exceeds the 14‑day threshold, and it includes the necessary threshold condition from the ground truth. |
| case_03 | FAIL | PASS | The answer correctly states that a covered dwelling loss is settled on a replacement‑cost basis when Coverage A is at least 80% of full replacement cost, and it includes the required 80% threshold. |
| case_04 | PASS | PASS | The answer correctly states that E‑17 does not apply for a 12‑day leak and includes the threshold from the ground truth, meeting both accuracy and completeness criteria. |
| case_05 | PASS | FAIL | Assertion failed: out_of_corpus_not_deflected |
| case_06 | PASS | FAIL | The answer incorrectly states a 30‑day limit for coverage, whereas the policy specifies a 14‑day threshold for continuous seepage, making the direction inaccurate. |
| case_07 | PASS | FAIL | The answer is ambiguous and does not give a definitive “no” as required by the policy; it incorrectly presents a conditional scenario that contradicts the ground truth. |
| case_08 | PASS | FAIL | Assertion failed: out_of_corpus_not_deflected |
| case_09 | PASS | PASS | The answer correctly states that HO‑2306 adds a carve‑out for seepage under 30 days in a dwelling not vacant for more than 60 consecutive days, covering all critical conditions. |
| case_10 | FAIL | PASS | The answer correctly states prompt notice, protection of the property, and cooperation, and it includes all required duties from the ground truth. |
