# adversarial-review Specification

## Purpose
TBD - created by archiving change add-adversarial-review. Update Purpose after archive.
## Requirements
### Requirement: review computes a deterministic verdict from a panel's charges
`risqlet review` SHALL compute a SHIP / REMAND / BLOCK verdict for a named decision from a set of structured charges produced by a host-run review panel, using only the charges as input, calling no LLM, and producing byte-identical output for identical input. Each charge SHALL carry a reviewer id, a category (short slug), a severity of `fatal`, `major`, or `minor`, and a `reproducible` flag. Charges with `reproducible` false SHALL NOT affect the verdict.

The verdict SHALL be: **BLOCK** when a category survives with a `fatal` charge; **REMAND** when a category survives with a `major` charge, or when a single reproducible `fatal` charge exists without corroboration; otherwise **SHIP**. A category *survives* only when at least two **distinct** reviewers each file a reproducible charge in that category — multiple charges from the same reviewer SHALL count once.

#### Scenario: Corroborated fatal blocks
- **WHEN** two distinct reviewers each file a reproducible `fatal` charge in the same category
- **THEN** the verdict is BLOCK

#### Scenario: Corroborated major remands
- **WHEN** two distinct reviewers each file a reproducible `major` charge in the same category and no category has a surviving fatal
- **THEN** the verdict is REMAND

#### Scenario: Uncorroborated charges ship
- **WHEN** every reproducible charge is raised by only one reviewer, with no lone fatal
- **THEN** the verdict is SHIP

#### Scenario: Distinct-reviewer corroboration, not charge count
- **WHEN** a single reviewer files two reproducible charges of the same category and no other reviewer raises it
- **THEN** that category does not survive, and it does not by itself cause a REMAND or BLOCK

#### Scenario: Lone fatal remands
- **WHEN** exactly one reviewer files a reproducible `fatal` charge and no category is corroborated
- **THEN** the verdict is REMAND (not SHIP, not BLOCK)

### Requirement: panel validity is enforced
`risqlet review` SHALL reject a panel that cannot produce a trustworthy verdict: the panel SHALL contain at least two distinct reviewers, and the author of the decision under review SHALL NOT be among the reviewers. An invalid panel SHALL be reported as an error naming the reason, and SHALL NOT record a verdict.

#### Scenario: Too few reviewers rejected
- **WHEN** a panel contains fewer than two distinct reviewers
- **THEN** review errors that a valid panel needs at least two independent reviewers, and records nothing

#### Scenario: Author cannot review their own decision
- **WHEN** the decision's author id appears among the reviewer ids
- **THEN** review errors that the author may not sit on the panel, and records nothing

### Requirement: verdicts are recorded, advisory, and human-gated
`risqlet review` SHALL append each computed verdict, with its inputs (the decision id, the reviewer ids, and the surviving categories), to an append-only `.risqlet/reviews.jsonl`. The verdict SHALL be advisory: recording it SHALL NOT change any risk's status or phase. A lifecycle transition prompted by a verdict SHALL still be made by a human principal through the existing event gate — the verdict informs the decision, it does not make it.

#### Scenario: Verdict recorded without transition
- **WHEN** review produces a BLOCK verdict for a risk in `accepted` status
- **THEN** the verdict is appended to reviews.jsonl and the risk's status is unchanged until a human records a transition

#### Scenario: Recorded verdict is reproducible
- **WHEN** `risqlet validate` recomputes a recorded verdict from its charges
- **THEN** validation fails if the recorded verdict does not match the recomputed one

### Requirement: the review panel is convened by the host, not risqlet
risqlet SHALL NOT convene the panel or invoke any model. A shipped `risk-court` Agent Skill SHALL instruct the host agent to convene at least two independent reviewers — ideally cross-perspective or cross-vendor — to challenge a named decision against the actual code and evidence, each emitting charges in risqlet's defined charges schema. risqlet's role SHALL be limited to validating the panel and computing the deterministic verdict from the emitted charges.

#### Scenario: Semantic review is the host's, arithmetic is risqlet's
- **WHEN** a review is run
- **THEN** the reviewers' judgments are produced by the host's model(s) and risqlet only computes and records the verdict, calling no model itself

#### Scenario: Skill states the independence requirement
- **WHEN** the `risk-court` skill is used
- **THEN** it directs the host to use reviewers independent of the decision's author and of each other, because the verdict's corroboration rule is meaningful only for independent charges

