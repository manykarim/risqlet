---
name: risk-court
description: >
  Adversarial review of a high-stakes risk/mitigation decision: convene an
  independent panel to challenge it against the actual code, then let the risqlet
  CLI produce a deterministic SHIP/REMAND/BLOCK verdict. Use before accepting a
  significant risk, signing off a mitigation as covering, or a phase gate — when
  a decision is schema-valid but you want it stress-tested. Requires the risqlet CLI.
---

# Risk court — adversarial review

`risqlet validate` checks structure; it cannot see that a *schema-valid* decision is
semantically wrong — a risk accepted on a hollow mitigation test, evidence that points
at an unrelated file, a critical defect scored low. This skill stress-tests one such
decision with an independent panel. **You run the panel; the verdict is computed
deterministically with no model call. A human makes the final call — it is advisory.**

Use it sparingly and deliberately: reviewing costs a panel of reviewers, so reserve it
for high-stakes decisions (accepting a significant risk, signing off a mitigation,
a phase gate), not every `proposed` risk.

## Procedure

1. **Name the decision and its author.** One risk/mitigation decision (e.g. "R-0003
   accepted; mitigation M-0001 covers it; priority LOW"), and the id of whoever made
   it (`author`). The author must NOT sit on the panel.

2. **Convene an independent panel — at least two reviewers.** They must be independent
   of the author and of each other; ideally different perspectives or different model
   vendors. The verdict's corroboration rule is meaningful *only* for independent
   charges — a panel that just agrees with itself proves nothing. Give each reviewer a
   distinct lens, e.g.:
   - **correctness** — does the decision reflect what the cited code actually does?
   - **evidence** — is the evidence real and sufficient, and is any mitigation *test*
     genuine (not hollow/tautological/unrelated)?
   - **priority** — is the score/status justified by the code and impact, or rubber-stamped?

3. **Each reviewer files charges against the ACTUAL code**, not the decision's prose.
   A charge is grounded (`reproducible: true`) only if the reviewer verified it against
   the real file/evidence; a hunch is `reproducible: false` and will not count. A sound
   decision should draw zero reproducible charges — do not pile on.

4. **Emit one charges JSON** (schema in `charges.schema.json`):

   ```json
   {
     "decision": "R-0003",
     "author": "agent:writer",
     "reviews": [
       {"reviewer": "reviewer-a", "charges": [
         {"category": "hollow-mitigation-test", "severity": "fatal",
          "reproducible": true, "claim": "the referenced test asserts x == x"}]},
       {"reviewer": "reviewer-b", "charges": [
         {"category": "hollow-mitigation-test", "severity": "fatal",
          "reproducible": true, "claim": "confirmed: it passes on any input"}]}
     ]
   }
   ```

   `category` is a short slug; `severity` is `fatal`, `major`, or `minor`.

5. **Compute the verdict:** `risqlet review --charges charges.json`. The command
   validates the panel (≥2 distinct reviewers, author excluded) and applies fixed rules:
   a category *survives* only when ≥2 **distinct** reviewers each file a reproducible
   charge in it.
   - **BLOCK** — a surviving category carries a `fatal` (a corroborated showstopper).
   - **REMAND** — a surviving `major`, or a single uncorroborated reproducible `fatal`.
   - **SHIP** — nothing survives.

   The verdict and its charges are appended to `.risqlet/reviews.jsonl`; exit code is
   0 for SHIP, 1 for REMAND/BLOCK (a CI signal, not a state change).

6. **A human decides.** The verdict recommends; it changes nothing. On REMAND/BLOCK, a
   human decides whether to rework, and records any status change through the normal
   human-principal event gate — exactly as without this skill.

## Boundaries

- The tool never convenes the panel or calls a model — that is your job. It only
  validates the panel and computes the verdict.
- The verdict is advisory. It does not transition any risk; only a `human:` event does.
- Reviewer independence is your responsibility. The tool enforces the mechanical part
  (distinct reviewers, author excluded); genuine independence it cannot check.
