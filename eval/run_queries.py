# eval/run_queries.py
#
# Fires a batch of real adjuster-style questions at the real /query endpoint
# (http://127.0.0.1:8000/query), so app/logs/query.log accumulates genuine
# traces (successes AND failures) to sample from for the Week 5 error-analysis.
#
# Prereqs: FastAPI server must be running (uvicorn app.main:app --reload)
# Run:     python eval/run_queries.py

import httpx

BASE_URL = "http://127.0.0.1:8000"
TOP_K = 3

QUESTIONS = [
    # --- exact-token / trap questions (edition confusion, decoys) ---
    "Does exclusion E-17 apply under form HO-0304 edition 03-24 if a pipe seeps for three weeks?",
    "Under the older edition of form HO-0304, how many days of seepage does exclusion E-17 require before it applies?",
    "Is water damage covered if it's a sudden pipe burst, not a slow leak?",
    "Does endorsement HO-2306 change how exclusion E-17 applies?",
    "If the dwelling was vacant for 90 days and there's a 20-day seepage loss, does endorsement HO-2306 cover it?",
    "What's the difference between the water damage exclusion in edition 03-24 versus edition 01-19?",
    "Does the sudden and accidental discharge peril cover a slow, ongoing leak under a sink?",
    "Is a claim for water damage automatically covered, or does exclusion E-17 need to be checked first?",
    "Does exclusion E-17 apply if the leak was discovered after 12 days?",
    "What form and edition governs the water damage exclusion for this policy?",

    # --- other exclusions ---
    "Does the policy cover flood damage?",
    "Is earthquake damage covered under this homeowners policy?",
    "Does exclusion E-12 cover normal wear and tear on the roof?",
    "Is damage from a nuclear incident covered?",
    "What does exclusion E-05 cover?",
    "Does the policy exclude sinkhole collapse?",

    # --- coverage limits ---
    "What is the Coverage A limit of liability?",
    "How much personal property coverage does this policy provide?",
    "What's the limit for other structures like a detached garage?",
    "If the house becomes uninhabitable, how much loss-of-use coverage is available?",
    "What is the total dwelling coverage limit?",

    # --- conditions ---
    "What are the claimant's duties after a loss?",
    "How does the appraisal process work if we disagree on the loss amount?",
    "How is a covered dwelling loss settled - replacement cost or actual cash value?",
    "What percentage of replacement cost must Coverage A be for replacement cost settlement to apply?",

    # --- ambiguous / compound / likely-to-fail ---
    "My client's basement flooded slowly over a month and the house was empty for two months - is any of this covered?",
    "Which exclusion code should I cite to deny a claim for a 15-day pipe seepage under the current form edition?",
    "Is mold damage covered if it results from a covered water loss?",
    "Does the policy cover a claim if the adjuster isn't sure which form edition was in effect at loss date?",

    # --- out-of-corpus (nothing in the policy should answer these) ---
    "Does this policy cover auto accidents?",
    "What's the claims phone number for Harborstone Mutual?",
    "Is there a discount for bundling home and auto insurance?",
]


def main() -> None:
    print(f"Firing {len(QUESTIONS)} questions at {BASE_URL}/query ...\n")

    with httpx.Client(timeout=60.0) as client:
        for i, question in enumerate(QUESTIONS, start=1):
            try:
                response = client.post(
                    f"{BASE_URL}/query",
                    json={"query": question, "top_k": TOP_K}
                )
                data = response.json()
                trace_id = data.get("trace_id", "no-trace-id")
                print(f"[{i}/{len(QUESTIONS)}] trace_id={trace_id}")
                print(f"  Q: {question[:80]}")
                print(f"  A: {data.get('answer', '')[:120]}\n")

            except Exception as e:
                print(f"[{i}/{len(QUESTIONS)}] FAILED ({type(e).__name__}: {e})")
                print(f"  Q: {question[:80]}\n")

    print(f"\nDone. {len(QUESTIONS)} questions sent. See app/logs/query.log for traces.")


if __name__ == "__main__":
    main()
