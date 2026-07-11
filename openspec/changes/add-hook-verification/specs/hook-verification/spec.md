# Spec: hook-verification

## ADDED Requirements

### Requirement: hooks are verified in the target environment
Before an executable guardrail hook is installed, risqlet SHALL verify it in the
target environment: preflight (its required tools resolve on PATH, its command
passes a `bash -n` syntax check) and behavioral (the rendered command run against
a benign fixture exits 0 within a timeout; a blocking hook run against a violating
fixture exits nonzero). A hook that fails any check SHALL be reported with the
failing checks. Verification SHALL run shell only for vetted rendered template
commands, in a temporary working directory, and SHALL kill a hanging command at
the timeout.

#### Scenario: Good hook verifies
- **WHEN** a secret-scan hook whose tools are present is verified
- **THEN** it passes benign (exit 0) and violation (blocking nonzero) checks

#### Scenario: Missing tool fails preflight
- **WHEN** a hook requires a tool that is not on PATH
- **THEN** verification fails naming the missing tool and the hook is not trusted

#### Scenario: False block detected
- **WHEN** a hook exits nonzero on the benign fixture
- **THEN** verification fails (it would block legitimate work)

#### Scenario: Hang is bounded
- **WHEN** a hook command does not terminate
- **THEN** verification times out, kills the process, and fails

### Requirement: install gates on verification by default
`guardrails install` and setup-installed hooks SHALL verify each hook and install
only hooks that pass, skipping failing hooks with their reasons. `--force` SHALL
install a failing hook anyway with an explicit warning; `--no-verify` SHALL skip
verification (documented as CI-only). Non-hook guardrails SHALL be unaffected.

#### Scenario: Failing hook not installed by default
- **WHEN** a hook fails verification during install
- **THEN** it is skipped with its failed checks and other guardrails still install

#### Scenario: Force overrides with warning
- **WHEN** install runs with `--force` and a hook fails verification
- **THEN** the hook is installed and a warning is printed

### Requirement: installed hooks carry the real command
The Claude Code guardrail install SHALL write the hook's real executable command
(not a placeholder), with its provenance marker, so the hook actually enforces.

#### Scenario: Real command installed
- **WHEN** a secret-scan guardrail installs to a Claude project
- **THEN** `.claude/settings.json` contains the real scanning command, not `true`

### Requirement: verify command re-checks installed hooks
`risqlet guardrails verify` SHALL re-run verification on the installed hooks
against the current environment and report pass/fail per hook, so environment
drift (a removed tool or test target) is detectable. It SHALL be read-only.

#### Scenario: Drift detected after tool removal
- **WHEN** a hook's required tool is later unavailable and `guardrails verify` runs
- **THEN** that hook is reported as failing with the missing tool

### Requirement: no broken-on-arrival Stop hook
The coverage/stop hook SHALL derive its test command from the project (pytest,
npm, or a Makefile test target) rather than hardcoding one; when no test command
can be determined, it SHALL be skipped with a note rather than installed.

#### Scenario: Non-make project does not get a broken stop hook
- **WHEN** the coverage stop guardrail is generated for a project with no Makefile
  test target and no detectable test command
- **THEN** it is skipped with a "declare your test command" note, not installed
