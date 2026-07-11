Use the risk-analysis skill (installed in this project's .claude/skills/ — if
it did not auto-load, read .claude/skills/risk-analysis/SKILL.md and its
references/ files and follow them exactly).

This is a RESUMED session. A register already exists in `.risqlet/` from an
earlier session that finished phase 2 (elicit): 5 reviewed risks, 8 proposed.
Start exactly as the skill says: `risqlet status --json`, then continue from the
phase and pending hints it reports. Do NOT re-run earlier phases, do NOT
re-elicit, and treat all recorded decisions as standing.

Complete phases 3, 4, and 5 (score → mitigate → emit).

SIMULATED GATES — read carefully. I am human:many. This is a scripted headless
run, so I pre-authorize the gate decisions below; every event you record MUST
carry `"note": "simulated-gate: scripted confirmation"`:

1. Scoring gate (phase 3): score ONLY the 5 reviewed risks (rubric anchors per
   factor per the skill; then `risqlet score --all`). I accept your scores as
   proposed — record reviewed→accepted for all 5, with the simulated-gate note,
   plus the elicit→score phase event when you enter phase 3.
2. Mitigation gate (phase 4): for each accepted risk, add 1-2 mitigations
   (treatment/lever/barrier, concrete action, honest residual_note, test
   charters in tests[]). I accept them — record accepted→mitigating for all 5
   and the score→mitigate phase event, same note.
3. Emit (phase 5): record mitigate→emit, export strategy-md to
   .risqlet/strategy.md and trace-matrix-csv to .risqlet/trace-matrix.csv.

Rules for this run:
- The `risqlet` CLI is on PATH. Never compute derived priorities yourself.
- Leave the 8 proposed risks untouched.
- Do not modify any file outside `.risqlet/`.
- Finish with `risqlet status --json` and `risqlet validate --json` outputs plus a
  short summary (scores table with anchors, mitigations per risk, the
  strategy's "What this does not cover" section verbatim) in your final answer.
