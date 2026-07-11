# Spec delta: agent-skills (add-ci-reassessment)

## ADDED Requirements

### Requirement: skills teach continuous re-assessment
The skills SHALL include a continuous-reassessment reference covering when to run `qrisk diff` (scope a change) and `qrisk check` (gate), and the PR-time and in-session loops; the risk-quickscan skill SHALL direct the agent to run `qrisk diff` first to see which existing risks already cover the change before eliciting new ones. Drift guards SHALL keep passing (`qrisk diff`, `qrisk check`, `qrisk ci` resolve as subcommands).

#### Scenario: Continuous reference present
- **WHEN** the skill content is read
- **THEN** it covers diff-for-scoping, check-for-gating, and both loops

#### Scenario: Quickscan scopes with diff
- **WHEN** the risk-quickscan skill is read
- **THEN** it instructs running qrisk diff to find already-covering risks first
