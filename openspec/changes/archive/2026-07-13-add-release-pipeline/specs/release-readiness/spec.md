## MODIFIED Requirements

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
