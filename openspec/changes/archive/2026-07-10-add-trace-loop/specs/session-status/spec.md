# Spec delta: session-status (add-trace-loop)

## ADDED Requirements

### Requirement: status surfaces failing mitigation tests
When test results are present, `qrisk status` SHALL add a pending hint naming accepted or mitigating risks that have at least one mitigation classified covered-failing. Absent results, no such hint appears.

#### Scenario: Failing-test hint
- **WHEN** an accepted risk has a mitigation whose covering test's latest result is fail
- **THEN** status pending contains a hint naming that risk

#### Scenario: No results, no hint
- **WHEN** the register has no results.jsonl
- **THEN** no failing-test hint appears
