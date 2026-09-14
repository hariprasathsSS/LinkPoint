import json
import time
from groq import Groq
from app.config import Settings
from app.agent.tools import get_claim, get_adjuster_notes, search_policy
from app.schema.agent_schema import ClaimStatus, AgentResponse

# Initialize Groq client directly for full control over the agent loop
client = Groq(api_key=Settings.GROQ_API_KEY)

# Budgets
MAX_ITERS = 7
MAX_TOKENS = 4000
MAX_COST = 0.50 # $0.50 max
WALL_CLOCK_TIMEOUT = 45 # seconds

GROQ_COST_PER_1K_IN = 0.0005 # rough estimate for llama3
GROQ_COST_PER_1K_OUT = 0.0015

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_claim",
            "description": "Fetches the base details of a claim, including the initial description, claim amount, and excess. Use this first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The claim ID"}
                },
                "required": ["claim_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_adjuster_notes",
            "description": "Fetches the field adjuster's inspection notes for a claim to find hidden details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The claim ID"},
                    "status": {"type": "string", "enum": ["OPEN", "UNDER_INVESTIGATION", "CLOSED"], "description": "The current status of the claim"}
                },
                "required": ["claim_id", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Searches the insurance policy documents to determine if a specific peril or condition is covered.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The question to ask the policy documents"}
                },
                "required": ["query"]
            }
        }
    }
]

async def run_agent(claim_id: str) -> AgentResponse:
    start_time = time.time()
    
    messages = [
        {"role": "system", "content": "You are a senior insurance claims triage agent. Your job is to determine if a claim should be approved or denied, and calculate the final payout (Claim Amount - Excess). You MUST use tools to gather information. Never guess. Once you have all info, return your final decision starting with 'APPROVED' or 'DENIED', followed by the math."},
        {"role": "user", "content": f"Please triage claim {claim_id}"}
    ]
    
    iters = 0
    total_tokens = 0
    total_cost = 0.0
    termination_reason = None
    
    while True:
        # Budget Checks
        if iters >= MAX_ITERS:
            termination_reason = "MAX_ITERS_REACHED"
            break
        if time.time() - start_time > WALL_CLOCK_TIMEOUT:
            termination_reason = "WALL_CLOCK_TIMEOUT"
            break
        if total_tokens > MAX_TOKENS:
            termination_reason = "MAX_TOKENS_REACHED"
            break
        if total_cost > MAX_COST:
            termination_reason = "MAX_COST_REACHED"
            break
            
        iters += 1
        
        response = client.chat.completions.create(
            model=Settings.GROQ_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=500
        )
        
        msg = response.choices[0].message
        usage = response.usage
        
        # Track Tokens & Cost
        if usage:
            total_tokens += usage.total_tokens
            cost = (usage.prompt_tokens / 1000) * GROQ_COST_PER_1K_IN + (usage.completion_tokens / 1000) * GROQ_COST_PER_1K_OUT
            total_cost += cost

        # If model wants to call a tool
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if fn_name == "get_claim":
                    result = get_claim(args["claim_id"])
                elif fn_name == "get_adjuster_notes":
                    # Pass the enum value
                    status = ClaimStatus[args["status"]] if args["status"] in [e.name for e in ClaimStatus] else ClaimStatus.OPEN
                    result = get_adjuster_notes(args["claim_id"], status)
                elif fn_name == "search_policy":
                    result = await search_policy(args["query"])
                else:
                    result = "Unknown tool"
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": result
                })
        else:
            # Final Answer reached
            decision = msg.content
            break
            
    if termination_reason:
        decision = f"ERROR: Agent terminated early due to {termination_reason}."

    latency = time.time() - start_time
    
    return AgentResponse(
        system="Agent",
        claim_id=claim_id,
        decision=decision,
        latency_seconds=latency,
        total_tokens=total_tokens,
        total_cost=total_cost,
        budget_termination=termination_reason
    )
