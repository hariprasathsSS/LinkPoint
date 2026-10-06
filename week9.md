# Week 9 · Task D — Bolt on the Claims-System MCP Server

## Background

LinkPoint is an insurance claims triage app. The agent (`react_agent.py`) currently hard-wires three tools directly via Python imports:
- `get_claim` — reads from `claims_w8.json`
- `get_adjuster_notes` — reads from `claims_w8.json`
- `search_policy` — queries Qdrant vector store

**Goal:** Migrate to MCP-based tool discovery so the agent picks up tools from servers automatically, then add a *second* server (the "claims-system" server) with **zero agent code changes** — proven by `git diff`.

---

## What We're Building

### Six Deliverables Required

| Deliverable | What it proves |
|---|---|
| `agent_diff.txt` (0 changed lines in agent module) | Config-only server swap |
| Config diff (MCP config before vs after) | Second server added by config |
| `wire.json` — annotated JSON-RPC exchange | You understand the protocol |
| Tool count: N before → M after (with names) | Discovery was real |
| `error_before_after.md` — docstring-as-prompt + recoverable error | Docstring quality & error UX |
| `risk_note.md` — 5-line supply-chain risk | Security thinking |

---

## Architecture

```
                  ┌──────────────────────────────────────────────────────┐
                  │  HOST  (LinkPoint FastAPI app)                        │
                  │                                                        │
                  │  ┌────────────────────────────────────┐               │
                  │  │  MCP CLIENT  (react_agent.py)       │               │
                  │  │  • Connects to MCP servers          │               │
                  │  │  • calls tools/list at startup      │               │
                  │  │  • dispatches tools/call at runtime │               │
                  │  │  • passes tool schemas to LLM       │               │
                  │  │  • MODEL CALL HAPPENS HERE ◄─────── │               │
                  │  └──────────┬─────────────┬───────────┘               │
                  └─────────────┼─────────────┼─────────────────────────-─┘
                                │             │
                    stdio/HTTP  │             │  stdio/HTTP
                                ▼             ▼
              ┌────────────────────┐   ┌────────────────────────┐
              │  SERVER 1          │   │  SERVER 2 (NEW)         │
              │  policy-search     │   │  claims-system          │
              │  mcp_server.py     │   │  claims_mcp_server.py   │
              │  tool: search_policy│  │  tool: get_claim_status │
              └────────────────────┘   │  tool: get_adjuster_note│
                                       └────────────────────────┘
```

**Where the model runs:** Only in the HOST (react_agent.py), never inside either MCP server.

---

## Files to Create / Modify

### New MCP Infrastructure

#### [NEW] `app/mcp/mcp_server.py` — Server 1: Policy Search
Wraps the existing `search_policy` logic as an MCP tool using `fastmcp`.

#### [NEW] `app/mcp/claims_mcp_server.py` — Server 2: Claims System
Exposes `get_claim_status` and `get_adjuster_note` as MCP tools.  
This is the server added "without touching the agent" — proven by diff.

#### [NEW] `app/mcp/mcp_config.json` — MCP server config (Server 1 only, before state)
```json
{
  "mcpServers": {
    "policy-search": {
      "command": "python",
      "args": ["-m", "app.mcp.mcp_server"]
    }
  }
}
```

#### [NEW] `app/mcp/mcp_config_v2.json` — MCP server config (Server 1 + 2, after state)
```json
{
  "mcpServers": {
    "policy-search": { ... },
    "claims-system": {
      "command": "python",
      "args": ["-m", "app.mcp.claims_mcp_server"]
    }
  }
}
```

### Agent Refactor (the locked module)

#### [MODIFY] `app/agent/react_agent.py` — Replace hard-coded tools with MCP discovery
The agent is refactored **once** to use an MCP client. After this, the config controls what tools are available. The `agent_diff.txt` will prove that adding Server 2 required zero changes to `react_agent.py`.

> [!IMPORTANT]
> The task says "without touching the agent" meaning between **server-one-only** → **server-one-plus-two**, not between the current hard-coded state. We refactor the agent once to be MCP-native, then prove that adding server 2 is config-only.

### Deliverable Documents

#### [NEW] `deliverables/agent_diff.txt` — git diff of agent module (0 lines changed)
#### [NEW] `deliverables/wire.json` — raw JSON-RPC exchange, hand-annotated
#### [NEW] `deliverables/error_before_after.md` — docstring-as-prompt + recoverable error transcript
#### [NEW] `deliverables/risk_note.md` — 5-line supply chain risk note
#### [NEW] `deliverables/tool_counts.md` — tool counts before/after with names

---

## Step-by-Step Execution Plan

### Phase 1 — Install `fastmcp`
```
pip install fastmcp mcp
```

### Phase 2 — Build Server 1: Policy Search (`app/mcp/mcp_server.py`)
- One tool: `search_policy(query: str)` — wraps the existing Qdrant query service
- Clean docstring written as a prompt: "Search the insurance policy documents. Returns the relevant policy text for coverage determinations. Query should be a natural language question about coverage, exclusions, or limits."

### Phase 3 — Build Server 2: Claims System (`app/mcp/claims_mcp_server.py`)
- Two tools:
  - `get_claim_status(claim_id: str)` — returns claim facts
  - `get_adjuster_note(claim_id: str, status: str)` — returns adjuster notes
- Rewrite docstrings as prompts per rubric requirement
- Make error path recoverable: instead of `"Error: Claim not found"` → `"Claim CLM-2024-88120 not found. Claim numbers follow the format CLM-YYYY-NNNNN (e.g. CLM-2024-00123). Please check the claim number and try again."`

### Phase 4 — Refactor Agent to use MCP Client
- Replace hard-coded `tools = [...]` and if/elif dispatch with MCP client
- Agent reads from `mcp_config.json`, calls `tools/list`, passes schemas to LLM, dispatches `tools/call`
- Git commit this as "feat: MCP-native agent" — this is the baseline

### Phase 5 — Add Server 2 (config only)
- Update `mcp_config.json` to add `claims-system` entry
- Git commit as "config: add claims-system server"
- Run `git diff HEAD~1 HEAD -- app/agent/react_agent.py` → 0 lines changed

### Phase 6 — Capture Wire Traffic (`wire.json`)
- Run a manual `initialize → tools/list → tools/call` sequence against claims-system server
- Annotate every top-level JSON-RPC field by hand

### Phase 7 — Produce All Deliverables

---

## Open Questions

> [!IMPORTANT]
> **Transport choice:** The task says "stdio or HTTP". Since both servers run locally, we'll use **stdio** transport (subprocess, simplest, no port conflicts). Is this acceptable?

> [!IMPORTANT]
> **Groq model in agent:** The existing agent uses Groq. The MCP client will still call Groq for inference. Tool schemas will be passed to Groq's `tools` parameter the same way. This means the LLM integration stays identical — only tool discovery changes.

---

## Verification Plan

### Automated
- `git diff HEAD~1 HEAD -- app/agent/react_agent.py | wc -l` → must be 0
- Run agent on `CLM-W8-001` → verify trajectory shows tools from MCP
- Run agent on `CLM-INVALID-999` → verify recoverable error message

### Manual
- Read `wire.json` annotations — every field labelled
- Count tools before/after from actual `tools/list` response
