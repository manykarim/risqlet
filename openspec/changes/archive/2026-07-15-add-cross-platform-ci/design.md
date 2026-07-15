## Context

Two bugs shipped because nothing ran risqlet anywhere but a Linux dev box against an
editable install:

- The Claude setup hook was a bash+`python3` one-liner. It failed on Windows for
  every user. The verification gate caught it correctly and reported
  `hook failed verification: bash not on PATH` — nobody was running a Windows job to
  see that message.
- `ci init --target claude-hooks` read `$CLAUDE_TOOL_FILE_PATH`, which Claude Code
  never sets. It was checked for parsing as JSON and naming real subcommands, and it
  passed both while doing nothing.

Current state: `fix-windows-hook-install` added `.github/workflows/test.yml` with a
Linux job (full suite) and a Windows job running six hand-picked test classes. That
selection was reasoned, not measured, and the job has never executed. macOS has never
been run at all. `test_wheel_ships_license_notice_and_data` builds a wheel, reads its
namelist, and discards it.

The known platform facts, established by reading the code:

- POSIX-only code is confined to `guardrails/verify.py`: `start_new_session=True`
  (ignored on Windows) and `os.killpg(os.getpgid(...))` (raises `AttributeError` —
  the attributes do not exist on Windows). It is reached only on the timeout path.
- Guardrail hook *templates* are shell (`case`/`esac`, `grep -nEiq`). They need a
  shell wherever they run. macOS has one; Windows runners happen to have Git Bash on
  `PATH`, which makes the Windows behavior here genuinely uncertain rather than
  cleanly broken.
- `setup`, `check`, the register, and the installed hook have no shell or POSIX
  dependency after `fix-windows-hook-install`.
- `detect()` resolves adapter dirs like `.claude` **relative to cwd**. `.claude/` is
  committed to this repo, so `detect()` returns `claude` on any machine when run from
  the repo root — including one with no Claude Code installed. This is why
  `test_detect_returns_installed` passes, and it would pass on a bare runner for the
  same wrong reason.

## Goals / Non-Goals

**Goals:**

- Run the same suite on Linux, macOS, and Windows, where green means the same thing.
- Prove the *shipped artifact* installs and runs on each platform, not the source tree.
- Prove `risqlet setup` configures a coding agent on each platform.
- Make platform gaps visible and reasoned rather than absent.

**Non-Goals:**

- Making `risqlet guardrails` work on Windows. Porting shell templates means moving
  each guardrail's logic into the CLI — the pattern proven for the check hook, but a
  design change, not a CI change.
- A Python version matrix. Platform is the risk this change addresses.
- Making the macOS/Windows jobs pass first try. They cannot be run from this host.

## Decisions

### 1. Full suite everywhere, with skips inside the suite — not a per-OS subset

The existing Windows job names six test classes. That is the wrong instrument: the
selection encodes an assumption about what works, so it can never discover that
something else broke. Whatever is not listed is not reported — it is simply absent,
and absence reads as green.

Instead every OS runs `pytest` unqualified, and platform gaps live in the suite as
`@pytest.mark.skipif` with a stated reason. A skip is visible in the run; an omission
is not. This also means adding a Windows-incompatible test cannot silently pass by
falling outside a hand-written list.

Cost: the Windows job may surface failures I did not predict. That is the point —
that is the evidence this change exists to produce.

### 2. Clean install from the wheel, in a venv with no source tree

Every current test imports risqlet from `src/` via an editable install. That
configuration ships to nobody. The class of bug it cannot see is exactly the class
that hurts: a missing `force-include`, a console script that does not resolve, package
data absent from the wheel.

So the install job: `uv build` → fresh venv → `pip install dist/*.whl` → run the
`risqlet` console script from a working directory that is **not** the repo, so the
source tree cannot satisfy an import that the wheel does not. Then exercise commands
that read shipped data (`setup` → adapters, `ci init` → templates, `catalog list` →
packs, `skills install` → bundled skills), because that data is force-included by
hatch config and nothing else proves it landed.

### 3. Test the agent-setup path, since that is the product claim

The Windows bug was in `setup`. A test suite that never runs `setup` from an install
cannot catch its successor. Each platform runs `setup` for every adapter risqlet ships
and asserts the artifacts, plus asserts nothing was skipped for a bad reason.

The distinction matters: `skipped` is a legitimate outcome (Codex's MCP is
global-only; Copilot has no hooks) and also how the Windows bug manifested
(`hook failed verification`). The job must fail on the second while tolerating the
first, so it asserts on the skip *reason*, not on skips being empty.

### 4. Make `detect()` honest rather than deleting the test

`test_detect_returns_installed` asserts `"claude" in detect(...)` with the comment
"claude is installed in this environment". It passes because the repo contains
`.claude/`. Two things are wrong: the test proves nothing, and `detect()` genuinely
misreports — a user in a repo with a `.github/` directory is told Copilot is
installed.

The narrow fix is to have detection distinguish "found on PATH" from "inferred from
a directory". The test then asserts the real condition. This is a small change to
`detect()`'s return shape, so it stays in scope; the alternative (delete the test)
keeps the misreport.

### 5. Guardrails reports an unsupported platform instead of crashing

`os.killpg` does not exist on Windows, so the timeout path dies with `AttributeError`.
Whatever we do about guardrail templates later, dying in an attribute lookup is a bad
way to learn a platform is unsupported. Windows gets a stated refusal.

This is deliberately *not* Windows support for guardrails — it is the honest failure
mode that lets the Windows suite run to completion and report a reasoned skip.

## Risks / Trade-offs

- **The macOS and Windows jobs cannot be tested from this host.** → They will run for
  the first time on the runner and should be expected to need iteration. This must be
  said plainly rather than presented as done; a workflow that has never executed is a
  hypothesis. The tasks include a verification step that is only closeable by a real
  run.

- **Windows runners have Git Bash on PATH.** Guardrail verification may therefore
  partly work there, making its behavior uncertain rather than cleanly broken. →
  Skip guardrail hook tests on Windows by policy (POSIX-only is the *stated* support
  boundary) rather than by whether a shell happens to be present. Support should be a
  decision, not an accident of the runner image.

- **Full-suite-everywhere may be red on first run.** → That is information, not
  failure. The alternative — a green subset — is the status quo that shipped two bugs.

- **Changing `detect()`'s return shape touches a public-ish surface.** → Keep the
  change minimal and additive; `setup`'s callers care about which agents to configure,
  which is unchanged.

- **CI cost triples.** → Three OSes on push/PR for a suite that runs in ~30s. This is
  the cheapest possible instrument for the failure mode that has already bitten twice.

## Migration Plan

1. Land the markers and the honest `detect()` first — the suite must be
   platform-aware before a Windows job runs it, or the first run is noise.
2. Replace `test.yml` with the matrix; keep the Linux job's full-suite+lint shape.
3. Add clean-install and setup-smoke jobs per platform.
4. Push, watch all three, and iterate on real failures rather than predicted ones.

Rollback: the workflow is additive and gates nothing until made a required check.
The test markers are honest regardless of whether the workflow lives.

## Open Questions

- Should the workflow become a required status check? Recommend yes, but only after
  three consecutive green runs — making a never-executed job required would block all
  work on its first red.
- Should macOS run the guardrail tests? It has a shell, so they should pass; if they
  prove flaky on BSD tooling (`grep -nEiq` behavior differs subtly from GNU), the
  honest response is a stated macOS skip, not a loosened assertion.
