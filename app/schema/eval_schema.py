# app/schema/eval_schema.py

from pydantic import BaseModel
from typing import Any


class JudgeRequest(BaseModel):
    case_id: str
    question: str
    answer: str
    mode: str
    judge_version: str = "v1"


class JudgeResponse(BaseModel):
    case_id: str
    verdict: str                    # "PASS" or "FAIL"
    method: str                     # "assertion" or "llm_judge"
    reason: str
    assertion_failed: str | None = None


class RunRequest(BaseModel):
    judge_version: str = "v1"


class ModeStats(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float


class RegressionResult(BaseModel):
    case_id: str
    verdict: str
    is_regression: bool


class RunResponse(BaseModel):
    judge_version: str
    summary: ModeStats
    by_mode: dict[str, ModeStats]
    assertions_run: int
    llm_judge_calls: int
    regression_cases: list[RegressionResult]
    results: list[JudgeResponse]


class AgreementRequest(BaseModel):
    judge_version: str = "v1"


class DisagreementCase(BaseModel):
    case_id: str
    your_label: str
    judge_verdict: str
    question: str
    answer: str
    judge_reason: str


class AgreementResponse(BaseModel):
    judge_version: str
    total_cases: int
    agreements: int
    disagreements: int
    agreement_pct: float
    disagreement_cases: list[DisagreementCase]
