# Changelog

All notable changes to risqlet are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- The release workflow is now **manually dispatched and mode-selectable**: a tag
  push no longer publishes anything. Dispatching `release` with a tag and a mode
  produces a draft GitHub release, a published GitHub release, or a full PyPI
  publish — every mode builds, tests, and attaches the sdist + wheel to the
  GitHub release. PyPI auth moved from Trusted Publishing (OIDC) to an API-token
  secret (`PYPI_API_TOKEN`); the `pypi` mode fails fast until the secret is set.
- Guardrail hooks are now **verified in the target environment** before install
  (required tools on PATH, shell syntax, benign-passes/violation-caught behaviour,
  timeout) and install is gated by default (`--no-verify` / `--force` to override);
  new `risqlet guardrails verify`. Installed Claude Code hooks now carry the
  **real** command (previously a `true` placeholder) and read the changed file
  from Claude's stdin JSON payload. `coverage-check-stop` derives the project's
  test command instead of hardcoding `make test`.

## [0.1.0] - 2026-07-11

First release. risqlet is an agent-facing risk-analysis, mitigation, and
test-strategy toolkit with a CLI-first deterministic core and all state in a
repo-native `.risqlet/` register.

### Added

- **Register & core** — file-per-risk YAML register, append-only decision log
  with human-principal gates, scoring policies as data (`sod-ap-v1` with
  severity-dominant Action-Priority bands, `li-v1` 3×3), and the `risqlet`
  CLI (`init`, `validate`, `status`, `score`, `export`).
- **Knowledge catalogs** — six clean-room packs (four default: `iso25010`,
  `techniques`, `heuristics`, `guidewords`; two opt-in security packs:
  `mitre-attack`, `owasp-web`) with `risqlet catalog list/show/search/licenses`.
- **Agent skills** — portable `risk-analysis` and `risk-quickscan` playbooks
  and `risqlet skills install` for Claude Code and other agents.
- **MCP adapter** — stateless stdio server (`risqlet mcp`, `risqlet[mcp]`
  extra) exposing the core as gate-preserving tools.
- **Ensemble tooling** — `risqlet dedupe` / `merge` and scoring-disagreement
  surfacing.
- **Trace loop** — `risqlet trace ingest/status` for Robot Framework and JUnit
  results, mitigation coverage, and detection-evidence notes.
- **Continuous re-assessment** — `risqlet diff` / `check` and `risqlet ci init`
  templates (GitHub Actions, GitLab CI, Claude Code hooks).
- **Guardrail generation** — `risqlet guardrails generate/diff/install` turns
  accepted mitigations into risk-tagged coding-agent guardrails (hooks,
  AGENTS.md rules, permissions, pre-commit/CI) from a vetted template library.

[Unreleased]: https://github.com/manykarim/risqlet/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/manykarim/risqlet/releases/tag/v0.1.0
