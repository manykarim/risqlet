# Spec delta: guardrail-generation (add-hook-verification)

## ADDED Requirements

### Requirement: executable templates carry a verifiable command
Guardrail templates whose surface executes (claude-hook, pre-commit) SHALL carry
an executable `command` and a `verify` block (required tools, blocking flag,
input mode, benign and violation fixtures). The command SHALL read a changed
file via a single env var so it is verifiable independent of agent; per-surface
install maps the agent's real variable to it. Advisory templates SHALL carry no
command and SHALL not be verified.

#### Scenario: Hook template exposes a command and fixtures
- **WHEN** a claude-hook template is loaded
- **THEN** it has a `command` and a `verify` block with tools and fixtures

#### Scenario: Advisory template has no command
- **WHEN** an AGENTS.md advisory template is loaded
- **THEN** it has no command and is excluded from verification
