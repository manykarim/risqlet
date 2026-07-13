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

Publishing is **manual**: pushing a tag never publishes anything. You tag the
release, then dispatch the `release` workflow and choose what to produce.

1. Ensure `main` is green: `uv run pytest && uv run ruff check .`.
2. Regenerate schemas if models changed:
   `uv run python -m risqlet.model.schema_gen` (the test suite fails if stale).
3. Bump `version` in `pyproject.toml`.
4. Move the `## [Unreleased]` items in `CHANGELOG.md` under a new
   `## [X.Y.Z] - <date>` heading and update the compare/link footnotes.
5. Commit: `release: vX.Y.Z`.
6. Tag and push: `git tag vX.Y.Z && git push --tags`.
7. Dispatch the release: **Actions → release → Run workflow**, enter the tag
   (`vX.Y.Z`) and pick a **mode**:
   - `gh-draft` (default) — build, then create a **draft** GitHub release with
     the sdist + wheel attached. Review/edit the notes, then publish it by hand.
   - `gh-release` — build, then create a **published** GitHub release with the
     artifacts attached.
   - `pypi` — build, **publish to PyPI** (token auth), then create a published
     GitHub release. This is the full release.

   Every mode first runs the gated build (sync, ruff, pytest, `uv build`) and
   attaches the same artifacts to the GitHub release.

## First-time publish prerequisites

The release workflow ships safe: it only runs when dispatched, and the `pypi`
mode fails fast until the token secret exists. Before the first PyPI publish a
maintainer must (see `docs/release-checklist.md`): claim the `risqlet` name on
PyPI, add a **`PYPI_API_TOKEN`** repository secret (Settings → Secrets and
variables → Actions), and set the maintainer contact in
`SECURITY.md`/`pyproject.toml`. GitHub releases need no extra secret.
