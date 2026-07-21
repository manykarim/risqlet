## 1. The deterministic verdict core

Build and pin the rules first — the corroboration rule is the load-bearing part and
the whole value proposition rests on getting it exactly right.

- [x] 1.1 New `src/risqlet/review.py`: a `ReviewError`, a charge/panel data shape, and
  `compute_verdict(decision_author, charges) -> {verdict, surviving, ...}` implementing:
  panel validity (≥2 distinct reviewers, author not a reviewer), distinct-reviewer
  corroboration (a category survives only when ≥2 distinct reviewers each file a
  reproducible charge in it), and the ladder BLOCK (surviving fatal) / REMAND (surviving
  major, or a lone reproducible fatal) / SHIP (otherwise). `reproducible=false` and
  `minor` never move the verdict.
- [x] 1.2 Unit-test every rule, including the flip cases proven decisive in the
  experiment: (a) one reviewer's two same-category charges do NOT corroborate → SHIP,
  not REMAND; (b) two distinct reviewers on one category → survives; (c) lone reproducible
  fatal → REMAND (not SHIP, not BLOCK); (d) corroborated fatal → BLOCK; (e) all-minor →
  SHIP. Assert deterministic (same input → same output).
- [x] 1.3 Panel-validity tests: <2 distinct reviewers → ReviewError; author among
  reviewers → ReviewError; neither records a verdict.

## 2. Record + read reviews.jsonl

- [x] 2.1 In `review.py`, append a verdict record (decision id, reviewer ids, verdict,
  surviving categories, the charges) to `.risqlet/reviews.jsonl` — UTF-8, `\n`,
  `json.dumps(sort_keys=True)`, mirroring how `trace` writes `results.jsonl`. A read
  helper returns recorded reviews; a malformed line raises with file:line context.
- [x] 2.2 Confirm the record carries enough to RECOMPUTE the verdict (the charges), so
  validate can verify it.

## 3. CLI surface

- [x] 3.1 Add a `review` subcommand to `src/risqlet/cli.py`: reads a charges JSON file
  (`--charges <path>` or stdin) for a `--decision <risk-id>`, computes the verdict via
  review.py, appends the record, and prints the verdict (human + `--json`). A
  `ReviewError` is one of the clean CLI errors (prints `error: ...`, exits 1) — add it to
  the `_CLEAN_CLI_ERRORS` tuple.
- [x] 3.2 The command is advisory: it MUST NOT change any risk's status or phase. Add a
  test asserting the risk file is byte-identical before/after a BLOCK verdict.
- [x] 3.3 Define the charges JSON schema (a small documented shape) the command accepts,
  and validate incoming charges (reject malformed/severity-out-of-range with ReviewError).

## 4. validate recomputes recorded verdicts

- [x] 4.1 In `src/risqlet/validate.py`, recompute each recorded verdict from its stored
  charges and add a finding when the recorded verdict does not match (mirroring the
  ensemble `disagreement` recompute). A register with no reviews.jsonl is unaffected.
- [x] 4.2 Test: a hand-tampered recorded verdict fails validate; an untouched one passes.

## 5. The host-facing skill

- [x] 5.1 New `skills/risk-court/` skill (markdown + a `charges.schema.json`): instruct
  the host to convene ≥2 independent reviewers (cross-perspective/cross-vendor), each
  challenging the named decision AGAINST THE ACTUAL CODE/EVIDENCE, and emit charges in
  the schema. State plainly that risqlet computes the verdict and calls no model, and that
  the corroboration rule is meaningful only for independent reviewers.
- [x] 5.2 Frame it as a TARGETED gate (high-stakes accept / phase sign-off), not a blanket
  pass over every risk — the review cost is host-borne.
- [x] 5.3 If risqlet ships skills via `setup`/`skills install`, register `risk-court`
  there; otherwise document how to invoke it. Keep the skill self-contained.

## 6. Docs

- [x] 6.1 README: a short "adversarial review" note — what it is, the framework-provider
  split (host reviews, risqlet computes the verdict, human decides), and honest scope
  (advisory, targeted, small evidence base).
- [x] 6.2 CHANGELOG entry under Added.
- [x] 6.3 NOTICE/provenance: record that the verdict rules are a clean-room
  reimplementation from agentic-qe's (MIT) QE-Court behavior, not copied source — the
  spec scenarios are the derivation trail.

## 7. Verify

- [x] 7.1 End-to-end: build a small scratch register, feed a charges file that reproduces
  the experiment (a corroborated hollow-mitigation-test → REMAND/BLOCK; an uncorroborated
  set → SHIP), confirm the verdict and the reviews.jsonl record, and confirm the risk
  status did not change.
- [x] 7.2 Full suite + lint green; both encoding guards still armed (review.py is on the
  text-I/O path — use `encoding="utf-8"`, `newline="\n"`).
- [x] 7.3 `openspec validate add-adversarial-review --strict`.
- [x] 7.4 `/verify` or a manual drive of the `review` command against the real
  robotframework-javaui decision set from the experiment, confirming it reproduces the
  3/3-vs-validate's-0/3 result end-to-end through the shipped command.
