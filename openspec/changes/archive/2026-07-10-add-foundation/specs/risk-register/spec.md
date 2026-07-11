# Spec: risk-register

## ADDED Requirements

### Requirement: Register directory layout
The system SHALL store all risk-analysis state in a `.qrisk/` directory containing `config.yaml`, a `register/` directory with one YAML file per risk named `R-NNNN.yaml` (four-digit, zero-padded), and an `events.jsonl` append-only log. No state SHALL be held outside these files (no server sessions, no databases).

#### Scenario: Scaffolded layout
- **WHEN** a register is initialized in an empty project
- **THEN** `.qrisk/config.yaml`, `.qrisk/register/`, and `.qrisk/events.jsonl` exist and validate against their schemas

#### Scenario: Register discovery from subdirectory
- **WHEN** a command runs in a subdirectory of a project containing `.qrisk/`
- **THEN** the nearest ancestor `.qrisk/` directory is used

### Requirement: Risk document schema
Each risk file SHALL contain: `schema_version`, unique `id` matching `^R-\d{4}$`, a non-empty `statement`, `aspects` (list of namespaced `catalog.slug` strings), `elicited_by` provenance (`method` from the enum riskstorming|hazop|stride|premortem|fmea|inside-out|manual, optional `prompt_ref`, `evidence` list), zero or more `scores` sets, a `status` from proposed|reviewed|accepted|mitigating|closed|rejected, and zero or more embedded `mitigations`. Unknown additional fields SHALL produce warnings, not errors.

#### Scenario: Valid risk accepted
- **WHEN** a risk file contains all required fields with valid values
- **THEN** validation passes

#### Scenario: Malformed id rejected
- **WHEN** a risk file has `id: R-12` or a duplicate id already used by another file
- **THEN** validation fails identifying the file and field

#### Scenario: Unknown fields tolerated
- **WHEN** a risk file contains an extra field not in the schema
- **THEN** validation emits a warning and exits successfully

### Requirement: Evidence-free risks flagged speculative
A risk whose `elicited_by.evidence` list is empty SHALL be flagged as `speculative` in validation output. Speculative risks SHALL NOT cause validation failure.

#### Scenario: Speculative flag
- **WHEN** a risk has no evidence entries
- **THEN** the validation report lists the risk as speculative with exit code 0

### Requirement: Mitigation schema with mandatory residual note
Each mitigation SHALL contain: `id` matching `^M-\d{4}$`, `risk_ids` referencing existing risks, `treatment` (avoid|reduce|transfer|accept), `lever` (severity|occurrence|detection), `barrier` (prevent|detect|recover), a non-empty `concrete` action description, a non-empty `residual_note`, and a `tests` list (possibly empty) of trace links.

#### Scenario: Missing residual note rejected
- **WHEN** a mitigation omits `residual_note` or leaves it empty
- **THEN** validation fails citing the mitigation id

#### Scenario: Dangling risk reference rejected
- **WHEN** a mitigation lists a `risk_id` for which no register file exists
- **THEN** validation fails citing the missing reference

### Requirement: Status lifecycle state machine
Risk status transitions SHALL be restricted to: proposed→reviewed, reviewed→accepted, accepted→mitigating, mitigating→closed, and proposed|reviewed→rejected. Any other transition SHALL fail validation.

#### Scenario: Legal transition
- **WHEN** a risk moves from proposed to reviewed with a matching event entry
- **THEN** validation passes

#### Scenario: Skipped state rejected
- **WHEN** a risk file shows status accepted but the event log contains no proposed→reviewed transition for it
- **THEN** validation fails citing the inconsistent history

### Requirement: Human principal required for transitions
Every status transition beyond `proposed`, and every phase change in `config.yaml`, SHALL be recorded as an `events.jsonl` entry containing a timestamp, the transition, and a `principal` field; transitions SHALL only be authorized by a principal with the `human:` prefix. Risks in `proposed` status MAY be created and edited without events.

#### Scenario: Agent-only transition rejected
- **WHEN** a status change event lists `principal: agent:security-persona`
- **THEN** validation fails stating a human principal is required

#### Scenario: Event history must replay to current state
- **WHEN** the sequence of events for a risk does not replay to the status recorded in its register file
- **THEN** validation fails citing the risk and the divergence

### Requirement: Config document
`config.yaml` SHALL define `schema_version`, `project` name, `catalogs` (list), `scoring_policy` id, `phase` (context|aspects|elicit|score|mitigate|emit), `constraints` (`max_aspects` default 6, `max_top_risks` default 10), and selected `aspects` (each with namespaced id, unique rank 1..max_aspects, and non-empty rationale).

#### Scenario: Aspect over-selection rejected
- **WHEN** more aspects are selected than `constraints.max_aspects`
- **THEN** validation fails citing the constraint

#### Scenario: Duplicate rank rejected
- **WHEN** two selected aspects share the same rank
- **THEN** validation fails
