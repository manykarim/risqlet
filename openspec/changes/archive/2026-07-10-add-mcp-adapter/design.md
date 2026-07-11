# Design: add-mcp-adapter

## Context

Core layers exist (store/lifecycle/policies/validate/exports, catalog, skills). Research decisions D1–D3 fix the adapter's shape: ≤10 consolidated tools (GitHub 40→13 evidence; AWS Labs' 100+-tool server as anti-pattern), framework-provider (no server-side inference; mcp-stride-gpt precedent), stateless per-request `project_dir` (MCP spec's stateless-first direction; state stays in `.qrisk/`).

## Goals / Non-Goals

**Goals:**
- An MCP-only client (no shell) can run the complete gated workflow: guidance → init → risks → scores → mitigations → decisions → exports, producing the identical `.qrisk/` register a CLI session would.
- Zero logic duplication: tools call the same store/validate/scoring/export/catalog/skills functions the CLI uses.
- Gates preserved: risks enter as `proposed` only; status/phase changes go through `record_decision` with the human-principal convention; `validate_register` is the backstop that catches violations.

**Non-Goals:** HTTP transport, auth, hosted deployment, MCP resources/prompts/elicitation/sampling features (uneven client support), any recommendation/ranking logic.

## Decisions

### D1. Module layout and dependency

```
src/qrisk/mcp/
├── __init__.py
├── tools.py      # nine plain functions: (args) -> dict; fully unit-testable
└── server.py     # FastMCP wiring: register tools, stdio run; ~50 lines
```

Dependency: official `mcp` SDK (FastMCP class) as optional extra `[project.optional-dependencies] mcp = ["mcp>=1.2"]`. `qrisk mcp` imports lazily and prints an actionable install hint if missing. Tool functions themselves have no `mcp` import — tests run without the extra installed.

### D2. Tool surface (9 tools)

| Tool | Args (all take `project_dir`) | Returns | Notes |
|---|---|---|---|
| `init_register` | `project_name?` | `{created}` | refuses non-empty register |
| `validate_register` | — | validate JSON report | the gate command |
| `score_risks` | `risk_id?` (default all) | `{updated, findings}` | deterministic engine only |
| `export_register` | `fmt` | `{format, content}` | three formats |
| `browse_catalog` | `action: list\|show\|search`, `pack?`, `entry_id?`, `terms?` | entries/entry/results | one tool, not three — consolidation per D1 |
| `get_guidance` | `topic: overview\|phases\|elicitation\|scoring\|risk-writing\|mitigation\|quickscan` | `{topic, content}` markdown | serves skill files as data; overview = risk-analysis SKILL.md, quickscan = quickscan SKILL.md |
| `upsert_risk` | `id?` (new if absent), `statement`, `aspects`, `elicited_by{...}`, `scores?` | `{id, path, warnings}` | writes `status: proposed` always; **rejects any attempt to set status** — description says so |
| `add_mitigation` | `risk_id`, `treatment`, `lever`, `barrier`, `concrete`, `residual_note`, `technique_ref?`, `tests?` | `{id, risk_id}` | model-validated; residual note enforced by the Mitigation model |
| `record_decision` | `type`, `risk?`, `from`, `to`, `principal`, `note`, and for status changes also updates the risk file's status field | `{recorded, validate}` | description states: only after explicit human confirmation; principal must be `human:*` (tool rejects `agent:*` up front — validate would too, this fails faster); returns a fresh validate report so violations surface immediately |

Rationale for `record_decision` updating the risk file's `status` alongside the event: an MCP-only client cannot edit files; without this the register would always fail replay consistency. The tool performs the *mechanical pair* (event + matching field update) after the client's human confirmed — same accountability model as the CLI path.

### D3. Behavior details

- Every tool resolves the register via the existing `find_register(explicit=project_dir)`; missing register → actionable error ("run init_register first") as an MCP tool error.
- `upsert_risk` allocates ids via `Store.next_risk_id()`; updates preserve YAML comments (ruamel path). Attempting `upsert_risk` on a risk whose status ≠ proposed is rejected ("reviewed+ risks change only via record_decision / human-edited files").
- All returns are JSON-serializable dicts (FastMCP structured output); no prose synthesis server-side.
- `get_guidance` reads from `qrisk.skills.skills_root()` — single source of truth with the skills; topics map to files.

### D4. Testing strategy

- Direct function tests for all nine tools: happy paths + gate behaviors (upsert rejects status field / non-proposed target; record_decision rejects `agent:` principal and illegal transitions via the returned validate report; add_mitigation without residual note fails; export byte-determinism).
- Server guard test: constructing the FastMCP server registers exactly the nine tools (skipped cleanly if the `mcp` extra is absent, but the extra is in the dev group so CI runs it).
- End-to-end tool-sequence test mirroring the e2e CLI test: guidance → init → upsert×2 → score → record decisions → export → validate passes.

## Risks / Trade-offs

- [record_decision can be called without real human consent] → same trust model as the CLI path, stated in the tool description; audit trail + validate remain the controls; hard enforcement stays a platform-hooks concern (documented).
- [Tool schemas drift from pydantic models] → tool args validated by re-using the models inside tools.py; a schema change fails tool tests.
- [Optional dependency confusion] → lazy import with explicit `pip install qrisk[mcp]` hint; core tests never import `mcp`.

## Migration Plan

Additive. No register/catalog/skills changes.

## Open Questions

- Streamable-HTTP transport if a hosted deployment is ever wanted — deferred; the stateless design makes it a wiring change.
