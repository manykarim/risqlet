# ensemble-tooling Specification

## Purpose
TBD - created by archiving change add-ensemble-tooling. Update Purpose after archive.
## Requirements
### Requirement: dedupe proposes clusters deterministically
`risqlet dedupe` SHALL cluster register risks by a deterministic similarity score combining normalized statement-token overlap, shared aspects, and shared evidence paths, using a configurable threshold (default 0.5). It SHALL report each cluster's members, pairwise scores, and a suggested survivor (most evidence, then longest statement, then lowest id), SHALL never modify any file, and SHALL produce identical output for identical registers.

#### Scenario: Near-duplicates clustered
- **WHEN** two risks share most statement tokens and an evidence path
- **THEN** dedupe reports them in one cluster with a suggested survivor

#### Scenario: Unrelated risks not clustered
- **WHEN** two risks share no meaningful tokens, aspects, or evidence
- **THEN** they appear in no common cluster

#### Scenario: Threshold configurable
- **WHEN** config sets a higher dedupe threshold
- **THEN** borderline pairs clustered at the default are no longer clustered

### Requirement: merge is mechanical and gate-preserving
`risqlet merge <survivor> <duplicate...>` SHALL union evidence and aspects into the survivor, move the duplicates' mitigations with their `risk_ids` rewritten, record the duplicates' identity and provenance under the survivor's `merged_from`, and delete the duplicate files. It SHALL refuse when any duplicate is not in `proposed` status, when the survivor is terminal, or when any id does not exist — leaving the register unchanged on refusal.

#### Scenario: Successful merge
- **WHEN** merging two proposed duplicates into a survivor with one mitigation each
- **THEN** the survivor holds the union of evidence and all mitigations referencing it, merged_from lists both duplicates, the duplicate files are gone, and validate passes

#### Scenario: Reviewed duplicate refused
- **WHEN** a duplicate has status reviewed
- **THEN** merge exits non-zero, names the risk, and no file changes

### Requirement: disagreement is computed, engine-owned
When a risk carries two or more score sets for the active policy, `risqlet score` SHALL compute `disagreement` as the mean over factors of the normalized value spread (0–1, rounded to 2 decimals) with per-factor detail, write it to the risk, and remove it when fewer than two qualifying score sets remain. `risqlet validate` SHALL recompute disagreement and fail on mismatch. Score sets for other policies SHALL be ignored by the computation.

#### Scenario: Spread computed
- **WHEN** a risk has two sod-ap-v1 score sets with severity 4 and 8 (range 1–10) and identical other factors
- **THEN** disagreement.factors.severity is 0.44 and disagreement.value reflects the mean spread

#### Scenario: Tampered disagreement detected
- **WHEN** a stored disagreement differs from the recomputation
- **THEN** validate fails citing the risk

#### Scenario: Single score set has no disagreement
- **WHEN** a risk has one score set
- **THEN** no disagreement field is present after scoring

### Requirement: contested scores surface in status
`risqlet status` SHALL include a pending hint naming risks in proposed, reviewed, or accepted status whose disagreement value exceeds 0.25.

#### Scenario: Contested hint
- **WHEN** a reviewed risk has disagreement 0.4
- **THEN** status pending contains a contested-scores hint naming it

