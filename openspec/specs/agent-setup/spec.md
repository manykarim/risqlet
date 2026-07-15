# agent-setup Specification

## Purpose
TBD - created by archiving change add-agent-setup. Update Purpose after archive.
## Requirements
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

### Requirement: setup verifies the hook it installs
`risqlet setup` SHALL verify any hook component it installs (e.g. the Claude Code
check hook) in the target environment before writing it, using the same gate as
guardrail install: a failing hook is skipped (or installed with `--force`), and
`--no-verify` opts out.

#### Scenario: Setup skips an unverifiable hook
- **WHEN** setup would install a hook whose required tool is missing
- **THEN** the hook is skipped with its reason and the rest of the setup proceeds

### Requirement: the installed check hook runs on every supported platform
The hook `risqlet setup` installs SHALL run on every platform risqlet supports
(Linux, macOS, Windows) without requiring a shell or any interpreter beyond
`risqlet` itself. Its command SHALL be a single executable invocation with literal
arguments: no shell metacharacters (`$(...)`, `"`, `|`, `;`, `&&`, `||`,
redirections), no `bash`, and no separate `python3`/`node`/PowerShell process. Any
payload parsing the hook needs SHALL live in the `risqlet` CLI, not in the hook
string. risqlet SHALL NOT ship a second, platform-specific variant of this hook.

#### Scenario: Hook installs on a host without bash
- **WHEN** `risqlet setup` installs the Claude Code hook component on a host where
  `bash` is not on PATH
- **THEN** the hook passes verification and is written, rather than being skipped
  with "hook failed verification: bash not on PATH"

#### Scenario: Hook command is shell-free
- **WHEN** the command written to `.claude/settings.json` is inspected
- **THEN** it contains no shell metacharacters and invokes only `risqlet`

#### Scenario: Hook does not depend on the interpreter's name
- **WHEN** the host provides Python as `python` rather than `python3`
- **THEN** the hook still verifies and runs, because it spawns no interpreter itself

### Requirement: installed hooks are identifiable without a shell comment
risqlet SHALL be able to recognize the hooks it installed in order to remove them
without touching a user's own hooks. Because a shell-free command cannot carry a
trailing `# risqlet:check` comment — the comment would be passed to the executable
as literal arguments — the hook SHALL be identified by its own invocation rather
than by an appended comment.

Removal SHALL also recognize hooks written by earlier risqlet versions, which carry
the shell command and its trailing comment marker, so that upgrading does not orphan
a hook that can never be cleaned up. Re-running `risqlet setup` SHALL replace a
previously installed hook rather than leaving a stale one beside the new one.

#### Scenario: Marker is not passed to the executable
- **WHEN** the installed hook command is run
- **THEN** no marker text reaches `risqlet` as an argument and the command succeeds

#### Scenario: Hook installed by an older version is still removable
- **WHEN** `risqlet setup --remove` runs against a settings file whose hook was
  installed by an earlier version carrying the old marker
- **THEN** that hook is removed and the user's own hooks are left intact

#### Scenario: Re-running setup replaces rather than duplicates
- **WHEN** `risqlet setup` runs on a project that already has an older risqlet hook
- **THEN** the settings file ends with exactly one risqlet hook, the current one

### Requirement: setup does not fail on a pre-existing markdown file's encoding
`risqlet setup` SHALL NOT fail to merge its instructions section because the target markdown file (`CLAUDE.md`, `AGENTS.md`) is not valid UTF-8. Earlier risqlet versions wrote that section through the host locale, and its text contains an em-dash, so a Windows user's file is cp1252 on disk and was produced by risqlet itself. Markdown mandates no encoding, so a user's editor may equally have written cp1252 prose around it.

Such a file SHALL be decoded as cp1252, its content preserved, and the marker-scoped
merge applied to the recovered text. The rewritten file SHALL be UTF-8, and the
recovery SHALL be reported. Setup SHALL NOT discard, replace, or mangle the user's
surrounding content in the process.

The tolerance SHALL be scoped to where risqlet's own output could have produced
non-UTF-8 bytes. The JSON and TOML agent configs SHALL stay strict: risqlet writes
them via `json.dumps`, whose `ensure_ascii` default emits pure ASCII, and both
formats mandate UTF-8 by specification — so a decode error there is a malformed file,
not risqlet's residue, and SHALL be raised rather than guessed at.

#### Scenario: A JSON agent config is not silently reinterpreted
- **WHEN** setup reads a `.mcp.json` or `settings.json` that is not valid UTF-8
- **THEN** it raises rather than decoding it as cp1252, because JSON requires UTF-8
  and risqlet cannot have written those bytes

#### Scenario: An instructions file written by an older risqlet still installs
- **WHEN** setup merges into a `CLAUDE.md` whose risqlet section contains a
  cp1252-encoded em-dash, as a pre-fix risqlet on Windows wrote it
- **THEN** setup completes, the section is updated, and the file is rewritten as
  UTF-8 — rather than raising `UnicodeDecodeError` and configuring nothing

#### Scenario: The user's own non-UTF-8 content survives
- **WHEN** setup merges into an instructions file whose *user-authored* prose is
  cp1252-encoded
- **THEN** that prose is preserved with its characters intact, not replaced or
  dropped

#### Scenario: Removal also tolerates it
- **WHEN** `risqlet setup --remove` runs against a non-UTF-8 config it previously
  wrote
- **THEN** the risqlet section is removed and the user's content is left intact

