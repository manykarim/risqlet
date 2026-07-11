# Design: add-register-defaults-and-resume

## Context

Post-roadmap-v1 state: register/CLI/catalog/skills/MCP shipped; dogfooding proved single-shot runs work. F4 (catalogs off by default) and F5 (resume untested, no status view) block multi-session reality. Both fixes are additive; the status command must be strictly read-only and deterministic to stay inside the framework-provider boundary.

## Goals / Non-Goals

**Goals:** out-of-the-box catalog validation; a single command answering "where is this session and what blocks the next gate?"; skills teach status-first resume; the resume path proven by a headless run.

**Non-Goals:** ensemble/dedupe (queue 2), trace ingestion (queue 3), schema changes, MCP tool additions (status data is derivable via validate/export for MCP clients; a status tool can join a later change if dogfooding shows need).

## Decisions

### D1. Default catalogs in `_STARTER_CONFIG`

`catalogs: [iso25010, techniques, heuristics, guidewords]` with a comment explaining they power soft reference checks and how to disable. Fresh `init` + `validate` must pass (packs are packaged, so loading always succeeds). Existing registers: untouched (no migration — config is user-owned).

### D2. `qrisk status` — read-only projection, `src/qrisk/status.py`

Builds a `StatusReport` dict from store + policies (reusing `validate`'s loading but never failing hard — schema-invalid files are counted and named, not fatal, since status must work on messy mid-session registers):

```
project, phase, catalogs
aspects: [{rank, id}]                      # ranked selection
risks: {proposed: n, reviewed: n, ...}     # counts by status
scoring: {scored: n, unscored: n}          # risks with >=1 derived vs. none (non-terminal only)
mitigation: {covered: n, uncovered: [ids]} # accepted+mitigating risks with >=1 mitigation
top_risks: [{id, priority, status, statement<=80ch}]   # ranked, capped by config
pending: [hints]                           # deterministic rules, see below
last_event: {ts, type, principal} | null
invalid_files: [names]                     # unparseable register files
```

Hint rules (pure functions of the counts — no prose generation): phase=aspects & no aspects selected; phase>=elicit & 0 risks; reviewed>0 & unscored among them ("N reviewed risks await scoring"); accepted/mitigating risks without mitigations; phase=emit & no strategy.md; any invalid_files; speculative count reminder. Text output: compact human table; `--json` the raw dict. Exit code always 0 unless the register itself is missing (status is a view, not a gate — `validate` remains the gate).

### D3. Skills: resume protocol

SKILL.md "Setup" becomes: `qrisk status --json 2>/dev/null || qrisk init` — if a register exists, read status and resume at its phase, honoring `pending` hints; phases.md gets a short "Resuming a session" section (status first; re-read the phase's entry criteria; never redo confirmed gates — decisions in events.jsonl stand). Line budgets hold (trim elsewhere if needed).

### D4. Resume dogfood experiment

Harness gains nothing new: `prepare`, then seed by copying `docs/experiments/rf-mcp/session/register-copy/.qrisk` into the target, `run` with `scripts/prompts/session-resume.md` (phases 3–5; simulated gates as before: I pre-authorize accepting all reviewed risks after scoring, and accepting the proposed mitigations; every event notes `simulated-gate: scripted confirmation`), `collect`, `cleanup`. New metrics assertions for this experiment (checked in the report, not new harness code): every reviewed risk gains a score set with anchors; every accepted risk ends with ≥1 mitigation with residual note; phase ends at emit; strategy-md + trace-matrix exported; validate passes.

## Risks / Trade-offs

- [Status drifts from lifecycle semantics] → status derives counts from the same models/enums; tests pin hint rules.
- [Seeded register references evidence from a moved HEAD] → acceptable: evidence paths in rf-mcp are stable files; noted in the report if any went missing.
- [Skills line budget overflow] → SKILL.md edit replaces the Setup lines rather than adding a section.

## Migration Plan

Additive. Existing registers keep their configs; only new `init`s get default catalogs.

## Open Questions

- Whether MCP needs a `get_status` tool — decide after the resume dogfood (noted for queue item 2 or 4).
