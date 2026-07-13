## 1. Rewrite the release workflow

- [x] 1.1 Replace `.github/workflows/release.yml`: trigger on `workflow_dispatch` with `tag` (string) and `mode` (choice: `gh-draft` default, `gh-release`, `pypi`) inputs; remove the `push: tags` trigger.
- [x] 1.2 `build` job: checkout `inputs.tag`, install uv, `uv sync`, `uv run ruff check .`, `uv run pytest`, `uv build`; upload `dist/` as an artifact.
- [x] 1.3 `github-release` job (runs when `mode` is `gh-draft`, `gh-release`, or `pypi`): download dist, `gh release create <tag> dist/* --generate-notes` with `--draft` only for `gh-draft`; `permissions: contents: write`, `GH_TOKEN: ${{ github.token }}`.
- [x] 1.4 `pypi-publish` job (runs only when `mode == pypi`, `environment: pypi`): download dist; preflight step that fails with an `::error::` if `PYPI_API_TOKEN` is empty; publish via `pypa/gh-action-pypi-publish@release/v1` with `password: ${{ secrets.PYPI_API_TOKEN }}`; remove the OIDC `id-token: write` permission.

## 2. Update docs and changelog

- [x] 2.1 Rewrite the release steps in `RELEASING.md` to describe manual dispatch with `tag` + `mode`, token-based PyPI, and the three modes.
- [x] 2.2 Update `docs/release-checklist.md`: replace the Trusted-Publishing setup with "add `PYPI_API_TOKEN` secret", and add "dispatch the release workflow (tag + mode)" as a maintainer step.
- [x] 2.3 Add a `CHANGELOG.md` `[Unreleased]` note describing the manual, mode-selectable, token-authenticated release workflow.

## 3. Update tests and verify

- [x] 3.1 Replace `test_release_workflow_is_tag_triggered_trusted_publishing` in `tests/test_packaging.py` with an assertion of the new shape: `workflow_dispatch`, a `mode` input with the three choices, `PYPI_API_TOKEN`, and no `id-token: write`.
- [x] 3.2 Validate the workflow YAML parses (e.g. a small test or `python -c` yaml load) and run `uv run pytest -q` + `uv run ruff check .` green.
- [x] 3.3 `openspec validate add-release-pipeline --strict` passes.
