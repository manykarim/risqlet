# risqlet-cli Specification

## Purpose
TBD - created by archiving change add-foundation. Update Purpose after archive.
## Requirements
### Requirement: init scaffolds a register
`risqlet init` SHALL create the `.risqlet/` layout with a commented starter `config.yaml`, empty `register/`, and empty `events.jsonl`. The starter config SHALL enable the packaged catalogs (`iso25010`, `techniques`, `heuristics`, `guidewords`) by default with a comment explaining the soft reference checks and how to disable them. It SHALL refuse to overwrite an existing non-empty `.risqlet/` directory.

#### Scenario: Fresh init
- **WHEN** `risqlet init` runs in a project without `.risqlet/`
- **THEN** the layout is created and `risqlet validate` immediately passes on it

#### Scenario: Catalogs active out of the box
- **WHEN** a fresh register is validated
- **THEN** the four packaged catalogs are loaded and catalog-aware reference checks apply

#### Scenario: Existing register protected
- **WHEN** `risqlet init` runs where `.risqlet/register/` already contains files
- **THEN** the command exits non-zero without modifying anything

### Requirement: validate is the single gate command
`risqlet validate` SHALL run schema validation, referential integrity, lifecycle/event consistency, derived-value recomputation, and constraint checks, exiting 0 only when all pass (warnings such as speculative flags do not fail). With `--json` it SHALL emit a machine-readable report listing every finding with file, field, severity, and message.

#### Scenario: Aggregated findings
- **WHEN** a register contains one schema error and one lifecycle violation
- **THEN** a single validate run reports both findings and exits 1

#### Scenario: JSON report for agents
- **WHEN** `risqlet validate --json` runs
- **THEN** stdout is a single JSON document with findings and a top-level pass/fail flag

### Requirement: score computes derived priorities
`risqlet score` SHALL compute derived fields for one risk (`risqlet score R-0001`) or all scored risks (`--all`) under each score set's declared policy, writing results back into the risk files while preserving YAML comments and key order. It SHALL never create or modify factor values.

#### Scenario: Batch scoring
- **WHEN** `risqlet score --all` runs on three risks with valid score sets
- **THEN** all three files gain up-to-date derived fields and nothing else in them changes

#### Scenario: Comment preservation
- **WHEN** a risk file containing YAML comments is rescored
- **THEN** the comments survive the rewrite

### Requirement: export renders deterministic outputs
`risqlet export --fmt <format>` SHALL support `register-yaml` (single consolidated YAML bundle), `strategy-md` (one-page strategy: selected aspects, top risks by derived priority capped at `constraints.max_top_risks`, mitigation table with treatment/lever/barrier, trace links, and a mandatory "What this does not cover" section aggregating all residual notes), and `trace-matrix-csv` (aspect→risk→mitigation→test rows). Output SHALL go to stdout by default or to a path given with `-o`. Identical register state SHALL produce byte-identical exports.

#### Scenario: Strategy respects constraints
- **WHEN** a register has 14 accepted risks and max_top_risks is 10
- **THEN** strategy-md lists the top 10 by derived priority and states that 4 further risks are tracked in the register

#### Scenario: Residual section always present
- **WHEN** strategy-md is exported
- **THEN** it contains a "What this does not cover" section even if only to state that no mitigations are recorded

#### Scenario: Deterministic output
- **WHEN** export runs twice on an unchanged register
- **THEN** the outputs are byte-identical

### Requirement: Register discovery and agent-friendly output
Every command SHALL accept `--dir PATH` and otherwise discover the register by walking up from the current directory. Every command SHALL support `--json` for structured output and SHALL use exit codes 0 (success) and 1 (failure) consistently.

#### Scenario: Explicit dir
- **WHEN** `risqlet validate --dir /elsewhere/project` runs
- **THEN** that project's register is validated regardless of cwd

