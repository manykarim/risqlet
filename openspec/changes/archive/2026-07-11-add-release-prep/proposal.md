# Proposal: add-release-prep

## Why

The product is feature-complete (10 archived changes, 260 tests, dogfooded on three real repos) and now has a settled, availability-verified name (`risqlet`). What stands between it and a public release is not code — it is the packaging metadata, governance docs, third-party attribution consolidation, and release mechanics that a published open-source project needs, plus a small set of genuinely human-gated steps (claiming the name, a legal read, the first publish) that only the maintainer can do. This change prepares everything that can be prepared and clearly marks what the human must execute.

## What Changes

- Complete `pyproject.toml` publication metadata: description, readme, license, authors, keywords, classifiers, `project.urls`, minimum Python.
- Governance/contribution docs: `CONTRIBUTING.md` (with the clean-room affirmation), `SECURITY.md` (vulnerability reporting), `CHANGELOG.md` (0.1.0 capabilities), `RELEASING.md` (SemVer + how to cut a release).
- Consolidated `NOTICE` file aggregating third-party attributions (MITRE ATT&CK notice, OWASP, and the concept-originator credits the catalog cites), complementing the runtime `risqlet catalog licenses` command; ensure `LICENSE`, `LICENSE-CATALOG`, and `NOTICE` ship in the sdist/wheel.
- A `py.typed` marker so downstream users get the package's types.
- A tag-triggered release workflow template (build + publish via PyPI trusted publishing/OIDC) — shipped, not run.
- A `docs/release-checklist.md` enumerating the **human-gated** steps (claim PyPI/npm/GitHub names, legal review of the clean-room catalog, first publish, optional `risqlet.dev`), each marked as requiring the maintainer.

## Capabilities

### New Capabilities

- `release-readiness`: the packaging-metadata completeness, governance/attribution artifacts, release workflow, and the human-gated checklist that together make the project publishable.

### Modified Capabilities

_None — additive project metadata and docs; no runtime behavior changes._

## Impact

- New: `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `RELEASING.md`, `NOTICE`, `docs/release-checklist.md`, `src/risqlet/py.typed`, `.github/workflows/release.yml` (template); `pyproject.toml` metadata expanded.
- No source-behavior or register-format change; existing 260 tests unaffected. A small test asserts packaging metadata and shipped-file completeness.
- Explicitly does NOT publish anything or claim any external name — those remain maintainer actions, enumerated in the checklist.
