# Proposal: add-hook-verification

## Why

Installing a guardrail hook can seriously disrupt development: a fail-closed
hook (`exit 2`) that false-positives, has a shell typo, or depends on a tool
that is not installed will block every affected edit — or, for a Stop hook,
prevent ending a session. Three shipped templates are blocking and assume
external tools (`grep`, `ruff`, `gitleaks`, `make test`); `guardrails install`
writes them without ever executing, parsing, or tool-checking them. Worse, the
current `claude-project` install writes a `true` **placeholder** instead of the
real command, so the hooks do not even enforce. A guardrail that has not been
proven to work in the environment it is added to is a liability, not a
safeguard — it must be verified before it is trusted to gate work.

## What Changes

- Hook/pre-commit templates gain an executable `command` and a `verify` block
  (required tools, blocking flag, how input is supplied, benign and violating
  fixtures). The `claude-project` install writes the **real** command, not a
  placeholder.
- New verification, run **in the target environment**: preflight (config parses,
  `bash -n` syntax, required tools on PATH) and behavioral (run the rendered
  command against a benign fixture → expect exit 0; for blocking hooks, against a
  violating fixture → expect the intended nonzero exit; with a timeout).
- `guardrails install` and `setup` hooks **verify by default and refuse to
  install a hook that fails** (`--force` overrides with a loud warning;
  `--no-verify` skips for CI where the env differs). New `risqlet guardrails
  verify` re-checks installed hooks (environments drift).
- Template safety fix: `coverage-check-stop` is parameterized to a detected/
  declared test command instead of hardcoded `make test`, so it is not
  broken-on-arrival on non-make projects (verification parks it if no command).

## Capabilities

### New Capabilities

- `hook-verification`: preflight + behavioral verification in the target env, the
  verify-by-default install gate, and the `verify` command.

### Modified Capabilities

- `guardrail-generation`: hook templates carry executable commands + verify
  metadata; `claude-project` install writes real verified commands; install
  gates on verification.
- `agent-setup`: the setup-installed hook is verified before install.

## Impact

- New `src/risqlet/guardrails/verify.py`; template `command`/`verify` fields
  (schema/model update); guardrails engine + CLI (`--no-verify`, `--force`,
  `guardrails verify`); `coverage-check-stop` template rewrite; setup hook verify.
- Behavioral verification runs shell in a temp scratch inside the target with a
  timeout; never writes outside the target; `.risqlet/` unaffected.
- Dogfood: claude code (haiku/sonnet) + opencode, project scope, temp projects
  only — confirm a verified secret-scan hook actually blocks a secret write and
  passes a benign one, and that a deliberately-broken hook is rejected at install.
