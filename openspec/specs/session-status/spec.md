# session-status Specification

## Purpose
TBD - created by archiving change add-register-defaults-and-resume. Update Purpose after archive.
## Requirements
### Requirement: status reports session state read-only
`risqlet status` SHALL report, without modifying any file: project, phase, active catalogs, ranked selected aspects, risk counts by status, scoring coverage (risks with vs. without derived priorities, terminal states excluded), mitigation coverage of accepted and mitigating risks (uncovered ids listed), top risks by derived priority capped by `constraints.max_top_risks`, the last event (timestamp, type, principal), and any unparseable register files. `--json` SHALL emit the full structured report. The command SHALL succeed (exit 0) on messy mid-session registers; only a missing register exits non-zero.

#### Scenario: Mid-session overview
- **WHEN** status runs on a register with mixed proposed/reviewed risks, partial scoring, and one schema-invalid file
- **THEN** counts, coverage, top risks, and the invalid file name are reported and exit code is 0

#### Scenario: Read-only guarantee
- **WHEN** status runs
- **THEN** no file under .risqlet/ changes

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

### Requirement: status surfaces failing mitigation tests
When test results are present, `risqlet status` SHALL add a pending hint naming accepted or mitigating risks that have at least one mitigation classified covered-failing. Absent results, no such hint appears.

#### Scenario: Failing-test hint
- **WHEN** an accepted risk has a mitigation whose covering test's latest result is fail
- **THEN** status pending contains a hint naming that risk

#### Scenario: No results, no hint
- **WHEN** the register has no results.jsonl
- **THEN** no failing-test hint appears

