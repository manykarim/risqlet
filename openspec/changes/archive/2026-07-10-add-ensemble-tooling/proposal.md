# Proposal: add-ensemble-tooling

## Why

The research evidence (separate-then-together beats both pure-independent and pure-joint; dissimilar personas measurably increase idea diversity) is encoded only as prose in the skills. The convergence half — deduplicating divergent passes and surfacing scoring disagreement — is exactly the work the framework's own principle assigns to deterministic code, and it is the largest unimplemented piece of the original design (Stage 2). Without it, multi-pass elicitation produces duplicate clutter and ensemble scores get averaged away in conversation.

## What Changes

- New `qrisk dedupe [--json]`: deterministic near-duplicate clustering (statement-token Jaccard + shared aspects + shared evidence, configurable threshold) with a suggested survivor per cluster — proposal only, never auto-merges.
- New `qrisk merge <survivor> <duplicate...>`: mechanical merge (evidence/aspect union, mitigation move with `risk_ids` rewrite, `merged_from` note, duplicate file removal); only `proposed` risks may be merged away.
- Ensemble scoring: `qrisk score` computes a risk-level `disagreement` field (0–1 normalized factor spread) when 2+ score sets exist for the active policy; `validate` recomputes it (engine-owned); `status` hints when contested scores await a gate.
- New skill reference `ensemble.md`: separate-then-together protocol, dissimilar-persona guidance, Claude Code subagent recipe, independent-scoring recipe; wired into SKILL.md phases 2–3.
- Dogfooding on the new target tshirt-shop-om: two-pass independent elicitation → dedupe → merge → simulated gate, metrics collected, findings appended to the report.

## Capabilities

### New Capabilities

- `ensemble-tooling`: dedupe clustering semantics, merge mechanics and refusals, and the disagreement computation.

### Modified Capabilities

- `session-status`: pending hints gain the contested-scores rule.
- `agent-skills`: the risk-analysis skill gains the ensemble protocol reference.

## Impact

- New `src/qrisk/ensemble.py` (similarity, clustering, merge), `score`/`validate`/`status` extensions, `Risk.disagreement` optional field (schema regenerated), CLI wiring, `skills/risk-analysis/references/ensemble.md`, dogfood prompt + experiment artifacts for tshirt-shop-om.
- Register format: one new optional engine-owned field (`disagreement`) — backward compatible (open-world).
