# Proposal: add-ci-reassessment

## Why

The register is only as good as its freshness — ISTQB's own critique of risk-based testing is that it's done once and goes stale. The research shows the change boundary (the PR) is where re-assessment pays off: Atlassian's merge-checks caught risks across 355k PRs at 0.075% flag rate, and Semgrep's post-write hooks keep analysis live inside coding sessions. qrisk has the register, coverage data, and priorities to do this, but nothing yet connects a code change to the risks it touches.

## What Changes

- New `qrisk diff [--base <ref>]`: map changed files to the register risks they touch (via evidence paths, test refs, statement tokens), with a why-matched reason and a suggested action per risk; read-only.
- New `qrisk check [--base <ref>]`: a CI gate — non-zero when a change touches an accepted/mitigating risk with failing or missing mitigation coverage, or a reviewed-but-never-rescored risk; mode `off|warn|block` and path filters in config.
- New `qrisk ci init [--target github|gitlab|claude-hooks|path]`: emit ready CI templates (GitHub Actions, GitLab CI) and a Claude Code hooks snippet for in-session re-assessment, shipped as package data.
- Skills: `references/continuous.md` and a `qrisk diff` scoping note in risk-quickscan.
- Dogfooding on tshirt-shop-om against its real recent commits.

## Capabilities

### New Capabilities

- `change-reassessment`: `qrisk diff` matching semantics, `qrisk check` gate modes and path filtering, and `qrisk ci init` template emission.

### Modified Capabilities

- `agent-skills`: quickscan gains the diff-scoping step; a continuous-reassessment reference is added.

## Impact

- New `src/qrisk/changeset.py` (diff matching, gate), `src/qrisk/ci/templates/` (package data), CLI `diff`/`check`/`ci` commands, `config.constraints.ci_gate`/`ci_paths` (open-world, optional), `skills/risk-analysis/references/continuous.md`, dogfood prompt + artifacts.
- No register schema change; new config fields are optional.
