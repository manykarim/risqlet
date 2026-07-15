## 1. Make the suite platform-aware

Ordered first: the suite must be honest about platforms *before* a Windows job runs
it, or the first run is noise rather than evidence.

- [x] 1.1 Register pytest markers in `pyproject.toml` (`[tool.pytest.ini_options]`
  `markers`): `posix_only` — "requires POSIX process handling or a shell hook
  template; risqlet guardrails is not supported on Windows".
- [x] 1.2 Mark the guardrail-hook tests in `tests/test_hook_verification.py` and
  `tests/test_guardrails.py` `posix_only` — those that render or verify a shell hook
  template, or that exercise the timeout/kill path. Do not mark tests that are
  platform-neutral (planning, diff, models).
- [x] 1.3 Apply the skip in `tests/conftest.py` via a `pytest_collection_modifyitems`
  hook: skip `posix_only` on Windows with the reason string, so the reason appears in
  the run rather than the test vanishing.
- [x] 1.4 Verify on Linux that nothing is skipped (`-m posix_only` collects, runs, and
  passes), so the marker cannot silently disable tests on the platform that supports
  them.

## 2. Make `detect()` honest

- [x] 2.1 Change `detect()` in `src/risqlet/setup/engine.py` to distinguish an agent
  found on PATH from one inferred from a directory, and to record which. Keep the
  returned agent-id list working for existing callers (`cmd_setup`, `--all-detected`).
- [x] 2.2 Note in the adapter data or `detect()` that unanchored dirs (`.claude`,
  `.cursor`, `.vscode`, `.github`) resolve against the cwd and therefore describe the
  *project*, not the machine.
- [x] 2.3 Rewrite `tests/test_setup.py::test_detect_returns_installed` to assert the
  real condition instead of passing because `.claude/` is committed: assert a
  PATH-detected agent is reported as such, and that a project-dir-only agent is
  reported as inferred-from-directory.
- [x] 2.4 Test that `detect()` run from a directory with no agent dirs and no agent
  binaries returns nothing — the case that currently cannot fail.

## 3. Guardrails degrades honestly on Windows

- [x] 3.1 In `src/risqlet/guardrails/verify.py`, guard the POSIX-only kill path
  (`os.killpg`/`os.getpgid`) so an unsupported platform is reported rather than
  raising `AttributeError`. Use `proc.kill()` as the fallback termination.
- [x] 3.2 Report guardrail hook verification as unsupported on Windows with a stated
  reason, consistent with the `posix_only` marker's boundary. Do not attempt to make
  shell templates work there.
- [x] 3.3 Test the fallback path without needing Windows (monkeypatch `os.killpg`
  absent / `os.name`), so the degradation itself is covered.

## 4. Install-and-run the built wheel

- [x] 4.1 Add a test/helper that builds the wheel (`uv build`), creates a fresh venv,
  installs the wheel with no dev dependencies, and runs the installed `risqlet`
  console script from a cwd outside the repo — so the source tree cannot satisfy an
  import the wheel misses. Mark it slow; it is the release-readiness check, not a
  unit test.
- [x] 4.2 Exercise the shipped package data from that clean install: `setup`
  (adapters), `ci init` (templates), `catalog list` (packs), `skills install`
  (bundled skills). Each must succeed from the wheel alone.
- [x] 4.3 Keep the existing `test_wheel_ships_license_notice_and_data` namelist check
  — it is cheap and catches a different thing (LICENSE/NOTICE/py.typed) — but it no
  longer stands in for proof that the artifact runs.

## 5. The CI matrix

- [x] 5.1 Replace `.github/workflows/test.yml` with a `matrix` over
  `ubuntu-latest`, `macos-latest`, `windows-latest`, running `uv sync` and the
  **full** suite on each. Do not select test subsets per OS — platform differences
  belong in the suite as skips (design decision 1).
- [x] 5.2 Keep lint (`ruff check .`) on Linux only — it is platform-independent and
  running it three times buys nothing.
- [x] 5.3 Add a `clean-install` job per platform: build the wheel, install into a
  fresh venv, run the CLI and the package-data commands from outside the repo.
- [x] 5.4 Add an `agent-setup` smoke job per platform: run `risqlet setup` for every
  adapter risqlet ships, assert artifacts land, and **fail on a skip whose reason is a
  verification failure** while tolerating legitimate skips (global-only MCP,
  unsupported components). This is the check that would have caught the Windows hook
  bug.
- [x] 5.5 Make each job's failure message name what broke and on which platform —
  a red matrix cell should not require reading 200 lines of pytest output.

## 6. Docs and honesty

- [x] 6.1 State the platform support matrix in README: CLI/register/check/setup/hook
  on Linux+macOS+Windows; `guardrails` POSIX-only. Do not claim more than CI runs.
- [x] 6.2 Add/verify `classifiers` in `pyproject.toml` name only the OSes CI
  exercises (`Operating System :: OS Independent` is a claim — if guardrails is
  POSIX-only, say what is actually independent).
- [x] 6.3 CHANGELOG entry: cross-platform CI added; `detect()` no longer reports an
  agent as installed on the strength of a project directory; guardrails reports
  unsupported-on-Windows instead of crashing.

## 7. Verify

- [x] 7.1 Full suite + lint green on Linux (this host).
- [x] 7.2 Simulate what can be simulated here: run the clean-install job's steps
  locally (build → fresh venv → install → run from outside the repo) and confirm the
  package data commands work from the wheel.
- [x] 7.3 Confirm the `posix_only` marker skips on a simulated Windows
  (`monkeypatch` / `-m "not posix_only"`) and that the remaining suite passes — the
  closest approximation to the Windows job available from Linux.
- [x] 7.4 `openspec validate add-cross-platform-ci --strict`.
- [ ] 7.5 **Push and watch all three matrix legs.** The macOS and Windows jobs cannot
  be run from this host; until they have executed, this change is a hypothesis. If
  they have not run at hand-off, say so plainly rather than reporting the change as
  verified.
