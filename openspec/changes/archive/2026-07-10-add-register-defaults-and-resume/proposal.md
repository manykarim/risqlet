# Proposal: add-register-defaults-and-resume

## Why

Dogfooding findings F4 and F5: quickscan runs never enabled catalogs on their own, so catalog-aware validation silently didn't run (F4); and the resume story — continuing a session at phases 3–5 — is completely untested, with no command that tells a returning agent or human where the session stands (F5). Both are cheap to close and unblock realistic multi-session use.

## What Changes

- `qrisk init` enables the four packaged catalogs by default in the scaffolded config.
- New read-only `qrisk status [--json]`: phase, aspects, risk counts by status, scoring/mitigation coverage, top risks by priority, pending-gate hints, last event.
- Skills reference `qrisk status` as the resume entry point (run first, resume where it points).
- Dogfooding: a headless resumed session on rf-mcp (phases 3–5 over the archived phase-0–2 register), metrics collected, findings appended to the dogfooding report.

## Capabilities

### New Capabilities

- `session-status`: the `qrisk status` command — content, hints, and JSON shape.

### Modified Capabilities

- `qrisk-cli`: the "init scaffolds a register" requirement changes — scaffolded config now enables the packaged catalogs by default.
- `agent-skills`: the risk-analysis skill gains the resume protocol (status-first).

## Impact

- `src/qrisk/store.py` (starter config), new `src/qrisk/status.py`, CLI wiring, skills text, drift-guard expectations, dogfood prompt + experiment artifacts.
- No register schema changes; existing registers unaffected.
