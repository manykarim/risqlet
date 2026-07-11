# Design: add-foundation

## Context

Greenfield repo. Two research reports (`docs/ai-augmented-risk-analysis-framework.md`, `docs/prior-art-architecture-ip-research.md`) fix the architecture: CLI-first deterministic core, all state in repo-native `.qrisk/` files (no server-held sessions), framework-provider pattern (this layer validates/computes; semantic analysis stays in the host LLM), and consolidated decisions D1–D10. This change implements the two bottom layers: the register file format (the system's real API) and the deterministic engine over it. Later changes (catalog packs, agent skills, MCP stdio adapter, dogfooding) consume this without migration — so schema choices here are the highest-stakes decisions of the roadmap.

## Goals / Non-Goals

**Goals:**
- A `.qrisk/` directory format any coding agent can read/write with plain file tools, validated by JSON Schema.
- Deterministic scoring/ranking/lifecycle enforcement via a `qrisk` CLI — LLMs never do arithmetic or silently mutate state.
- Scoring policies as swappable data packs.
- Human accountability: state transitions require a named human principal in an append-only log.

**Non-Goals:**
- Catalog content (change 2), agent skills/playbooks (change 3), MCP adapter (change 4), persona ensembles, embedding-based dedupe, web UI.
- Multi-repo or centralized register storage.
- Final product naming/branding (working name `qrisk` for the CLI; PyPI publication deferred).

## Decisions

### D1. File layout: file-per-risk

```
.qrisk/
├── config.yaml          # project, active catalogs, scoring policy, constraints, phase
├── register/
│   ├── R-0001.yaml      # one risk per file (embedded mitigations)
│   └── ...
├── events.jsonl         # append-only decision/audit log
└── strategy.md          # generated output slot (export target)
```

File-per-risk keeps PR diffs reviewable, avoids merge conflicts in parallel elicitation, and enables path-based CI filtering. Alternative (single `register.yaml`) rejected: conflict-prone, unreviewable diffs at 20+ risks. Mitigations are embedded in their risk file (a mitigation addressing multiple risks lists `risk_ids`; it lives in the lowest-numbered risk's file) — a separate `mitigations/` dir was rejected as premature indirection.

### D2. Risk document shape (ontology from report #1 §5.2, trimmed to v1)

```yaml
id: R-0001                    # ^R-\d{4}$, allocated by CLI (max existing + 1)
statement: "Because <condition>, <event> may occur, causing <consequence>"
aspects: [iso25010.security]  # namespaced catalog.slug; free-form allowed in v1
elicited_by:
  method: riskstorming        # enum: riskstorming|hazop|stride|premortem|fmea|inside-out|manual
  prompt_ref: ""              # card/guideword/persona ref, optional
  evidence: []                # doc refs, incident IDs, code paths; empty ⇒ validate flags "speculative"
scores:                       # 0..n score sets; computed fields written ONLY by `qrisk score`
  - policy: sod-ap-v1
    values: {severity: 8, occurrence: 4, detection: 7}
    rubric_anchors: ["sev8: data corruption", "occ4: monthly", "det7: no automated check"]
    scored_by: [agent:security-persona]
    derived: {rpn: 224, action_priority: HIGH}   # CLI-computed; validate rejects hand-edits that mismatch
status: proposed              # proposed|reviewed|accepted|mitigating|closed|rejected
mitigations:
  - id: M-0001
    risk_ids: [R-0001]
    treatment: reduce         # avoid|reduce|transfer|accept   (ISO 31000)
    lever: detection          # severity|occurrence|detection  (FMEA)
    barrier: detect           # prevent|detect|recover         (bow-tie)
    technique_ref: ""         # catalog ref, optional in v1
    concrete: "nightly reconciliation check ..."
    residual_note: "chargebacks remain undetected until settlement +2d"   # REQUIRED, non-empty
    tests: []                 # e.g. rf:suite/path::TestName — trace links
```

`disagreement` (ensemble spread) is deferred to the ensemble change but the `scores` list shape already supports multiple scorers. Rationale for mandatory `residual_note`: anti-completeness-theater (report #1 principle).

### D3. Lifecycle and the decision log

Status transitions form a validated state machine: `proposed → reviewed → accepted → mitigating → closed`, with `rejected` reachable from `proposed|reviewed`. Every transition MUST be accompanied by an `events.jsonl` entry:

```json
{"ts":"2026-07-10T12:00:00Z","type":"status_change","risk":"R-0001","from":"proposed","to":"reviewed","principal":"human:many","note":"..."}
```

`qrisk validate` cross-checks each risk's current status against replayed events and **fails if any transition beyond `proposed` lacks an event with a `human:` principal** (agents may create/edit `proposed` risks freely; only humans advance them). This is the hook-independent gate that works on every agent platform. Phase advancement in `config.yaml` (`phase: context|aspects|elicit|score|mitigate|emit`) is gated the same way (`type":"phase_change"`, human principal required).

Events are the accountability trail, not event-sourced state: files are the source of truth for content; events are the source of truth for *who authorized transitions*. Full event sourcing (agentic-riskstorming ADR-002) was rejected for v1 — file-per-risk plus a transition log gets the audit value at a fraction of the machinery.

### D4. Scoring policy packs as data

`policies/sod-ap-v1.yaml` (packaged, plus user overrides via `.qrisk/policies/`):

```yaml
id: sod-ap-v1
factors:
  severity:   {min: 1, max: 10}
  occurrence: {min: 1, max: 10}
  detection:  {min: 1, max: 10}   # high = poor detectability
derived:
  rpn: {formula: product}          # sorting heuristic only — no thresholds on raw RPN
  action_priority:
    type: lookup                   # AIAG-VDA-style AP table
    bands:                         # first matching rule wins, evaluated top-down
      - {when: {severity: ">=9"},                                    value: HIGH}
      - {when: {severity: "7-8", occurrence: ">=4"},                 value: HIGH}
      - {when: {severity: "7-8", occurrence: "2-3", detection: ">=5"}, value: MEDIUM}
      # ... complete band table in implementation
      - {default: LOW}
```

`li-v1` defines `likelihood`/`impact` 1–3 and a 3×3 `priority` lookup (critical/high/medium/low). The engine is generic: ordinal factors + derived fields (`product` formula or `lookup` table). Rule evaluation is strictly top-down first-match, so the pack is auditable by reading. `qrisk score` rejects score sets missing `rubric_anchors` (one per factor) — anchoring discipline reduces score variance.

### D5. CLI surface (v1)

- `qrisk init` — scaffold `.qrisk/` with commented config; idempotent (refuses to overwrite non-empty).
- `qrisk validate` — JSON Schema validation of all files + referential integrity (aspect refs, mitigation risk_ids, unique ids) + lifecycle/gate checks (D3) + `derived` recomputation check + speculative-evidence flags. Exit 0/1 with a machine-readable `--json` report; this is the command agents run constantly.
- `qrisk score [R-NNNN|--all]` — compute/refresh `derived` for score sets under the active policy; never invents factor values.
- `qrisk export --fmt register-yaml|strategy-md|trace-matrix-csv [-o PATH]` — deterministic serializations. `strategy-md` renders the one-page strategy skeleton (top risks by derived priority, honoring `config.constraints.max_top_risks`, with mitigation/trace tables and a mandatory "what this does not cover" section aggregating residual notes). Defaults to stdout for composability; `strategy.md` written only with `-o .qrisk/strategy.md`.

All commands take `--dir` (default: nearest `.qrisk/` walking up from cwd, git-style). Output is plain text; `--json` everywhere for agent consumption.

### D6. Package architecture

```
src/qrisk/
├── model/        # pydantic models: Risk, Mitigation, ScoreSet, Config, Event
├── schemas/      # JSON Schema files (generated from models at build time, committed)
├── policies/     # engine.py + packaged sod-ap-v1.yaml, li-v1.yaml
├── store.py      # .qrisk/ discovery, load/save, id allocation, events append/replay
├── lifecycle.py  # state machine + gate checks
├── exports/      # register-yaml, strategy-md, trace-matrix-csv renderers
└── cli.py        # argparse (stdlib) wiring — thin; all logic in the layers above
```

Pydantic v2 for models (validation + JSON Schema generation from one source of truth; schemas committed so non-Python consumers can validate). `argparse` over click/typer: zero extra deps for a small stable surface. `ruamel.yaml` for round-trip-safe YAML (preserves comments/order when CLI touches user files — agents and humans co-edit these). Dependency budget: pydantic, ruamel.yaml, jsonschema (test-time cross-check) only.

## Risks / Trade-offs

- [Schema too rigid for later changes] → every document gets `schema_version: 1`; unknown extra fields are warnings, not errors (open-world validation), so later layers can annotate without breaking old CLIs.
- [Hand-edited `derived` fields drift from policy] → `validate` recomputes and fails on mismatch; `derived` is advisory output, never input.
- [Human-principal gate is spoofable by an agent writing `human:x` events] → v1 accepts this (convention + review); the Claude Code hooks layer (change 3) adds enforcement where supported. Documented honestly in README.
- [ruamel round-trip quirks] → store writes are limited to well-defined mutations (id allocation, derived refresh); tests cover comment preservation.
- [ID collisions in parallel branches] → file-per-risk means collisions surface as git conflicts on identically numbered new files; documented workflow: re-number via `qrisk validate --fix-ids` (stretch; manual in v1).

## Migration Plan

None — greenfield. First git commit lands with this change's implementation.

## Open Questions

- Whether `aspects` should be constrained to loaded catalogs once change 2 lands (v1: free-form namespaced strings, validated for format only).
- PyPI name check (`qrisk` availability vs. QRISK3 clinical-score confusion) before any publication — not blocking local/git usage.
