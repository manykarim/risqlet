# Spec delta: skills-cli (add-agent-setup)

## ADDED Requirements

### Requirement: skills install is reachable via setup
The existing `risqlet skills install` behavior SHALL be preserved and SHALL also
be invoked by `risqlet setup` for adapters that support the skills component, so
skills reach Claude Code (project/global) and other skills-capable agents through
the unified setup flow.

#### Scenario: Setup installs skills via the Claude adapter
- **WHEN** `risqlet setup --agents claude --components skills --scope project` runs
- **THEN** the skills are installed to `.claude/skills` exactly as
  `risqlet skills install` would, and recorded in the setup manifest

#### Scenario: Direct skills install still works
- **WHEN** `risqlet skills install` runs directly
- **THEN** it behaves as before, unaffected by the setup layer
