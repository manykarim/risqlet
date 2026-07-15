# risk-register Specification

## Purpose
TBD - created by archiving change add-foundation. Update Purpose after archive.
## Requirements
### Requirement: Register directory layout
The system SHALL store all risk-analysis state in a `.risqlet/` directory containing `config.yaml`, a `register/` directory with one YAML file per risk named `R-NNNN.yaml` (four-digit, zero-padded), and an `events.jsonl` append-only log. No state SHALL be held outside these files (no server sessions, no databases).

#### Scenario: Scaffolded layout
- **WHEN** a register is initialized in an empty project
- **THEN** `.risqlet/config.yaml`, `.risqlet/register/`, and `.risqlet/events.jsonl` exist and validate against their schemas

#### Scenario: Register discovery from subdirectory
- **WHEN** a command runs in a subdirectory of a project containing `.risqlet/`
- **THEN** the nearest ancestor `.risqlet/` directory is used

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

### Requirement: Catalog-aware reference validation
When a risk references an aspect `ns.slug` whose namespace `ns` matches a loaded catalog pack, an unknown `slug` SHALL produce a validation warning (not an error). The same soft check SHALL apply to `technique_ref` and `prompt_ref` values of the form `ns.slug` when `ns` is a loaded pack; refs using other syntaxes (e.g. `guideword:LATE`, `persona:ops`) remain free-form. Aspects in namespaces that are not loaded packs SHALL continue to be format-checked only.

#### Scenario: Unknown slug in loaded catalog warns
- **WHEN** the iso25010 pack is loaded and a risk references aspect `iso25010.typo-aspect`
- **THEN** validate emits a warning naming the aspect and still exits 0

#### Scenario: Known slug passes silently
- **WHEN** a risk references aspect `iso25010.security` and the pack contains security
- **THEN** no catalog finding is emitted

#### Scenario: Unloaded namespace unchanged
- **WHEN** a risk references aspect `companyx.internal-aspect` and no such pack is loaded
- **THEN** only the format check applies, as before

### Requirement: register files are UTF-8 on every platform
risqlet SHALL read and write every text file — `config.yaml`, the `register/*.yaml` risk documents, `events.jsonl`, and shipped data such as catalog and policy packs — as UTF-8 explicitly, independent of the host's locale encoding, and SHALL NOT rely on Python's default text encoding (UTF-8 on Linux and macOS, cp1252 on Windows).

Writing a risk SHALL NOT fail because its text contains characters outside the
platform's locale encoding: a statement containing `→`, an em-dash, CJK, or an emoji
SHALL round-trip through the register unchanged on every supported platform. Reading
SHALL NOT silently substitute characters — a register written on one platform and
read on another SHALL yield identical text.

Text writes SHALL use `\n` line endings on every platform. Python's text mode
translates `\n` to `\r\n` on Windows, which would make otherwise-deterministic
output differ by host.

Reading SHALL tolerate a file that is not valid UTF-8 rather than failing the
command, because risqlet itself produced such files: versions before the encoding fix
wrote the register in the host locale, so a Windows register containing an em-dash is
cp1252 on disk. A file that does not decode as UTF-8 SHALL be decoded as cp1252, its
text recovered intact, and the recovery SHALL be reported rather than performed
silently. The next write SHALL normalize the file to UTF-8, so a file is repaired by
being used rather than by a migration step.

The fallback SHALL be a fixed encoding, not the host's locale, so that behaviour and
tests are identical on every platform. It SHALL NOT apply to files risqlet has only
ever written as ASCII (`events.jsonl`, whose JSON escapes non-ASCII): there, a decode
error indicates real corruption and SHALL still be raised.

#### Scenario: Non-ASCII risk round-trips
- **WHEN** a risk whose statement contains `→`, an em-dash, and CJK is saved and
  read back
- **THEN** the statement is unchanged, and the bytes on disk decode as UTF-8

#### Scenario: Locale encoding does not reach the register
- **WHEN** risqlet runs on a host whose locale encoding is cp1252
- **THEN** the register is still written and read as UTF-8, and no
  `UnicodeEncodeError` or silent character substitution occurs

#### Scenario: Event log accepts non-ASCII
- **WHEN** an event whose rationale contains non-ASCII text is appended to
  `events.jsonl`
- **THEN** the append succeeds and the log remains valid UTF-8 JSONL

#### Scenario: Line endings do not depend on the host
- **WHEN** the same register is written on Windows and on Linux
- **THEN** the files are byte-identical, using `\n` in both

#### Scenario: A register an older version wrote in cp1252 still loads
- **WHEN** a register file containing a cp1252-encoded em-dash — as a pre-fix risqlet
  on Windows wrote it — is read
- **THEN** the text is recovered intact, the recovery is reported, and the command
  succeeds instead of raising `UnicodeDecodeError`

#### Scenario: A recovered file is normalized on write
- **WHEN** a file recovered from cp1252 is subsequently written
- **THEN** it is written as UTF-8, so the file stops being non-UTF-8 once used

