# Release checklist

The repository is publish-*ready*: packaging metadata, governance docs, the
consolidated `NOTICE`, and an (inert) release workflow are all in place. The
steps below are the ones that only the **maintainer** can perform — each is
marked `[maintainer]`. This project's tooling does not perform any of them:
it publishes nothing and claims no external name on its own.

## Before first publish

- [ ] `[maintainer]` **Claim the name.** Verify `risqlet` is still free and
      register/reserve it on **PyPI** (and, if desired, npm and the GitHub
      org/repo). PyPI and npm names are first-come; do this early.
- [ ] `[maintainer]` **Legal review of the clean-room catalog.** Have counsel
      review `src/risqlet/catalog/packs/` and `NOTICE` against the clean-room
      protocol (`CLEAN-ROOM.md`) before public distribution — especially the
      MITRE ATT&CK and OWASP attributions and the ISO/HTSM concept credits.
- [ ] `[maintainer]` **Set the maintainer contact.** Confirm the author/email in
      `pyproject.toml` and the reporting address in `SECURITY.md`.
- [ ] `[maintainer]` **Review what goes public.** Decide whether
      `docs/experiments/` (dogfooding transcripts that describe findings —
      including unpatched vulnerabilities — in other repositories) belongs in a
      public repo. Exclude or scrub if any target project is private or the
      findings are sensitive.

## Configure automated publishing

- [ ] `[maintainer]` **Create the GitHub repository** and push `main`.
- [ ] `[maintainer]` **Configure PyPI Trusted Publishing** for the repo and the
      `release.yml` workflow (PyPI → project → Publishing → add a GitHub
      publisher). No API token is stored; the workflow uses OIDC.
- [ ] `[maintainer]` Create a GitHub environment named `pypi` (optionally with
      required reviewers) to gate the publish job.

## Cut the release

- [ ] `[maintainer]` Follow `RELEASING.md`: green CI, bump version, update
      `CHANGELOG.md`, tag `v0.1.0`, push the tag. The workflow builds and
      publishes.

## Optional

- [ ] `[maintainer]` Acquire `risqlet.dev` **only if** the schema `$id` URLs
      should resolve — JSON-Schema `$id` is an identifier and need not resolve,
      so this is cosmetic.
