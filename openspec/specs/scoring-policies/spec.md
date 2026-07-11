# scoring-policies Specification

## Purpose
TBD - created by archiving change add-foundation. Update Purpose after archive.
## Requirements
### Requirement: Policies are data packs
Scoring policies SHALL be defined entirely in YAML data packs declaring ordinal `factors` (name, min, max) and `derived` fields computed either by a `product` formula or a top-down first-match `lookup` band table. The engine SHALL load packaged policies (`sod-ap-v1`, `li-v1`) and user-supplied packs from `.risqlet/policies/`, validating pack structure before use. Adding a policy SHALL NOT require code changes.

#### Scenario: Packaged policy loads
- **WHEN** the active policy is `sod-ap-v1`
- **THEN** the engine loads it and reports factors severity, occurrence, detection (1–10)

#### Scenario: Malformed pack rejected
- **WHEN** a user pack declares a lookup band referencing an undeclared factor
- **THEN** loading fails with a message naming the band and factor

#### Scenario: User pack override
- **WHEN** `.risqlet/policies/custom-v1.yaml` exists and config selects `custom-v1`
- **THEN** the engine uses it without any code change

### Requirement: Deterministic derived computation
Derived fields SHALL be computed only by the engine from factor values: identical inputs SHALL always produce identical outputs. The `sod-ap-v1` policy SHALL compute `rpn` as the product of severity, occurrence, and detection, and `action_priority` (HIGH|MEDIUM|LOW) via its band table with severity-dominant ordering (severity ≥ 9 is always HIGH regardless of other factors). The `li-v1` policy SHALL compute `priority` (critical|high|medium|low) from a 3×3 likelihood×impact lookup.

#### Scenario: Severity dominance
- **WHEN** a risk scores severity 9, occurrence 1, detection 1 under sod-ap-v1
- **THEN** action_priority is HIGH even though rpn is 9

#### Scenario: No thresholds on raw RPN
- **WHEN** two risks have equal rpn but different factor distributions
- **THEN** their action_priority values are determined by the band table, not the rpn value

#### Scenario: 3x3 matrix corner
- **WHEN** a risk scores likelihood high and impact high under li-v1
- **THEN** priority is critical

### Requirement: Factor values validated against policy ranges
Score sets SHALL declare the policy they were scored under; every declared factor MUST be present, integer, and within the policy's min/max. Factors not declared by the policy SHALL be rejected.

#### Scenario: Out-of-range factor rejected
- **WHEN** a score set under sod-ap-v1 contains severity 11
- **THEN** scoring fails citing the factor and allowed range

### Requirement: Rubric anchors required
A score set SHALL include a non-empty `rubric_anchors` list with at least one anchor per factor; the engine SHALL refuse to compute derived values for score sets lacking them.

#### Scenario: Anchorless scores refused
- **WHEN** a score set has values but an empty rubric_anchors list
- **THEN** the engine reports the risk as unscoreable and computes nothing

### Requirement: Derived values are engine-owned
Validation SHALL recompute derived fields for every scored risk and fail if stored values differ from computed values, so hand-edited (or LLM-edited) priorities cannot silently persist.

#### Scenario: Tampered priority detected
- **WHEN** a risk file's stored action_priority is HIGH but the band table computes MEDIUM
- **THEN** validation fails citing the mismatch

