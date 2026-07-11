# Design: add-release-prep

## Context

Queue item 6, the release gate. Everything technical is done; this change is packaging, governance, and attribution — plus an honest boundary around the steps only the maintainer can perform (credentials, legal judgement, irreversible publish). The clean-room protocol and per-pack `notice` fields already exist; this consolidates them for distribution. Naming is settled (`risqlet`, verified free on PyPI/npm/GitHub with no in-field trademark collision).

## Goals / Non-Goals

**Goals:** make the repo publishable — complete packaging metadata, standard OSS governance files, a single consolidated third-party `NOTICE`, a release workflow, and a checklist that names the human-gated actions so nothing is ambiguous or silently skipped.

**Non-Goals (and must stay non-goals — they are maintainer actions):** actually publishing to PyPI/npm, claiming the GitHub org/repo, pushing to a public remote, obtaining the legal opinion, buying `risqlet.dev`. The agent lacks the credentials and the standing to do these; doing them would be exactly the kind of irreversible outward-facing action to leave to the human.

## Decisions

### D1. Packaging metadata (`pyproject.toml`)

Fill the standard publishable fields: `description` (one line), `readme = "README.md"`, `license`, `authors`, `keywords` (risk analysis, risk-based testing, FMEA, test strategy, MCP, agent, quality), `classifiers` (Development Status, Intended Audience :: Developers, License :: OSI Approved :: Apache Software License, Programming Language :: Python :: 3.12/3.13, Topic :: Software Development :: Quality Assurance / Testing), and `project.urls` (Homepage, Repository, Issues, Changelog). Ensure `LICENSE`, `LICENSE-CATALOG`, and `NOTICE` are included in the sdist/wheel (hatchling includes top-level `LICENSE*` by default; add `NOTICE` explicitly if needed). Keep version at `0.1.0` for the first release.

### D2. Third-party `NOTICE`

A single top-level `NOTICE` (Apache-2.0 §4(d) convention) that reproduces: the MITRE ATT&CK attribution/trademark statement (mirroring the `mitre-attack` pack's `notice`), the OWASP taxonomy note, and a "concepts credited" section listing the originators the catalog provenance references (ISO/IEC 25010 characteristic names; HAZOP; STRIDE/Microsoft; HTSM/SFDIPOT — Bach & Bolton; pre-mortem — Klein; consistency oracles — Bolton & Bach; second-order-risk — Wiberg) as concept sources, not text sources. This is the distribution-time complement to the runtime `risqlet catalog licenses` command; the design note states both exist and why.

### D3. Governance docs

- `CONTRIBUTING.md`: dev setup (`uv sync`, `uv run pytest`, `uv run ruff check`), the PR checklist, and — load-bearing — the **clean-room affirmation** for any catalog-pack contribution (restating CLEAN-ROOM.md rule 5).
- `SECURITY.md`: how to report a vulnerability (a security-adjacent tool should have one); private disclosure contact, no public issues for vulns.
- `CHANGELOG.md`: Keep-a-Changelog format, one `0.1.0` entry summarizing the shipped capabilities (register + CLI, catalogs, skills, MCP, trace loop, CI re-assessment, security packs).
- `RELEASING.md`: SemVer policy, and the mechanical release steps (bump version, update CHANGELOG, tag `vX.Y.Z`, workflow publishes).

### D4. Types marker

Add `src/risqlet/py.typed` (PEP 561) so downstream code gets the package's type hints; ensure it ships (hatchling includes package data).

### D5. Release workflow (template, not run)

`.github/workflows/release.yml`: on tag `v*`, build sdist+wheel with `uv build` and publish via **PyPI Trusted Publishing (OIDC)** — no stored token. It is inert until (a) the repo exists on GitHub and (b) the maintainer configures the PyPI trusted-publisher link. The design and the checklist both state it will not run before those human steps.

### D6. Human-gated checklist (`docs/release-checklist.md`)

An explicit, ordered list of what only the maintainer can do, each flagged `[maintainer]`: verify names still free and **claim** `risqlet` on PyPI + npm + the GitHub org/repo; obtain a **legal review** of the clean-room catalog before public distribution; (optional) acquire `risqlet.dev` if the schema `$id` URLs should resolve — noting JSON-Schema `$id` is an identifier and need not resolve, so this is cosmetic; configure PyPI trusted publishing; cut the first release (`v0.1.0`). The checklist is the deliverable that makes the boundary unambiguous.

### D7. Verification

One lightweight test (`tests/test_packaging.py`): asserts the required `pyproject` metadata fields are present and non-empty, that `NOTICE`/`LICENSE`/`LICENSE-CATALOG` exist, that `py.typed` exists, and that a built wheel contains `LICENSE`, `NOTICE`, and the skills/catalog/CI package data (reusing the wheel-inspection approach already used for CI templates). No network, no publish.

## Risks / Trade-offs

- [Agent oversteps into publishing] → hard non-goal; the workflow is inert and the checklist marks every outward action `[maintainer]`. Nothing in this change pushes, publishes, or claims a name.
- [NOTICE and per-pack `notice` drift] → the NOTICE's MITRE section is copied from the pack; a comment in NOTICE points at `risqlet catalog licenses` as the authoritative runtime source, and the packaging test could (optionally) assert the MITRE string appears in both.
- [Metadata classifiers go stale] → kept minimal and standard; not asserted beyond presence.

## Migration Plan

Additive project metadata and docs. No runtime or format change.

## Open Questions

- Final maintainer identity/email and disclosure contact for `SECURITY.md`/`authors` — placeholder used, flagged in the checklist for the maintainer to set before publish.
