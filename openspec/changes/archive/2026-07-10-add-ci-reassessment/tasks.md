# Tasks: add-ci-reassessment

## 1. Change-set core

- [x] 1.1 Implement src/qrisk/changeset.py: changed-file discovery (git diff / --files / stdin), risk touch-matching (evidence/test high, statement-token low; normalized path components reusing ensemble/trace helpers), per-risk reasons + confidence + suggested action, untouched-high-priority reminder — read-only, deterministic
- [x] 1.2 Implement the check gate: flag rules (touched accepted/mitigating with failing/untested coverage; touched reviewed+ lacking passing coverage), modes off/warn/block with exit codes, ci_paths glob filtering

## 2. CI templates

- [x] 2.1 Author src/qrisk/ci/templates/: github.yml, gitlab.yml, claude-hooks.json (valid, path-filtered, first-party actions only, reference real qrisk commands); ship as package data (wheel force-include)
- [x] 2.2 Implement `qrisk ci init --target github|gitlab|claude-hooks|PATH [--force]` with conventional locations and overwrite protection

## 3. CLI wiring

- [x] 3.1 Wire `qrisk diff [--base] [--files] [--json]` and `qrisk check [--base] [--json]`

## 4. Tests

- [x] 4.1 diff: evidence/test/statement matches, annotation stripping + path normalization, --files/stdin, untouched-high-priority reminder, read-only
- [x] 4.2 check: gate modes off/warn/block exit codes, ci_paths filtering, coverage-driven flags
- [x] 4.3 ci init: each target emits to the right place, overwrite protection, unknown target; templates parse as valid YAML/JSON and reference only existing qrisk subcommands
- [x] 4.4 validate/register unaffected; skills drift guards green

## 5. Skills

- [x] 5.1 Write references/continuous.md; add qrisk diff scoping step to risk-quickscan SKILL.md; budgets hold

## 6. Dogfood on tshirt-shop-om

- [x] 6.1 Write scripts/prompts/ci-diff.md (seed archived ensemble register, no code changes, qrisk diff/check --base HEAD~3 vs real commits, ci_paths filter trial)
- [x] 6.2 Run: prepare tshirt-shop-om, seed register, run, collect into docs/experiments/tshirt-shop-om/ci/, cleanup to baseline
- [x] 6.3 Evaluate + append findings to dogfooding report; apply small fixes

## 7. Wrap-up

- [x] 7.1 Full pytest + ruff (unpiped); commit
