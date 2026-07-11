---
name: risk-quickscan
description: >
  Fast, single-pass risk scan of a specific change, diff, or PR — writes
  proposed risks into the .risqlet/ register without running a full session.
  Use during coding when a change looks risky, before merging a nontrivial
  PR, or when asked to "check this change for risks". Requires the risqlet CLI.
---

# Risk quickscan

Scope: **one change** (diff, PR, or named feature) — not the whole product.
You add `proposed` risks to the register and report; you never advance
workflow phase or risk status, and you never record events. Gates belong to
the full `risk-analysis` session.

## Procedure

1. **Scope the change.** Read the diff and the files it touches (callers and
   callees included). Run `risqlet diff --base <merge-base>` first: it lists which
   existing register risks this change already touches, so you extend or
   re-score those instead of writing duplicates. If `.risqlet/` does not exist,
   ask before `risqlet init` — a register is a commitment, not a side effect.

2. **One systematic pass over the changed elements.** For each changed
   element, apply the fitting guideword sets — `risqlet catalog show
   guidewords.flow-deviations` (changed flows/messages),
   `guidewords.data-shapes` (new/changed inputs),
   `guidewords.threat-categories` (anything crossing a trust boundary),
   `guidewords.lifecycle-moments` (migrations, config, deploy changes).
   Add a dependency check: what does this change assume about the things it
   calls, and are those assumptions tested? (`heuristics.dependency-variation`)

3. **Write findings as risks.** Plausible + evidenced ones only, each its own
   `.risqlet/register/R-NNNN.yaml` with `status: proposed`,
   `method: inside-out`, `prompt_ref` naming the guideword or signal, and
   `evidence` citing the actual diff paths. Statement format:
   "Because <condition>, <event> may occur, causing <consequence>". Never
   invent evidence; if a worry has none, say it in the report instead of
   writing it to the register.

4. **Validate and report.** `risqlet validate --json`, then report:
   - new risks (id + one-line statement each),
   - existing register risks this change touches (they may need re-scoring),
   - what you did NOT look at (untouched-but-coupled areas, non-code effects).

## Escalation rule

Recommend a full `risk-analysis` session (and say why) when any of:
- this scan produced **3 or more** plausible risks,
- any candidate looks like **severity 9–10** (safety, legal, irreversible
  data loss, existential trust damage),
- the change touches an area the register has never covered.

Otherwise finish with the report; the proposed risks wait in the register for
the next session's gate.
