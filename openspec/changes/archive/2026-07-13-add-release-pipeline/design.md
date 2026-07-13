## Context

`release.yml` today fires on `push: tags: v*` and publishes to PyPI via Trusted
Publishing (OIDC), gated by a `pypi` environment. The maintainer wants publishing
to be an explicit, per-run human decision, and will authenticate PyPI with an API
token secret added later — not OIDC. GitHub-hosted runners already provide `gh`
and an automatic `GITHUB_TOKEN`, so creating GitHub releases needs no extra
secret; only PyPI does.

## Goals / Non-Goals

**Goals**
- One workflow, manually dispatched, that can produce a GH release draft, a
  published GH release, or a full PyPI publish — maintainer's choice per run.
- Same tested build feeds every mode; artifacts attach to the GH release.
- Token-based PyPI auth; workflow ships safely before the secret exists.

**Non-Goals**
- Claiming the PyPI name, adding the secret, or cutting a real release.
- Auto-release on tag push (explicitly removed).
- Signing/attestation, multi-registry (npm) publishing.

## Decisions

- **`workflow_dispatch` with `tag` + `mode` inputs, not tag-push.** A tag push
  cannot carry a mode choice and risks accidental publishes; manual dispatch
  makes the intent explicit. `tag` is checked out so the build matches the tag.
  *Alternative considered:* tag-push that always creates a draft — rejected as a
  second, confusing code path; manual dispatch alone is clearer.
- **Three modes as one `choice` input**, default `gh-draft` (least destructive).
  Job-level `if:` on `inputs.mode` selects which downstream jobs run. `pypi` mode
  also creates the published GH release, so "full publish" yields both PyPI and a
  GitHub release in one run.
- **Token auth via `secrets.PYPI_API_TOKEN`** passed as `password:` to
  `pypa/gh-action-pypi-publish`. The OIDC `id-token: write` permission is
  removed. A preflight step reads the token into an env var and `exit 1`s with an
  `::error::` if empty — GitHub `if:` cannot test secret presence, so the check
  lives in a step. *Alternative:* keep OIDC — rejected per maintainer's explicit
  token choice.
- **`gh release create <tag> dist/* --generate-notes [--draft]`** for the GH
  release, using `GH_TOKEN: ${{ github.token }}` and `contents: write`. Reuses
  the artifacts downloaded from the build job.
- **Keep the `pypi` environment** on the publish job so a maintainer can add
  required reviewers later as a second gate.

## Risks / Trade-offs

- [Maintainer picks `pypi` before adding the token] → preflight step fails loudly
  with a clear message; nothing is uploaded.
- [A tag/mode mismatch republishes an existing version] → PyPI rejects duplicate
  versions; GH `release create` errors if the release already exists. Both fail
  safe; documented in `RELEASING.md`.
- [`--generate-notes` differs from CHANGELOG] → acceptable; RELEASING.md tells the
  maintainer to edit the draft before publishing. Draft is the default mode.

## Migration Plan

- Replace `release.yml` wholesale; update `RELEASING.md` and
  `docs/release-checklist.md` from Trusted-Publishing to token/manual/multi-mode;
  note the change in CHANGELOG `[Unreleased]`; update the packaging test.
- Rollback: restore the previous OIDC `release.yml` from git history. No state to
  migrate; nothing has been published.

## Open Questions

- None. Secret name fixed as `PYPI_API_TOKEN`; maintainer adds it when ready.
