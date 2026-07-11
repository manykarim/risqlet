# Ensemble protocol: separate, then together

Independent generation followed by deliberate convergence outperforms both
lone-pass analysis and everyone-in-one-conversation brainstorming — and
deliberately *dissimilar* perspectives find more than redundant similar ones.
This file makes that mechanical.

## Separate: run passes independently

- Complete each elicitation pass (see `elicitation.md`) and **write its risks
  to the register before reading any other pass's output**. Anchoring is the
  enemy; the order you run passes in should not shape what they find.
- Choose lenses far apart: hostile actor + impaired user + on-call operator
  beats three flavors of tester. Record the lens in `prompt_ref` and, for
  scoring, in `scored_by`.
- On platforms with subagents (e.g. Claude Code), run one isolated subagent
  per pass or persona. Give each: the phase-2 rules from `risk-writing.md`,
  its single lens, and instructions to write `proposed` risk files directly.
  Isolation is the point — no shared conversation, no peeking. The main agent
  merges afterwards. (Sequential independent passes by one agent are the
  portable fallback and still work.)

## Together: converge deterministically, decide humanly

1. `risqlet dedupe --json` — deterministic clustering by statement/aspect/
   evidence overlap. It **proposes**; it never merges.
2. Judge each cluster yourself: same failure found twice → merge; related but
   distinct failures → keep both (mention the relation in the statements).
   Token overlap is not meaning — you are the semantic layer.
3. `risqlet merge <survivor> <duplicates...>` executes agreed merges: evidence
   and mitigations union into the survivor, provenance preserved under
   `merged_from`. Only `proposed` risks can be merged away — a reviewed risk
   embodies a human decision and stays.
4. Report per-pass counts and merge decisions at the phase-2 gate.

## Independent scoring (phase 3)

For contested or high-stakes risks, score twice from different lenses: two
score sets under the active policy, distinct `scored_by`, anchors written
independently. Then `risqlet score --all` computes a `disagreement` value
(0–1 normalized spread). **Never average the sets or pick one silently** —
disagreement above ~0.25 appears in `risqlet status` as a pending gate item;
present both readings and their anchors to the human, record the resolution
(keep one set, or re-anchor and rescore).
