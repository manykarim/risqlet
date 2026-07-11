# mcp-adapter Specification

## Purpose
TBD - created by archiving change add-mcp-adapter. Update Purpose after archive.
## Requirements
### Requirement: Stateless stdio server with a capped tool surface
`risqlet mcp` SHALL run a stdio MCP server exposing at most 10 tools, every tool taking an explicit `project_dir` and holding no server-side session state. The `mcp` dependency SHALL be an optional extra; running `risqlet mcp` without it SHALL print an actionable install hint and exit 1. The server SHALL perform no LLM inference.

#### Scenario: Tool count guard
- **WHEN** the server is constructed
- **THEN** it registers exactly the specified nine tools

#### Scenario: Missing extra
- **WHEN** `risqlet mcp` runs without the mcp package installed
- **THEN** it exits 1 telling the user to install risqlet[mcp]

### Requirement: Core tools mirror the CLI
`init_register`, `validate_register`, `score_risks`, and `export_register` SHALL behave identically to their CLI counterparts (same refusals, same reports, same deterministic outputs), returning structured JSON.

#### Scenario: Validate report parity
- **WHEN** validate_register runs on a register
- **THEN** its report equals `risqlet validate --json` output for the same state

#### Scenario: Export determinism
- **WHEN** export_register runs twice on unchanged state
- **THEN** the returned content is identical

### Requirement: browse_catalog consolidates catalog access
A single `browse_catalog` tool SHALL cover list (optionally per pack), show (by entry id), and search (by terms), returning the same data as the corresponding CLI commands and actionable errors for unknown packs/entries/actions.

#### Scenario: Search via MCP
- **WHEN** browse_catalog is called with action search and terms ["reconciliation"]
- **THEN** techniques.data-reconciliation is among the results

### Requirement: get_guidance serves the playbooks as data
`get_guidance` SHALL return the bundled skill/reference markdown for topics overview, phases, elicitation, scoring, risk-writing, mitigation, and quickscan, sourced from the same files the skills ship — so MCP-only clients receive the identical protocol text.

#### Scenario: Guidance parity with skills
- **WHEN** get_guidance is called with topic phases
- **THEN** the returned content equals skills/risk-analysis/references/phases.md

#### Scenario: Unknown topic
- **WHEN** get_guidance is called with an unknown topic
- **THEN** an error lists the valid topics

### Requirement: Register writes preserve the gates
`upsert_risk` SHALL create or update risks only in `proposed` status: it SHALL reject payloads containing a status field and reject updates to risks whose current status is not proposed. `add_mitigation` SHALL enforce the mitigation model including the mandatory residual note. `record_decision` SHALL append a status/phase event and, for status changes, update the risk file's status to match; it SHALL reject principals not prefixed `human:` and SHALL return a fresh validate report with the result.

#### Scenario: Status smuggling rejected
- **WHEN** upsert_risk is called with a status field or against a reviewed risk
- **THEN** the tool errors and the register is unchanged

#### Scenario: Agent principal rejected
- **WHEN** record_decision is called with principal agent:helper
- **THEN** the tool errors before writing anything

#### Scenario: Decision keeps register consistent
- **WHEN** record_decision moves R-0001 proposed→reviewed with a human principal
- **THEN** the event is appended, the risk file shows reviewed, and the returned validate report passes

#### Scenario: Missing residual note
- **WHEN** add_mitigation is called without residual_note
- **THEN** the tool errors citing the field

### Requirement: MCP-only workflow completeness
Using only the nine tools, a client SHALL be able to complete the full workflow: read guidance, initialize, write risks with provenance, score, record human decisions, add mitigations, and export a strategy whose register passes validation.

#### Scenario: End-to-end via tools only
- **WHEN** the documented tool sequence runs against a fresh directory
- **THEN** the final validate report passes and strategy-md content is produced

