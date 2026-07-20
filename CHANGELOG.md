# Changelog

All notable changes to risqlet are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- **A malformed user-editable YAML file no longer prints a raw traceback.** A
  duplicate key (or other parse error) in `config.yaml`, a `register/*.yaml` risk, a
  user **policy** pack (`.risqlet/policies/`), or a user **catalog** pack
  (`.risqlet/catalogs/`) raised ruamel's `YAMLError`, which the CLI did not catch —
  so `status`, `check`, `score`, `diff`, `validate`, and `catalog list` dumped a
  traceback. `check` is the CI gate, so it landed in users' CI logs. Every
  user-editable YAML load now wraps a parse error as the layer's domain error
  (`StoreError` / `PolicyError` / `CatalogError`) with the file path and the concise
  reason (e.g. `found duplicate key "constraints" (line 20)`), and the CLI treats all
  three as clean errors — so these commands exit 1 with a readable message. Non-YAML
  errors still propagate, and reads of shipped package data are unaffected.

### Changed
- **`guardrails install` refuses a POSIX shell hook on Windows on every path, not
  just the default one.** The refusal (shell hooks can't run on Windows — they shell
  out to bash/python3) previously lived only in the verify gate, so `--no-verify`
  silently wrote a non-runnable hook into `settings.json` and `--force` wrote it with
  only a warning. The unrunnable hooks are now removed from the plan before install,
  so a hook that cannot run never lands on any path (default / `--no-verify` /
  `--force`); the install degrades to permissions-only, with the skip reported.
  Platform-impossibility is not forceable — `--force` still overrides an ordinary
  verification failure, but cannot will a shell hook into working on Windows. Because
  the guardrails lock is written from the same filtered plan, `guardrails diff` now
  correctly reports a refused hook as missing rather than falsely in-sync.

### Fixed
- **`risqlet setup` no longer crashes on a `CLAUDE.md` that an older risqlet wrote.**
  Making reads strict UTF-8 was right for what risqlet writes from now on and wrong
  for what was already on disk — including files risqlet itself wrote in cp1252
  before that fix. A Windows user upgrading hit
  `UnicodeDecodeError: ... byte 0x97 ...` on the em-dash in risqlet's *own*
  instructions block. This was a regression introduced by the encoding fix, not a
  pre-existing bug, and it hit exactly the users that fix was for.
  Reads of markdown instructions files and the register now fall back to cp1252,
  recover the text intact, report the recovery, and rewrite the file as UTF-8 — so a
  file heals the first time risqlet touches it. The tolerance is scoped by evidence to
  where risqlet's own output contained non-ASCII; the JSON and TOML configs stay
  strict, since risqlet only ever wrote ASCII there and both formats mandate UTF-8.
- **Text I/O is now explicitly UTF-8 everywhere, fixing silent data corruption on
  Windows.** risqlet read and wrote every file — the register, `config.yaml`,
  catalog packs, agent configs — in Python's *locale* encoding. That is UTF-8 on
  Linux and macOS, so it never showed there, but cp1252 on Windows, where it failed
  two ways: reads of our own UTF-8 data corrupted silently (an em-dash, present in
  every catalog pack, became `â€"` with nothing raising), and writes of text outside
  cp1252 crashed with `UnicodeEncodeError` — a risk statement containing `→` or CJK
  was enough. `git diff` output and hook stdout were exposed too, via
  `subprocess(text=True)`, and risqlet's **own stdout** was locale-encoded — so
  `--json` output and the `risqlet mcp` stdio transport, both machine interfaces
  agents parse, emitted cp1252 on Windows. The CLI now pins its streams to UTF-8. No on-disk format changed: every file was already UTF-8;
  risqlet now reads them as what they are. `events.jsonl` was never affected —
  `json.dumps` escapes non-ASCII to `\uXXXX` by default.
- **Output no longer depends on the host's line endings.** Text writes pin
  `newline="\n"`, so a register or export written on Windows is byte-identical to
  one written on Linux. Python's text mode had been translating `\n` to `\r\n`,
  quietly making "deterministic output" untrue across platforms.

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
