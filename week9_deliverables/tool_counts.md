# Tool Count: Before → After
# Source: tools/list responses, not from notes

## BEFORE — mcp_config_v1.json (policy-server only)

Total tools discovered: **1**

| # | Server         | Tool Name       | Description (first 80 chars)                              |
|---|---------------|-----------------|----------------------------------------------------------|
| 1 | policy-server | `search_policy` | Search the insurance policy documents for coverage rules |

Command to reproduce:
    python -m app.mcp.tool_counter --config mcp_config_v1.json

---

## AFTER — mcp_config.json (policy-server + claims-server)

Total tools discovered: **3**

| # | Server          | Tool Name              | Description (first 80 chars)                              |
|---|----------------|------------------------|----------------------------------------------------------|
| 1 | policy-server   | `search_policy`        | Search the insurance policy documents for coverage rules |
| 2 | claims-server   | `get_claim`            | Fetch the base facts of a claim: status, claim amount... |
| 3 | claims-server   | `get_adjuster_notes`   | Fetch the field adjuster's inspection notes for a claim  |

Command to reproduce:
    python -m app.mcp.tool_counter --config mcp_config.json

---

**Summary line:** `1 tool before → 3 tools after`
New tools added by config change only: `get_claim`, `get_adjuster_notes`
Agent code (mcp_agent.py) lines changed: **0**
