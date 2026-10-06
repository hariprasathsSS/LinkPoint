# Week 9 — MCP Implementation
## Insurance Claims · Task Set D · Pdf-Ingester-v1

> **Module:** M5 — MCP, Multi-agent & A2A  
> **Evaluated:** Week 10 · Monday  
> **Points:** 100

---

## Table of Contents

1. [What Was Built](#1-what-was-built)
2. [Architecture & MCP Roles](#2-architecture--mcp-roles)
3. [Directory Structure](#3-directory-structure)
4. [File-by-File Implementation](#4-file-by-file-implementation)
   - [policy_server.py — Server 1 (your own)](#41-policy_serverpy--server-1-your-own)
   - [claims_server.py — Server 2 (claims-system)](#42-claims_serverpy--server-2-claims-system)
   - [mcp_config.json — the only thing that changes](#43-mcp_configjson--the-only-thing-that-changes)
   - [mcp_agent.py — MCP-aware ReAct agent](#44-mcp_agentpy--mcp-aware-react-agent)
   - [wire_capture.py — JSON-RPC recorder](#45-wire_capturepy--json-rpc-recorder)
   - [tool_counter.py — Discovery reporter](#46-tool_counterpy--discovery-reporter)
5. [Requirement-by-Requirement Walkthrough](#5-requirement-by-requirement-walkthrough)
   - [Req 1 — Config-only server add, zero agent changes](#req-1--config-only-server-add-zero-agent-changes)
   - [Req 2 — git diff proves zero agent lines changed](#req-2--git-diff-proves-zero-agent-lines-changed)
   - [Req 3 — Tool counts before and after](#req-3--tool-counts-before-and-after)
   - [Req 4 — Raw JSON-RPC wire traffic annotated](#req-4--raw-json-rpc-wire-traffic-annotated)
   - [Req 5 — Docstring-as-prompt + recoverable error](#req-5--docstring-as-prompt--recoverable-error)
   - [Req 6 — Supply-chain risk note](#req-6--supply-chain-risk-note)
6. [How to Run Everything](#6-how-to-run-everything)
7. [Submission Checklist](#7-submission-checklist)
8. [Bonus — Gateway Process](#8-bonus--gateway-process)
9. [Common Mistakes — How We Avoided Each One](#9-common-mistakes--how-we-avoided-each-one)

---

## 1. What Was Built

The existing `react_agent.py` had **three tools hard-coded** — `get_claim`, `get_adjuster_notes`, `search_policy`. Adding a tool meant editing the agent file.

This week we replaced that with an MCP-aware setup:

| Before (Week 8) | After (Week 9) |
|-----------------|----------------|
| Tools hard-coded in `react_agent.py` | Tools discovered at runtime via `tools/list` |
| Adding a tool = code change + redeploy | Adding a server = edit one JSON config line |
| One monolithic agent file | Host (agent) + two independent MCP servers |
| Tool logic tangled in agent | Tool logic lives in self-contained servers |

The **agent module never changes** when you add server two. That is the entire point.

---

## 2. Architecture & MCP Roles

```
┌──────────────────────────────────────────────────────────┐
│  HOST  (mcp_agent.py)                                    │
│                                                          │
│  1. Reads mcp_config.json                                │
│  2. Connects to each server via stdio                    │
│  3. Runs tools/list → builds Groq tool schema            │
│  4. ← LLM CALL HAPPENS HERE (Groq API)                  │
│  5. Routes tool_calls to the right server                │
│  6. Feeds result back into message history               │
│  7. Loops until final answer                             │
└────────────┬─────────────────────┬───────────────────────┘
             │ stdio               │ stdio
             ▼                     ▼
┌────────────────────┐   ┌────────────────────────────────┐
│  SERVER 1          │   │  SERVER 2                      │
│  policy_server.py  │   │  claims_server.py              │
│                    │   │                                │
│  Tool:             │   │  Tools:                        │
│  • search_policy   │   │  • get_claim                   │
│                    │   │  • get_adjuster_notes          │
│  Wraps the RAG     │   │  Wraps claims_w8.json          │
│  retrieval pipeline│   │  with recoverable errors       │
│                    │   │                                │
│  NO LLM inside     │   │  NO LLM inside                 │
└────────────────────┘   └────────────────────────────────┘
```

**Where the model runs:** Inside the HOST process (`mcp_agent.py`), at the `client.chat.completions.create()` call.  
**Where the model does NOT run:** Inside either MCP server. Servers are data-access layers only.

---

## 3. Directory Structure

```
Pdf-Ingester-v1/
├── app/
│   ├── agent/
│   │   ├── react_agent.py        ← UNTOUCHED (Week 8 hard-coded agent)
│   │   ├── fixed_workflow.py     ← UNTOUCHED
│   │   └── tools.py              ← UNTOUCHED
│   ├── mcp/                      ← NEW: entire Week 9 module
│   │   ├── __init__.py
│   │   ├── mcp_config_v1.json    ← Config with 1 server (policy only)
│   │   ├── mcp_config.json       ← Config with 2 servers (the v2, used in prod)
│   │   ├── policy_server.py      ← Server 1: your own MCP server
│   │   ├── claims_server.py      ← Server 2: claims-system MCP server
│   │   ├── mcp_agent.py          ← MCP-aware ReAct agent (host)
│   │   ├── wire_capture.py       ← Records raw JSON-RPC exchange
│   │   └── tool_counter.py       ← Reports tool discovery counts
│   └── routes/v1/
│       └── claim.py              ← Added /claim/mcp-agent/{id} endpoint
└── week9_deliverables/
    ├── agent_diff.txt            ← Proof: 0 agent lines changed
    ├── tool_counts.md            ← 1 tool → 3 tools with names
    ├── wire.json                 ← Raw JSON-RPC + hand annotations
    ├── error_before_after.md     ← Docstring rewrite + transcript
    └── risk_note.md              ← 5-line supply-chain risk
```

---

## 4. File-by-File Implementation

### 4.1 `policy_server.py` — Server 1 (your own)

**File:** [`app/mcp/policy_server.py`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/policy_server.py)

**Purpose:** Exposes your existing RAG retrieval pipeline (`search_policy`) as an MCP-discoverable tool. Any external agent connecting to this server can call it without knowing how the RAG internals work.

**Key decisions:**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("policy-server")

@mcp.tool()
async def search_policy(query: str) -> str:
    """
    [docstring written as a prompt — tells model WHEN to call,
     what NOT to use it for, and what to do on error]
    """
    ...
    # wraps: get_query_service() → QueryRequest → retrieval_service.ask()
```

- Uses `fastmcp` for minimal boilerplate
- Transport: `stdio` (spawned as a subprocess by the host)
- Docstring is the tool description the LLM sees — written as a usage instruction, not a code comment
- Error path returns a recoverable message ("do not infer coverage from silence")

**Run standalone:**
```bash
python -m app.mcp.policy_server
```

---

### 4.2 `claims_server.py` — Server 2 (claims-system)

**File:** [`app/mcp/claims_server.py`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/claims_server.py)

**Purpose:** Exposes two tools from the claims platform. This is the server added purely via config — no agent code changes.

**Tools exposed:**

| Tool | What it does | Key safeguard |
|------|-------------|---------------|
| `get_claim` | Fetches claim facts | Format-validates claim ID before hitting data; returns valid ID list on unknown ID |
| `get_adjuster_notes` | Fetches adjuster inspection notes | Validates status enum; reports actual status on mismatch |

**Recoverable error design (the Week 9 key requirement):**

```python
# BEFORE (original tools.py):
return f"Error: Claim {claim_id} not found."
# → Model cannot self-correct. Doesn't know if it's a typo, wrong format, or dead system.

# AFTER (claims_server.py):
return (
    f"Claim '{claim_id}' was not found in the system. "
    f"Valid claim IDs currently on file: {', '.join(all_ids)}. "
    f"Please verify the claim number — a typo or wrong week prefix is the most common cause."
)
# → Model gets the valid ID list, diagnosis, and can retry or escalate correctly.
```

**Format validation guard:**
```python
_CLAIM_ID_RE = re.compile(r"^CLM-[A-Z0-9]+-\d{3,}$")

if not _CLAIM_ID_RE.match(claim_id):
    return (
        f"'{claim_id}' does not match the expected claim-ID format. "
        f"Claim IDs look like CLM-W8-001 ..."
    )
```

**Architectural rule enforced:** No LLM calls inside this server. It is a data-access layer only. The server has no idea which AI is calling it.

---

### 4.3 `mcp_config.json` — the only thing that changes

**File:** [`app/mcp/mcp_config.json`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/mcp_config.json)

This is the **only file that changes** when adding Server 2. The agent reads this at startup.

**v1 (one server):**
```json
{
  "servers": [
    { "name": "policy-server", "command": "python", "args": ["-m", "app.mcp.policy_server"] }
  ]
}
```

**v2 (two servers — the deliverable state):**
```json
{
  "servers": [
    { "name": "policy-server", "command": "python", "args": ["-m", "app.mcp.policy_server"] },
    { "name": "claims-server", "command": "python", "args": ["-m", "app.mcp.claims_server"] }
  ]
}
```

That single JSON block addition is all that "bolting on Server 2" requires. The agent discovers the new tools automatically.

---

### 4.4 `mcp_agent.py` — MCP-aware ReAct agent

**File:** [`app/mcp/mcp_agent.py`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/mcp_agent.py)

This is the HOST. It replaces the hard-coded `react_agent.py` for Week 9.

**Startup sequence (runs once per request):**

```python
servers = _load_config()           # reads mcp_config.json

for srv in servers:
    session, groq_tools = await _connect_server(stack, srv)
    # _connect_server does:
    #   1. spawn subprocess via stdio_client
    #   2. await session.initialize()    ← MCP handshake
    #   3. await session.list_tools()    ← discovery
    #   4. convert MCP schema → Groq schema
    
    for tool in groq_tools:
        tool_to_session[tool_name] = session  # routing table
```

**The ReAct loop:**

```python
while True:
    # ← LLM CALL HAPPENS HERE
    response = client.chat.completions.create(
        model=Settings.GROQ_MODEL,
        messages=messages,
        tools=all_groq_tools,   # discovered dynamically — never hard-coded
        tool_choice="auto",
    )
    
    if msg.tool_calls:
        for tc in msg.tool_calls:
            session = tool_to_session.get(tc.function.name)
            result = await session.call_tool(tc.function.name, args)
            # ↑ MCP tools/call — routed to the right server automatically
    else:
        decision = msg.content  # final answer
        break
```

**Why zero agent code changes when adding Server 2:**
- The `all_groq_tools` list is built from config, not hard-coded.
- The `tool_to_session` routing table is built at runtime from whatever was discovered.
- Adding a server to the config adds its tools to both automatically.

**Output validator (prompt-injection defense, preserved from Week 8):**
```python
if "APPROVED" in decision.upper():
    # Re-fetch claim amount directly, bypassing the AI
    # Block payout if it exceeds the original claim limit
```

---

### 4.5 `wire_capture.py` — JSON-RPC recorder

**File:** [`app/mcp/wire_capture.py`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/wire_capture.py)

Connects to the claims server and records all three MCP messages with hand-written field annotations, saved to `week9_deliverables/wire.json`.

**Run:**
```bash
python -m app.mcp.wire_capture
```

**What it captures:**

| Message | Direction | Model involved? |
|---------|-----------|-----------------|
| `initialize` | host ↔ server | **No** — protocol handshake |
| `tools/list` | host ↔ server | **No** — discovery, builds tool array for LLM |
| `tools/call` | host → server | **Yes** — LLM already ran on host, produced the call |

---

### 4.6 `tool_counter.py` — Discovery reporter

**File:** [`app/mcp/tool_counter.py`](file:///D:/HP/Pdf-Ingester-v1/app/mcp/tool_counter.py)

Connects to all servers in a given config and prints tool counts + names from `tools/list`.

**Run:**
```bash
# Before (1 server)
python -m app.mcp.tool_counter --config mcp_config_v1.json

# After (2 servers)
python -m app.mcp.tool_counter --config mcp_config.json
```

---

## 5. Requirement-by-Requirement Walkthrough

### Req 1 — Config-only server add, zero agent changes

**How it works:**
1. `mcp_agent.py` reads `mcp_config.json` at startup
2. For each server entry, it spawns the subprocess and calls `tools/list`
3. All discovered tools go into `all_groq_tools` — the LLM sees them
4. When the LLM calls a tool, `tool_to_session[fn_name]` routes it to the right server

**To prove a tool from Server 2 was called:**
- Check `trajectory` in the `AgentResponse` — it logs every tool name called
- A call to `get_claim` or `get_adjuster_notes` proves Server 2 was used
- The `system` field returns `"MCP-Agent"` to distinguish from the old hard-coded agent

**API endpoint:**
```
POST /claim/mcp-agent/{claim_id}
```

---

### Req 2 — git diff proves zero agent lines changed

See [`week9_deliverables/agent_diff.txt`](file:///D:/HP/Pdf-Ingester-v1/week9_deliverables/agent_diff.txt)

The diff of `app/mcp/mcp_agent.py` between the v1-config snapshot and the v2-config snapshot is **empty** — the file is identical. The config diff shows the one JSON block added.

To generate this yourself:
```bash
# 1. Commit with mcp_config_v1.json as mcp_config.json
git commit -m "week9: one server"

# 2. Replace with the two-server config
copy app\mcp\mcp_config.json app\mcp\mcp_config_bak.json  # already done

# 3. Show the diff
git diff app/mcp/mcp_agent.py   # empty — agent untouched
git diff app/mcp/mcp_config.json  # shows the 7 added lines
```

---

### Req 3 — Tool counts before and after

See [`week9_deliverables/tool_counts.md`](file:///D:/HP/Pdf-Ingester-v1/week9_deliverables/tool_counts.md)

```
BEFORE (mcp_config_v1.json): 1 tool
  [policy-server]  search_policy

AFTER  (mcp_config.json):    3 tools
  [policy-server]  search_policy
  [claims-server]  get_claim
  [claims-server]  get_adjuster_notes
```

Numbers come from running `tool_counter.py`, not from memory.

---

### Req 4 — Raw JSON-RPC wire traffic annotated

See [`week9_deliverables/wire.json`](file:///D:/HP/Pdf-Ingester-v1/week9_deliverables/wire.json) (generated by `wire_capture.py`)

**The three messages:**

```
initialize   → Protocol negotiation. No model. Just "hello, what version are you?".
tools/list   → Discovery. No model. Host builds the tool array it will pass to the LLM.
tools/call   → Execution. LLM already ran on HOST. Server just executes the call.
```

**Model call location (one sentence):**
> The model call happens inside `mcp_agent.py` at `client.chat.completions.create()`, after `tools/list` has returned but before `tools/call` is sent — the LLM decides to call a tool, then the host forwards that decision to the server.

**Every top-level JSON-RPC field annotated:**

| Field | Meaning |
|-------|---------|
| `jsonrpc` | Always `"2.0"` — identifies the JSON-RPC protocol version |
| `id` | Request correlation ID; response carries the same ID |
| `method` | The RPC method name (`initialize`, `tools/list`, `tools/call`) |
| `params` | Input arguments for the method |
| `result` | Successful response payload |
| `error` | Present instead of `result` if the call failed |

---

### Req 5 — Docstring-as-prompt + recoverable error

See [`week9_deliverables/error_before_after.md`](file:///D:/HP/Pdf-Ingester-v1/week9_deliverables/error_before_after.md)

**Two changes made to `get_claim` in `claims_server.py`:**

1. **Docstring rewritten as a prompt:**
   - Old: "Fetches the base details of a claim..." (a code comment)
   - New: Tells the model *when* to call, *what format* the ID must follow, *what each error path means*, and *what not to do* (don't fabricate data on system error)

2. **Error made recoverable:**
   - Old: `"Error: Claim X not found."` — model cannot distinguish typo / wrong format / dead system
   - New: Returns the list of valid IDs + a diagnosis — model can self-correct or escalate with information

**Result:** With the old error, the model gave a DENIED decision with no claim data loaded. With the new error, the model surfaces the valid IDs and asks the user to confirm — it does not fabricate a coverage decision.

---

### Req 6 — Supply-chain risk note

See [`week9_deliverables/risk_note.md`](file:///D:/HP/Pdf-Ingester-v1/week9_deliverables/risk_note.md)

5 lines covering: who wrote it, what it can reach, what it logs, what a stolen token does, ship/don't decision.

---

## 6. How to Run Everything

### Install MCP dependency
```bash
pip install mcp fastmcp
```

### Run the FastAPI app (includes new /mcp-agent endpoint)
```bash
uvicorn app.main:app --reload
```

### Test the MCP agent
```bash
# Triage a real claim
curl -X POST http://localhost:8000/claim/mcp-agent/CLM-W8-001

# Test with unknown claim (shows recoverable error)
curl -X POST http://localhost:8000/claim/mcp-agent/CLM-W8-999
```

### Generate tool count report
```bash
# Before (1 server)
python -m app.mcp.tool_counter --config mcp_config_v1.json

# After (2 servers)
python -m app.mcp.tool_counter --config mcp_config.json
```

### Capture wire.json
```bash
python -m app.mcp.wire_capture
# → saves to week9_deliverables/wire.json
```

### Show agent diff (zero lines)
```bash
git diff app/mcp/mcp_agent.py
# (empty output — proves agent unchanged)
```

---

## 7. Submission Checklist

| Item | File | Status |
|------|------|--------|
| agent_diff.txt (0 changed lines) | `week9_deliverables/agent_diff.txt` | ✅ |
| Config diff (one JSON block added) | Shown in `agent_diff.txt` | ✅ |
| wire.json — annotated | `week9_deliverables/wire.json` (run wire_capture.py) | ✅ |
| Tool count: 1 → 3, with names | `week9_deliverables/tool_counts.md` | ✅ |
| error_before_after.md | `week9_deliverables/error_before_after.md` | ✅ |
| risk_note.md (5 lines) | `week9_deliverables/risk_note.md` | ✅ |

---

## 8. Bonus — Gateway Process

> Put both servers behind one gateway process so the agent connects to one front door,
> the gateway fans out, and every tools/call is written to a single audit line.

**Design sketch** (`app/mcp/gateway.py`):

```python
# Gateway listens on a single stdio or HTTP port.
# It holds connections to both servers internally.
# On tools/list: merges tool schemas from both, returns union.
# On tools/call: inspects tool name, routes to correct server.
# On every call: writes ONE audit line → audit.log
#   format: {timestamp, caller_ip, tool_name, claim_id, status}

# Token scoping:
# Token A → can call: get_claim, search_policy  (claim status OK)
# Token B → can call: get_claim, get_adjuster_notes, search_policy  (full access)
# On tools/call with scoped Token A to get_adjuster_notes:
#   gateway returns → {"content": ["Access denied: your token does not permit get_adjuster_notes. 
#                                   You can still call get_claim to check claim status."]}
#   isError: false  ← recoverable, not a crash
```

The denial reaches the model as a recoverable tool result — model sees it, does not crash, and can fall back to `get_claim`.

---

## 9. Common Mistakes — How We Avoided Each One

| Mistake from the brief | How this implementation avoids it |
|------------------------|----------------------------------|
| Hard-coding the tool list after connecting | `all_groq_tools` is built entirely from `tools/list` response — if the config has 2 servers, 3 tools appear automatically |
| Putting an LLM call inside an MCP server | Both servers are pure data-access: `claims_server.py` reads JSON, `policy_server.py` calls the retrieval service. Zero `Groq()` calls inside either server. |
| Exposing exclusions schedule as a tool | Policy exclusions are context attached by the RAG retrieval (via `search_policy`), not a separate tool the model polls |
| Swallowing unknown claim into opaque "Error: lookup failed" | `get_claim` returns the valid ID list + format hint + diagnosis on every failure path — model can always self-correct |
| Adding the third-party server without asking what it can reach | `risk_note.md` documents exactly what the server touches, what it logs (nothing, currently), and conditions for production ship |
