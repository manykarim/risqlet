## Why

risqlet claims to be an agent-facing toolkit you install and point at a coding
agent. Nothing proves that claim on any platform except by hand.

The repo has no test CI. `fix-windows-hook-install` added a first `test` workflow
(Linux full suite, Windows hook subset), but that job has never run, and its Windows
scope was hand-picked from reasoning rather than evidence. macOS is untested
entirely. The evidence that this gap is real, not theoretical:

- **`risqlet setup` was broken on Windows for every user** and nobody knew until a
  bug report. The verification gate caught it correctly; no CI ran to see it.
- **`ci init --target claude-hooks` never worked on any platform** — it read an
  environment variable Claude Code does not set. Tests checked the template parsed
  and named real subcommands, never that it did anything.
- **Nothing installs the package and runs it.** `test_wheel_ships_license_notice_and_data`
  builds a wheel and inspects its file list, then throws it away. A wheel whose
  entry point or package data is broken on Windows would pass today.

Every test today runs against an editable install from the source tree. That is the
one configuration no user has.

## What Changes

- **A `test` workflow matrix over Linux, macOS, and Windows**, replacing the
  Linux+Windows job added by `fix-windows-hook-install`. Runs on push, PR, and
  dispatch.
- **A clean-install job per platform**: build the wheel, install it into a fresh
  venv with no dev dependencies and no source tree on `sys.path`, and drive the
  real `risqlet` console script. This is the first test of the artifact users
  actually get — it catches broken entry points and missing package data
  (`setup/adapters/*.yaml`, `ci/templates/`, `guardrails/templates/`, catalogs,
  bundled skills) on each OS.
- **An agent-setup smoke test per platform**: run `risqlet setup` for each adapter
  the platform supports, assert the expected artifacts land, and assert no
  component is silently skipped. This is the check that would have caught the
  Windows hook bug.
- **Honest platform markers.** `risqlet guardrails` is POSIX-only: its templates are
  shell (`grep`, `case`/`esac`) and `guardrails/verify.py` calls
  `os.killpg`/`os.getpgid`. Those tests get a marker that skips them on Windows with
  a stated reason, so the Windows job can run the *whole* suite and its result means
  something, instead of a hand-picked subset that silently omits whatever is
  inconvenient.
- **Environment-coupled tests made honest.** `test_detect_returns_installed` passes
  today for the wrong reason: `detect()` resolves the adapter dir `.claude`
  *relative to the cwd*, and `.claude/` is committed to this repo — so it reports
  "claude is installed" on any machine, detecting the repo rather than the agent.
  `test_good_lint_hook_passes` needs `ruff` on `PATH` and fails under a bare
  `python -m pytest`. Both are pinned to explicit, stated conditions.
- **`guardrails` degrades honestly on Windows** rather than dying in POSIX-only
  process handling: an unsupported platform is reported, not crashed into. (Full
  Windows support for guardrails remains out of scope — see below.)

### Not in scope

- **Making `risqlet guardrails` work on Windows.** Its hook templates are POSIX
  shell one-liners; porting them means moving each guardrail's logic into the CLI
  (the pattern `fix-windows-hook-install` proved for the check hook). That is a
  design change, not a CI change. This change makes the gap *visible and honest*;
  it does not close it.
- Publishing, release automation, or the `release` workflow's contents beyond the
  test job it shares.
- Python version matrix. Platform coverage is the goal; `requires-python = ">=3.12"`
  and a version matrix multiplies cost against a different risk.

## Capabilities

### New Capabilities

- `cross-platform-support`: which platforms risqlet supports, what "supported"
  guarantees per component, and how that is proven — installation from the built
  artifact, agent setup, and the test suite, on each supported OS.

### Modified Capabilities

- `release-readiness`: wheel checks currently stop at "the file list looks right".
  The artifact must be installed and executed on each supported platform before it
  is considered releasable.
- `agent-setup`: `detect()`'s relative-path adapter dirs make detection depend on
  the current working directory, which reports an agent as installed when it only
  found a directory in the repo. Detection must state what it actually detected.

## Impact

Affected code:

- `.github/workflows/test.yml` — replaced with the three-OS matrix, plus the
  clean-install and agent-setup smoke jobs.
- `tests/conftest.py` — platform markers; the `risqlet_on_path` fixture.
- `tests/test_guardrails.py`, `tests/test_hook_verification.py` — POSIX-only markers.
- `tests/test_setup.py` — `test_detect_returns_installed` pinned to a real condition.
- `tests/test_packaging.py` — install-and-run the wheel, not just inspect it.
- `src/risqlet/guardrails/verify.py` — report an unsupported platform instead of
  crashing in `os.killpg`.
- `src/risqlet/setup/engine.py` — `detect()` cwd-dependence.
- `pyproject.toml` — pytest marker registration.

Risk: the macOS and Windows jobs cannot be run from the development host (Linux).
Their first real execution is on the runner, and they should be expected to need
iteration. This change is what converts "we reasoned it works" into evidence, so
the honest framing is that it *starts* producing that evidence rather than
concluding it.
