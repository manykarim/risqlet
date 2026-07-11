# Spec delta: agent-skills (add-trace-loop)

## ADDED Requirements

### Requirement: risk-analysis skill teaches the trace loop
The risk-analysis skill SHALL document the test_ref conventions (`rf:`, `pytest:`, `junit:`, `charter:`), the replacement of a `charter:` ref with a concrete ref once the test exists, and a trace workflow (ingest results, read `qrisk trace status`, use detection-evidence notes at the score gate). Drift guards (catalog ids, CLI commands, line budgets) SHALL keep passing.

#### Scenario: Trace guidance present
- **WHEN** the skill content is read
- **THEN** it covers the ref conventions, charter replacement, and the ingest→status→act workflow

#### Scenario: trace command known
- **WHEN** the drift guards run
- **THEN** `qrisk trace` resolves as a CLI subcommand
