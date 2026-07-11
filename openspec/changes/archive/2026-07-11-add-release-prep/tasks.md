# Tasks: add-release-prep

## 1. Packaging metadata

- [x] 1.1 Expand pyproject.toml: description, readme, license, authors (placeholder flagged), keywords, classifiers (Apache-2.0 OSI + Python 3.12/3.13 + QA/Testing topics), project.urls (Homepage/Repository/Issues/Changelog); ensure LICENSE/LICENSE-CATALOG/NOTICE ship in wheel+sdist
- [x] 1.2 Add src/risqlet/py.typed marker

## 2. Attribution and governance docs

- [x] 2.1 Write NOTICE (MITRE ATT&CK statement, OWASP taxonomy note, credited-concepts section; points to `risqlet catalog licenses`)
- [x] 2.2 Write CONTRIBUTING.md (dev setup, PR checklist, clean-room affirmation for catalog contributions)
- [x] 2.3 Write SECURITY.md (private vulnerability reporting; placeholder contact flagged)
- [x] 2.4 Write CHANGELOG.md (Keep-a-Changelog; 0.1.0 capability summary) and RELEASING.md (SemVer + release steps)

## 3. Release workflow and checklist

- [x] 3.1 Author .github/workflows/release.yml (tag v* → uv build → PyPI trusted publishing; inert until maintainer setup)
- [x] 3.2 Write docs/release-checklist.md enumerating maintainer-only steps (claim PyPI/npm/GitHub, legal review, trusted-publishing config, first release; optional risqlet.dev) each marked [maintainer]

## 4. Verification

- [x] 4.1 tests/test_packaging.py: required pyproject metadata present + non-empty; NOTICE/LICENSE/LICENSE-CATALOG/py.typed exist; built wheel contains LICENSE, NOTICE, py.typed, and skills/catalog/ci package data; no network/publish

## 5. Wrap-up

- [x] 5.1 Full pytest + ruff (unpiped exit codes); README top matter links the new governance docs; commit. NO publish, NO external name claim, NO push to a public remote (maintainer actions per the checklist)
