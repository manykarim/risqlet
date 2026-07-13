## Why

The shipped `release.yml` auto-publishes to PyPI on every `v*` tag push via
Trusted Publishing (OIDC). The maintainer wants publishing to stay **manual and
deliberate**: a tag should never silently push to PyPI, and the maintainer wants
to choose per-run whether to cut a GitHub release draft, a published GitHub
release, or a full PyPI publish. PyPI auth will use an **API-token secret added
to GitHub later**, not Trusted Publishing.

## What Changes

- **BREAKING** (workflow behaviour): replace the auto-on-tag OIDC publish with a
  **manually dispatched, mode-selectable** release workflow. Tagging alone no
  longer publishes anything.
- `release.yml` becomes `workflow_dispatch`-driven with two inputs:
  - `tag` — the existing `vX.Y.Z` tag to build and release from (checked out).
  - `mode` — one of:
    - `gh-draft` (default, safest): build, then create a **draft** GitHub
      release with the sdist + wheel attached.
    - `gh-release`: build, then create a **published** GitHub release with the
      sdist + wheel attached.
    - `pypi`: build, publish to **PyPI using the token secret**, then create a
      published GitHub release with the artifacts (a full release).
- Every mode runs the same gated **build** job first (uv sync, ruff, pytest,
  `uv build`) and uploads the dist as a workflow artifact; downstream jobs
  attach those same files to the GitHub release.
- PyPI auth switches from OIDC to **token** (`secrets.PYPI_API_TOKEN`). The
  `pypi` job preflights the secret and fails with a clear message if it is
  absent, so the workflow is safe to ship before the secret exists.
- `RELEASING.md` and `docs/release-checklist.md` are updated to describe the
  manual, token-based, mode-selectable process (replacing the Trusted-Publishing
  instructions). CHANGELOG `[Unreleased]` notes the new release process.
- The packaging test that pins the workflow to OIDC is updated to assert the new
  manual/token/multi-mode shape.

Out of scope: claiming the PyPI name, adding the token secret, and actually
cutting a release — all remain maintainer actions performed outside this change.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `release-readiness`: the "inert release workflow" requirement changes from a
  tag-triggered Trusted-Publishing auto-publish to a manually dispatched,
  mode-selectable (GH draft / GH release / PyPI), token-authenticated pipeline
  that attaches build artifacts to the GitHub release; the maintainer-actions
  requirement is updated to reference configuring the PyPI **API token secret**
  instead of Trusted Publishing.

## Impact

- `.github/workflows/release.yml` (rewritten).
- `RELEASING.md`, `docs/release-checklist.md`, `CHANGELOG.md` (docs).
- `tests/test_packaging.py` (workflow-shape assertion).
- No runtime/library code, CLI, or package-data changes. No outward action:
  nothing is published and no secret is added by this change.
