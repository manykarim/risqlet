# Design: add-agent-setup

## Context

Verified against installed instances: **claude** (`.claude/`, `.mcp.json`,
`CLAUDE.md`, settings hooks, `.claude/commands`), **codex** (`~/.codex/config.toml`
`[mcp_servers.*]`, `~/.codex/skills`, `~/.codex/prompts`, AGENTS.md), **opencode**
(`opencode.jsonc` with an `mcp` key, AGENTS.md), **kilo** (`~/.config/kilo/kilo.jsonc`),
**pi** (`~/.pi/agent/settings.json` + `mcp-*.json`). Plus Cursor (`.cursor/mcp.json`,
`.cursor/rules`) and Copilot (`.vscode/mcp.json`, `.github/copilot-instructions.md`).
Key nuance: some agents register MCP **globally only** (codex TOML, pi settings),
others per-project (claude/cursor/opencode/copilot). The adapter model must encode
per-component *supported scopes*, not assume uniformity.

## Goals / Non-Goals

**Goals:** one command that configures many agents at project or global scope, in
both a scriptable non-interactive mode and a friendly interactive mode; honest
per-agent capability; clean, precise removal; never clobbering user config.

**Non-Goals:** a heavy TUI dependency (stdlib prompts only); reimplementing each
agent (we write their config, we don't wrap them); guaranteeing parity across
agents (tiered + honestly reported); installing globally during automated tests
(dogfood is project-scope into temp dirs only).

## Decisions

### D1. Data-driven adapters (`src/risqlet/setup/adapters/*.yaml`, package data)

One descriptor per agent — paths + methods are data so a schema change is a data
edit, exactly like the CI/guardrail templates:

```yaml
id: claude
name: Claude Code
detect: { binary: claude, dirs: [".claude"] }
components:
  skills:       { scopes: [project, global], project: ".claude/skills", global: "~/.claude/skills", method: copy-skills }
  mcp:          { scopes: [project],          project: ".mcp.json",       method: json-merge, key: "mcpServers" }
  instructions: { scopes: [project, global], project: "CLAUDE.md",       global: "~/.claude/CLAUDE.md", method: md-section }
  hooks:        { scopes: [project],          project: ".claude/settings.json", method: json-hooks }
  commands:     { scopes: [project],          project: ".claude/commands", method: copy-commands }
```

Per-agent component support (launch matrix):

| agent | skills | mcp (scope) | instructions | hooks | commands |
|---|---|---|---|---|---|
| claude | project+global | project | CLAUDE.md | yes | yes |
| cursor | project (rules) | project (`.cursor/mcp.json`) | `.cursor/rules/risqlet.mdc` | — | — |
| opencode | project (via AGENTS.md/config) | project (`opencode.jsonc` `mcp`) | AGENTS.md | — | — |
| codex | global (`~/.codex/skills`) | **global** (`~/.codex/config.toml`) | AGENTS.md + `~/.codex/prompts` | — | prompts (global) |
| copilot | — | project (`.vscode/mcp.json` `servers`) | `.github/copilot-instructions.md` | — | — |
| kilo | (verify) | project/global (`kilo.jsonc`) | `.kilo*/rules` / AGENTS.md | — | — |
| pi | (verify) | **global** (`~/.pi/agent/settings.json`) | AGENTS.md | — | — |

`instructions` (AGENTS.md, or the agent's native rules file) is the universal
floor — every adapter supports it. kilo/pi exact skills/MCP surfaces are verified
against the installed instances during implementation; a wrong guess degrades to
instructions-only, clearly labeled, never a crash.

### D2. Canonical specs rendered per agent

One canonical MCP server spec — `{command: "risqlet", args: ["mcp"]}` — rendered
into each agent's schema by `method`:
- `json-merge`/`mcpServers` → `.mcp.json`, `.cursor/mcp.json`
- `json-merge`/`servers` → `.vscode/mcp.json` (Copilot uses `servers`)
- `jsonc-merge`/`mcp` → `opencode.jsonc`, `kilo.jsonc` (opencode shape:
  `{type: local, command: [risqlet, mcp], enabled: true}`)
- `toml-merge`/`mcp_servers` → `~/.codex/config.toml`
- `pi-json` → `~/.pi/agent/settings.json` mcp block

One canonical instructions block (a short "this project uses risqlet — run
`risqlet status` to resume; the register is in `.risqlet/`; agents propose,
humans decide" section) rendered as a marker-delimited `md-section` into AGENTS.md
or the agent's rules file. Skills reuse the existing `skills.install`; commands
reuse copy semantics; hooks reuse the `ci init --target claude-hooks` content.

### D3. Manifest and reversibility

`.risqlet/agents.lock` (project) / `~/.risqlet/agents.lock` (global), a JSON list
of actions: `{agent, component, scope, target_path, method, marker|created}` plus
a `risqlet_version`. Every write is either a *created file* (removal deletes it if
still risqlet-owned) or a *marker-scoped edit* (removal strips the delimited
section / removes the named JSON/TOML key). Merges never touch entries risqlet did
not add. `--update` re-renders and replaces managed content when the version
stamp or content hash changed (staleness like `guardrails diff`).

### D4. CLI surface

```
risqlet setup [--agents a,b | --all-detected] [--scope project|global]
              [--components skills,mcp,instructions,hooks,commands]
              [--dry-run] [--json] [--yes] [--force]
risqlet setup --remove [--agents ...] [--scope ...]
risqlet setup --update [--agents ...] [--scope ...]
risqlet setup --status [--json]
```

Mode resolution: if `--agents`/`--all-detected` given OR stdin is not a TTY →
**non-interactive** (apply directly; `--yes` skips the final confirm, required in
CI). Else → **interactive**: detect (pre-check found agents) → multiselect agents
→ components (defaulted per agent capability) → scope → preview plan → confirm.
`--dry-run` prints the plan (per agent: files/sections/entries to write, and what
is skipped and why) and writes nothing. Project-only component at global scope (or
vice-versa) is dropped from the plan with a clear note, never silently mangled.

### D5. Interactive prompts (stdlib only)

Numbered multiselect via `input()` (toggle by number, `a` = all, empty = done),
a scope prompt, and a preview/confirm. No `rich`/`textual` dependency. Detection
results pre-select. Not-a-TTY → refuse interactive and print the non-interactive
usage. Keeps the 2-runtime-dep footprint.

### D6. Dogfood (project scope, temp dirs, installed agents)

For each of claude/codex/opencode/kilo/pi: `risqlet setup --agents <x> --scope
project --yes` into a fresh temp project (never global, never a real repo), assert
the expected files/sections/MCP entries appear with markers; `--status` lists
them; `--remove` restores the temp project to empty (only risqlet artifacts gone);
`--dry-run` writes nothing. Where an agent is MCP-global-only (codex/pi), assert
the plan reports MCP as "global-only — run with --scope global" rather than
writing it. Real global configs are never touched by the test.

## Risks / Trade-offs

- [Combinatorial matrix] → data-driven adapters + tiered, honestly-reported
  support; `dry-run` shows exactly what each agent gets and skips.
- [MCP schema churn / stateless-first RC] → render methods are data-selected;
  a format change is a template edit.
- [Clobbering user config] → marker-scoped merges + manifest; removal only ever
  deletes risqlet-owned files or risqlet-added keys/sections.
- [Detection false negatives] → detect is a hint (pre-check); the human/flags are
  the truth; `--all-detected` is opt-in.
- [kilo/pi surfaces uncertain] → verified against installed instances at build
  time; unknown component degrades to instructions-only with a labeled note.
- [Global writes in tests] → tests are project-scope into temp dirs only, per the
  explicit constraint; a guard rejects global-scope writes under the dogfood.

## Migration Plan

Additive. `skills install`, `ci init`, `guardrails install` keep working;
`setup` orchestrates them. No register/format change.

## Open Questions

- Whether to also emit per-agent slash-commands wrapping `/risk-analysis` etc.
  beyond Claude/codex — deferred; `commands` is in the component model but only
  claude+codex implement it at launch.
