## MODIFIED Requirements

### Requirement: agent adapters with honest capability
Setup SHALL drive a data-driven adapter per supported agent (Claude Code,
Cursor, opencode, Codex, Copilot, kilo, pi). Each adapter declares which
components (skills, mcp, instructions, hooks, commands) it supports and at which
scopes. Setup SHALL install the intersection of requested components and adapter
capability, and SHALL report per agent what was installed and what was skipped
(with the reason). Instructions SHALL be supported by every adapter.

Detection SHALL report what it actually found. An adapter's declared directories are
resolved relative to the current working directory unless anchored (`~`), so a
project-local directory such as `.claude` or `.github` present in the repo means only
that the repo contains that directory — not that the agent is installed on the
machine. Detection SHALL distinguish an agent found on `PATH` from one inferred from
a directory, and SHALL NOT report an agent as installed on the strength of a
directory belonging to the project being scanned.

#### Scenario: Full Claude install
- **WHEN** setup installs the Claude adapter at project scope
- **THEN** skills, an MCP registration, an instructions section, hooks, and
  commands are written

#### Scenario: MCP-global-only agent
- **WHEN** a project-scope install targets an agent whose MCP registration is
  global-only (e.g. Codex, pi)
- **THEN** its instructions install at project scope and its MCP is reported as
  global-only (run with `--scope global`) rather than written into the project

#### Scenario: Unsupported component skipped, not failed
- **WHEN** a requested component is not supported by an agent
- **THEN** it is skipped with a labeled note and the rest still install

#### Scenario: Detection does not depend on where it was run from
- **WHEN** `detect` runs in a project containing a `.claude` directory on a machine
  with no Claude Code installed
- **THEN** the result distinguishes that this came from a project directory rather
  than reporting the agent as installed on the machine
