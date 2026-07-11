Use the risk-quickscan skill (installed in this project's .claude/skills/ —
if it did not auto-load, read .claude/skills/risk-quickscan/SKILL.md and
follow it exactly).

Scope: the most recent substantive changes in this repository. Determine them
with `git log --oneline -15` and `git diff HEAD~5 --stat` (adjust the range to
capture a meaningful recent change set; if the repo has no usable recent diff,
scan the core module of the codebase instead and say so).

Rules for this run:
- The `risqlet` CLI is on PATH. A register does not exist yet: run `risqlet init`
  (this run is pre-authorized to create it).
- Follow the skill: guideword-set passes over the changed elements, plus the
  dependency check.
- Write only well-evidenced `proposed` risks; cite real file paths you actually
  opened in `elicited_by.evidence`. Do not change any file outside `.risqlet/`.
- Finish with `risqlet validate --json` and include its full JSON output plus
  your report (new risks, touched areas, what you did not look at, escalation
  recommendation) in your final answer.
