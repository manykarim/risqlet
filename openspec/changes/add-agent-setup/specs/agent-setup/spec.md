# Spec: agent-setup

## ADDED Requirements

### Requirement: setup runs non-interactively for CI/headless
`risqlet setup` SHALL run without prompts when agents are specified via
`--agents`/`--all-detected` or when stdin is not a TTY: it applies the plan
directly (with `--yes` to skip any confirmation), supports `--scope`,
`--components`, `--dry-run`, and `--json`, and exits nonzero on error. `--dry-run`
SHALL write nothing and report the full plan including what each agent is skipped
for and why.

#### Scenario: Scripted install
- **WHEN** `risqlet setup --agents claude --scope project --yes` runs in a project
- **THEN** the Claude components install and the command exits 0 with no prompts

#### Scenario: Dry run writes nothing
- **WHEN** `risqlet setup --agents claude --dry-run` runs
- **THEN** the plan is printed and no file is created or modified

#### Scenario: Non-TTY never prompts
- **WHEN** setup runs with stdin not a TTY and no agents specified
- **THEN** it prints non-interactive usage and does not block on input

### Requirement: setup runs interactively for humans
When stdin is a TTY and no agents are specified, `risqlet setup` SHALL detect
installed agents (pre-selecting them), let the user multiselect agents and
components and choose a scope, preview the plan, and apply only on confirmation,
using only the standard library (no heavy TUI dependency).

#### Scenario: Interactive selection applies on confirm
- **WHEN** a user runs `risqlet setup` in a TTY, selects agents, and confirms
- **THEN** the chosen components install for the chosen agents

### Requirement: agent adapters with honest capability
Setup SHALL drive a data-driven adapter per supported agent (Claude Code,
Cursor, opencode, Codex, Copilot, kilo, pi). Each adapter declares which
components (skills, mcp, instructions, hooks, commands) it supports and at which
scopes. Setup SHALL install the intersection of requested components and adapter
capability, and SHALL report per agent what was installed and what was skipped
(with the reason). Instructions SHALL be supported by every adapter.

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

### Requirement: MCP registration rendered per agent schema
Setup SHALL render one canonical MCP server spec into each agent's own config
format and key (JSON `mcpServers`/`servers`, opencode/kilo JSONC `mcp`, Codex
TOML `[mcp_servers.*]`, pi settings), merging into existing config without
disturbing entries risqlet did not add.

#### Scenario: Merge preserves foreign entries
- **WHEN** an agent's MCP config already contains another server
- **THEN** after install that server remains and a `risqlet` entry is added

### Requirement: manifest-based install, remove, update, status
Every install SHALL be recorded in a manifest (`.risqlet/agents.lock` for project
scope, `~/.risqlet/agents.lock` for global) capturing each created file and
marker-scoped edit with a version stamp. `risqlet setup --remove` SHALL reverse
precisely from the manifest — deleting risqlet-created files and stripping only
risqlet-added sections/keys, leaving user content intact. `--update` SHALL refresh
stale managed content; `--status` SHALL report what is installed where.

#### Scenario: Clean removal
- **WHEN** setup installs to a project and then `setup --remove` runs
- **THEN** all risqlet-created files and sections are gone and the user's own
  config is unchanged

#### Scenario: Status lists installs
- **WHEN** `risqlet setup --status` runs after an install
- **THEN** it lists the agents, components, scopes, and paths that were installed

#### Scenario: Update refreshes stale content
- **WHEN** managed content differs from the current render (e.g. after upgrade)
  and `setup --update` runs
- **THEN** the managed sections/files are refreshed and foreign content is untouched

### Requirement: scope intelligence and safety
Global scope SHALL install the tool surface (skills, MCP where supported);
project scope SHALL additionally cover instructions and project-only components.
A component requested at an unsupported scope SHALL be dropped from the plan with
a clear note. Setup SHALL never write outside the target project's and the chosen
scope's conventional locations, and never into `.risqlet/` except the manifest.

#### Scenario: Project-only component at global scope dropped
- **WHEN** a project-only component is requested at global scope
- **THEN** it is dropped with a note and does not error the whole run
