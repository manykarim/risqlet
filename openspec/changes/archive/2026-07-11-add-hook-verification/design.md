# Design: add-hook-verification

## Context

Grounded: `src/risqlet/guardrails/templates/` ships three fail-closed (`exit 2`)
hook templates (`secret-scan-posttool`, `lint-format-posttool`,
`coverage-check-stop`) plus a `gitleaks` pre-commit; `guardrails/engine.py`
installs hook *text* with no execution/parse/tool check, and `_install_claude`
writes a `true # marker` placeholder rather than the real command. This change
makes the hooks real and proves them in the target environment before trusting
them, matching risqlet's detection-evidence honesty: a hook whose own test fails
must not be allowed to gate work.

## Goals / Non-Goals

**Goals:** verify hooks (static + behavioral) in the environment they are added
to; refuse to install unverified blocking hooks by default; make installed hooks
actually enforce (real command, not placeholder); re-verify on demand; stop
shipping a broken-on-arrival Stop hook.

**Non-Goals:** verifying advisory AGENTS.md rules (nothing to execute);
sandboxing beyond a temp cwd + timeout + tool allowlist; guaranteeing a hook is
*correct* forever (env drifts — hence `verify`); CI-runner emulation for the CI
templates (they run in CI; preflight tool-checks only).

## Decisions

### D1. Template `command` + `verify` metadata

Executable templates (claude-hook, pre-commit) gain:

```yaml
command: |          # rendered like the body ({{paths_case}} etc.), the truth we run
  f="$RISQLET_HOOK_FILE"; case "$f" in {{paths_case}}) grep -nEi '<pattern>' "$f" \
    && { echo 'risqlet: possible secret'; exit 2; } ;; esac; exit 0
verify:
  tools: [grep]           # must resolve on PATH
  blocking: true          # exits nonzero on a violation
  input: file             # file (a path via env) | none (e.g. Stop) | git-staged
  benign: "port = 8080\n"                 # a fixture that MUST pass (exit 0)
  violation: "api_key = 'AKIAIOSFODNN7EXAMPLE'\n"   # MUST be caught (nonzero)
```

Hook commands read the changed file from a single env var `RISQLET_HOOK_FILE`;
per-surface install maps the agent's real var to it (Claude Code sets
`CLAUDE_TOOL_FILE_PATH`, so the installed hook is
`RISQLET_HOOK_FILE="$CLAUDE_TOOL_FILE_PATH" <command>`). This makes the same
command verifiable independent of agent. Advisory templates keep no `command`
and are never verified.

### D2. Verification (`src/risqlet/guardrails/verify.py`)

`verify_hook(rendered_command, spec, cwd) -> VerifyResult` with ordered checks:

1. **Preflight** — every `spec.tools` resolves via `shutil.which`; `bash -n -c
   <command>` parses (syntax); (pre-commit) config is valid YAML.
2. **Behavioral** — in a temp scratch under `cwd`, with `timeout` (default 10s):
   - `input: file` → write `benign` to a temp file, run `bash -c` with
     `RISQLET_HOOK_FILE=<tmp>` → expect exit 0. If `blocking`, write `violation`
     to a temp file, run → expect nonzero (and *not* a timeout).
   - `input: none` (Stop) → run in temp cwd → expect exit 0.
   - `input: git-staged` (pre-commit) → preflight tool check only in v1
     (behavioral needs a seeded git repo; documented limitation).

`VerifyResult{ok, checks:[{name, passed, detail}]}`. A false block (benign →
nonzero), a missing tool, a syntax error, a hang (timeout), or a
non-catching blocking hook (violation → 0) all fail verification. Timeout kills
the process group so a hanging hook cannot wedge the verifier.

### D3. Install gate

`guardrails install` (and `setup` hooks) render each hook's command, verify it,
and **only install passing hooks by default**. Failing hooks are reported with
their failed checks and skipped; `--force` installs them anyway with a loud
warning; `--no-verify` skips verification entirely (documented as CI-only, when
the runtime env differs from the authoring env). Non-hook guardrails
(AGENTS.md/permission/CI) install unchanged. The Claude install writes the
**real** command (D1) with the provenance marker in a trailing comment.

### D4. `risqlet guardrails verify`

Re-runs verification on the *installed* hooks (read from the guardrails lock /
plan) against the current environment, reporting pass/fail — so a user who later
uninstalls `gitleaks` or removes a test target learns their guardrail is now
broken. Read-only.

### D5. `coverage-check-stop` rewrite

Replace hardcoded `make test` with a detected test command: pyproject/pytest →
`pytest -q`; `package.json` → `npm test`; `Makefile` with a `test:` target →
`make test`; else the template renders no command and install skips it with
"declare your test command". Its `verify.input: none` runs the command once;
on a fresh project with no tests it may legitimately pass (0 tests) — acceptable;
the point is it no longer bricks the Stop hook on a non-make repo.

### D6. Fixtures are safe and synthetic

`violation` fixtures are obviously-fake (`AKIAIOSFODNN7EXAMPLE` is AWS's public
documentation example key; a deliberate lint error). They are written only to
temp files under the target's scratch and deleted; nothing real is scanned or
committed during verification.

## Risks / Trade-offs

- [Behavioral verify executes shell] → only rendered template commands (vetted,
  not model text), in a temp cwd, tool-allowlisted, timeout-bounded, process
  group killed on timeout.
- [Env at authoring ≠ env at runtime (CI)] → `--no-verify` opt-out documented;
  `guardrails verify` re-checks; default stays safe (verify on).
- [False sense that a passing hook is bug-free] → verify proves benign-pass +
  violation-block + tools + syntax + no-hang, not general correctness; reported
  honestly as "verified: <checks>", not "correct".
- [Real commands now enforce (behavior change)] → that is the point; but it is a
  behavior change from the placeholder — called out in the changelog; verify-gate
  makes it safe.

## Migration Plan

Additive to templates and install flow; a register/guardrail already installed
with placeholder hooks is replaced with real+verified ones on next install.
No `.risqlet/` format change.

## Open Questions

- Whether to auto-run `guardrails verify` from a scheduled/CI hook — deferred; the
  command exists for manual/CI use now.
