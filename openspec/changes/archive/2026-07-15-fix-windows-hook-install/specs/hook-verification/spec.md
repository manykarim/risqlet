## MODIFIED Requirements

### Requirement: hooks are verified in the target environment
Before an executable guardrail hook is installed, risqlet SHALL verify it in the
target environment: preflight (its required tools resolve on PATH, and its command
passes a static check appropriate to its form) and behavioral (the rendered command
run against a benign fixture exits 0 within a timeout; a blocking hook run against a
violating fixture exits nonzero). A hook that fails any check SHALL be reported with
the failing checks. Verification SHALL run shell only for vetted rendered template
commands, in a temporary working directory, and SHALL kill a hanging command at
the timeout.

The static check SHALL follow the command's form rather than assuming a shell. A
shell command SHALL be syntax-checked with `bash -n`, and `bash` SHALL be treated
as one of its required tools. A shell-free command — a single executable with
literal arguments and no shell metacharacters — SHALL NOT be failed for the absence
of a shell; it SHALL be verified behaviorally by executing it directly, without a
shell, which subsumes the syntax check. Absence of a tool a hook does not use SHALL
NOT fail that hook.

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

#### Scenario: Shell-free hook verifies without a shell
- **WHEN** a hook whose command is a single executable with literal arguments is
  verified on a host with no `bash` on PATH
- **THEN** it is not failed for the missing shell; it is run directly against a
  benign payload and passes when it exits 0

#### Scenario: Shell hook still requires its shell
- **WHEN** a hook whose command uses shell metacharacters is verified on a host
  with no `bash` on PATH
- **THEN** verification fails naming the missing shell, and the hook is not installed
