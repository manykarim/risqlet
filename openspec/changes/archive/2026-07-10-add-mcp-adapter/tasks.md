# Tasks: add-mcp-adapter

## 1. Tool functions

- [x] 1.1 Implement src/qrisk/mcp/tools.py: init/validate/score/export wrappers returning structured dicts with actionable errors
- [x] 1.2 Implement browse_catalog (list/show/search) and get_guidance (topic → skill file content from skills_root)
- [x] 1.3 Implement upsert_risk (proposed-only, id allocation, status-field rejection, non-proposed rejection), add_mitigation (model-validated), record_decision (human: principal check, event append + status field sync, returns validate report)

## 2. Server wiring and CLI

- [x] 2.1 Implement src/qrisk/mcp/server.py (FastMCP registration of the 9 tools, stdio run) and `qrisk mcp` subcommand with lazy import + install hint; add optional extra qrisk[mcp] and mcp to dev group

## 3. Tests and docs

- [x] 3.1 Direct tests for all nine tools: happy paths, gate behaviors (status smuggling, agent principal, residual note, illegal transition surfaced by returned report), export determinism, guidance parity with skill files, unknown topic/action errors
- [x] 3.2 Server guard test (exactly 9 tools) and MCP-only end-to-end workflow test (guidance → init → risks → score → decisions → mitigation → export → validate passes)
- [x] 3.3 README section: MCP usage, .mcp.json / Claude Desktop config snippet, when to prefer CLI+skills vs MCP; full pytest + ruff; commit
