# Spec delta: session-status (add-ensemble-tooling)

## MODIFIED Requirements

### Requirement: deterministic pending-gate hints
The report SHALL include a `pending` list derived by fixed rules from register state, including at least: aspects phase with no selection; elicit-or-later phase with zero risks; reviewed risks lacking scores; accepted or mitigating risks lacking mitigations; unparseable files; and risks in proposed, reviewed, or accepted status whose scoring disagreement exceeds 0.25. No free-text generation — identical state yields identical hints.

#### Scenario: Scoring hint
- **WHEN** three reviewed risks have no score sets
- **THEN** pending contains a hint naming the count of reviewed risks awaiting scoring

#### Scenario: Contested scores hint
- **WHEN** a reviewed risk carries disagreement above 0.25
- **THEN** pending contains a contested-scores hint naming it

#### Scenario: No hints when consistent
- **WHEN** a register's state is consistent with its phase and gates
- **THEN** pending is empty
