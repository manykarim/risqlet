# Tasks: add-trace-loop

## 1. Trace core

- [x] 1.1 Implement src/qrisk/trace.py parsers: RF output.xml and JUnit XML via xml.etree, auto-detect by root, extract (suite/classname, name, outcome, duration); actionable errors on unknown root / malformed XML
- [x] 1.2 Implement the test_ref resolver: normalize rf:/pytest:/junit:/charter: refs and parsed results to (basename, testname) keys; charter never matches
- [x] 1.3 Implement results.jsonl append (CLI-stamped ts) and per-key history (last-N)
- [x] 1.4 Implement coverage classification (untested/charter-only/covered-passing/covered-failing, precedence, per-risk rollup) and detection-evidence note generation (lever=detection, low detection score, failing/absent test)

## 2. CLI, status, exports

- [x] 2.1 Wire `qrisk trace ingest <path>...` and `qrisk trace status [--json]`
- [x] 2.2 status: failing-mitigation-test pending hint (results-gated)
- [x] 2.3 Exports: trace-matrix result column; strategy-md failing/missing-tests subsection

## 3. Tests

- [x] 3.1 Parsers: RF pass/fail/skip + nested suites; JUnit pass/fail/error/skip; unknown root; malformed
- [x] 3.2 Resolver normalization across conventions; charter non-match
- [x] 3.3 Coverage classification precedence + rollup; detection-evidence note; results.jsonl append/history
- [x] 3.4 trace-matrix result column; strategy subsection; validate unaffected by results; status hint; skills drift guards

## 4. Skills

- [x] 4.1 Write references/trace.md; note ref conventions + charter replacement in risk-writing.md/mitigation.md; SKILL.md phase 5 ingest mention; budgets hold

## 5. Dogfood on rf-mcp

- [x] 5.1 Write scripts/prompts/trace-demo.md (seed session register, run bounded real tests → output.xml/junit, ingest, trace status, charter→ref rewrite + re-ingest, graceful if no tests run)
- [x] 5.2 Run: prepare rf-mcp, seed archived session register, run, collect into docs/experiments/rf-mcp/trace/, cleanup to baseline
- [x] 5.3 Evaluate + append findings to dogfooding report; apply small fixes

## 6. Wrap-up

- [x] 6.1 Full pytest + ruff (unpiped); commit
