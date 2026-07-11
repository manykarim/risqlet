# Tasks: add-register-defaults-and-resume

## 1. Init defaults

- [x] 1.1 Enable packaged catalogs in _STARTER_CONFIG with explanatory comment; adjust affected tests; add test that fresh init validates clean with catalog checks active

## 2. Status command

- [x] 2.1 Implement src/qrisk/status.py (StatusReport builder: counts, coverage, top risks via policy ranking, deterministic pending hints, last event, invalid-file tolerance)
- [x] 2.2 Wire `qrisk status [--json]` into the CLI (read-only; exit 0 on messy registers, non-zero only when register missing)
- [x] 2.3 Tests: empty/mid-session/complete registers, --json shape, each hint rule, read-only guarantee, invalid-file tolerance

## 3. Skills resume protocol

- [x] 3.1 Update risk-analysis SKILL.md Setup (status-first) and phases.md (Resuming a session section: never redo recorded gates); keep line budgets; drift guards green

## 4. Resume dogfood

- [x] 4.1 Write scripts/prompts/session-resume.md (phases 3-5, simulated gates with labeling, pre-authorizations for score acceptance and mitigation acceptance)
- [x] 4.2 Run experiment: prepare rf-mcp, seed archived phase-0-2 register, run, collect into docs/experiments/rf-mcp/session-resume/, cleanup to baseline
- [x] 4.3 Evaluate (reviewed risks scored with anchors, accepted risks mitigated with residual notes, phase=emit, exports render, validate passes); append findings to docs/experiments/dogfooding-report.md; apply small fixes

## 5. Wrap-up

- [x] 5.1 Full pytest + ruff (fail on lint); commit
