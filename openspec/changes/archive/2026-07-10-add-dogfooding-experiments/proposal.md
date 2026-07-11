# Proposal: add-dogfooding-experiments

## Why

Every layer is built and unit-tested, but nothing yet proves the intended end-to-end reality: a real coding agent, in a real repo it has never seen, following the skills to produce a validate-passing, evidence-grounded risk register. Dogfooding on two dissimilar projects (rf-mcp: Python MCP server; robotframework-javaui: Rust/Java UI library) is the cheapest honest test — and its findings are the feedback loop the roadmap promised.

## What Changes

- New experiment harness (`scripts/dogfood.py`): prepares a target repo (skills installed to its `.claude/skills/`, `qrisk` on PATH), drives timeboxed `claude -p` headless runs with controlled prompts and restricted permissions, captures outputs and the produced `.qrisk/` register into `docs/experiments/<target>/`, and leaves the target repo clean.
- Experiment 1 (both targets): `risk-quickscan` over a representative module/diff.
- Experiment 2 (rf-mcp): abbreviated full `risk-analysis` session (phases 0–2, human gates simulated by scripted confirmations, clearly labeled).
- Evaluation report `docs/experiments/dogfooding-report.md`: metrics per run (risk count, validate results, speculative ratio, evidence spot-checks, statement-format compliance, catalog-ref usage, wall-clock) plus a findings→fixes list.
- Small clearly-indicated fixes applied in this change; larger findings recorded for future changes.

## Capabilities

### New Capabilities

- `dogfood-harness`: The repeatable experiment procedure — target preparation, headless-run constraints (timebox, permissions, cleanliness guarantees), artifact capture, and the evaluation metrics.

### Modified Capabilities

_None planned upfront; the findings→fixes step may touch skills or CLI text without requirement-level changes (any requirement-level fix gets its own delta)._

## Impact

- New: `scripts/dogfood.py`, `docs/experiments/` artifacts, evaluation report.
- Target repos are read/analyzed but never committed to; experiment registers are copied out and cleaned up.
- Success criteria: both targets yield a validate-passing register with ≥3 evidenced risks; ≥1 finding-driven fix applied here.
