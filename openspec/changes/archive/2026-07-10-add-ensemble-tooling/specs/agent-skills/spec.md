# Spec delta: agent-skills (add-ensemble-tooling)

## ADDED Requirements

### Requirement: risk-analysis skill teaches the ensemble protocol
The risk-analysis skill SHALL include an ensemble reference covering: independent pass/persona execution (write before cross-reading; dissimilar personas), deterministic convergence via `qrisk dedupe` with merge decisions kept with agent+human (`qrisk merge` for true duplicates only), an optional isolated-subagent recipe for platforms that support it, and independent multi-scoring where disagreement is surfaced rather than averaged. Drift guards (catalog ids, CLI commands, line budgets) SHALL keep passing.

#### Scenario: Ensemble reference present
- **WHEN** the skill content is read
- **THEN** it covers independent passes, dedupe-then-decide convergence, and disagreement-not-averaging

#### Scenario: New commands known
- **WHEN** the drift guards run
- **THEN** `qrisk dedupe` and `qrisk merge` resolve as CLI subcommands
