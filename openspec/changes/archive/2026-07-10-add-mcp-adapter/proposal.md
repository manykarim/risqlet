# Proposal: add-mcp-adapter

## Why

Coding agents with shell access already have the full workflow via CLI + skills, but MCP-connected clients without repo shell access (Claude Desktop, restricted agent setups, MCP-first platforms) currently cannot use qrisk at all. A thin stateless MCP adapter over the existing core closes that gap and completes the portability story — without duplicating logic, growing a second state model, or violating the small-tool-surface evidence.

## What Changes

- New `qrisk mcp` CLI subcommand running a stdio MCP server (official Python MCP SDK), packaged as an optional extra `qrisk[mcp]` so the core stays dependency-light.
- Nine stateless tools, all taking an explicit `project_dir`: `init_register`, `validate_register`, `score_risks`, `export_register`, `browse_catalog`, `get_guidance` (returns skill/reference markdown as data — playbooks for MCP-only clients), `upsert_risk` (proposed-only; refuses status changes), `add_mitigation` (residual note mandatory), `record_decision` (status/phase events; human-principal obligation stated; validate remains the backstop).
- Framework-provider guarantees: the server performs no inference, returns structure/validation/guidance only, and keeps all state in `.qrisk/` files.
- Tests for every tool function (including gate behaviors) plus a server construction/tool-count guard (≤ 10 tools); README section with client configuration examples.

## Capabilities

### New Capabilities

- `mcp-adapter`: The tool surface, its statelessness and gate-preserving semantics, the guidance-as-data behavior, and the packaging/entry point.

### Modified Capabilities

_None — the adapter is a pure consumer of register, policies, catalog, and skills content._

## Impact

- New source: `src/qrisk/mcp/` (tool functions + thin server wiring), CLI `mcp` subcommand, optional dependency group.
- Downstream: the dogfooding change can exercise either integration path (CLI+skills or MCP) in example projects.
