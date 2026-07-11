# Design: add-guardrail-generation

## Context

The mitigation model already carries `barrier` (prevent/detect/recover), `lever`, `treatment`, `tests`, and the risk carries `evidence` paths and scored priority. Bow-tie barriers map onto coding-agent control surfaces; the register is therefore a latent specification for a set of project-tailored guardrails. We already ship a generic `risqlet check` PostToolUse hook and CI templates, and the skills/MCP portability tiering is established. This change generalizes that one hook into a *risk-driven, provenance-tagged, human-gated* guardrail generator.

## Goals / Non-Goals

**Goals:** turn accepted mitigations into installable guardrails across the three portability tiers; keep every guardrail traceable to its risk; be honest about hard-vs-soft enforcement; keep generation safe (vetted templates, human-gated install); avoid guardrail spam.

**Non-Goals:** becoming a policy engine (risqlet *orchestrates and justifies* existing enforcers — it emits a Semgrep/pre-commit rule tagged with a risk id; it does not reimplement Semgrep/OPA). No free-form LLM-authored hook commands. No auto-install. No runtime enforcement *by* risqlet (the target's own hooks/CI enforce). No non-standard agent formats beyond AGENTS.md + Claude Code + pre-commit/CI (other agents get the AGENTS.md + pre-commit tiers).

## Decisions

### D1. Vetted template library (`src/risqlet/guardrails/templates/`, package data)

Each template is a YAML descriptor + a snippet body:

```yaml
id: secret-scan-posttool
title: Post-write secret scan (blocking)
surface: claude-hook          # agents-md | claude-hook | claude-permission | pre-commit | ci
enforcement: hard             # hard (blocks/surfaces deterministically) | soft (advisory)
barriers: [prevent, detect]   # which mitigation barriers this satisfies
selectors:                    # how a mitigation opts in
  aspects: [iso25010.confidentiality, iso25010.security]
  catalog_refs: [owasp-web.cryptographic-failures, owasp-web.security-logging-and-monitoring-failures]
  tags: [secrets, leakage]
params: [paths]               # parameterized from the risk (evidence dirs → paths)
body: |
  # ...rendered hook JSON / rule text with {{paths}} and the provenance marker...
```

The **body is fixed, vetted text**; only declared `params` are interpolated from the register (never free-form model output). This is the security boundary: a generated hook runs arbitrary commands, so its command comes from the library, not the LLM. Templates ship in the wheel like skills/CI templates.

Initial library (~10): `secret-scan-posttool` (hard hook), `env-read-deny` (hard permission), `agents-no-secret-logging` (soft AGENTS.md), `coverage-check-stop` (hard Stop hook), `test-exists-posttool` (soft/warn hook), `lint-format-posttool` (hard hook), `complexity-gate-ci` (hard CI), `precommit-secret-scan` (universal), `agents-change-scope` (soft AGENTS.md: touch these paths → re-run `risqlet check`), `injection-review-agents` (soft AGENTS.md for owasp-web.injection).

### D2. Selection and rendering (`src/risqlet/guardrails/engine.py`)

Deterministic. For each risk with status accepted or mitigating (human-reviewed — never `proposed`) and priority at/above `config.constraints.guardrail_min_priority` (default: any scored; knob exists to fight friction fatigue), and for each of its mitigations, match templates whose `barriers` include the mitigation's `barrier` and whose `selectors` match the risk's aspects / mitigation `technique_ref` / catalog-ref tags. Parameterize `paths` from the risk's evidence directories (reuse `changeset`/`ensemble` path normalization). Each rendered guardrail embeds a provenance marker `risqlet:<risk-id>:<barrier>:<template-id>` in a comment/field so `diff` and `install` can find, update, and retire it. Deterministic ordering; identical register → identical plan.

### D3. Honesty labeling (the framework-provider ethos, applied to enforcement)

The plan labels each guardrail `hard` or `soft` from its template. For any risk with severity ≥ 8 (or li impact = 3) that is accepted/mitigating and whose selected guardrails are **all soft**, emit an advisory finding: `"R-00xx (severity 8) is covered only by advisory guardrails — an AGENTS.md rule suggests, it does not enforce; add a hard hook or accept the residual."` Advisory only — it never blocks generation. This mirrors the detection-evidence note and the "gate is convention not authentication" honesty: risqlet refuses to let a soft rule masquerade as enforcement for a high-severity risk, but the human decides.

### D4. Commands

- `risqlet guardrails generate [--json]` — print the plan: per target surface, the guardrails with their risk provenance, hard/soft label, and params; plus the advisory-only warnings and a friction summary (N guardrails across M surfaces). Read-only.
- `risqlet guardrails diff [--json]` — scan the target for installed provenance markers; report **stale** (marker's risk now closed/rejected/absent), **missing** (accepted risk in the plan with no installed marker), and **drift** (installed body differs from the current render). Read-only.
- `risqlet guardrails install --target claude-project | agents-md | pre-commit | path [--force]` — write the selected guardrails for that surface into their conventional location (`.claude/settings.json` hooks/permissions merged, `AGENTS.md` section, `.pre-commit-config.yaml` block, or an explicit path), each with its provenance marker. Refuses to overwrite a differing existing block without `--force`. Install is the explicit human action; `generate` never writes. Claude `settings.json` merges are additive and marker-scoped so re-install/removal is clean.

### D5. Portability tiers (reuse skills/MCP tiering)

- **AGENTS.md** — cross-agent, *soft* rules (advisory). The portable floor.
- **Claude Code** — `.claude/settings.json` hooks & permissions: the *hard* enforcement layer (premium).
- **pre-commit / CI** — universal hard checks (git-level), reusing the CI-template machinery from `add-ci-reassessment`.

`generate` shows all applicable tiers; `install --target` picks one. Non-Claude agents get AGENTS.md + pre-commit.

### D6. Skills

`references/guardrails.md`: the barrier→surface map, when to generate/diff/install, the hard-vs-soft honesty rule, the human-review-before-install requirement. `mitigation.md`/SKILL.md phase 4: one line noting that a mitigation's `barrier` and `evidence` drive `risqlet guardrails`, so choosing `barrier: prevent` vs `detect` has downstream teeth. Drift guards resolve the new `guardrails` subcommand and any referenced catalog ids.

### D7. Dogfood (tshirt-shop-om)

Seed the archived ensemble security register (several access-control and tenant-isolation risks — accepted for the demo). `risqlet guardrails generate` → expect: a secret/injection AGENTS.md rule set, path-deny/scan hooks scoped to the auth/tenant evidence paths, a coverage-check, each tagged with its risk id; and an advisory-only warning if a sev-9 risk is soft-only. `install --target path <tmp>` into a scratch dir (NOT the target's real `.claude/` — dogfood writes to a temp target to avoid mutating the example repo), verify provenance markers and that `diff` flags a deliberately-closed risk as stale. Cleanup; target repo untouched.

## Risks / Trade-offs

- [Friction fatigue → guardrails disabled] → generate only for accepted/scored risks, prioritized; `guardrail_min_priority` knob; the plan prints a friction summary so a human sees the count before installing. Few and load-bearing beats many and ignored.
- [Generated hook is an attack/error surface] → bodies come only from the vetted template library, never model text; human-gated install; provenance markers make every rule auditable and removable.
- [Advisory rules give false security] → D3 explicitly flags high-severity risks with soft-only coverage; output always labels hard vs soft.
- [Drift as register evolves] → `guardrails diff` + provenance markers (same staleness solution as `status`/`check`).
- [Scope creep into a policy engine] → templates emit rules for *existing* enforcers (Semgrep/pre-commit/ruff); risqlet selects, parameterizes, and justifies — it does not execute or reimplement them.
- [Mutating target repos in dogfood] → dogfood installs to a temp path only; harness cleanup + baseline check as before.

## Migration Plan

Additive. No register/schema change; guardrails live in the target project's agent-config files, not `.risqlet/`. `config.constraints.guardrail_min_priority` is optional (open-world).

## Open Questions

- Whether a future guardrail *hit* (a hook that fired and blocked something) should feed back into the register as Occurrence/Detection evidence — a tempting loop closure, but deferred; would need the target's hook to call `risqlet` back, which is a bigger integration.
- MCP parity for `guardrails` — deferred with the other CLI-first-then-MCP decisions.
