"""Race: single agent vs manager+workers on the SAME 10 Week-6 cases (case_01..case_10), SAME judge.

Prereq: uvicorn app.main:app --reload   (Qdrant up, .env filled)
Usage:  python eval/run_multi_race.py [--fail-case case_07]

Writes to eval/results/: race_results.json, race_table.md, handoffs.log, failure_case.md (facts section).
verdict.md is written by a human from these numbers.
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.service.eval_service import EvalService  # noqa: E402  (same judge_v1 as Week 6)

BASE = os.getenv("RACE_BASE_URL", "http://127.0.0.1:8003")
CASES_PATH = ROOT / "eval" / "eval_cases.json"
OUT = ROOT / "eval" / "results"
N_CASES = 10  # case_01..case_10, fixed


def pct(values, p):
    """Nearest-rank percentile (with n=10, p99 == max)."""
    s = sorted(values)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def call(client, question, mode, case_id, fail=False):
    try:
        r = client.post(f"{BASE}/chat", json={"message": question, "mode": mode,
                                              "case_id": case_id, "inject_coverage_failure": fail})
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        return {"answer": f"ERROR: {e}", "latency": 0.0, "total_tokens": 0, "cost": 0.0, "hops": [], "events": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail-case", default="case_07")
    args = ap.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))[:N_CASES]
    judge = EvalService()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {"single": [], "multi": []}

    with httpx.Client(timeout=300.0) as client:
        for c in cases:
            for mode in ("single", "multi"):
                print(f"{c['case_id']} [{mode}] ...", flush=True)
                res = call(client, c["question"], mode, c["case_id"])
                j = judge.judge_one(c["case_id"], c["question"], res["answer"], c["mode"],
                                    c.get("ground_truth", ""), "v1")
                rows[mode].append({"case_id": c["case_id"], "question": c["question"], **res,
                                   "verdict": j.verdict, "judge_reason": j.reason})

        # ---- failure injection (separate run, NOT counted in the 10-case numbers) ----
        fc = next(c for c in cases if c["case_id"] == args.fail_case)
        print(f"FAILURE RUN {fc['case_id']} ...", flush=True)
        fres = call(client, fc["question"], "multi", fc["case_id"], fail=True)
        fj = judge.judge_one(fc["case_id"], fc["question"], fres["answer"], fc["mode"],
                             fc.get("ground_truth", ""), "v1")

    (OUT / "race_results.json").write_text(json.dumps({"rows": rows, "failure": fres}, indent=2), encoding="utf-8")

    # ---- race_table.md ----
    def stats(mode):
        r = rows[mode]
        lat = [x["latency"] for x in r]
        tok = sum(x["total_tokens"] for x in r)
        cost = sum(x["cost"] for x in r)
        passed = sum(1 for x in r if x["verdict"] == "PASS")
        return dict(passed=passed, p50=pct(lat, 50), p99=pct(lat, 99), tokens=tok, cpc=cost / len(r))

    s, m = stats("single"), stats("multi")
    ids = ", ".join(c["case_id"] for c in cases)
    mult = m["tokens"] / s["tokens"] if s["tokens"] else float("nan")

    # dominant hand-off in the multi arm
    by_edge = defaultdict(int)
    for x in rows["multi"]:
        for h in x["hops"]:
            by_edge[f"{h['from']} -> {h['to']}"] += h["total_tokens"]
    top_edge, top_tok = max(by_edge.items(), key=lambda kv: kv[1]) if by_edge else ("n/a", 0)
    top_share = top_tok / m["tokens"] * 100 if m["tokens"] else 0

    table = f"""# Race table - single agent vs claims squad

Cases (identical for both arms, judge_v1): {ids}
Cost model: ${0.0005}/1K prompt tokens, ${0.0015}/1K completion tokens (same constants both arms). Judge tokens excluded.
p99 uses nearest-rank on 10 samples, i.e. equals the slowest case.

| Metric | Single agent | Multi-agent squad |
|---|---|---|
| Pass rate | {s['passed']}/{N_CASES} ({s['passed']*10}%) | {m['passed']}/{N_CASES} ({m['passed']*10}%) |
| p50 latency (s) | {s['p50']:.2f} | {m['p50']:.2f} |
| p99 latency (s) | {s['p99']:.2f} | {m['p99']:.2f} |
| Total tokens | {s['tokens']} | {m['tokens']} |
| Cost per claim ($) | {s['cpc']:.5f} | {m['cpc']:.5f} |

**Context re-send multiplier: {mult:.1f}x** ({m['tokens']} multi tokens / {s['tokens']} single tokens). Dominant hand-off: **{top_edge}, {top_share:.0f}% of all multi-agent tokens**.

## Per-case verdicts
| Case | Single | Multi | Multi judge reason |
|---|---|---|---|
""" + "\n".join(
        f"| {a['case_id']} | {a['verdict']} | {b['verdict']} | {b['judge_reason'].replace('|', '/')} |"
        for a, b in zip(rows["single"], rows["multi"]))
    (OUT / "race_table.md").write_text(table + "\n", encoding="utf-8")

    # ---- handoffs.log ----
    lines = ["# one line per hand-off (= one LLM call). prompt_tokens is the context re-sent on that hop.",
             "arm | case | seq | from -> to | prompt | completion | total"]
    for mode in ("single", "multi"):
        for x in rows[mode]:
            for h in x["hops"]:
                lines.append(f"{mode} | {h['case_id']} | {h['seq']} | {h['from']} -> {h['to']} | "
                             f"{h['prompt_tokens']} | {h['completion_tokens']} | {h['total_tokens']}")
    lines += ["", "# multi-agent tokens by hand-off (all 10 cases)"]
    for k, v in sorted(by_edge.items(), key=lambda kv: -kv[1]):
        lines.append(f"{k}: {v} tokens ({v / m['tokens'] * 100:.0f}%)" if m["tokens"] else k)
    lines += ["", f"MULTIPLIER: {mult:.1f}x = {m['tokens']} / {s['tokens']} tokens; "
                  f"dominant hand-off: {top_edge}, {top_share:.0f}% of all tokens"]
    (OUT / "handoffs.log").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- failure_case.md (facts; classification confirmed by a human reading the answer) ----
    ans = fres["answer"]
    low = ans.lower()
    acknowledged = any(w in low for w in ["unable", "could not", "couldn't", "cannot", "error", "unavailable",
                                          "not verified", "unverified", "don't have", "failed"])
    guess = "degraded to a partial answer" if acknowledged else "LIED (answered without the exclusions check)"
    fail_md = f"""# Failure case - coverage worker returns 500 on {fc['case_id']}

**Question:** {fc['question']}
**Ground truth:** {fc.get('ground_truth', '')}

**Injected fault:** coverage_worker raised `500 Internal Server Error` before any policy search.
**Retries performed:** none (manager has no retry logic).

**Manager events:**
{chr(10).join('- ' + e for e in fres.get('events', []))}

**Final answer shipped to the user:**
> {ans}

**Judge (v1):** {fj.verdict} - {fj.reason}

**What the orchestrator actually did (auto-heuristic, confirm by reading the answer above): {guess}**
"""
    (OUT / "failure_case.md").write_text(fail_md, encoding="utf-8")
    print(table)
    print(f"\nOutputs in {OUT}")


if __name__ == "__main__":
    main()
