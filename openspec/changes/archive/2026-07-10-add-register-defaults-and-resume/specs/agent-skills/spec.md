# Spec delta: agent-skills (add-register-defaults-and-resume)

## ADDED Requirements

### Requirement: risk-analysis skill teaches status-first resume
The risk-analysis skill SHALL instruct the agent to run `qrisk status` before starting work, resume at the phase it reports while honoring its pending hints, and never re-run gates whose decisions are already recorded in the event log. SKILL.md line budgets continue to hold.

#### Scenario: Resume protocol present
- **WHEN** the skill content is read
- **THEN** it directs status-first resume and forbids redoing recorded gate decisions

#### Scenario: Drift guard still passes
- **WHEN** the skills drift-guard tests run
- **THEN** `qrisk status` resolves as an existing CLI subcommand
