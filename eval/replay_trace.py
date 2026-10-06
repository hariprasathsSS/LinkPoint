# eval/replay_trace.py
#
# Given a trace_id (or none, to pick one at random with a seed), reconstructs
# that query's answer using ONLY the fields recorded in the trace itself:
# the retrieved chunk_ids (re-fetched from Qdrant by id, NOT re-searched),
# the recorded prompt_version, and the recorded model/generation_params.
# Prints original vs. replayed answer side by side, and notes anything that
# could not be faithfully reconstructed.
#
# Run: python eval/replay_trace.py [trace_id]
#      python eval/replay_trace.py            # picks one at random (seeded)

import json
from pathlib import Path
import random
import sys

# Windows' console codepage (cp1252) can't print many Unicode characters LLM
# output commonly contains (smart quotes, narrow no-break spaces, etc.).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient

from app.config import Settings
from app.service.llm_service import LLMService
from app.service.prompt_service import PromptService

LOG_PATH = Path(__file__).parent.parent / "app" / "logs" / "query.log"
COLLECTION_NAME = "insurance_claims_eval"
REPLAY_SEED = 7  # separate, documented seed for the single-trace replay pick


def load_traces() -> list[dict]:
    if not LOG_PATH.exists():
        raise SystemExit(f"No trace log found at {LOG_PATH} - run eval/run_queries.py first")
    traces = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))
    if not traces:
        raise SystemExit("Trace log is empty - run eval/run_queries.py first")
    return traces


def fetch_chunk_texts(chunk_ids: list[str]) -> dict:
    client = QdrantClient(host="localhost", port=6333)
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )
    by_chunk_id = {p.payload.get("chunk_id"): p.payload.get("text") for p in points}
    return {cid: by_chunk_id.get(cid) for cid in chunk_ids}


def replay(trace: dict) -> str:
    chunk_ids = [r["chunk_id"] for r in trace["retrieved"] if r.get("chunk_id")]
    texts = fetch_chunk_texts(chunk_ids)

    missing = [cid for cid, text in texts.items() if text is None]
    if missing:
        print(f"NOTE: {len(missing)} retrieved chunk_id(s) no longer resolve to text in "
              f"'{COLLECTION_NAME}' (deleted/re-ingested since this trace was recorded): {missing}")

    results = [
        {"result": {"text": texts[cid]}}
        for cid in chunk_ids
        if texts.get(cid) is not None
    ]

    if trace.get("prompt_version") != PromptService.PROMPT_VERSION:
        print(f"NOTE: trace recorded prompt_version={trace.get('prompt_version')!r}, "
              f"current PromptService.PROMPT_VERSION={PromptService.PROMPT_VERSION!r} - "
              "the prompt template may have changed since this trace was recorded.")

    prompt = PromptService().build(query=trace["question"], results=results)

    if trace.get("model") != Settings.GROQ_MODEL:
        print(f"NOTE: trace recorded model={trace.get('model')!r}, current "
              f"Settings.GROQ_MODEL={Settings.GROQ_MODEL!r} - could not force the original "
              "model; replaying with whatever model is currently configured instead.")
    if trace.get("generation_params") != LLMService.GENERATION_PARAMS:
        print(f"NOTE: trace recorded generation_params={trace.get('generation_params')!r}, "
              f"current LLMService.GENERATION_PARAMS={LLMService.GENERATION_PARAMS!r}.")

    return LLMService().generate(prompt)


def main() -> None:
    traces = load_traces()

    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
        trace = next((t for t in traces if t["trace_id"] == trace_id), None)
        if trace is None:
            raise SystemExit(f"trace_id {trace_id} not found in {LOG_PATH}")
    else:
        rng = random.Random(REPLAY_SEED)
        trace = rng.choice(traces)
        print(f"Randomly picked trace_id (seed={REPLAY_SEED}): {trace['trace_id']}")

    print(f"\n=== Original trace: {trace['trace_id']} ===")
    print(f"Question: {trace['question']}")
    print(f"Original answer:\n{trace['answer']}")

    replayed_answer = replay(trace)

    print("\n=== Replayed answer ===")
    print(replayed_answer)


if __name__ == "__main__":
    main()
