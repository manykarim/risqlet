# Design: add-ci-reassessment

## Context

Queue item 4. Register, trace coverage, and priorities exist; the missing piece is connecting a diff to the risks it touches, at PR time and in-session. Reuse existing helpers: `ensemble.evidence_path` (annotation stripping), `ensemble.statement_tokens`, `trace.ref_key` / `read_results`, `status.build_status` ranking. Constraints: read-only analysis (`diff`/`check` never mutate), stdlib + git CLI only, path filters to keep noise low (Atlassian pattern), gate opt-in-ish (default `warn`).

## Goals / Non-Goals

**Goals:** deterministic change→risk mapping; a CI gate with sane exit-code semantics and noise control; copy-paste CI/hook templates; the PR-time and in-session loops teachable; proven on a real repo's real commits.

**Non-Goals:** hosting a bot or posting comments (templates delegate to standard CI actions), server-side git, source-coverage %, MCP tools (revisit item 4 close-out), auto-mutating the register from CI.

## Decisions

### D1. Change→risk matching (`src/qrisk/changeset.py`)

Inputs: a list of changed paths (from `git diff --name-only <base>...HEAD` executed by the command; or `--files a b`, or newline stdin for non-git use). A risk is **touched** by a changed path if any:
- an `elicited_by.evidence` item's normalized path (`evidence_path`) equals or is a suffix/prefix path-component match of the changed path;
- a mitigation `tests[]` ref's path (via `ref_key` locator) matches the changed path basename;
- (best-effort, lower confidence) ≥2 distinct statement tokens (via `statement_tokens`, length ≥4) appear as path components of the changed path.

Match records carry `reason` (`evidence:<path>` | `test:<ref>` | `statement:<tokens>`) and a `confidence` (`high` for evidence/test, `low` for statement). Path matching: compare on POSIX-normalized components; a risk evidence `src/pay/terminal.py` matches changed `src/pay/terminal.py` (high) and, as a directory signal, `src/pay/` prefix matches (medium — evidence dir). Output per touched risk: id, status, priority (from active policy), reasons, suggested action (`re-score` if scored & reviewed+, `re-elicit this area` if the newest evidence predates the change / risk still proposed, `verify coverage` if it has failing/untested mitigations). Also report top-N untouched high-priority risks as a "still worth attention" reminder. Deterministic, read-only.

### D2. `qrisk check` gate

Computes the diff mapping, then flags a change when a touched risk is:
- accepted/mitigating **and** has a `covered-failing` or `untested`/`charter-only` mitigation (trace results consulted if present); or
- reviewed-or-accepted **and** its newest score predates... — simplified for v1: reviewed+ risk touched by the change and not scored (no score set) OR scored but flagged by trace. (No timestamps on scores yet, so "stale" = "touched reviewed+ risk lacking passing coverage".)

Modes from `config.constraints.ci_gate`: `off` (always exit 0, prints nothing), `warn` (print flags, exit 0 — default), `block` (print flags, exit 1 if any). Path filter `config.constraints.ci_paths` (glob list; empty = all): changed paths not matching any glob are excluded before mapping (the 41%-excluded pattern). `--json` emits `{mode, flagged: [...], excluded_paths: n, exit}`.

### D3. CI templates and `qrisk ci init`

Templates in `src/qrisk/ci/templates/` (package data, shipped like skills): `github.yml` (a PR-triggered workflow: setup uv, `qrisk validate`, `qrisk check --base origin/${{ github.base_ref }}`, write `$GITHUB_STEP_SUMMARY` from `qrisk check --json`; uses only first-party actions, path-filtered), `gitlab.yml` (a merge-request job), `claude-hooks.json` (a `PostToolUse` hook on `Write|Edit` running `qrisk check --json` to surface touched risks in-session). `qrisk ci init --target github|gitlab|claude-hooks|<path>` writes the template to its conventional location (`.github/workflows/qrisk.yml`, `.gitlab-ci.qrisk.yml`, prints the hooks JSON for the user to merge into settings, or an explicit path), refusing overwrite without `--force`. Templates are static, valid YAML/JSON (tested).

### D4. Skills

`references/continuous.md`: when to run `diff` (scoping a change: what's already covered) vs `check` (the gate); reading touched-risk output and acting; the two loops (PR-time via CI template, in-session via hooks). `risk-quickscan/SKILL.md`: add a step 1.5 — "`qrisk diff --base <merge-base>` to see which existing risks already cover this change before eliciting new ones" (avoids duplicate risks). Budgets hold.

### D5. Dogfood on tshirt-shop-om

`scripts/prompts/ci-diff.md`: seed a small register (reuse the archived ensemble experiment register from `docs/experiments/tshirt-shop-om/ensemble-quickstart/register-copy` — its risks cite real order/approval paths), make **no** code changes, run `qrisk diff --base HEAD~3` and `qrisk check --base HEAD~3` against the repo's real recent commits (which touched order/approval code — should touch the seeded risks), report touched risks with reasons and the gate outcome, and try a `ci_paths` filter. Metrics: changed files, touched risks, high-confidence matches, gate mode/exit. Cleanup to baseline.

## Risks / Trade-offs

- [Statement-token matching false positives] → marked `low` confidence, never the sole basis for a `check` block (block considers evidence/test matches on reviewed+ risks); documented.
- [No score timestamps → weak "stale" detection] → v1 uses coverage + touched-reviewed heuristics; a `scored_at` field is a future enhancement (noted).
- [git not present / shallow clone in CI] → command errors actionably; template uses `fetch-depth: 0` and documents it; `--files`/stdin fallback for non-git.
- [Template drift from real CLI flags] → a test parses each template and asserts referenced `qrisk` subcommands exist (same drift-guard idea as skills).

## Migration Plan

Additive; new config fields optional (defaults: gate `warn`, paths all). Registers without them behave as `warn`/all.

## Open Questions

- MCP parity for diff/check and a consolidated MCP review at item-4 close — will assess after this run whether MCP tools are warranted or CLI+templates suffice.
