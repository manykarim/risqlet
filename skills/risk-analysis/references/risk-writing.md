# Writing risks into the register

One file per risk: `.risqlet/register/R-NNNN.yaml` (next free number, four
digits). Template:

```yaml
schema_version: 1
id: R-0007
statement: Because <condition that exists today>, <event> may occur,
  causing <consequence someone cares about>
aspects: [iso25010.reliability]        # from the selected six
elicited_by:
  method: hazop                        # riskstorming|hazop|stride|premortem|fmea|inside-out|manual
  prompt_ref: "guidewords.flow-deviations:late"
  evidence: ["src/payments/terminal.py", "docs/adr/007-async-ack.md"]
scores: []                             # filled in phase 3
status: proposed                       # ALWAYS proposed when you create it
mitigations: []                        # filled in phase 4
```

## The statement

`Because <condition>, <event> may occur, causing <consequence>.`

- **Condition** — a fact about the product/context, checkable today. If you
  cannot point at where the condition lives, you have a speculation, not a
  condition.
- **Event** — the failure happening, concrete enough to recognize in a log or
  a bug report. "Quality degrades" is not an event.
- **Consequence** — who is hurt and how; this is what severity gets scored on.

Good: "Because the terminal acknowledges asynchronously with a 30s window,
a late confirmation may be recorded as failed while the cardholder was
charged, causing double-charge complaints and books that disagree with the
PSP settlement."
Bad: "Payments might have issues under load." (no condition, no event, no one
hurt).

## Provenance and evidence

- `method` + `prompt_ref`: what elicited it — catalog id
  (`heuristics.premortem`), guideword (`guidewords.data-shapes:huge`), or
  signal (`hotspot:src/sync/`). This makes the register auditable: anyone can
  re-run the question.
- `evidence`: repo paths, ADRs, incident ids, observed behavior. **Real ones.**
  Quote nothing you have not opened. An empty list is allowed but flags the
  risk speculative (`risqlet validate` warns) — say so in your summary and
  either ground it before the gate or recommend dropping it.

## Hygiene

- One risk per file; split "and also" statements.
- Same failure via two elicitation routes = one risk, union of evidence,
  both prompt_refs noted in the statement's history (keep the stronger
  `prompt_ref` in the field).
- Don't pre-filter by your own severity guess during elicitation — capture,
  then let scoring sort. The cap applies to the *selected* set, not to what
  the register may hold.
- Run `risqlet validate --json` after writing a batch; fix findings immediately.
