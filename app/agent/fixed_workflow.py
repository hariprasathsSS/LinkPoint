import time
import json
from groq import Groq
from app.config import Settings
from app.agent.tools import get_claim, get_adjuster_notes, search_policy, _load_claims
from app.schema.agent_schema import ClaimStatus, AgentResponse

client = Groq(api_key=Settings.GROQ_API_KEY)

GROQ_COST_PER_1K_IN = 0.0005
GROQ_COST_PER_1K_OUT = 0.0015

async def run_workflow(claim_id: str) -> AgentResponse:
    start_time = time.time()
    total_tokens = 0
    total_cost = 0.0
    
    # Step 1: Get Claim
    claim_info = get_claim(claim_id)
    
    # Extract status manually to call notes (since workflow is dumb, it just looks it up)
    try:
        claims = _load_claims()
        status_str = claims[claim_id]["status"]
        status = ClaimStatus[status_str]
    except:
        status = ClaimStatus.OPEN
        
    # Step 2: Get Notes
    notes_info = get_adjuster_notes(claim_id, status)
    
    # Step 3: Search Policy (Fixed query combining both)
    # The workflow doesn't know how to query perfectly, so it just lumps it together
    query = f"Are these conditions covered? {claim_info} {notes_info}"
    policy_info = await search_policy(query)
    
    # Step 4: Final LLM evaluation
    prompt = f"""
    You are a strict insurance claims triage agent. Review the following information and calculate the payout.
    Return your final decision starting with 'APPROVED' or 'DENIED', followed by the math (Claim Amount - Excess).
    
    [CLAIM]
    {claim_info}
    
    [ADJUSTER NOTES]
    {notes_info}
    
    [POLICY RULES]
    {policy_info}
    """
    
    response = client.chat.completions.create(
        model=Settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    
    usage = response.usage
    if usage:
        total_tokens = usage.total_tokens
        total_cost = (usage.prompt_tokens / 1000) * GROQ_COST_PER_1K_IN + (usage.completion_tokens / 1000) * GROQ_COST_PER_1K_OUT
        
    decision = response.choices[0].message.content
    latency = time.time() - start_time
    
    return AgentResponse(
        system="Workflow",
        claim_id=claim_id,
        decision=decision,
        latency_seconds=latency,
        total_tokens=total_tokens,
        total_cost=total_cost,
        budget_termination=None
    )
