Use the risk-analysis skill (installed in this project's .claude/skills/ — if
it did not auto-load, read .claude/skills/risk-analysis/SKILL.md and its
references/ files and follow them exactly).

Run an ABBREVIATED session: phases 0, 1, and 2 only (context → aspects →
elicit). Stop after the phase-2 gate; do not score or mitigate.

SIMULATED GATES — read carefully. I am human:many. This is a scripted headless
run, so I pre-authorize the gate decisions as follows, and every event you
record MUST carry `"note": "simulated-gate: scripted confirmation"` so the
audit trail is honest about it:

1. Aspects gate: I confirm your top-ranked proposal, capped at 5 aspects.
   Record the phase_change events (context→aspects, aspects→elicit) with
   principal "human:many" and the simulated-gate note.
2. Top-risk gate: I confirm your top 5 risks by your own ranking. Record
   proposed→reviewed status_change events for exactly those risks, same
   principal and note. Leave all other risks proposed.

Rules for this run:
- The `risqlet` CLI is on PATH; run `risqlet init` first (pre-authorized).
- Phase 0: read real project documentation and code; write the context brief
  into your final answer. Evidence cited on risks must be files you opened.
- Phase 2: run at least three elicitation passes per the skill (guideword
  sweep, pre-mortem, inside-out) and record per-pass counts.
- Do not modify any file outside `.risqlet/`.
- Finish with `risqlet validate --json` and `risqlet export --fmt register-yaml`,
  and include the validate JSON, per-pass counts, and your top-5 rationale in
  the final answer.
