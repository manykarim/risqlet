# Tasks: add-foundation

## 1. Project scaffolding

- [x] 1.1 Create pyproject.toml (uv, Python 3.12+, deps: pydantic, ruamel.yaml; dev: pytest, ruff, jsonschema), src/qrisk package skeleton, LICENSE (Apache-2.0), .gitignore, README stub
- [x] 1.2 Verify `uv sync` and an empty pytest run succeed

## 2. Domain models and schemas

- [x] 2.1 Implement pydantic models: Risk, Mitigation, ScoreSet, ElicitedBy, Config (with aspects/constraints), Event — enums and field constraints per spec (open-world: extra fields warn)
- [x] 2.2 Generate JSON Schema files from models into src/qrisk/schemas/ and commit them; test that generation is deterministic
- [x] 2.3 Unit tests: valid/invalid risk documents, mandatory residual_note, id patterns, config constraints (max_aspects, unique ranks)

## 3. Store layer

- [x] 3.1 Implement .qrisk/ discovery (walk-up + --dir), load/save of config and register files with ruamel round-trip (comment/order preservation), R/M id allocation
- [x] 3.2 Implement events.jsonl append and replay (status + phase events)
- [x] 3.3 Unit tests: discovery from subdirectory, comment preservation on rewrite, id allocation after gaps

## 4. Lifecycle and gates

- [x] 4.1 Implement status state machine (legal transitions incl. rejected branch) and event/state consistency check (replay must match file status)
- [x] 4.2 Implement human-principal gate: transitions beyond proposed and phase changes require an event with human: principal
- [x] 4.3 Unit tests: legal/illegal transitions, skipped-state detection, agent-principal rejection, phase-gate enforcement

## 5. Scoring policy engine

- [x] 5.1 Implement generic pack loader + validator (factors, product formula, top-down first-match lookup bands; band factor refs checked)
- [x] 5.2 Author packaged policy packs: sod-ap-v1 (full AP band table, severity-dominant) and li-v1 (3×3 matrix); support user packs from .qrisk/policies/
- [x] 5.3 Implement scoring: range validation, rubric-anchor requirement (≥1 per factor), deterministic derived computation
- [x] 5.4 Unit tests: severity dominance (S9/O1/D1 → HIGH), equal-RPN different-AP cases, li-v1 corners, out-of-range and anchorless rejection, malformed pack errors, user pack override

## 6. Validation

- [x] 6.1 Implement `validate` pipeline: JSON Schema pass, referential integrity (aspect format, mitigation risk_ids, unique ids), lifecycle checks, derived recomputation mismatch, speculative-evidence warnings, constraint checks
- [x] 6.2 Implement --json report (findings with file/field/severity/message + top-level pass flag)
- [x] 6.3 Unit tests: aggregated multi-finding run, warnings don't fail, tampered derived detected, dangling references

## 7. CLI

- [x] 7.1 Implement argparse CLI wiring: init (idempotent, refuses non-empty), validate, score [R-NNNN|--all], export --fmt -o; global --dir/--json; exit codes 0/1
- [x] 7.2 Unit/integration tests: fresh init validates clean, init refuses existing register, score --all writes derived only, explicit --dir

## 8. Exports

- [x] 8.1 Implement register-yaml bundle and trace-matrix-csv renderers (deterministic ordering)
- [x] 8.2 Implement strategy-md renderer: aspects, top-N risks by derived priority (cap + "N further risks" note), mitigation table, mandatory "What this does not cover" section from residual notes
- [x] 8.3 Unit tests: constraint capping, residual section always present, byte-identical repeat export

## 9. Documentation and wrap-up

- [x] 9.1 Write README: architecture summary (CLI-first, framework-provider, register-in-repo), .qrisk/ format reference, CLI usage, honest note on the human-principal convention's enforcement limits
- [x] 9.2 End-to-end smoke test: init → hand-author 2 risks + scores + mitigation → score --all → validate → all three exports (this scenario becomes the fixture for later changes)
- [x] 9.3 Run ruff + full pytest; initial git commit of the entire project
