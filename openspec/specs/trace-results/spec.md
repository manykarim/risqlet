# trace-results Specification

## Purpose
TBD - created by archiving change add-trace-loop. Update Purpose after archive.
## Requirements
### Requirement: ingest parses RF and JUnit results
`risqlet trace ingest <path>...` SHALL parse Robot Framework `output.xml` and JUnit XML using only the standard library, auto-detecting format by root tag, extracting per-test suite/classname, name, outcome (pass|fail|skip), and duration when present, and appending each occurrence to an append-only `.risqlet/results.jsonl`. Unknown roots and malformed XML SHALL produce actionable errors naming the file.

#### Scenario: Robot Framework output
- **WHEN** an output.xml with passing and failing tests is ingested
- **THEN** each test appears in results.jsonl with the correct outcome

#### Scenario: JUnit output
- **WHEN** a JUnit XML with a `<failure>` testcase and a `<skipped>` testcase is ingested
- **THEN** the first is recorded fail and the second skip

#### Scenario: Unknown format
- **WHEN** an XML whose root is neither robot nor testsuite is ingested
- **THEN** the command errors naming the file and the expected formats

### Requirement: test_ref resolver normalizes conventions
A resolver SHALL map mitigation `tests[]` refs (`rf:`, `pytest:`, `junit:`, `charter:`) and parsed results to a common comparison key of (suite-or-file basename lowercased, test name lowercased), so a mitigation ref matches its result across path/name spelling differences. `charter:` refs SHALL never match a result.

#### Scenario: Cross-convention match
- **WHEN** a mitigation ref `rf:suites/reconciliation.robot::Nightly Settlement Match` and an RF result for suite Reconciliation test "Nightly Settlement Match" are compared
- **THEN** they resolve to the same key and match

#### Scenario: Charter never matches
- **WHEN** a mitigation carries only a `charter:` ref
- **THEN** it matches no result

### Requirement: coverage classification
`risqlet trace status` SHALL classify each mitigation as covered-passing, covered-failing, charter-only, or untested (precedence failing > passing > charter-only > untested), roll up per risk as the worst mitigation state, and report which risks have failing or missing mitigation tests. `--json` SHALL emit the structured report. Results SHALL live outside the register schema so `risqlet validate` is unaffected by their presence or absence.

#### Scenario: Failing dominates
- **WHEN** a mitigation has one passing and one failing covering test
- **THEN** it is classified covered-failing

#### Scenario: Validate unaffected
- **WHEN** results.jsonl exists with any content
- **THEN** `risqlet validate` behaves identically to when it is absent

### Requirement: detection-evidence notes
When a mitigation with `lever: detection` has a low Detection score (≤4) on its risk under the active policy and its covering tests are failing or absent, `risqlet trace status` SHALL emit an advisory note naming the risk, the claimed Detection score, the covering test, and its recent history (e.g. failed X of last Y, or no results), recommending a re-score or fix. These notes SHALL NOT modify any score.

#### Scenario: Unearned detection flagged
- **WHEN** R-0007's detection mitigation is scored detection 3 but its covering test's latest results are failing
- **THEN** a note names R-0007, the score 3, the test, and its failing history, and no score changes

### Requirement: exports carry results
`trace-matrix-csv` SHALL include a latest-result column per test ref (outcome, or charter/none), and `strategy-md` SHALL include a "Mitigations with failing or missing tests" subsection under "What this does not cover".

#### Scenario: Matrix result column
- **WHEN** trace-matrix-csv is exported after ingesting results
- **THEN** each test row shows the latest outcome for its ref

