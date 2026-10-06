"""Manager: classify intent -> delegate to workers (in parallel) -> synthesise.

Deliberately simple failure handling: a worker exception is NOT retried; its error text is
handed to synthesis as the worker's output. What synthesis then does with it is what the
failure_case.md experiment records (we do not pre-script the outcome).
"""
import asyncio
import json
import re

from app.agents.common import ANSWER_RULES, llm_chat
from app.agents.coverage_worker import run_coverage_worker, WorkerError
from app.agents.notes_worker import run_notes_worker
from app.agents.telemetry import start_trace

ROUTER_SYSTEM = (
    "You are the manager of AKIRA Claims squad. Classify the user message and plan delegation. "
    "Reply with JSON ONLY and NO other text. Your response must be parseable by json.loads(). "
    "Format: {\"intent\": \"claim_question\"|\"claim_search\"|\"ingest\"|\"chitchat\", "
    "\"coverage_question\": string|null, \"claim_id\": string|null}. "
    "intent=claim_question for questions needing policy/coverage checks (e.g. 'can we approve...', 'is this covered'). "
    "intent=claim_search for ONLY finding claims by customer, date, peril. "
    "If the user asks to approve a claim for a specific person, intent=claim_question. "
    "claim_id only if the user explicitly names a claim ID like CLM-XXXX, else null."
)

SYNTH_SYSTEM = (
    "You are the manager of AKIRA Claims squad. Combine the specialist outputs into one final answer to the user's question.\n"
    "If answering a policy/coverage question, follow these rules: be precise and complete, state every critical condition (day thresholds, limits, clauses), and keep conditional answers conditional.\n"
    "If the question is about a specific claim or customer search, provide the claim details clearly.\n"
    "If you have partial information (e.g., you found the claim details but the coverage specialist didn't find the policy specifics), provide the claim details you DO have and explain what coverage needs to be verified. Do NOT reject the whole answer.\n"
    "ONLY if BOTH the claim records AND the policy coverage information are completely unknown/not found, reply exactly: \"I'm sorry, but I don't have that information.\""
)


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


async def run_multi(question: str, case_id: str = "adhoc", inject_coverage_failure: bool = False) -> dict:
    with start_trace("multi", case_id) as t:
        events: list[str] = []
        try:
            msg = await llm_chat("user", "manager_router",
                                 [{"role": "system", "content": ROUTER_SYSTEM},
                                  {"role": "user", "content": question}], max_tokens=300)
            plan = _parse_json(msg.content)
            intent = plan.get("intent", "claim_question")
            events.append(f"plan={plan or 'UNPARSEABLE->default'}")

            if intent == "ingest":
                answer = "To ingest a PDF, upload it to POST /ingest."
            elif intent == "chitchat":
                answer = "I am the AKIRA Claims Assistant - ask me a claim or policy question."
            else:
                cov_q = plan.get("coverage_question") or question
                claim_id = plan.get("claim_id")
                outputs = {}
                
                if intent == "claim_search":
                    outputs["notes_worker"] = await run_notes_worker(claim_id or "", question)
                else:
                    # Sequential Workflow for claim questions
                    # 1. Run notes_worker first to get the facts (if any)
                    try:
                        notes_result = await run_notes_worker(claim_id or "", question)
                        outputs["notes_worker"] = notes_result
                    except Exception as e:
                        notes_result = f"[notes_worker returned error: {e}]"
                        outputs["notes_worker"] = notes_result
                        
                    # 2. Pass those facts to the coverage_worker so it knows what to search for
                    enriched_cov_q = (
                        f"Original Question: {cov_q}\n"
                        f"Claim Context (from notes specialist):\n{notes_result}\n\n"
                        f"Please check the policy to see if the specific peril/loss described above is covered."
                    )
                    
                    try:
                        cov_result = await run_coverage_worker(enriched_cov_q, inject_coverage_failure)
                        outputs["coverage_worker"] = cov_result
                    except Exception as e:
                        outputs["coverage_worker"] = f"[coverage_worker returned error: {e}]"

                worker_text = "\n\n".join(f"### {k}\n{v}" for k, v in outputs.items())
                smsg = await llm_chat("manager", "synthesis",
                                      [{"role": "system", "content": SYNTH_SYSTEM},
                                       {"role": "user", "content":
                                        f"Question: {question}\n\nSpecialist outputs:\n{worker_text}"}],
                                      max_tokens=1500)
                answer = smsg.content or ""
        except Exception as e:  # noqa: BLE001
            answer = f"ERROR: {e}"
            events.append(f"manager crashed: {e}")
        return {"mode": "multi", "answer": answer, "latency": t.latency, "total_tokens": t.total_tokens,
                "cost": t.cost, "hops": t.hops, "events": events}
