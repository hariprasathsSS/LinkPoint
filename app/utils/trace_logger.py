# app/utils/trace_logger.py
#
# Writes one JSON line per /query request to app/logs/query.log, with enough
# fields to replay a trace later: trace_id, prompt_version, retrieved
# chunk_ids+scores, model+params, and the answer. Claimant-identifying text
# is redacted before the line is written, not after.

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "query.log"

# This synthetic corpus's only claimant-identifying text is the named
# insured on the Declarations page; the claim-number pattern is kept ready
# for when real claim numbers exist, even though none appear in this corpus.
_NAME_PATTERN = re.compile(r"Jordan A\. Whitfield")
_CLAIM_NUMBER_PATTERN = re.compile(r"\bCLM-\d{4,}\b")


def redact(text: str) -> str:
    if not text:
        return text
    text = _NAME_PATTERN.sub("[REDACTED_NAME]", text)
    text = _CLAIM_NUMBER_PATTERN.sub("[REDACTED_CLAIM_NO]", text)
    return text


def log_trace(*, question, retrieved, model, generation_params, prompt_version, answer) -> str:
    entry = {
        "trace_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": redact(question),
        "prompt_version": prompt_version,
        "retrieved": retrieved,
        "model": model,
        "generation_params": generation_params,
        "answer": redact(answer),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["trace_id"]
