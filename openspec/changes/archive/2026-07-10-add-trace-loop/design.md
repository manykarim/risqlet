# Design: add-trace-loop

## Context

Queue item 3. Mitigations already carry `tests[]` refs (`rf:suite::Name`, `pytest:path::test_name`, or `charter:mission`). What's missing is the result feedback. Constraints: stdlib-only parsing (no pytest/robot deps), results kept outside the register schema so `validate` is unaffected, and detection-evidence stays advisory (framework-provider — the tool informs, the human re-scores).

## Goals / Non-Goals

**Goals:** ingest RF/JUnit results and match them to mitigation tests; report coverage state per mitigation/risk; make Detection scores accountable to real test outcomes; surface it in exports and status; prove it on rf-mcp's actual suites.

**Non-Goals:** running tests (ingest only), source-coverage %, statistical flaky detection (last-N history only), MCP tool additions (CLI-first; revisit in queue item 4), pytest-native (json) ingestion (JUnit XML covers pytest via `--junitxml`).

## Decisions

### D1. Ref conventions and the resolver (`src/qrisk/trace.py`)

A `test_ref` is `<kind>:<locator>`. Recognized kinds: `rf:` (suite path or name `::` test name), `pytest:` (file path `::` test function), `junit:` (classname `::` name), `charter:` (a mission string — not a real test, cannot match a result). The resolver normalizes any ref and any parsed result to a comparison key `(basename-or-suite-lowercased, testname-lowercased)`: RF suite `Reconciliation` test `Nightly Settlement Match` → `(reconciliation, nightly settlement match)`; pytest `tests/test_x.py::test_foo` → `(test_x, test_foo)`; JUnit classname `tests.test_x` name `test_foo` → `(test_x, test_foo)`. Matching is on that key, so an `rf:` charter written as `rf:suites/reconciliation.robot::Nightly Settlement Match` matches an RF result regardless of full-path vs. name differences. `charter:` refs never match (they are TODO markers).

### D2. Parsers (stdlib `xml.etree.ElementTree`)

Auto-detect by root tag: `<robot>` → RF parser, `<testsuite>`/`<testsuites>` → JUnit parser. RF: walk `suite`/`test`, read the nested `status` element's `status` attr (PASS/FAIL/SKIP) and `elapsed`/timestamps if present. JUnit: walk `testcase`; presence of a `<failure>`/`<error>` child → fail, `<skipped>` → skip, else pass; `classname`, `name`, `time`. Both yield `[{suite/classname, name, outcome, duration}]`. Unknown root → actionable error. Malformed XML → error naming the file.

### D3. Results log

`.qrisk/results.jsonl`, append-only, one line per ingested test occurrence: `{ts, test_ref (normalized display form), key: [k1,k2], outcome, source (filename), duration}`. `ts` is the ingest time passed in by the CLI (no `Date.now` in scripts — CLI stamps it). History per key = all lines with that key, most recent last; last-N (N=5) drives "failed X of last Y".

### D4. Coverage classification (`qrisk trace status`)

Per mitigation over its `tests[]`: `untested` (no tests[]), `charter-only` (all tests[] are `charter:` or none have results yet), `covered-failing` (≥1 non-charter test whose latest result is fail), `covered-passing` (≥1 non-charter test all latest-passing, none failing). Precedence: failing > passing > charter-only > untested. Per-risk rollup = worst mitigation state; risks with an accepted+ status and a failing/untested detection mitigation are flagged. Output human table or `--json`.

### D5. Detection-evidence feedback (the loop-closer)

For each mitigation with `lever: detection` whose covering tests are failing or absent, emit an advisory note joining it to the risk's Detection score: read the risk's active-policy score set, and if `detection` factor is low (≤4, "we claimed good detection") while the covering test is failing/missing, produce: `"<risk> detection scored <d> but covering test <ref> <failed X of last Y | has no results> — re-score detection or fix the test"`. Notes are output only; scores are never touched. Threshold (≤4) fixed for v1.

### D6. Exports and status integration

- `trace-matrix-csv`: add a `result` column = latest outcome for the row's test ref (or `charter`/`none`).
- `strategy-md`: "What this does not cover" gains "### Mitigations with failing or missing tests" listing flagged mitigations with their state.
- `qrisk status`: pending hint when any accepted/mitigating risk has a `covered-failing` mitigation ("N risk(s) have failing mitigation tests: ids"). Reuses results; if no results.jsonl, silent.

### D7. Skills

`references/trace.md` (short): ingest workflow (run tests → ingest reports → read `trace status` → act), coverage states table, detection-evidence use at the score/mitigate gate, charter→real-ref lifecycle. `risk-writing.md`/`mitigation.md`: one-line note on the three real ref conventions and replacing a `charter:` with a concrete ref once the test exists. SKILL.md phase 5: "if test results exist, `qrisk trace ingest <reports>` and review `qrisk trace status`." Budgets hold.

### D8. Dogfood on rf-mcp

`scripts/prompts/trace-demo.md`: seed archived rf-mcp session register (has mitigations with `rf:`/`charter:` tests), run a bounded subset of the repo's real tests producing `output.xml` and a JUnit file (agent chooses safe fast tests; timeboxed), `qrisk trace ingest` both, `qrisk trace status`. Then pick one mitigation whose `charter:` corresponds to a test that actually ran, rewrite it to the concrete ref, re-ingest, show the state flip to covered-passing/failing. Report coverage table + any detection-evidence notes. Metrics: results ingested, mitigations by state, detection notes, charter→ref rewrites.

## Risks / Trade-offs

- [Ref matching false positives across suites with same test name] → key includes suite/file basename; documented residual risk; charter refs never match.
- [rf-mcp tests slow/flaky/needs display] → prompt instructs a bounded safe subset and a timebox; if no tests run, the run still demonstrates ingest on a synthetic/JUnit file and says so (graceful).
- [results.jsonl mistaken for register state] → lives outside the schema, `validate` ignores it, documented as telemetry not truth-of-record.

## Migration Plan

Additive. Registers without results behave exactly as before; `trace status` on a resultless register reports all-charter/untested.

## Open Questions

- MCP `trace` tools — deferred to queue item 4 with the other MCP parity questions.
