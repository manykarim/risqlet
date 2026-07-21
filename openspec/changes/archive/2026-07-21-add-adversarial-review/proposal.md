## Why

risqlet's existing gates are structural. `validate` checks schema, replayable
human-principal events, and speculative-evidence flags; `check` gates CI on coverage
state. Neither can catch a decision that is **schema-valid but semantically wrong** —
a risk "accepted" on a mitigation whose test is hollow, a risk whose evidence path
points at an unrelated file, or a genuinely critical defect scored LOW.

This gap was measured, not assumed. In an experiment on `robotframework-javaui`, six
decisions were constructed that `risqlet validate` passed (all six), three of them
subtly weak in exactly those ways. `validate` caught **0 of 3**. An adversarial panel
of independent reviewers, whose structured objections were resolved by a deterministic
verdict, caught **3 of 3** — and additionally flagged a decision believed sound that
turned out to rest on a misread of the code (dead Rust mistaken for the live path).

The pattern is a clean fit for risqlet's core thesis. It comes from agentic-qe's
"QE Court" (MIT; reimplemented here from behavior, no code copied), whose own design
already splits the way risqlet requires: the LLM reviewers run in a host-driven Skill,
while the SHIP/REMAND/BLOCK verdict is *pure deterministic rules with no LLM calls*.
That is the framework-provider pattern exactly — the host does the semantic review,
risqlet does the arithmetic — and it extends risqlet's stated mission ("agents propose,
humans decide"; "keep mitigations honest") with a structured adversarial gate it does
not have today.

The experiment also surfaced a load-bearing subtlety: the verdict rule must require
corroboration by **distinct** reviewers. A naive rule that counts one reviewer's
multiple objections as agreement turns the gate into a rubber-stamp REMAND machine
that flags everything; the correct rule (a charge survives only when ≥2 distinct
reviewers raise it) ships the genuinely-sound decisions and flags only the weak ones.
That subtlety is precisely why the verdict must be **deterministic and test-owned by
risqlet** rather than left to the host — which is the argument for building it here.

## What Changes

- **New `risqlet review` command** (deterministic, read-mostly + append): given a
  panel's structured charges for a specific decision, it validates the panel, computes
  a SHIP/REMAND/BLOCK verdict, and appends the review record to an append-only
  `.risqlet/reviews.jsonl`. It calls no LLM and is fully reproducible from its input.
- **A verdict algorithm** owned and tested by risqlet:
  - Panel validity: ≥2 distinct reviewers, and the decision's author is not among them.
  - A charge (category, severity ∈ fatal|major|minor, reproducible) *survives* only when
    ≥2 **distinct** reviewers file a reproducible charge in the same category.
  - Verdict: **BLOCK** on a surviving fatal; **REMAND** on a surviving major (or a lone
    reproducible fatal); else **SHIP**.
- **A new Agent Skill** (`risk-court`) that instructs the host to convene an independent
  multi-reviewer panel — ideally cross-perspective/cross-vendor — to challenge a named
  decision, each reviewer emitting charges in the defined JSON schema. The skill runs the
  LLMs; risqlet never does.
- **Human as final judge, unchanged.** The verdict is a *recommendation* recorded for
  audit. Any resulting lifecycle transition (accept, rework) is still made by a human via
  the existing human-principal event gate — the verdict does not itself change a risk's
  status.
- **`risqlet validate` verifies recorded verdicts** are recomputable from their charges
  (mirroring how it recomputes ensemble `disagreement`), so a tampered or stale verdict
  is caught.

### Not in scope

- risqlet convening the panel or calling any model — the host owns all semantic review.
- Auto-transitioning a risk's status from a verdict — humans decide; the gate is unchanged.
- A general "score" or DoE/ANOVA emission gate (part of aqe's court); this change adopts
  only the verdict + panel-validity core that the experiment validated.

## Capabilities

### New Capabilities

- `adversarial-review`: a deterministic verdict over a host-run adversarial review panel —
  panel-validity rules, distinct-reviewer charge corroboration, the SHIP/REMAND/BLOCK
  computation, the append-only `reviews.jsonl` record, and the `risk-court` skill contract.

### Modified Capabilities

None. The verdict is advisory; the human-principal transition gate and the register
layout are reused, not changed. The review log is a sibling append-only file declared by
this capability, following the precedent set by `trace-results`' `results.jsonl`.

## Impact

Affected code:

- `src/risqlet/review.py` (new) — the deterministic referee (panel validity, corroboration,
  verdict) and the `reviews.jsonl` reader/appender.
- `src/risqlet/cli.py` — a `review` subcommand (compute + record a verdict from a charges file).
- `src/risqlet/validate.py` — recompute recorded verdicts and fail on mismatch.
- `skills/risk-court/` (new) — the host-facing panel skill + a charges JSON schema.
- `tests/` — verdict rules (including the distinct-reviewer corroboration edge that flips
  ship↔remand), panel-validity, validate-recompute, and a small end-to-end.

Behavior: additive and opt-in; no existing command changes behavior. A register with no
reviews behaves exactly as today.

Risk: the value depends on the host actually convening *independent* reviewers — a panel of
identical or colluding reviewers corroborates nothing useful. The skill states the
independence requirement, and the deterministic rules (distinct-reviewer corroboration,
author-excluded) are the enforceable part risqlet owns; genuine reviewer independence is a
host responsibility the skill documents but cannot fully guarantee. The experiment's N was
small (6 decisions, one project), so this ships the *mechanism* with honest scope, not a
claim of universal accuracy.
