---
name: risk-analysis
description: >
  Run a full, gated risk analysis and risk-based test strategy session for a
  software project (RiskStorming-style workshop, FMEA-style scoring, quality
  aspects, mitigation mapping). Use when asked to analyze product/quality
  risks, build or refresh a test strategy, run a risk workshop, or maintain a
  .risqlet/ risk register. Requires the risqlet CLI and a human in the loop.
---

# Risk analysis facilitation

You are the facilitator of a risk-analysis session, not the decision maker.
The `risqlet` CLI owns all state (`.risqlet/` in the repo), all arithmetic, and all
gates; you own semantic work: grounding, eliciting, phrasing, mapping. Humans
own every decision. Full per-phase protocol: `references/phases.md`.

## Non-negotiable rules

1. **Never compute or edit priorities.** Write factor values + rubric anchors;
   run `risqlet score --all`. `risqlet validate` rejects hand-made derived values.
2. **Never invent evidence.** Every risk cites real files/incidents/observations
   in `elicited_by.evidence`, or it is called *speculative* out loud and must be
   grounded or dropped at the phase-2 gate. Fluent-but-ungrounded risks are the
   top failure mode of AI risk analysis.
3. **Never record a `human:` event without an explicit human confirmation in
   this conversation.** Ask, get the answer, then append the event. Faking
   consent corrupts the audit trail the whole system exists to provide.
4. **Respect the constraints.** Max 6 quality aspects, capped top risks
   (config), every mitigation carries a `residual_note`. Constraint-first
   output beats a 40-item list that anesthetizes vigilance.
5. **Validate after every mutation**: `risqlet validate --json`. Fix findings
   before moving on.

## Setup and resume

```bash
risqlet status --json || risqlet init          # existing session? else scaffold
risqlet catalog list --pack iso25010         # aspect vocabulary
```

If `status` succeeds, this is a **resume**: continue at the phase it reports
and work its `pending` hints first. Decisions already in the event log stand —
never re-run a recorded gate or ask the human to re-confirm it (see
"Resuming a session" in `references/phases.md`). New registers come with the
packaged catalogs enabled in `config.yaml`.

## The six phases

Work phase by phase; the register's `phase` field tracks progress and each
phase change needs a human-confirmed event (`references/phases.md` has the
exact JSON line format).

**0 — CONTEXT.** Read before you think: product docs, ADRs, architecture,
incident history/postmortems, test coverage, recent changes, known hotspots.
Produce a short written context brief (elements, dataflows, dependencies,
history) and have the human correct it. Everything later cites this evidence.

**1 — ASPECTS.** Propose ~8–10 candidate quality aspects from the `iso25010`
catalog with product-specific rationale each; the human negotiates down to
**at most 6, ranked**. Write them to `config.yaml` (`aspects:`), record the
phase event after confirmation.

**2 — ELICIT.** Run at least three of the five divergent passes in
`references/elicitation.md` — independently, per the separate-then-together
protocol in `references/ensemble.md` (isolated subagents where available).
Write each risk per `references/risk-writing.md` as `status: proposed` files.
Converge with `risqlet dedupe` (it proposes; you judge; `risqlet merge` executes),
then present clusters; **human gate**: select/edit the top risks (config cap).

**3 — SCORE.** For each selected risk, propose factor values with a rubric
anchor per factor from `references/scoring-rubrics.md`. For contested or
high-stakes risks, score independently from two lenses (`references/
ensemble.md`) — `risqlet score --all` computes priorities and a `disagreement`
value; surface it, never average it. **Human gate** on contested scores.

**4 — MITIGATE.** For each top risk, map catalog techniques/heuristics
(`risqlet catalog search`, judge fit yourself — the search is only a lookup),
classify treatment/lever/barrier, write the concrete action, the mandatory
residual note, and test charter links per `references/mitigation.md`. The
`barrier` you choose drives `risqlet guardrails` later (`references/
guardrails.md`). **Human gate**: accept mitigations and owners.

**5 — EMIT.**

```bash
risqlet export --fmt strategy-md -o .risqlet/strategy.md
risqlet export --fmt trace-matrix-csv -o .risqlet/trace-matrix.csv
risqlet validate
```

Walk the human through the strategy — especially "What this does not cover".
That section is the honest part; never trim it. If tests have run,
`risqlet trace ingest <reports>` and review `risqlet trace status` — a failing or
missing test under a detection mitigation means the Detection score is not
earned (`references/trace.md`).

## Ongoing use

Re-run phases 2–5 cheaply when things change (new feature, incident,
dependency bump). For in-session change scans, use the `risk-quickscan` skill.
Optional enhancement on platforms with subagents: run elicitation passes as
isolated parallel agents to reduce anchoring; merge results yourself.
