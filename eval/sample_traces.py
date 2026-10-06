# eval/sample_traces.py
#
# Draws a genuinely random, seeded sample of 20 trace_ids from the real
# trace log, for the Week 5 open-coding exercise. Prints the seed and the
# sampled ids - paste both into notes.md as proof the sample wasn't
# cherry-picked.
#
# Run: python eval/sample_traces.py

import json
from pathlib import Path
import random

LOG_PATH = Path(__file__).parent.parent / "app" / "logs" / "query.log"
SAMPLE_SEED = 42
SAMPLE_SIZE = 20


def main() -> None:
    if not LOG_PATH.exists():
        raise SystemExit(f"No trace log found at {LOG_PATH} - run eval/run_queries.py first")

    trace_ids = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                trace_ids.append(json.loads(line)["trace_id"])

    if not trace_ids:
        raise SystemExit("Trace log is empty - run eval/run_queries.py first")

    sample_size = min(SAMPLE_SIZE, len(trace_ids))
    if sample_size < SAMPLE_SIZE:
        print(f"WARNING: only {len(trace_ids)} traces available, sampling all of them "
              f"instead of {SAMPLE_SIZE}")

    rng = random.Random(SAMPLE_SEED)
    sampled = rng.sample(trace_ids, sample_size)

    print(f"seed = {SAMPLE_SEED}")
    print(f"sampled {sample_size} of {len(trace_ids)} total traces:")
    for tid in sampled:
        print(tid)


if __name__ == "__main__":
    main()
