# Mapping mitigations

Every accepted risk gets at least one mitigation — or an explicit,
human-confirmed decision to accept it. A mitigation is embedded in its risk's
file:

```yaml
mitigations:
  - id: M-0004                    # next free M number, global across register
    risk_ids: [R-0007]
    treatment: reduce             # avoid | reduce | transfer | accept
    lever: detection              # severity | occurrence | detection
    barrier: detect               # prevent | detect | recover
    technique_ref: techniques.data-reconciliation
    concrete: Nightly job compares PSP settlement file against the transaction
      journal; mismatches page the payments on-call with both records attached.
    residual_note: Issuer-side chargebacks stay invisible until settlement +2d;
      intra-day divergence is not caught.
    tests: ["rf:suites/reconciliation.robot::Nightly Settlement Match"]
```

## The three classifications (they are different questions)

- **treatment** — the strategic posture: `avoid` (remove the risky thing),
  `reduce` (make it less likely/bad/invisible), `transfer` (insurance, SLA,
  third party), `accept` (named human lives with it — record who).
- **lever** — which scoring factor this attacks: design changes and
  fail-safes push **severity** down; prevention and error-proofing push
  **occurrence** down; tests, checks, and alerts improve **detection**.
- **barrier** — where it sits on the timeline: **prevent** (before the event),
  **detect** (as it happens), **recover** (after). A healthy top risk usually
  ends up with barriers in at least two positions.

The `barrier` (and the risk's `evidence` paths) also drive `risqlet guardrails` — a `prevent` barrier can become a Claude Code deny-permission or blocking hook, a `detect` barrier a post-write scan or CI check, each scoped to the evidence paths and tagged with the risk id. So choosing prevent vs detect has downstream enforcement teeth (see `references/guardrails.md`).

Testing mostly buys *detection*; if every mitigation in the session is
`lever: detection`, say so — the product may need design work, not more tests.

## Finding techniques

`risqlet catalog search <terms>` is a keyword lookup, not a recommender: fetch
candidates, `risqlet catalog show <id>`, and judge fit against the risk's
condition yourself. Techniques for doing (`techniques.*`), thinking tools and
oracles for recognizing (`heuristics.*`). No entry fits? Write the concrete
action anyway and leave `technique_ref` empty — the register serves the risk,
not the catalog.

## Residual notes (mandatory, and the point)

One honest sentence: what this mitigation does NOT cover — timing windows,
excluded cases, assumptions that can rot. Validate rejects mitigations without
one. The export aggregates them into "What this does not cover", which is the
section that keeps the strategy honest. Writing "fully covers the risk" is
almost always false; find the gap.

## Test charters

`tests[]` links mitigations to verification, one entry per test in a
recognized form (see `references/trace.md`): `rf:suite::Name`,
`pytest:path::test_name`, `junit:classname::name`, or a `charter:<mission>`
for a test that should exist but does not yet. Charters should be concrete
enough that a test-generation agent (or a human) can start: subject,
variation idea, oracle. **Replace a `charter:` with the concrete ref the
moment the test exists** — then `risqlet trace ingest` + `risqlet trace status`
report whether it actually passes, closing aspect → risk → mitigation → test →
result. A detection-lever mitigation whose test is red has not earned its
Detection score.
