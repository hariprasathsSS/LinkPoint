# eval/run_eval.py
#
# One-command eval runner. Calls POST /eval/run on the running FastAPI server
# and prints the pass-rate table to the terminal.
#
# Prerequisites:
#   uvicorn app.main:app --reload   (in a separate terminal)
#
# Usage:
#   python eval/run_eval.py              (judge v1, default)
#   python eval/run_eval.py --v2         (judge v2, after prompt iteration)

import sys
import httpx

BASE_URL = "http://127.0.0.1:8000"
VERSION = "v2" if "--v2" in sys.argv else "v1"

def main():
    print(f"\nRunning eval with judge {VERSION} ...\n")

    try:
        r = httpx.post(
            f"{BASE_URL}/eval/run",
            json={"judge_version": VERSION},
            timeout=120.0,
        )
        r.raise_for_status()
    except httpx.ConnectError:
        print("ERROR: Cannot reach the FastAPI server.")
        print("Start it first:  uvicorn app.main:app --reload")
        sys.exit(1)

    data = r.json()

    # --- Pass rate table by mode ---
    print(f"{'Mode':<22} {'Cases':>6} {'Pass':>6} {'Fail':>6} {'Pass%':>7}")
    print("-" * 52)
    for mode, stats in sorted(data["by_mode"].items()):
        print(
            f"{mode:<22} {stats['total']:>6} {stats['passed']:>6} "
            f"{stats['failed']:>6} {stats['pass_rate']:>6.1f}%"
        )
    print("-" * 52)
    s = data["summary"]
    print(f"{'TOTAL':<22} {s['total']:>6} {s['passed']:>6} {s['failed']:>6} {s['pass_rate']:>6.1f}%")
    print(f"\nAssertions run: {data['assertions_run']}  |  LLM judge calls: {data['llm_judge_calls']}")

    # --- Regression cases ---
    regressions = data.get("regression_cases", [])
    if regressions:
        print("\nRegression cases:")
        for reg in regressions:
            icon = "PASS" if reg["verdict"] == "PASS" else "FAIL"
            print(f"  [{icon}] {reg['case_id']}")

    print()

if __name__ == "__main__":
    main()
