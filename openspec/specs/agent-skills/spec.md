# agent-skills Specification

## Purpose
TBD - created by archiving change add-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: Cross-vendor skill format
Each shipped skill SHALL be a directory containing a `SKILL.md` with YAML frontmatter declaring `name` (matching the directory name) and `description`; additional depth SHALL live in bundled reference files, keeping `SKILL.md` within a lean line budget (risk-analysis ≤ 200 lines, risk-quickscan ≤ 150). Skills SHALL NOT depend on platform-specific features; platform enhancements may be mentioned as optional.

#### Scenario: Frontmatter well-formed
- **WHEN** every shipped SKILL.md is parsed
- **THEN** name and description are present and name matches the directory

#### Scenario: Progressive-disclosure budget
- **WHEN** SKILL.md line counts are measured
- **THEN** they are within the declared budgets

### Requirement: risk-analysis skill drives the gated pipeline
The `risk-analysis` skill SHALL instruct the agent through six phases (context, aspects, elicit, score, mitigate, emit) where every phase names its entry/exit criteria and the exact `risqlet` commands to run, and every gate requires explicit human confirmation before any `human:` principal event is recorded. It SHALL restate the output contracts (max 6 aspects, capped top risks, mandatory residual notes) and the evidence rule: risks without repo evidence are speculative and must be grounded or dropped at the phase-2 gate; evidence paths must never be invented.

#### Scenario: Phases and gates documented
- **WHEN** the skill content is read
- **THEN** all six phases appear with human gates at aspects selection, top-risk selection, contested scores, and mitigation acceptance

#### Scenario: Determinism boundary stated
- **WHEN** the scoring guidance is read
- **THEN** it directs factor values + rubric anchors to be written to the register and `risqlet score` to compute all derived priorities, never the model

### Requirement: Elicitation recipes reference the catalog
The skill's elicitation material SHALL define at least five divergent passes (guideword sweep, pre-mortem, persona lenses, inside-out code-anchored, outside-in catalog match) and reference catalog entries by id only (no duplicated entry text). All referenced catalog ids SHALL resolve against the packaged packs.

#### Scenario: Referenced ids resolve
- **WHEN** catalog entry ids are extracted from all skill files
- **THEN** every id resolves via the catalog loader

#### Scenario: Referenced commands exist
- **WHEN** `risqlet` subcommands are extracted from all skill files
- **THEN** every subcommand exists in the CLI parser

### Requirement: risk-quickscan is gate-free and self-limiting
The `risk-quickscan` skill SHALL scope analysis to a specific change/diff, write only `proposed` risks with provenance, never modify workflow phase or risk status, and end by recommending a full risk-analysis session when it found three or more plausible risks or any severity-9 candidate.

#### Scenario: Quickscan constraints stated
- **WHEN** the quickscan skill is read
- **THEN** it forbids phase/status changes and defines the escalation recommendation rule

### Requirement: risk-analysis skill teaches status-first resume
The risk-analysis skill SHALL instruct the agent to run `risqlet status` before starting work, resume at the phase it reports while honoring its pending hints, and never re-run gates whose decisions are already recorded in the event log. SKILL.md line budgets continue to hold.

#### Scenario: Resume protocol present
- **WHEN** the skill content is read
- **THEN** it directs status-first resume and forbids redoing recorded gate decisions

#### Scenario: Drift guard still passes
- **WHEN** the skills drift-guard tests run
- **THEN** `risqlet status` resolves as an existing CLI subcommand

### Requirement: risk-analysis skill teaches the ensemble protocol
The risk-analysis skill SHALL include an ensemble reference covering: independent pass/persona execution (write before cross-reading; dissimilar personas), deterministic convergence via `risqlet dedupe` with merge decisions kept with agent+human (`risqlet merge` for true duplicates only), an optional isolated-subagent recipe for platforms that support it, and independent multi-scoring where disagreement is surfaced rather than averaged. Drift guards (catalog ids, CLI commands, line budgets) SHALL keep passing.

#### Scenario: Ensemble reference present
- **WHEN** the skill content is read
- **THEN** it covers independent passes, dedupe-then-decide convergence, and disagreement-not-averaging

#### Scenario: New commands known
- **WHEN** the drift guards run
- **THEN** `risqlet dedupe` and `risqlet merge` resolve as CLI subcommands

### Requirement: risk-analysis skill teaches the trace loop
The risk-analysis skill SHALL document the test_ref conventions (`rf:`, `pytest:`, `junit:`, `charter:`), the replacement of a `charter:` ref with a concrete ref once the test exists, and a trace workflow (ingest results, read `risqlet trace status`, use detection-evidence notes at the score gate). Drift guards (catalog ids, CLI commands, line budgets) SHALL keep passing.

#### Scenario: Trace guidance present
- **WHEN** the skill content is read
- **THEN** it covers the ref conventions, charter replacement, and the ingest→status→act workflow

#### Scenario: trace command known
- **WHEN** the drift guards run
- **THEN** `risqlet trace` resolves as a CLI subcommand

### Requirement: skills teach continuous re-assessment
The skills SHALL include a continuous-reassessment reference covering when to run `risqlet diff` (scope a change) and `risqlet check` (gate), and the PR-time and in-session loops; the risk-quickscan skill SHALL direct the agent to run `risqlet diff` first to see which existing risks already cover the change before eliciting new ones. Drift guards SHALL keep passing (`risqlet diff`, `risqlet check`, `risqlet ci` resolve as subcommands).

#### Scenario: Continuous reference present
- **WHEN** the skill content is read
- **THEN** it covers diff-for-scoping, check-for-gating, and both loops

#### Scenario: Quickscan scopes with diff
- **WHEN** the risk-quickscan skill is read
- **THEN** it instructs running risqlet diff to find already-covering risks first

### Requirement: elicitation references the security packs
The risk-analysis skill's elicitation guidance SHALL note that security-relevant products can enable the `mitre-attack` and `owasp-web` packs via `config.catalogs` and match risks against their entries, referencing them by id. Drift guards SHALL resolve those ids against the packaged packs.

#### Scenario: Security pack guidance present
- **WHEN** the elicitation reference is read
- **THEN** it names the mitre-attack and owasp-web packs and how to enable them

#### Scenario: Referenced ids resolve
- **WHEN** the drift guards extract catalog ids from the skills
- **THEN** any mitre-attack or owasp-web ids resolve against the packaged packs

### Requirement: skills teach barrier-driven guardrails
The risk-analysis skill SHALL document that a mitigation's `barrier` and its risk's `evidence` drive `risqlet guardrails` (the barrier→surface map, the hard-vs-soft enforcement distinction, and human review before install), and the mitigate-phase guidance SHALL note that choosing `barrier: prevent` vs `detect` has downstream guardrail consequences. Drift guards SHALL resolve the `guardrails` subcommand.

#### Scenario: Guardrails guidance present
- **WHEN** the skill content is read
- **THEN** it covers the barrier→surface mapping, hard vs soft enforcement, and human-gated install

#### Scenario: Subcommand known to drift guard
- **WHEN** the skills drift guards run
- **THEN** `risqlet guardrails` resolves as a CLI subcommand

