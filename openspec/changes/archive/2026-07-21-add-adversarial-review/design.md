## Context

risqlet gates decisions structurally (`validate`: schema + replayable human events +
speculative flags; `check`: coverage CI gate). None of these can see that a
schema-valid decision is *semantically* wrong. Measured on `robotframework-javaui`:
six decisions `validate` passed, three subtly weak (hollow mitigation test,
evidence-mismatch, under-scored critical defect). `validate` caught 0/3; an adversarial
panel resolved by a deterministic verdict caught 3/3, and flagged a fourth "sound"
decision that rested on mistaking dead Rust code for the live attach path.

The source pattern is agentic-qe's "QE Court" (MIT). Its own architecture already
matches risqlet: the reviewers run in a host Skill; the SHIP/REMAND/BLOCK resolution is
pure deterministic rules (`referee.ts`: "No I/O, no LLM calls; the orchestration lives
in the skill; the RULES live here"). This change reimplements the verdict core from that
behavior — no code copied — and wires it into risqlet's file-native, human-gated model.

## Goals / Non-Goals

**Goals:**

- A deterministic, test-owned verdict over an independent review panel's charges.
- Framework-provider: host runs the panel; risqlet computes arithmetic and records.
- Advisory + human-gated: the verdict informs, a human decides; no auto-transition.
- Repo-native and auditable: charges + verdict in an append-only file; recomputable by `validate`.
- Ship the mechanism with honest scope, not a claim of universal accuracy.

**Non-Goals:**

- risqlet calling any model or convening the panel.
- Auto-changing a risk's status from a verdict.
- aqe's score-emission / DoE-ANOVA gate — out of scope; only the validated verdict core.
- Guaranteeing reviewer independence (a host property the skill documents, not enforceable in risqlet).

## Decisions

### 1. Corroboration requires DISTINCT reviewers — the load-bearing rule

The experiment ran the referee two ways. A naive rule that counts a *category's charge
volume* (so one reviewer filing two objections "corroborates" itself) flagged all six
decisions — a rubber-stamp REMAND machine with no discriminating value. Requiring a
category to be raised by **≥2 distinct reviewers** flipped the result: the genuinely
sound decisions SHIP, only the weak ones REMAND/BLOCK. This single rule is the
difference between the gate being useful and being noise.

That fragility is the core argument for **risqlet owning the verdict** rather than
leaving it to the host: it is exactly the kind of subtle deterministic rule that must be
specified and test-pinned, and exactly what risqlet exists to own (arithmetic and gates,
not semantics).

### 2. Severity ladder: BLOCK / REMAND / SHIP

- **BLOCK**: a surviving category carries a `fatal` — a reproduced, corroborated
  showstopper (e.g. two reviewers independently confirm the mitigation test is hollow).
- **REMAND**: a surviving `major`, *or* a single reproducible `fatal` with no
  corroboration. A lone fatal is deliberately REMAND, not BLOCK (one reviewer may be
  right but unconfirmed) and not SHIP (a credible fatal must not pass silently) — this
  is the rule that correctly caught the dead-code decision the panel wasn't unanimous on.
- **SHIP**: nothing survives and no lone fatal — the decision stands.

`minor` charges never move the verdict; they are advisory notes carried in the record.

### 3. Advisory, not authoritative — the human gate is unchanged

The verdict is recorded, not enacted. A BLOCK on an `accepted` risk does not un-accept
it; it records that the panel found a corroborated fatal, and a human then decides
whether to rework and records that transition through the existing human-principal
event gate. This keeps the single source of lifecycle authority (a `human:` event) and
avoids a second, competing state machine. It also means the feature is safe to adopt
incrementally: a register that never runs `review` is unaffected.

### 4. Charges are the host↔risqlet interface

The contract between the semantic half (host) and the arithmetic half (risqlet) is a
JSON charges document: a list of `{reviewer, category, severity, reproducible, claim}`
for a named decision. The host's `risk-court` skill produces it; `risqlet review`
consumes it. This is the same shape as risqlet's other framework-provider seams (the
host produces semantics as structured data; risqlet computes over it) and keeps risqlet
free of any model dependency. `reproducible=false` charges are recorded but excluded
from the verdict, so a reviewer can voice a suspicion without it counting as evidence.

### 5. reviews.jsonl, following the trace-results precedent

The verdict + inputs append to `.risqlet/reviews.jsonl`. `trace-results` already
established that a capability may add its own append-only sibling log alongside
`events.jsonl`/`results.jsonl` without modifying `risk-register`'s layout. `validate`
recomputes recorded verdicts from their charges and fails on mismatch — the same
integrity treatment ensemble `disagreement` gets — so a hand-edited verdict is caught.

### 6. Clean-room provenance

agentic-qe is MIT, so inspiration is permitted, but risqlet must not ingest its source.
The verdict rules here are specified from *observed behavior* (the referee's
resolveVerdict/validatePanel semantics, described in this change's proposal and spec),
not transcribed from `referee.ts`. The spec's scenarios are the independent
derivation trail.

## Risks / Trade-offs

- **Value depends on genuine reviewer independence.** A panel of near-identical reviewers
  corroborates nothing useful, or corroborates wrongly. → risqlet enforces the
  *mechanical* independence it can (≥2 distinct reviewers, author excluded); the skill
  documents the rest. Honest framing: risqlet owns the verdict's correctness, not the
  panel's quality.
- **Small evidence base.** 6 decisions, one project. → Ship the mechanism, spec the rules
  precisely, and let real use accrue evidence; do not oversell accuracy in docs.
- **Cost is host-borne.** Convening N reviewers per decision is real token cost for the
  host. → This is a *targeted* gate (review a high-stakes accept / phase sign-off), not a
  blanket pass over every risk; the skill frames it that way.
- **A second gate could confuse authority.** → Mitigated by keeping the verdict strictly
  advisory; the human-principal event remains the only thing that moves lifecycle state.

## Migration Plan

Additive and opt-in; no migration. `reviews.jsonl` is created on first `review`. Existing
registers and commands are unaffected. Rollback is removing the command/skill; recorded
reviews are inert data.

## Open Questions

- Should a BLOCK verdict *warn* (non-zero exit) when the reviewed risk is already in a
  gated status (accepted/mitigating), to surface it in CI, while still not transitioning?
  Leaning yes — a recorded-but-invisible BLOCK is weak; but it must stay advisory.
- What decision granularity does `review` target — a single risk, a mitigation, or a whole
  phase sign-off? Start with a single risk/mitigation (matches the experiment); a
  phase-level panel can follow.
- Should `validate` treat an unaddressed BLOCK (recorded, but the risk still accepted with
  no subsequent human rework event) as a warning? Deferred; it edges toward enacting the
  verdict, which decision 3 avoids.
