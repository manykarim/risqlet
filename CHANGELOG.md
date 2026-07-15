# Changelog

All notable changes to risqlet are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Cross-platform CI.** The `test` workflow now runs the full suite on Linux,
  macOS, and Windows on every push and PR. Each platform also builds the wheel,
  installs it into a fresh venv with no dev dependencies, and drives the real
  `risqlet` console script from outside the repo — the first check of the artifact
  users actually get, rather than the editable source install every test used
  before. `risqlet setup` is smoke-tested for every agent adapter on every platform.
  Platform differences are `posix_only` skips *inside* the suite, so they are
  visible with a stated reason rather than omitted from a per-OS test selection.
- Supported operating systems are now declared in `pyproject.toml` classifiers, and
  a test ties them to the CI matrix — dropping a platform from CI fails that test
  instead of leaving a stale promise on PyPI.

### Fixed
- **`detect()` no longer reports an agent as installed on the strength of a project
  directory.** Adapter dirs like `.claude` and `.github` resolve against the current
  working directory, so any repo containing one made setup report that agent as
  detected — on a machine with the agent nowhere in sight. Detection now
  distinguishes "found on PATH" from "used by this project" / "configured for you",
  and the interactive picker says which. Agents found only via a project directory
  are still offered (that directory is good evidence the *project* uses them).
- **`risqlet guardrails` reports Windows as unsupported instead of crashing.** The
  timeout path called `os.killpg`/`os.getpgid`, which do not exist on Windows, so an
  unsupported platform surfaced as an `AttributeError`. Shell guardrail hooks are now
  refused on Windows with a stated reason and skipped by the install gate. This makes
  the existing gap honest; it does not close it — `guardrails` remains POSIX-only.
- **`risqlet setup` now installs the Claude Code check hook on Windows.** It
  previously failed with `skip claude/hooks: hook failed verification: bash not on
  PATH`: the hook was a POSIX shell one-liner that spawned `python3` only to read
  the edited file path out of Claude's stdin payload. `risqlet check` now parses
  that payload itself via the new `--hook-input claude` flag, so the installed hook
  is a single bare command — `risqlet check --hook-input claude --json` — needing no
  shell and no second interpreter on any platform. Verification no longer requires
  `bash`; it runs the real command against a synthetic payload instead.
  Note this fixes `setup` only — `risqlet guardrails install` remains unsupported on
  Windows, as its hook templates are POSIX shell and its verifier uses POSIX-only
  process handling.
- **The `risqlet ci init --target claude-hooks` template never worked, on any
  platform.** It read `$CLAUDE_TOOL_FILE_PATH`, an environment variable Claude Code
  does not set (the payload arrives as JSON on stdin), so the hook silently checked
  an empty path. It now emits the same command `setup` installs.

### Added
- `risqlet check --hook-input claude` reads a Claude Code hook payload from stdin
  and checks the file it names. Distinct from `--stdin` (newline-separated paths),
  which is unchanged. Because it runs inside an agent's edit loop it reports only
  and always exits 0 — a malformed payload or an internal error is a silent no-op,
  and `ci_gate: block` does not fail the edit. The gate's blocking behaviour is
  unchanged for CI use.
- A `test` CI workflow running the suite on Linux and the hook-related tests plus a
  real `risqlet setup` on Windows, so the platform this bug occurred on is covered.

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
