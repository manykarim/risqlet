# guardrail-generation Specification

## Purpose
TBD - created by archiving change add-guardrail-generation. Update Purpose after archive.
## Requirements
### Requirement: vetted template library
Guardrails SHALL be rendered only from a vetted template library shipped as package data. Each template SHALL declare its id, target surface (agents-md | claude-hook | claude-permission | pre-commit | ci), enforcement level (hard | soft), the mitigation barriers it satisfies, its selectors, and its parameters; only declared parameters SHALL be interpolated into the fixed template body. Guardrail bodies SHALL NOT be free-form model output.

#### Scenario: Template loads and validates
- **WHEN** the guardrail templates are loaded
- **THEN** each declares surface, enforcement, barriers, and a body, and invalid templates are rejected

#### Scenario: Only declared params interpolated
- **WHEN** a guardrail is rendered
- **THEN** the body matches the template except for its declared parameters, with no model-authored command text

### Requirement: risk-driven selection with provenance
`risqlet guardrails generate` SHALL select templates for risks in accepted or mitigating status (never proposed) by matching each mitigation's barrier and the risk's aspects/catalog-ref tags to template selectors, parameterizing paths from the risk's evidence. Each rendered guardrail SHALL embed a provenance marker identifying its risk id, barrier, and template id. Generation SHALL be read-only and deterministic.

#### Scenario: Barrier and evidence drive selection
- **WHEN** an accepted confidentiality risk has a prevent mitigation with evidence under src/auth/
- **THEN** a secret-scan/path-deny guardrail scoped to that path is proposed, tagged with the risk id

#### Scenario: Proposed risks excluded
- **WHEN** a risk is still proposed
- **THEN** no guardrail is generated for it

#### Scenario: Deterministic and read-only
- **WHEN** generate runs twice on an unchanged register
- **THEN** the plans are identical and no file changed

### Requirement: hard/soft honesty labeling
The plan SHALL label each guardrail hard (enforcing) or soft (advisory). For any accepted or mitigating risk of high severity whose selected guardrails are all soft, generate SHALL emit an advisory finding that the risk is covered only by advisory guardrails and is not enforced. This finding SHALL NOT block generation.

#### Scenario: Advisory-only high-severity flagged
- **WHEN** a severity-9 accepted risk's only applicable guardrails are soft AGENTS.md rules
- **THEN** the plan warns that the risk is advisory-only and not enforced, and still lists the soft guardrails

#### Scenario: Hard coverage not flagged
- **WHEN** a high-severity risk has at least one hard guardrail
- **THEN** no advisory-only warning is emitted for it

### Requirement: diff detects stale, missing, and drift
`risqlet guardrails diff` SHALL scan a target for installed provenance markers and report guardrails whose risk is now closed/rejected/absent (stale), accepted risks in the plan with no installed guardrail (missing), and installed guardrails whose body differs from the current render (drift). It SHALL be read-only.

#### Scenario: Stale guardrail after risk closes
- **WHEN** a guardrail's risk is later closed
- **THEN** diff reports that guardrail as stale

#### Scenario: Missing guardrail for new risk
- **WHEN** a newly accepted risk has no installed guardrail
- **THEN** diff reports it as missing

### Requirement: install is explicit and human-gated
`risqlet guardrails install --target <surface|path>` SHALL write the selected guardrails to that surface's conventional location with their provenance markers, refusing to overwrite a differing existing block without `--force`. `generate` and `diff` SHALL never write. Guardrails SHALL be written to the target project's agent-config files, never into `.risqlet/`, and `risqlet validate` behavior SHALL be unaffected by their presence.

#### Scenario: Install writes marked guardrails
- **WHEN** install --target agents-md runs
- **THEN** an AGENTS.md section is written with each guardrail carrying its risk provenance marker

#### Scenario: Overwrite protection
- **WHEN** a differing guardrail block already exists and --force is absent
- **THEN** install exits non-zero and changes nothing

#### Scenario: Register untouched
- **WHEN** any guardrails command runs
- **THEN** no file under .risqlet/ changes and validate behaves identically

