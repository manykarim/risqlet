# Proposal: add-agent-setup

## Why

Getting risqlet working in a project today is a five-command scavenger hunt with
different `--target` vocabularies and manual `.mcp.json` editing, and there is no
help at all for Cursor / opencode / Codex / Copilot / kilo / pi. That is the
opposite of "easy and intuitive," and it is the main adoption friction now that
the tool is published. OpenSpec's `init` shows the model: one entry point that
configures many agents, idempotently, at project or global scope. risqlet
already owns the pieces (skills install, ci init, guardrails install, the MCP
server, marker-scoped merges) — it needs the single front door and clean removal.

## What Changes

- New `risqlet setup` command with two modes:
  - **Non-interactive** (CI/headless/scriptable): `risqlet setup --agents claude,cursor --scope project --yes` (also `--all-detected`, `--components`, `--dry-run`, `--json`). No prompts; nonzero exit on error.
  - **Interactive** (human TTY): `risqlet setup` detects agents, offers a stdlib multiselect of agents/components/scope, previews, confirms, applies. Falls back to non-interactive help when stdin is not a TTY.
- Seven **agent adapters** (data-driven, like the CI/guardrail templates): Claude Code (full — skills, MCP, instructions, hooks, commands) and an instructions+MCP(+skills where supported) tier for Cursor, opencode, Codex, Copilot, kilo, pi. Each adapter declares which components it supports and at which scopes; `setup` installs the intersection of what risqlet offers × what the agent supports, and reports honestly what each agent got and did not.
- **Manifest-based reversibility**: `.risqlet/agents.lock` (project) and `~/.risqlet/agents.lock` (global) record every file created, section inserted, and MCP entry added, so `risqlet setup --remove` reverses precisely, `--update` refreshes stale content, and `--status` shows what is installed. Never clobbers user config (marker-scoped merges).
- Scope intelligence: global installs the tool surface (skills + MCP); project adds the register, instructions, guardrails, hooks; project-only components asked for globally are refused with a clear message.

## Capabilities

### New Capabilities

- `agent-setup`: the `setup` command (both modes), the adapter model and the seven adapters, MCP-registration rendering per agent schema, the manifest, and install/remove/update/status semantics.

### Modified Capabilities

- `skills-cli`: `skills install` becomes one path the Claude adapter uses; behavior preserved, now also reachable via `setup`.

## Impact

- New `src/risqlet/setup/` (adapter descriptors as package data, engine, renderers, interactive prompts), CLI `setup` command, manifest format.
- Writes into the *target project's / user's* agent-config files (`.mcp.json`, `.cursor/`, `AGENTS.md`, `opencode.jsonc`, `~/.codex/config.toml`, etc.), always marker-scoped; never into `.risqlet/` except the manifest.
- No register/schema change. Dogfood verifies against the installed claude/codex/opencode/kilo/pi instances, project-scope, in temp projects only.
