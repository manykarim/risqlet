# Elicitation passes

Five divergent passes. Run at least three, independently (finish one raw list
before consulting another). Each pass has a different blind spot; the union is
the value. Marginal cost of an extra pass is low — convergence quality is the
scarce resource, so keep raw lists and merge deliberately.

For every candidate risk, capture provenance while it is fresh:
`method`, `prompt_ref` (what triggered the idea), `evidence` (files/facts from
the context brief). Format details: `risk-writing.md`.

## Pass A — Guideword sweep (systematic)

`method: hazop` · exhaustive by construction; finds the unglamorous risks.

1. List the product's elements from the context brief: flows, interfaces,
   data stores, jobs, integrations.
2. Pick guideword sets by element type — `risqlet catalog show
   guidewords.flow-deviations` for flows/messages,
   `guidewords.threat-categories` for trust-crossing interfaces,
   `guidewords.data-shapes` for inputs, `guidewords.environment-shifts` and
   `guidewords.lifecycle-moments` for operations, `guidewords.scale-shifts`
   for capacity.
3. Cross element × word and ask "how would this happen here, and what would
   it cause?" Note plausible ones only — but decide plausibility from
   evidence, not comfort. `prompt_ref: guidewords.<set>:<word>`.

## Pass B — Pre-mortem (prospective hindsight)

`method: premortem` · finds risks people are too polite or optimistic to name.

`risqlet catalog show heuristics.premortem`. Write 3–5 short failure stories:
"It is six months later; the product failed badly because …" — one story per
selected quality aspect works well. Extract each story's causal chain into
risks. `prompt_ref: heuristics.premortem`.

## Pass C — Persona lenses (perspective diversity)

`method: riskstorming` · finds risks invisible from the builder's chair.

`risqlet catalog show heuristics.persona-switching` and
`guidewords.user-extremes`. Adopt 3–4 deliberately *dissimilar* lenses (e.g.
hostile actor, impaired user, on-call operator, auditor) and re-walk the main
flows from each. Platforms with subagents: one isolated subagent per lens,
merged afterwards, further reduces anchoring. `prompt_ref:
guidewords.user-extremes:<persona>`.

## Pass D — Inside-out (code-anchored)

`method: inside-out` · grounds the register in this codebase, not software in
general.

Start from the repo's own signals: churn hotspots, complex modules, TODO/FIXME
clusters, thin test coverage, error-handling gaps, incident-implicated areas.
For each, ask what failure it invites and which aspect it threatens. This pass
produces the best-evidenced risks — cite paths directly.
`prompt_ref: <the signal>`, e.g. `hotspot:src/payments/`.

## Pass E — Outside-in (catalog match)

`method: riskstorming` · imports the industry's memory of how software fails.

Walk the selected aspects; for each, scan `risqlet catalog list --pack
techniques` and `--pack heuristics` asking "does the failure this entry
guards against apply here?" Consistency-oracle entries
(`heuristics.history-oracle`, `claims-oracle`, `standards-oracle`, …) are
particularly productive: each names a way the product can be *wrong*.
`prompt_ref: <entry id>`.

**Security-heavy products:** enable the opt-in security packs in
`config.catalogs` (`mitre-attack`, `owasp-web`). Sweep the adversary lens with
`mitre-attack.enterprise-tactics` (what an attacker attempts at each stage) and
`mitre-attack.initial-access-review` / `privilege-and-lateral` /
`exfiltration-and-impact`; match web exposure against the `owasp-web.*`
categories (`owasp-web.broken-access-control`, `owasp-web.injection`,
`owasp-web.server-side-request-forgery`, …). Reference them by id in
`prompt_ref` just like any entry;
this pairs naturally with Pass C's hostile-actor persona.

## Convergence

Merge near-duplicates (union of evidence, sharpest statement wins), attach
aspects, drop or mark speculative anything with no evidence, and rank by your
judgment before the human gate. Report per-pass counts — if one pass produced
nothing, say so; it usually means the context brief is thin there.
