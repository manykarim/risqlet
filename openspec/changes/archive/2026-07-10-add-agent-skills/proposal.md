# Proposal: add-agent-skills

## Why

The determinism layer (CLI, register, gates) and the knowledge layer (catalog packs) exist, but nothing yet tells an agent *how to run a risk analysis* — the phase protocol, elicitation recipes, scoring discipline, and anti-hallucination rules live only in research docs. Agent Skills are the evidence-backed vehicle for this (progressive disclosure, cross-vendor portability, complements-not-replaces tools), and shipping them makes the system actually usable from Claude Code and other coding agents — the prerequisite for the dogfooding change.

## What Changes

- New canonical `skills/` directory (cross-vendor Agent Skills format) with two skills:
  - `risk-analysis`: the full six-phase facilitation playbook (context → aspects → elicit → score → mitigate → emit) over the `qrisk` CLI, with human gates, provenance/evidence discipline, and constraint-first output contracts; detail split into bundled reference files (phases, elicitation recipes, scoring rubrics, risk writing, mitigation mapping).
  - `risk-quickscan`: lightweight single-pass scan of a change/PR that emits `proposed` risks only and recommends a full session when warranted.
- New CLI command group `qrisk skills list|install` — copies canonical skills into `.claude/skills/`, `~/.claude/skills/`, or any path (other agents discover plain markdown skills their own way); skills ship as package data so installation works from an installed wheel.
- New drift-guard tests: skill frontmatter parses, all referenced catalog entry ids resolve, referenced CLI commands exist, SKILL.md stays lean (progressive-disclosure budget).
- README section on using the skills from Claude Code and other agents.

## Capabilities

### New Capabilities

- `agent-skills`: The two skills' required content and structure — phase protocol with human gates, elicitation passes with catalog references, scoring/mitigation discipline, quickscan behavior — and the portability/size constraints.
- `skills-cli`: The `qrisk skills` command group (list, install targets, packaging as package data).

### Modified Capabilities

_None — the register, catalog, and existing CLI behaviors are unchanged; skills are a consumer._

## Impact

- New: `skills/risk-analysis/` (SKILL.md + references/), `skills/risk-quickscan/SKILL.md`, `src/qrisk/skills_cli.py` (or equivalent), packaging config for skill data files, tests.
- Downstream: change 4 (MCP adapter) reuses the same playbooks; the dogfooding change installs these skills into example projects via `qrisk skills install`.
