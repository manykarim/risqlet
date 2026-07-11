# Tasks: add-guardrail-generation

## 1. Template library

- [x] 1.1 Define the guardrail template descriptor model (id, surface, enforcement, barriers, selectors, params, body) + loader; ship src/risqlet/guardrails/templates/ as package data (wheel force-include)
- [x] 1.2 Author ~10 vetted templates: secret-scan-posttool, env-read-deny, agents-no-secret-logging, coverage-check-stop, test-exists-posttool, lint-format-posttool, complexity-gate-ci, precommit-secret-scan, agents-change-scope, injection-review-agents (fixed bodies, declared params only)

## 2. Selection / render / diff engine

- [x] 2.1 Implement selection: accepted/mitigating risks (never proposed), priority >= guardrail_min_priority, match barrier + aspects/catalog-ref/tags to template selectors; parameterize paths from evidence (reuse changeset/ensemble normalization); deterministic
- [x] 2.2 Implement render with provenance markers (risqlet:<risk>:<barrier>:<template>) and hard/soft labeling; advisory-only warning for high-severity accepted risks with soft-only coverage
- [x] 2.3 Implement diff: scan target for markers → stale / missing / drift (read-only)
- [x] 2.4 Implement install: write per-surface (claude settings.json merge, AGENTS.md section, pre-commit block, explicit path) with markers; overwrite protection; never writes to .risqlet/

## 3. CLI

- [x] 3.1 Wire `risqlet guardrails generate|diff|install [--target ...] [--json] [--force]`; generate/diff read-only, install explicit

## 4. Tests

- [x] 4.1 Templates load/validate; only declared params interpolated (no free-form body drift)
- [x] 4.2 Selection: barrier+evidence→template mapping, proposed excluded, path scoping, min-priority filter, determinism, read-only
- [x] 4.3 Honesty: hard/soft labels; advisory-only warning fires for sev>=8 soft-only, not when a hard guardrail present
- [x] 4.4 diff stale/missing/drift via markers; install targets + overwrite protection + markers present + .risqlet/ untouched + validate unaffected
- [x] 4.5 Skills drift guards green with the new subcommand

## 5. Skills

- [x] 5.1 Write references/guardrails.md (barrier→surface map, hard vs soft, human-gated install); mitigate-phase note in SKILL.md/mitigation.md; budgets hold

## 6. Dogfood on tshirt-shop-om

- [x] 6.1 Write scripts/prompts/guardrails-demo.md (seed ensemble security register, accept the top risks, generate plan, install to a TEMP path only, diff after closing one risk)
- [x] 6.2 Run: prepare tshirt-shop-om, seed+accept register, run, collect into docs/experiments/tshirt-shop-om/guardrails/, cleanup to baseline (target's real .claude/ untouched)
- [x] 6.3 Evaluate + append findings to dogfooding report; apply small fixes

## 7. Wrap-up

- [x] 7.1 Full pytest + ruff (unpiped); commit
