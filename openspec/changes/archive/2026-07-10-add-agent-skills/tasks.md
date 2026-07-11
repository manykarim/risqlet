# Tasks: add-agent-skills

## 1. Skill authoring

- [x] 1.1 Write skills/risk-analysis/SKILL.md (frontmatter tuned for discovery; lean six-phase router with gates, output contracts, evidence rule; points to references)
- [x] 1.2 Write references/phases.md (per-phase entry/exit criteria, exact qrisk commands, event JSON line format, human-confirmation protocol before any human: event)
- [x] 1.3 Write references/elicitation.md (five pass recipes with catalog entry ids and per-pass output expectations)
- [x] 1.4 Write references/scoring-rubrics.md (original anchor tables for severity/occurrence/detection 1-10 and likelihood/impact 1-3; anchor-citation discipline; disagreement surfacing)
- [x] 1.5 Write references/risk-writing.md (statement format, provenance fields, evidence rules, speculative handling) and references/mitigation.md (treatment/lever/barrier decision guide, residual-note discipline, test-charter drafting into tests[])
- [x] 1.6 Write skills/risk-quickscan/SKILL.md (diff-scoped passes, proposed-only, escalation rule)

## 2. skills CLI

- [x] 2.1 Implement skills discovery (repo skills/ + package data via importlib.resources), frontmatter parsing, `qrisk skills list [--json]`
- [x] 2.2 Implement `qrisk skills install [SKILL ...] --target claude-project|claude-user|PATH [--force]` with overwrite protection and unknown-skill errors
- [x] 2.3 Packaging: include skills/ in the wheel as qrisk data; verify install works from package data path

## 3. Drift guards and docs

- [x] 3.1 Tests: frontmatter validity + name/dir match, SKILL.md line budgets, catalog-id resolution, qrisk-subcommand existence, install round-trips (list/install/--force/unknown)
- [x] 3.2 README section: using the skills from Claude Code (project/user install) and other agents (path install); note on gates and validation
- [x] 3.3 Full pytest + ruff; commit
