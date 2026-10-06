# risk_note.md — Supply-Chain Risk: claims-system MCP server

1. **Who wrote it:** The claims platform team (internal, but a separate team with their own release cycle — not reviewed by this team's security process before integration).
2. **What it can reach:** All claims in `claims_w8.json` including adjuster notes for every open, under-investigation, and closed case — effectively the full adjuster note history across the portfolio.
3. **What it logs:** Unknown — the server has no visible audit trail in its current implementation; every `tools/call` to `get_adjuster_notes` succeeds silently with no caller identity recorded.
4. **What a stolen token could do:** An attacker with the server's stdio handle (or an HTTP token if this moves to remote MCP) could call `get_adjuster_notes` on every claim ID in sequence, exfiltrating the full adjuster note history — fraud flags, vacancy findings, litigation notes — without triggering any alert.
5. **Ship or don't:** **Conditional ship** — safe to run locally on stdio with no external exposure; block remote deployment until the server logs caller identity + claim ID per call and `get_adjuster_notes` requires an explicit per-claim authorization token rather than accepting any caller who can reach the socket.
