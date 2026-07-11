# Spec: session-status

## ADDED Requirements

### Requirement: status reports session state read-only
`qrisk status` SHALL report, without modifying any file: project, phase, active catalogs, ranked selected aspects, risk counts by status, scoring coverage (risks with vs. without derived priorities, terminal states excluded), mitigation coverage of accepted and mitigating risks (uncovered ids listed), top risks by derived priority capped by `constraints.max_top_risks`, the last event (timestamp, type, principal), and any unparseable register files. `--json` SHALL emit the full structured report. The command SHALL succeed (exit 0) on messy mid-session registers; only a missing register exits non-zero.

#### Scenario: Mid-session overview
- **WHEN** status runs on a register with mixed proposed/reviewed risks, partial scoring, and one schema-invalid file
- **THEN** counts, coverage, top risks, and the invalid file name are reported and exit code is 0

#### Scenario: Read-only guarantee
- **WHEN** status runs
- **THEN** no file under .qrisk/ changes

### Requirement: deterministic pending-gate hints
The report SHALL include a `pending` list derived by fixed rules from register state, including at least: aspects phase with no selection; elicit-or-later phase with zero risks; reviewed risks lacking scores; accepted or mitigating risks lacking mitigations; and unparseable files. No free-text generation — identical state yields identical hints.

#### Scenario: Scoring hint
- **WHEN** three reviewed risks have no score sets
- **THEN** pending contains a hint naming the count of reviewed risks awaiting scoring

#### Scenario: No hints when consistent
- **WHEN** a register's state is consistent with its phase and gates
- **THEN** pending is empty
