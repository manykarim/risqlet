# Closing the loop: test results

A mitigation is a promise; a passing test is the promise kept. `risqlet trace`
connects mitigation `tests[]` refs to real execution results so the register
knows which risks are actually covered — and so a detection score has to be
earned, not just claimed.

## Test ref conventions

Write mitigation `tests[]` entries in one of these forms:

- `charter:<mission>` — a test that should exist but does not yet (a TODO). It
  never matches a result; it keeps the intent visible.
- `rf:<suite-or-path>::<Test Name>` — Robot Framework.
- `pytest:<path>::<test_func>` — pytest (run with `--junitxml`).
- `junit:<classname>::<name>` — any JUnit-XML producer.

Matching is by normalized (suite/file basename, test name), so path spelling
does not matter. **Replace a `charter:` with a concrete ref the moment the
test exists** — that is what flips the mitigation from charter-only to
covered-passing/failing.

## Workflow

1. Run the relevant tests, producing `output.xml` (RF) or a JUnit file.
2. `risqlet trace ingest <report.xml> ...` — appends to `.risqlet/results.jsonl`
   (telemetry, outside the register; `validate` ignores it).
3. `risqlet trace status` — per-mitigation state (covered-passing /
   covered-failing / charter-only / untested), per-risk rollup, and
   detection-evidence notes.

## Detection evidence at the score gate

The loop-closing move: when a `lever: detection` mitigation claims a low
Detection score (good detectability) but its covering test is failing or
absent, `trace status` says so — e.g. *"R-0007 detection scored 3 but covering
test … failed 2 of last 3 runs — re-score detection or fix the test"*. The
tool never changes the score; bring the note to the human at the score or
mitigate gate and decide: fix the test, or re-score detection upward (worse
detectability) to tell the truth. A red test quietly propping up a "3" is
exactly the completeness theater the register exists to prevent.
