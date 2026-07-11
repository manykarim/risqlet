# Spec delta: agent-setup (add-hook-verification)

## ADDED Requirements

### Requirement: setup verifies the hook it installs
`risqlet setup` SHALL verify any hook component it installs (e.g. the Claude Code
check hook) in the target environment before writing it, using the same gate as
guardrail install: a failing hook is skipped (or installed with `--force`), and
`--no-verify` opts out.

#### Scenario: Setup skips an unverifiable hook
- **WHEN** setup would install a hook whose required tool is missing
- **THEN** the hook is skipped with its reason and the rest of the setup proceeds
