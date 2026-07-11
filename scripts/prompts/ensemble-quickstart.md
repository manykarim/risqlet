Use the risk-analysis skill (installed in this project's .claude/skills/ — if
it did not auto-load, read .claude/skills/risk-analysis/SKILL.md and its
references/ files, especially references/ensemble.md, and follow them exactly).

Run an ABBREVIATED ENSEMBLE session: phases 0, 1, and 2 only, with the
separate-then-together protocol. Stop after the phase-2 gate.

Phase 2 must use EXACTLY TWO independent passes, in this order, writing each
pass's risks to the register COMPLETELY before starting the other:

- Pass A — hostile-actor persona (`guidewords.user-extremes:hostile` +
  `guidewords.threat-categories`): walk the order/approval/payment flows as an
  attacker or malicious staff member.
- Pass B — flow-deviations guideword sweep (`guidewords.flow-deviations`) over
  the order lifecycle: stage transitions, approvals, production board
  drag-and-drop, reverts (the recent commits touch exactly these).

Then converge: run `risqlet dedupe --json`, judge each cluster yourself (same
failure twice = merge with `risqlet merge`; related-but-distinct = keep both),
and report cluster count and merge decisions.

SIMULATED GATES — I am human:many; scripted headless run; every event you
record MUST carry `"note": "simulated-gate: scripted confirmation"`:

1. Aspects gate: I confirm your top-ranked proposal, capped at 5 aspects
   (record context→aspects, aspects→elicit phase events).
2. Top-risk gate (after dedupe/merge): I confirm your top 5 by your own
   ranking — record proposed→reviewed for exactly those; the rest stay
   proposed.

Rules:
- `risqlet` is on PATH; `risqlet init` first (pre-authorized). Register created
  fresh; leave no files outside `.risqlet/` modified.
- Evidence must be real files you opened; cite paths precisely.
- Finish with `risqlet status --json`, `risqlet validate --json`, and
  `risqlet dedupe --json` outputs plus per-pass risk counts and your merge
  rationale in the final answer.
