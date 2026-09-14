# app/service/eval_service.py
#
# Orchestrates the two-tier eval system:
#   Tier 1 — deterministic assertions (regex, no LLM cost)
#   Tier 2 — LLM judge for nuanced accuracy + completeness checks
#
# Reads eval_cases.json and labels_25.json from the eval/ directory.

import json
import re
from collections import defaultdict
from pathlib import Path

from app.service.llm_service import LLMService
from app.schema.eval_schema import (
    JudgeResponse,
    ModeStats,
    RegressionResult,
    RunResponse,
    DisagreementCase,
    AgreementResponse,
)

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
EVAL_CASES_PATH = EVAL_DIR / "eval_cases.json"
LABELS_PATH = EVAL_DIR / "labels_25.json"
JUDGE_V1_PATH = EVAL_DIR / "judge_v1.txt"
JUDGE_V2_PATH = EVAL_DIR / "judge_v2.txt"

# ---------------------------------------------------------------------------
# Tier 1 — Deterministic assertions
# ---------------------------------------------------------------------------

DENIAL_KEYWORDS = ["not covered", "does not cover", "excluded", "exclusion applies",
                   "no.", "no,", "cannot be covered", "will not cover"]


def _looks_like_denial(answer: str) -> bool:
    low = answer.lower()
    return any(kw in low for kw in DENIAL_KEYWORDS)


def _is_out_of_corpus_mode(mode: str) -> bool:
    return mode == "mode_4_correct"


def run_assertions(answer: str, mode: str) -> tuple[bool, str | None]:
    """
    Returns (passed: bool, failed_assertion_name: str | None).
    If passed is True the case moves to the LLM judge.
    If passed is False the case is immediately FAIL.
    """

    # Assertion 1 — denial must cite an exclusion code (E-XX)
    if _looks_like_denial(answer):
        if not re.search(r"E-\d{2}", answer):
            return False, "denial_missing_exclusion_id"

    # Assertion 2 — out-of-corpus questions must deflect correctly
    if _is_out_of_corpus_mode(mode):
        low = answer.lower()
        deflects = any(p in low for p in ["don't have", "do not have", "not have that", "no information"])
        if not deflects:
            return False, "out_of_corpus_not_deflected"

    return True, None


# ---------------------------------------------------------------------------
# Tier 2 — LLM judge
# ---------------------------------------------------------------------------

