# Proposal: add-trace-loop

## Why

The register already links aspect → risk → mitigation → test *charter*, but the loop dead-ends there: nothing tells us whether the tests that are supposed to mitigate a risk actually pass. Closing it to aspect → risk → mitigation → test → **result** is the differentiator no competitor ships, and it makes FMEA's Detection dimension honest — a detection mitigation whose test is red has not actually earned its low Detection score. This is Stage 3 of the original roadmap.

## What Changes

- New `qrisk trace ingest <path>...`: parse Robot Framework `output.xml` and JUnit XML (stdlib only, auto-detected), match results to mitigation `tests[]` refs, append to `.qrisk/results.jsonl`.
- New `qrisk trace status [--json]`: per-mitigation coverage state (covered-passing / covered-failing / charter-only / untested), per-risk rollup, flags for failing-or-missing tests.
- Detection-evidence feedback: advisory notes when a `lever: detection` mitigation's covering test is failing or absent ("detection scored 3 but the covering test failed 2 of last 3 runs") — never mutates scores.
- Exports: trace-matrix gains a latest-result column; strategy-md's "What this does not cover" gains a failing/missing-tests subsection.
- Skills: test_ref conventions and charter→real-ref replacement documented; new `references/trace.md`; phase 5 mentions ingest.
- Dogfooding on rf-mcp with its real Robot Framework + pytest suites, including a charter→concrete-ref rewrite demonstration.

## Capabilities

### New Capabilities

- `trace-results`: result ingestion (parsers, ref resolver, results log), coverage-state classification, and detection-evidence notes.

### Modified Capabilities

- `session-status`: status surfaces failing/missing-test coverage as pending hints.
- `qrisk-cli`: export formats gain result columns/sections.
- `agent-skills`: risk-writing/mitigation guidance + trace reference.

## Impact

- New `src/qrisk/trace.py` (parsers, resolver, coverage), `.qrisk/results.jsonl` (outside the register schema — validate unaffected), CLI `trace` group, export extensions, `skills/risk-analysis/references/trace.md`, dogfood prompt + artifacts.
- No register schema change; results live in their own append-only log.
