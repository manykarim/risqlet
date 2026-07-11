# Proposal: add-foundation

## Why

Two deep-research reports in `docs/` establish that no existing tool provides agent-facing, quality-breadth risk analysis (existing MCP servers cover STRIDE/security only), and that the winning architecture is a CLI-first deterministic core with all state in repo-native files. This change builds that foundation — the register format and deterministic engine every later layer (catalog packs, agent skills, MCP adapter, dogfooding experiments) plugs into without migration.

## What Changes

- New Python 3.12+ package (`uv`-managed, Apache-2.0) with a `qrisk` console entry point.
- New `.qrisk/` repo-native risk register format: file-per-risk YAML (`.qrisk/register/R-NNNN.yaml`), `config.yaml` (active catalogs, scoring policy, output constraints), `events.jsonl` (append-only decision log), `strategy.md` output slot — all with published JSON Schemas.
- New deterministic CLI commands: `qrisk init`, `qrisk validate`, `qrisk score`, `qrisk export`. Arithmetic, ranking, and lifecycle gates are computed here — never by an LLM (framework-provider pattern).
- New scoring policy engine driven by YAML data packs, not code: `sod-ap-v1` (Severity×Occurrence×Detection with Action-Priority lookup, no raw RPN thresholds) as default; `li-v1` (3×3 likelihood×impact) as lightweight profile.
- Risk lifecycle enforcement: status transitions (`proposed → reviewed → accepted → mitigating → closed/rejected`) require an append-only decision entry with a named human principal; `validate` refuses phase advancement without one.
- Project scaffolding: `pyproject.toml`, LICENSE (Apache-2.0), README, `.gitignore`, pytest suite.

## Capabilities

### New Capabilities

- `risk-register`: The `.qrisk/` file formats and ontology — Risk (statement, aspects, provenance, scores, status lifecycle, decisions), Mitigation (treatment/lever/barrier classification, mandatory residual note, test trace links), QualityAspect selection (namespaced ids, rank 1–6, rationale), config, and append-only event log; JSON Schema validation for all of them.
- `scoring-policies`: Policy packs as data (S×O×D + Action-Priority table; likelihood×impact matrix), the deterministic computation of derived priorities, and rejection of scores lacking rubric anchors.
- `qrisk-cli`: The command-line surface (`init`, `validate`, `score`, `export`) including phase-gate enforcement and export formats (register YAML bundle, strategy markdown, trace-matrix CSV).

### Modified Capabilities

_None — greenfield project, no existing specs._

## Impact

- New source tree: `src/qrisk/` (domain, policies, schemas, cli), `tests/`, `policies/` data packs, `schemas/` JSON Schema files.
- New dev toolchain: `uv`, `pytest`, `ruff`.
- No existing code affected (first change in the repo). Downstream changes (catalog packs, agent skills, MCP adapter) will consume the formats and CLI defined here, so schema decisions in this change are load-bearing for the whole roadmap.
