# catalog-cli Specification

## Purpose
TBD - created by archiving change add-catalog. Update Purpose after archive.
## Requirements
### Requirement: catalog list
`risqlet catalog list` SHALL print all entries of the loaded packs (packaged plus user packs referenced by config or present in `.risqlet/catalogs/`), one per line with entry id, kind, and summary; `--pack <id>` SHALL restrict to one pack. `--json` SHALL emit the structured entry list.

#### Scenario: List all
- **WHEN** `risqlet catalog list` runs in a project
- **THEN** entries from all four packaged packs appear with their full ids

#### Scenario: List one pack
- **WHEN** `risqlet catalog list --pack guidewords` runs
- **THEN** only guidewords entries appear

### Requirement: catalog show
`risqlet catalog show <entry-id>` SHALL print the full entry (name, kind, summary, prompts, tags, provenance, related, words). Unknown ids SHALL exit 1 with a message naming the id.

#### Scenario: Show entry
- **WHEN** `risqlet catalog show techniques.stress-testing` runs
- **THEN** the entry's prompts and provenance are printed and exit code is 0

#### Scenario: Unknown entry
- **WHEN** `risqlet catalog show techniques.nope` runs
- **THEN** exit code is 1 and the message names the id

### Requirement: catalog search is a convenience, not a recommender
`risqlet catalog search <terms...>` SHALL perform case-insensitive keyword matching over entry names, summaries, tags, and slugs, returning matching entry ids ranked by match count. The command's help text SHALL state that semantic risk-to-technique mapping is the calling agent's job; the tool does not rank suitability.

#### Scenario: Keyword hit
- **WHEN** `risqlet catalog search reconciliation` runs
- **THEN** techniques.data-reconciliation is among the results

#### Scenario: No match
- **WHEN** `risqlet catalog search zzzunmatched` runs
- **THEN** the command exits 0 with an empty result set

### Requirement: Configured catalogs must resolve
`risqlet validate` SHALL fail with an error when a `config.catalogs` entry cannot be loaded (missing pack or schema-invalid pack file).

#### Scenario: Missing pack
- **WHEN** config lists catalog `does-not-exist`
- **THEN** validate exits 1 citing the catalog id