def _load_judge_prompt(version: str) -> str:
    path = JUDGE_V1_PATH if version == "v1" else JUDGE_V2_PATH
    if not path.exists():
        raise FileNotFoundError(f"Judge prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _build_judge_call(system_prompt: str, question: str, answer: str, ground_truth: str) -> str:
    return f"""{system_prompt}

---

GROUND TRUTH (from the policy documents):
{ground_truth}

QUESTION ASKED:
{question}

ANSWER GIVEN:
{answer}

---

Your verdict:"""


def _parse_verdict(raw: str) -> tuple[str, str]:
    """Extract PASS/FAIL and reason from raw LLM output."""
    raw = raw.strip()
    upper = raw.upper()
    if upper.startswith("PASS"):
        verdict = "PASS"
    elif upper.startswith("FAIL"):
        verdict = "FAIL"
    else:
        # Fallback: scan for the word
        verdict = "PASS" if "PASS" in upper else "FAIL"

    # Reason is everything after the first em-dash or regular dash
    for sep in [" — ", " - ", "—", "-"]:
        if sep in raw:
            reason = raw.split(sep, 1)[1].strip()
            return verdict, reason
    return verdict, raw


# ---------------------------------------------------------------------------
# Public service methods
# ---------------------------------------------------------------------------

class EvalService:

    def __init__(self):
        self.llm = LLMService()

    def judge_one(self, case_id: str, question: str, answer: str,
                  mode: str, ground_truth: str, judge_version: str) -> JudgeResponse:
        """Grade a single case through assertions then LLM judge."""

        # Empty answers (cases 21-25 not yet live-queried) are auto-FAIL
        if not answer or not answer.strip():
            return JudgeResponse(
                case_id=case_id,
                verdict="FAIL",
                method="assertion",
                reason="Answer is empty — case has not been queried against the live app yet.",
                assertion_failed="empty_answer",
            )

        # Tier 1 — assertions
        passed_assertions, failed_name = run_assertions(answer, mode)
        if not passed_assertions:
            return JudgeResponse(
                case_id=case_id,
                verdict="FAIL",
                method="assertion",
                reason=f"Assertion failed: {failed_name}",
                assertion_failed=failed_name,
            )

        # Tier 2 — LLM judge (skip for deflection-only modes that already passed assertions)
        if _is_out_of_corpus_mode(mode):
            return JudgeResponse(
                case_id=case_id,
                verdict="PASS",
                method="assertion",
                reason="Out-of-corpus question correctly deflected — assertion sufficient.",
                assertion_failed=None,
            )

        system_prompt = _load_judge_prompt(judge_version)
        full_prompt = _build_judge_call(system_prompt, question, answer, ground_truth)
        raw = self.llm.generate(full_prompt)
        verdict, reason = _parse_verdict(raw)

        return JudgeResponse(
            case_id=case_id,
            verdict=verdict,
            method="llm_judge",
            reason=reason,
            assertion_failed=None,
        )

    def run_all(self, judge_version: str) -> RunResponse:
        """Run the judge on all cases in eval_cases.json."""
        cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))

        results: list[JudgeResponse] = []
        assertions_run = 0
        llm_calls = 0
        mode_buckets: dict[str, list[JudgeResponse]] = defaultdict(list)
        regression_results: list[RegressionResult] = []

        for c in cases:
            resp = self.judge_one(
                case_id=c["case_id"],
                question=c["question"],
                answer=c.get("answer", ""),
                mode=c["mode"],
                ground_truth=c.get("ground_truth", ""),
                judge_version=judge_version,
            )
            results.append(resp)
            mode_buckets[c["mode"]].append(resp)

            if resp.method == "assertion":
                assertions_run += 1
            else:
                llm_calls += 1

            if c.get("is_regression"):
                regression_results.append(
                    RegressionResult(case_id=c["case_id"],
                                     verdict=resp.verdict,
                                     is_regression=True)
                )

        # Build per-mode stats
        by_mode: dict[str, ModeStats] = {}
        total_passed = 0
        for mode, mode_results in mode_buckets.items():
            passed = sum(1 for r in mode_results if r.verdict == "PASS")
            total = len(mode_results)
            total_passed += passed
            by_mode[mode] = ModeStats(
                total=total,
                passed=passed,
                failed=total - passed,
                pass_rate=round(passed / total * 100, 1) if total else 0.0,
            )

        total = len(results)
        summary = ModeStats(
            total=total,
            passed=total_passed,
            failed=total - total_passed,
            pass_rate=round(total_passed / total * 100, 1) if total else 0.0,
        )

        return RunResponse(
            judge_version=judge_version,
            summary=summary,
            by_mode=by_mode,
            assertions_run=assertions_run,
            llm_judge_calls=llm_calls,
            regression_cases=regression_results,
            results=results,
        )

    def compute_agreement(self, judge_version: str) -> AgreementResponse:
        """Compare judge verdicts against hand labels in labels_25.json."""
        if not LABELS_PATH.exists():
            raise FileNotFoundError(
                "labels_25.json not found. Write your hand labels first and commit the file."
            )

        labels: list[dict] = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        label_map = {entry["case_id"]: entry for entry in labels}

        # Run the judge to get verdicts
        run_result = self.run_all(judge_version)
        verdict_map = {r.case_id: r for r in run_result.results}

        cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))

        agreements = 0
        disagreements = 0
        disagreement_cases: list[DisagreementCase] = []

        for c in cases:
            cid = c["case_id"]
            if cid not in label_map or cid not in verdict_map:
                continue

            your_label = label_map[cid]["label"].upper()
            judge_verdict = verdict_map[cid].verdict.upper()

            if your_label == judge_verdict:
                agreements += 1
            else:
                disagreements += 1
                disagreement_cases.append(DisagreementCase(
                    case_id=cid,
                    your_label=your_label,
                    judge_verdict=judge_verdict,
                    question=c["question"],
                    answer=c.get("answer", ""),
                    judge_reason=verdict_map[cid].reason,
                ))

        total = agreements + disagreements
        return AgreementResponse(
            judge_version=judge_version,
            total_cases=total,
            agreements=agreements,
            disagreements=disagreements,
            agreement_pct=round(agreements / total * 100, 1) if total else 0.0,
            disagreement_cases=disagreement_cases,
        )
