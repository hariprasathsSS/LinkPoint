# app/routes/v1/eval.py

from fastapi import APIRouter, HTTPException
from app.schema.eval_schema import (
    JudgeRequest,
    JudgeResponse,
    RunRequest,
    RunResponse,
    AgreementRequest,
    AgreementResponse,
)
from app.service.eval_service import EvalService

eval_router = APIRouter(prefix="/eval", tags=["eval"])


def _get_service() -> EvalService:
    return EvalService()


@eval_router.post(
    "/judge",
    response_model=JudgeResponse,
    summary="Grade a single answer",
    description=(
        "Runs tier-1 assertions first (regex, free). "
        "If assertions pass, calls the LLM judge for accuracy and completeness. "
        "Returns PASS or FAIL with a one-sentence reason."
    ),
)
def judge_one(request: JudgeRequest):
    from app.eval_cases_helper import get_ground_truth  # lazy import to avoid circular
    ground_truth = get_ground_truth(request.case_id)
    try:
        return _get_service().judge_one(
            case_id=request.case_id,
            question=request.question,
            answer=request.answer,
            mode=request.mode,
            ground_truth=ground_truth,
            judge_version=request.judge_version,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@eval_router.post(
    "/run",
    response_model=RunResponse,
    summary="Run judge on all 25 eval cases",
    description=(
        "Loops through all cases in eval/eval_cases.json. "
        "Returns pass rate broken down by taxonomy mode and flags regression cases."
    ),
)
def run_all(request: RunRequest):
    try:
        return _get_service().run_all(judge_version=request.judge_version)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@eval_router.post(
    "/agreement",
    response_model=AgreementResponse,
    summary="Measure judge vs human agreement",
    description=(
        "Compares judge verdicts against your hand labels in eval/labels_25.json. "
        "Returns the agreement percentage and the full list of disagreement cases. "
        "Call with judge_version='v1' then 'v2' to see the before/after delta."
    ),
)
def agreement(request: AgreementRequest):
    try:
        return _get_service().compute_agreement(judge_version=request.judge_version)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
