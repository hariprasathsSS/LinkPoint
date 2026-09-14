# app/eval_cases_helper.py
# Thin helper so the eval route can look up ground_truth by case_id
# without loading the full EvalService.

import json
from pathlib import Path

_EVAL_CASES_PATH = Path(__file__).resolve().parent.parent / "eval" / "eval_cases.json"
_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _cache
    if _cache is None:
        cases = json.loads(_EVAL_CASES_PATH.read_text(encoding="utf-8"))
        _cache = {c["case_id"]: c for c in cases}
    return _cache


def get_ground_truth(case_id: str) -> str:
    cases = _load()
    if case_id not in cases:
        return ""
    return cases[case_id].get("ground_truth", "")
