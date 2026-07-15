# release-readiness Specification

## Purpose
TBD - created by archiving change add-release-prep. Update Purpose after archive.
## Requirements
### Requirement: complete publication metadata
`pyproject.toml` SHALL declare the metadata a public package needs: a one-line `description`, `readme`, license, at least one author, `keywords`, `classifiers` (including the Apache-2.0 OSI classifier and the supported Python versions), and `project.urls` (at least Repository and Issues). The built wheel and sdist SHALL include `LICENSE`, `LICENSE-CATALOG`, and `NOTICE`, and the package SHALL ship a `py.typed` marker.

Inspecting the built artifact's contents SHALL NOT by itself establish that the
artifact works. Before a release is considered ready, the wheel SHALL be installed
into a fresh environment — no development dependencies, no source tree on
`sys.path` — and the installed `risqlet` console script SHALL be executed, on every
platform the project claims to support. The classifiers SHALL name only operating
systems that are exercised this way.

#### Scenario: Metadata present
- **WHEN** `pyproject.toml` is inspected
- **THEN** description, readme, license, authors, keywords, classifiers, and project.urls are all present and non-empty

#### Scenario: License and notice ship
- **WHEN** a wheel is built
- **THEN** it contains LICENSE, NOTICE, and the package's py.typed marker

#### Scenario: The wheel is proven to run, not just to contain
- **WHEN** release readiness is assessed
- **THEN** the wheel has been installed into a clean environment and its console
  script run on each supported platform, not only inspected for expected paths

#### Scenario: Runtime package data is proven present
- **WHEN** the installed CLI runs a command that loads shipped data (an agent
  adapter, a CI or guardrail template, a catalog pack, a bundled skill)
- **THEN** it succeeds from the installed wheel alone, with no source tree present

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
A release workflow SHALL be provided that is **manually dispatched** and NEVER
publishes as a side effect of pushing a tag. It SHALL accept a `tag` input (the
`vX.Y.Z` tag to build from) and a `mode` input selecting exactly one of:
`gh-draft` (create a draft GitHub release), `gh-release` (create a published
GitHub release), or `pypi` (publish to PyPI and create a published GitHub
release). Every mode SHALL first run a gated build job (dependency sync, lint,
tests, and an sdist + wheel build) and SHALL attach the built sdist and wheel to
the GitHub release it creates. PyPI publishing SHALL authenticate with an
API-token secret (`PYPI_API_TOKEN`), and the `pypi` mode SHALL fail with a clear
message when that secret is absent, so the workflow is safe to ship before the
secret is configured.

#### Scenario: Manual dispatch with mode selection
- **WHEN** the release workflow is inspected
- **THEN** it is triggered by manual dispatch (not by tag push alone) and exposes a `mode` input offering draft-GitHub-release, published-GitHub-release, and PyPI-publish choices

#### Scenario: Artifacts attached, never auto-published
- **WHEN** any release mode runs
- **THEN** it builds and attaches the sdist and wheel to the GitHub release, and PyPI upload happens only in the `pypi` mode using the `PYPI_API_TOKEN` secret

#### Scenario: Safe before the secret exists
- **WHEN** the `pypi` mode runs without `PYPI_API_TOKEN` configured
- **THEN** the job fails with an explicit "token not set" message rather than attempting an unauthenticated publish

### Requirement: human-gated actions enumerated
A release checklist SHALL enumerate every action that only the maintainer can perform — claiming the PyPI/npm/GitHub names, obtaining the legal review of the clean-room catalog, adding the `PYPI_API_TOKEN` secret to the GitHub repository, and cutting each release by manually dispatching the workflow with a tag and mode — each explicitly marked as a maintainer action. This change SHALL NOT itself publish, push to a public remote, add any secret, or claim any external name.

#### Scenario: Checklist marks maintainer steps
- **WHEN** the release checklist is read
- **THEN** name-claiming, legal review, adding the PyPI token secret, and dispatching a release are each marked as maintainer-only actions

#### Scenario: No outward action taken
- **WHEN** this change is implemented
- **THEN** nothing is published, no external name is claimed, no secret is added, and no push to a public remote occurs

