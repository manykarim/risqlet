# Spec: catalog-cli

## ADDED Requirements

### Requirement: catalog list
`qrisk catalog list` SHALL print all entries of the loaded packs (packaged plus user packs referenced by config or present in `.qrisk/catalogs/`), one per line with entry id, kind, and summary; `--pack <id>` SHALL restrict to one pack. `--json` SHALL emit the structured entry list.

#### Scenario: List all
- **WHEN** `qrisk catalog list` runs in a project
- **THEN** entries from all four packaged packs appear with their full ids

#### Scenario: List one pack
- **WHEN** `qrisk catalog list --pack guidewords` runs
- **THEN** only guidewords entries appear

### Requirement: catalog show
`qrisk catalog show <entry-id>` SHALL print the full entry (name, kind, summary, prompts, tags, provenance, related, words). Unknown ids SHALL exit 1 with a message naming the id.

#### Scenario: Show entry
- **WHEN** `qrisk catalog show techniques.stress-testing` runs
- **THEN** the entry's prompts and provenance are printed and exit code is 0

#### Scenario: Unknown entry
- **WHEN** `qrisk catalog show techniques.nope` runs
- **THEN** exit code is 1 and the message names the id

### Requirement: catalog search is a convenience, not a recommender
`qrisk catalog search <terms...>` SHALL perform case-insensitive keyword matching over entry names, summaries, tags, and slugs, returning matching entry ids ranked by match count. The command's help text SHALL state that semantic risk-to-technique mapping is the calling agent's job; the tool does not rank suitability.

#### Scenario: Keyword hit
- **WHEN** `qrisk catalog search reconciliation` runs
- **THEN** techniques.data-reconciliation is among the results

#### Scenario: No match
- **WHEN** `qrisk catalog search zzzunmatched` runs
- **THEN** the command exits 0 with an empty result set

### Requirement: Configured catalogs must resolve
`qrisk validate` SHALL fail with an error when a `config.catalogs` entry cannot be loaded (missing pack or schema-invalid pack file).

#### Scenario: Missing pack
- **WHEN** config lists catalog `does-not-exist`
- **THEN** validate exits 1 citing the catalog id
