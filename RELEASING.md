# Releasing risqlet

risqlet follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **MAJOR** — breaking changes to the `.risqlet/` register format, the CLI
  surface, or the published JSON Schemas.
- **MINOR** — new commands, catalog packs, guardrail templates, or other
  backward-compatible capabilities.
- **PATCH** — fixes and doc changes with no interface impact.

The register format carries `schema_version`; a bump to it is a MAJOR change and
must ship with a migration note.

## Cutting a release

1. Ensure `main` is green: `uv run pytest && uv run ruff check .`.
2. Regenerate schemas if models changed:
   `uv run python -m risqlet.model.schema_gen` (the test suite fails if stale).
3. Bump `version` in `pyproject.toml`.
4. Move the `## [Unreleased]` items in `CHANGELOG.md` under a new
   `## [X.Y.Z] - <date>` heading and update the compare/link footnotes.
5. Commit: `release: vX.Y.Z`.
6. Tag and push: `git tag vX.Y.Z && git push --tags`.
7. The `release.yml` workflow builds the sdist+wheel and publishes to PyPI via
   Trusted Publishing.

## First-time publish prerequisites

The release workflow is inert until a maintainer completes the one-time setup —
see `docs/release-checklist.md`. In short: claim the name on PyPI, configure
PyPI Trusted Publishing for the GitHub repo, and set the maintainer contact in
`SECURITY.md`/`pyproject.toml`.
