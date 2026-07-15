## MODIFIED Requirements

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
