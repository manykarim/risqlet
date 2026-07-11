# Phase protocol

State machine: `context → aspects → elicit → score → mitigate → emit`
(backward moves allowed). The current phase lives in `.risqlet/config.yaml`;
every change of it — and every risk status change — is an event in
`.risqlet/events.jsonl`.

## Recording events (only after explicit human confirmation)

Append one JSON line per transition. Get the human's name once at session
start and reuse it as the principal.

```json
{"ts":"<ISO-8601 UTC>","type":"phase_change","from":"context","to":"aspects","principal":"human:<name>","note":"<why>"}
{"ts":"<ISO-8601 UTC>","type":"status_change","risk":"R-0007","from":"proposed","to":"reviewed","principal":"human:<name>","note":"<decision context>"}
```

Legal status transitions: proposed→reviewed, reviewed→accepted,
accepted→mitigating, mitigating→closed, proposed/reviewed→rejected.
After appending, update the risk file's `status` field to match, then
`risqlet validate` — it replays events and fails on any divergence.

The confirmation script is always the same: state what you propose to record,
ask "Shall I record this decision in your name?", wait for a yes, then write.
If the human is absent, stop at the gate and leave everything `proposed`.

## Resuming a session

`risqlet status --json` first, always. It reports the current phase, counts,
top risks, and `pending` hints (e.g. "5 reviewed risks await scoring") — that
list is your work queue, in order, before anything new. Rules:

- Recorded decisions stand. Do not re-elicit aspects that are selected, do not
  re-run gates whose events exist, do not ask the human to re-confirm them.
- Re-read the current phase's entry criteria below, then continue from there.
- If `status` reports unparseable files or `risqlet validate` fails, repair the
  register first — with the human for anything beyond mechanical fixes.

## Phase 0 — CONTEXT

Entry: register exists (`risqlet init` if not).
Do: read product docs, ADRs/architecture, incident reports/postmortems, test
layout and coverage signals, recent git history (churn hotspots), dependency
manifest. Write a **context brief** (~1 page) into the conversation: elements,
dataflows, external dependencies, incident themes, weak-coverage areas.
Exit: human corrects/confirms the brief. This brief is the evidence base —
phase 2 risks cite the files and facts collected here.

## Phase 1 — ASPECTS

Entry: confirmed context brief.
Do: `risqlet catalog list --pack iso25010`; propose 8–10 candidates, each with
a one-sentence rationale grounded in the brief (not generic praise of
quality). The human negotiates the final ranked set — **at most 6**. Fewer is
fine; forced choice is the point.
Write to `config.yaml`:

```yaml
aspects:
  - {id: iso25010.reliability, rank: 1, rationale: "<product-specific>"}
```

Exit: human confirms → record phase event → `risqlet validate`.

## Phase 2 — ELICIT

Entry: aspects locked.
Do: run ≥3 divergent passes (see `elicitation.md`) *independently* — complete
one pass's raw list before reading another's output, to limit anchoring.
Write every candidate as its own file `.risqlet/register/R-NNNN.yaml`
(`status: proposed`; next free number; format in `risk-writing.md`).
Then converge: cluster near-duplicates (merge files, keep the union of
evidence and the strongest statement), map each risk to the selected aspects,
and mark evidence-free ones speculative in your summary.
Exit gate: present clusters ranked by your judgment; the human selects/edits
the top set (respect `constraints.max_top_risks`). Record `proposed→reviewed`
events for the selected risks (one confirmation for the batch is fine —
list the ids). Non-selected risks stay `proposed` (they remain in the
register; that is a feature). `risqlet validate`.

## Phase 3 — SCORE

Entry: reviewed top risks.
Do per risk: propose factor values under the active policy with one rubric
anchor per factor (`scoring-rubrics.md`), citing evidence where it exists
("det8: no automated check exists — see coverage gap in context brief").
Genuinely uncertain? Present two defensible scorings and ask.
Then:

```bash
risqlet score --all
risqlet validate --json
```

Report computed priorities. Exit: human resolves contested scores; record
`reviewed→accepted` for risks the human accepts into the working set.

## Phase 4 — MITIGATE

Entry: accepted risks.
Do per risk: find candidate techniques (`risqlet catalog search <terms>`, then
`risqlet catalog show <id>` and judge fit yourself); write mitigations per
`mitigation.md` — treatment, lever, barrier, concrete action, residual note,
test charters in `tests[]`. Every accepted risk gets ≥1 mitigation or an
explicit human-confirmed `accept` treatment.
Exit: human accepts mitigations (batch confirmation OK); record
`accepted→mitigating` for risks with agreed actions. `risqlet validate`.

## Phase 5 — EMIT

```bash
risqlet export --fmt strategy-md -o .risqlet/strategy.md
risqlet export --fmt trace-matrix-csv -o .risqlet/trace-matrix.csv
risqlet validate
```

Present the strategy; read "What this does not cover" aloud rather than
summarizing it away. Suggest concrete next triggers for re-assessment
(feature X lands, incident, dependency major bump). Record the final phase
event. Commit `.risqlet/` if the human wants the register versioned (they
should — it is designed for git).
