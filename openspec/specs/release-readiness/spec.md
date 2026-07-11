# release-readiness Specification

## Purpose
TBD - created by archiving change add-release-prep. Update Purpose after archive.
## Requirements
### Requirement: complete publication metadata
`pyproject.toml` SHALL declare the metadata a public package needs: a one-line `description`, `readme`, license, at least one author, `keywords`, `classifiers` (including the Apache-2.0 OSI classifier and the supported Python versions), and `project.urls` (at least Repository and Issues). The built wheel and sdist SHALL include `LICENSE`, `LICENSE-CATALOG`, and `NOTICE`, and the package SHALL ship a `py.typed` marker.

#### Scenario: Metadata present
- **WHEN** `pyproject.toml` is inspected
- **THEN** description, readme, license, authors, keywords, classifiers, and project.urls are all present and non-empty

#### Scenario: License and notice ship
- **WHEN** a wheel is built
- **THEN** it contains LICENSE, NOTICE, and the package's py.typed marker

### Requirement: consolidated third-party notice
A top-level `NOTICE` SHALL reproduce the required third-party attributions — the MITRE ATT&CK statement, the OWASP taxonomy note, and a credited-concepts section naming the originators the catalog references — and SHALL point to `risqlet catalog licenses` as the authoritative runtime source.

#### Scenario: MITRE notice consolidated
- **WHEN** NOTICE is read
- **THEN** it contains the MITRE ATT&CK attribution and names the runtime `catalog licenses` command

### Requirement: governance documents
The repository SHALL provide `CONTRIBUTING.md` (including the clean-room affirmation required for catalog-pack contributions), `SECURITY.md` (a private vulnerability-reporting process), `CHANGELOG.md` (a 0.1.0 entry), and `RELEASING.md` (versioning and release steps).

#### Scenario: Governance files present
- **WHEN** the repository root is inspected
- **THEN** CONTRIBUTING.md, SECURITY.md, CHANGELOG.md, and RELEASING.md exist and CONTRIBUTING restates the clean-room rule

### Requirement: inert release workflow
A tag-triggered release workflow SHALL be provided that builds and publishes via PyPI Trusted Publishing, and SHALL NOT publish or run until the maintainer has created the public repository and configured trusted publishing.

#### Scenario: Workflow shipped, not armed
- **WHEN** the release workflow is inspected
- **THEN** it triggers only on version tags and uses trusted publishing (no stored token), and requires maintainer setup before it can run

### Requirement: human-gated actions enumerated
A release checklist SHALL enumerate every action that only the maintainer can perform — claiming the PyPI/npm/GitHub names, obtaining the legal review of the clean-room catalog, configuring trusted publishing, and cutting the first release — each explicitly marked as a maintainer action. This change SHALL NOT itself publish, push to a public remote, or claim any external name.

#### Scenario: Checklist marks maintainer steps
- **WHEN** the release checklist is read
- **THEN** name-claiming, legal review, and first publish are each marked as maintainer-only actions

#### Scenario: No outward action taken
- **WHEN** this change is implemented
- **THEN** nothing is published, no external name is claimed, and no push to a public remote occurs

