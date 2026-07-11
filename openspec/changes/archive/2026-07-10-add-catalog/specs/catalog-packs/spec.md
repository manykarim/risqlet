# Spec: catalog-packs

## ADDED Requirements

### Requirement: Pack file format
A catalog pack SHALL be a single YAML file declaring `id` (the namespace), `title`, `version`, `license`, `attribution`, and an `entries` list. Each entry SHALL declare `slug` (kebab-case, unique within the pack), `name`, `kind` (aspect|technique|heuristic|guideword-set), a non-empty `summary`, 1–3 `prompts`, `tags`, and a non-empty one-line `provenance`; entries MAY declare `related` (full `pack.slug` ids) and, for guideword sets, a non-empty `words` list. A published JSON Schema SHALL validate pack files.

#### Scenario: Valid pack loads
- **WHEN** a pack file conforms to the schema
- **THEN** it loads and its entries are addressable as `<pack-id>.<slug>`

#### Scenario: Duplicate slug rejected
- **WHEN** two entries in one pack share a slug
- **THEN** pack loading fails naming the slug

#### Scenario: Guideword set requires words
- **WHEN** an entry has kind guideword-set and an empty words list
- **THEN** pack loading fails naming the entry

#### Scenario: Provenance mandatory
- **WHEN** an entry omits provenance or leaves it empty
- **THEN** pack loading fails naming the entry

### Requirement: Packaged clean-room packs
The distribution SHALL include four packs — `iso25010` (quality aspects), `techniques`, `heuristics`, `guidewords` — totalling at least 70 entries, whose entry text is entirely original: established concept names and originator citations appear as facts, but no text from TestSphere, RiskStorming, Would Heu-Risk It?, HTSM, ISO standards, or other licensed sources is reproduced. Every packaged entry SHALL carry provenance naming the concept's origin. Catalog content SHALL be licensed CC BY 4.0, separately from the Apache-2.0 code license.

#### Scenario: Coverage floor
- **WHEN** the packaged packs are loaded
- **THEN** all four pack ids resolve and the combined entry count is ≥ 70

#### Scenario: Every entry attributed
- **WHEN** any packaged pack is loaded
- **THEN** every entry has a non-empty provenance line

#### Scenario: Quality aspects available for phase 1
- **WHEN** the iso25010 pack is loaded
- **THEN** it contains at least 18 entries of kind aspect, including the nine 2023 characteristic names

### Requirement: Clean-room authoring protocol
The repository SHALL document the clean-room rules in `CLEAN-ROOM.md`: source card/standard text must not be consulted while authoring entry text; concept names and citations are permitted as facts; every entry needs a provenance line; contributions affirm compliance. `LICENSE-CATALOG` SHALL contain the CC BY 4.0 grant for pack content.

#### Scenario: Governance files present
- **WHEN** the repository is inspected
- **THEN** CLEAN-ROOM.md and LICENSE-CATALOG exist and the README states the dual licensing

### Requirement: User packs
Packs found in `.qrisk/catalogs/*.yaml` SHALL be loadable by pack id exactly like packaged packs, and SHALL shadow a packaged pack with the same id. Distribution of licensed third-party deck content is the user's responsibility; the tool only reads local files.

#### Scenario: User pack loads
- **WHEN** `.qrisk/catalogs/company-v1.yaml` exists and config lists catalog `company-v1`
- **THEN** its entries resolve as `company-v1.<slug>`

#### Scenario: User pack shadows packaged
- **WHEN** `.qrisk/catalogs/techniques.yaml` exists
- **THEN** it is loaded instead of the packaged techniques pack
