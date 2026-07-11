# Design: add-ensemble-tooling

## Context

Queue item 2. The elicitation skills already produce multi-pass output; nothing converges it deterministically. Constraints: offline and dependency-light (no embeddings — token methods only, upgrade path documented), divergence-to-LLM/convergence-to-code, gates preserved (merging away a reviewed risk would erase a human decision).

## Goals / Non-Goals

**Goals:** deterministic duplicate clustering with actionable proposals; safe mechanical merges; disagreement as a first-class, engine-owned number; the ensemble protocol teachable and dogfooded on a fresh target (tshirt-shop-om).

**Non-Goals:** embeddings/semantic similarity (future pack-in), automated subagent spawning (recipe text only — platform-specific), MCP tool additions (CLI-first; MCP parity can follow demand), auto-merge of anything.

## Decisions

### D1. Similarity and clustering (`src/qrisk/ensemble.py`)

Pairwise score = `0.6 * jaccard(statement_tokens) + 0.2 * jaccard(aspects) + 0.2 * jaccard(evidence_paths)` where statement tokens are lowercased, punctuation-stripped, stopword-filtered (small built-in list), and evidence paths are annotation-stripped (reuse the harness's normalization, moved into ensemble.py). Clusters = connected components over pairs ≥ threshold (`constraints.dedupe_threshold`, default 0.5; read via open-world config, no schema change needed — Constraints model gains the optional field). Survivor suggestion: most evidence items → longest statement → lowest id. Deterministic ordering everywhere (sorted ids). Output: human table or `--json {clusters: [{score_matrix, members, suggested_survivor}]}`. Exit 0 always (report, not gate).

### D2. Merge mechanics (`qrisk merge`)

Refusals first: survivor must exist and be non-terminal; every duplicate must exist and be `proposed` (erasing reviewed+ risks would erase recorded human decisions — those go through `record_decision`/manual edits with events). Mechanics: evidence = ordered union; aspects = ordered union; duplicates' mitigations appended to survivor with `risk_ids` rewritten (duplicate id → survivor id in each moved mitigation; other ids kept); `merged_from` list appended on survivor (`[{id, prompt_ref, method}]` — open-world extra, documented); duplicate files deleted. Mitigation id collisions cannot occur (ids are globally allocated). Post-merge the CLI prints a reminder to run `qrisk validate`. All writes ruamel round-trip.

### D3. Disagreement (engine-owned, like `derived`)

`Risk.disagreement: dict | None` (new optional model field; schemas regenerated). Computed by `qrisk score` when ≥2 score sets exist for the active policy **and** all of them pass value/anchor checks: per factor `spread = (max - min) / (factor_max - factor_min)`; `value = round(mean(spreads), 2)`. Written as `{policy, value, factors: {name: spread}}`; removed (set to None) when <2 score sets remain. `validate` recomputes and errors on mismatch (same pattern as derived). `status`: pending hint when any risk with status proposed/reviewed/accepted has `disagreement.value > 0.25` — "N risk(s) have contested scores (disagreement > 0.25): ids — resolve at the gate". Threshold fixed (not configurable) until field use shows need.

### D4. Skill: `references/ensemble.md`

Sections: why separate-then-together (one line of evidence citation); running passes independently (finish and write each pass before reading others; on Claude Code optionally one subagent per pass/persona with instructions to write risks directly with distinct `prompt_ref`/`scored_by`, main agent merges); convergence recipe (`qrisk dedupe` → judge clusters — the tool proposes, you decide → `qrisk merge` true duplicates only → distinct-but-related risks stay separate with cross-references in statements); independent scoring (2+ score sets from different lenses, `scored_by` distinct, never average — `qrisk score` computes disagreement, contested scores go to the human). SKILL.md phase 2/3 bullets get one-line pointers; budget raised to 210 lines in the drift guard if the edit needs it.

### D5. Dogfood: ensemble-lite on tshirt-shop-om

New prompt `ensemble-quickstart.md`: phases 0–2 with exactly two passes written independently (pass A: hostile-actor persona via `guidewords.user-extremes:hostile`; pass B: `guidewords.flow-deviations` sweep over the order/approval flows — the repo's recent commits touch approval gating), then `qrisk dedupe --json`, merge only true duplicates, simulated gate (pre-authorized top-5), finish with status+validate+dedupe outputs in the answer. Metrics: standard set + cluster count + merges performed. Harness unchanged (F7 fix already in).

## Risks / Trade-offs

- [Token Jaccard misses paraphrase duplicates] → acknowledged; threshold errs low-recall/high-precision (0.5) so false merges are unlikely and misses just leave near-dupes for the human gate; embeddings noted as upgrade.
- [Two agents write the same risk id concurrently in subagent recipe] → recipe instructs per-pass id ranges OR sequential writes by the main agent; file-per-risk makes collisions visible as identical filenames.
- [`merged_from` as open-world extra triggers unknown-field warnings] → add it to the Risk model as optional known field instead (cleaner than a warning per merge).
- [Disagreement on mixed-policy score sets] → computed only over sets matching the active policy; others ignored.

## Migration Plan

Additive; existing registers gain nothing until dedupe/merge/ensemble scoring is used.

## Open Questions

- MCP parity for dedupe/merge — revisit after tshirt-shop-om run (noted for queue item 4).
