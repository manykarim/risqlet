# Tasks: add-agent-setup

## 1. Adapter model and descriptors

- [x] 1.1 Define adapter descriptor model (id, detect, per-component {scopes, paths, method, key}) + loader; ship src/risqlet/setup/adapters/*.yaml as package data
- [x] 1.2 Author 7 adapter descriptors verified against installed instances: claude (full), cursor, opencode, codex (mcp global-only), copilot, kilo, pi (mcp global-only); instructions supported by all

## 2. Render + engine

- [x] 2.1 Renderers: canonical MCP spec -> json-merge(mcpServers/servers), jsonc-merge(mcp), toml-merge(mcp_servers), pi-json; canonical instructions -> md-section (AGENTS.md / native rules), marker-delimited; reuse skills.install, ci hooks content, command copy
- [x] 2.2 Engine: detect(), plan(agents, scope, components) with capability intersection + scope filtering + skip-reasons, apply(plan) with marker-scoped merges (never clobber foreign entries)
- [x] 2.3 Manifest: .risqlet/agents.lock (project) / ~/.risqlet/agents.lock (global) read/write; version stamp + content hashes
- [x] 2.4 remove (reverse from manifest), update (refresh stale), status (report installed)

## 3. CLI + interactive

- [x] 3.1 Wire `risqlet setup` with flags (--agents/--all-detected, --scope, --components, --dry-run, --json, --yes, --force, --remove, --update, --status); mode resolution (non-interactive if flags or non-TTY)
- [x] 3.2 Interactive stdlib multiselect (agents pre-checked from detection, components, scope, preview, confirm); non-TTY falls back to usage

## 4. Tests

- [x] 4.1 Adapters load/validate; capability matrix + scope support correct; canonical MCP renders correctly per format (json/jsonc/toml); instructions md-section round-trips
- [x] 4.2 Engine plan: intersection, scope filtering, global-only-MCP reported not written, unsupported component skipped with reason, dry-run writes nothing, deterministic
- [x] 4.3 apply merges preserve foreign MCP entries; manifest records actions; remove restores to clean (foreign content intact); update refreshes; status output
- [x] 4.4 CLI: non-interactive install/remove/status/dry-run/json exit codes; non-TTY never prompts; project-only@global dropped with note; skills-cli delta (skills reachable via setup + direct still works)

## 5. Dogfood (installed agents, project scope, temp dirs only)

- [x] 5.1 Harness/script: for each installed agent (claude, codex, opencode, kilo, pi), `setup --agents X --scope project --yes` into a fresh temp project, assert files/sections/MCP markers, `--status`, `--remove` -> clean, `--dry-run` writes nothing; NEVER global, NEVER a real repo; verify kilo/pi exact surfaces and correct any adapter guesses
- [x] 5.2 Record results in docs/experiments/agent-setup/ (kept local); append a summary note to the dogfooding report

## 6. Docs + wrap-up

- [x] 6.1 README: replace the multi-command install with `pip install risqlet && risqlet setup`; document the two modes, agent matrix, and removal
- [x] 6.2 Full pytest + ruff (unpiped); commit
