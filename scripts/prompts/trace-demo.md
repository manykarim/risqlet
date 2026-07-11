Use the risk-analysis skill, focusing on the trace loop
(.claude/skills/risk-analysis/references/trace.md — read it).

A completed risk register already exists in `.risqlet/` (a full session:
5 mitigating risks with mitigations, some carrying `charter:` and `rf:` test
refs). Your job is to close the loop by ingesting REAL test results from this
repository.

Steps:

1. `risqlet status --json` and `risqlet trace status --json` to see the starting
   coverage (mitigations will be charter-only / untested).

2. Run a BOUNDED, SAFE, FAST subset of this repo's own tests and capture a
   machine-readable report. Prefer pytest with JUnit output:
   `python -m pytest <a small fast test dir or file> -q --junitxml=.risqlet/junit.xml`
   (pick unit tests that need no display/network; timebox to a few minutes; if
   the suite won't run cleanly headless, run the smallest subset that does and
   say so). If Robot Framework suites are trivially runnable, an `output.xml`
   is also fine. Do NOT modify repo source or test files.

3. `risqlet trace ingest .risqlet/junit.xml` (and any output.xml). Then
   `risqlet trace status` — report per-mitigation coverage and any
   detection-evidence notes verbatim.

4. Charter→concrete-ref demonstration: pick ONE mitigation whose `charter:`
   describes something one of the tests you just ran actually covers (or is
   closest to). Rewrite that single `tests[]` entry from the `charter:` form
   to the concrete `pytest:<path>::<name>` (or `rf:`) ref for the real test,
   keeping everything else unchanged. Re-run `risqlet trace ingest` if needed and
   `risqlet trace status` to show that mitigation flip from charter-only to
   covered-passing or covered-failing. This edits only `.risqlet/`.

5. `risqlet validate --json` (must still pass — results live outside the schema).

Rules: `risqlet` on PATH; only `.risqlet/` may be written; no events/status
changes needed (this is a trace demo, not a gate). Finish with the before/after
`trace status` outputs, the tests you ran, the charter→ref rewrite you made,
and the validate JSON in your final answer.
