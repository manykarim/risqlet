Use the risk-analysis skill's continuous-reassessment guidance
(.claude/skills/risk-analysis/references/continuous.md — read it).

A risk register already exists in `.risqlet/` (from an earlier ensemble session:
security + order-flow risks citing real order/approval/tenant code paths).
This is a re-assessment demo against the repo's REAL recent commits. Make NO
code changes and record NO events — `risqlet diff` and `risqlet check` are
read-only.

Steps:

1. `git log --oneline -6` to see the recent commits (they touch the
   order/approval workflow). Pick a base a few commits back (e.g. HEAD~3).

2. `risqlet diff --base HEAD~3 --json` — report which register risks the recent
   changes touch, with the match reasons and confidence, and the
   suggested action per risk. Also note the untouched-high-priority reminder.

3. `risqlet check --base HEAD~3 --json` — report the gate outcome (mode, flagged
   risks, exit). The default gate mode is warn.

4. Demonstrate the path filter: set `constraints.ci_paths` in
   `.risqlet/config.yaml` to a glob that EXCLUDES most changed files (e.g.
   `["nonexistent/**"]`), re-run `risqlet check --base HEAD~3 --json`, and show
   that excluded_paths rose and nothing is flagged. Then restore ci_paths to
   empty (all paths). This edits only `.risqlet/config.yaml`.

5. `risqlet validate --json` — must still pass (diff/check are read-only;
   ci config fields don't affect validation).

Rules: `risqlet` on PATH; only `.risqlet/config.yaml` may be touched (for the
filter demo); no code, no register risk edits, no events. Finish with the
`risqlet diff` and both `risqlet check` (unfiltered + filtered) JSON outputs and a
short narrative of which real commits touched which risks in your final answer.
