# Turning mitigations into coding-agent guardrails

An accepted mitigation is a promise; a guardrail in the coding agent's own
environment is that promise made hard to break. `risqlet guardrails` reads the
accepted register and proposes project-tailored guardrails — each traceable to
the risk that justifies it — that you review and install. It generates from a
vetted template library only (never free-form hook commands: a generated hook
runs arbitrary code).

## The barrier → surface map

A mitigation's `barrier` (and the risk's `evidence` paths) drive what gets
generated:

```
 barrier    →  surface                       enforces?
 prevent    →  claude-permission (deny)       HARD  — blocks the action
               claude-hook (PreToolUse)        HARD
               AGENTS.md rule                  SOFT  — advises only
 detect     →  claude-hook (PostToolUse/Stop)  HARD  — surfaces/blocks
               pre-commit / CI                 HARD
               AGENTS.md "re-check risks" rule  SOFT
 recover    →  runbook / docs                 (not a guardrail)
```

Evidence paths scope the rules: a confidentiality risk evidenced in
`src/auth/` yields a secret-scan hook and path-deny *scoped to that directory*,
not a repo-wide blanket.

## Hard vs soft — be honest

Only hooks and permissions **enforce**; an AGENTS.md rule **advises** and an
agent can ignore it mid-generation. `guardrails generate` labels every rule
hard or soft, and flags any high-severity accepted risk covered *only* by soft
rules: *"R-00xx is high-severity but covered only by advisory guardrails — add
a hard hook or accept the residual."* Do not let a polite instruction stand in
for enforcement on a serious risk.

## Workflow

1. Reach the mitigate/emit phase with risks accepted and mitigations recorded
   (their `barrier` matters — `prevent` vs `detect` changes what is generated).
2. `risqlet guardrails generate` — review the plan: which rules, which risks,
   hard/soft, the friction count, and any advisory-only warnings.
3. **Human review, then** `risqlet guardrails install --target agents-md |
   claude-project | pre-commit | <path>`. Install is deliberate; `generate`
   and `diff` never write. Prefer few, load-bearing guardrails — ten blocking
   hooks get disabled; a handful get kept.
4. `risqlet guardrails diff` later — every rule carries a `risqlet:<risk>:...`
   marker, so diff reports stale (risk closed), missing (new accepted risk),
   and drift as the register evolves. Retire stale rules; they had a reason,
   and the reason is gone.

Portability: AGENTS.md rules work across agents (the soft floor); Claude Code
hooks/permissions are the hard layer; pre-commit/CI are universal. risqlet
*selects, parameterizes, and justifies* rules for existing enforcers
(gitleaks, ruff, your test command) — it does not replace them.
