# Spec delta: agent-skills (add-guardrail-generation)

## ADDED Requirements

### Requirement: skills teach barrier-driven guardrails
The risk-analysis skill SHALL document that a mitigation's `barrier` and its risk's `evidence` drive `risqlet guardrails` (the barrier→surface map, the hard-vs-soft enforcement distinction, and human review before install), and the mitigate-phase guidance SHALL note that choosing `barrier: prevent` vs `detect` has downstream guardrail consequences. Drift guards SHALL resolve the `guardrails` subcommand.

#### Scenario: Guardrails guidance present
- **WHEN** the skill content is read
- **THEN** it covers the barrier→surface mapping, hard vs soft enforcement, and human-gated install

#### Scenario: Subcommand known to drift guard
- **WHEN** the skills drift guards run
- **THEN** `risqlet guardrails` resolves as a CLI subcommand
