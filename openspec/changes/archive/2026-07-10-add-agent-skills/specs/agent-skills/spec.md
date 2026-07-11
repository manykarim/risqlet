# Spec: agent-skills

## ADDED Requirements

### Requirement: Cross-vendor skill format
Each shipped skill SHALL be a directory containing a `SKILL.md` with YAML frontmatter declaring `name` (matching the directory name) and `description`; additional depth SHALL live in bundled reference files, keeping `SKILL.md` within a lean line budget (risk-analysis ≤ 200 lines, risk-quickscan ≤ 150). Skills SHALL NOT depend on platform-specific features; platform enhancements may be mentioned as optional.

#### Scenario: Frontmatter well-formed
- **WHEN** every shipped SKILL.md is parsed
- **THEN** name and description are present and name matches the directory

#### Scenario: Progressive-disclosure budget
- **WHEN** SKILL.md line counts are measured
- **THEN** they are within the declared budgets

### Requirement: risk-analysis skill drives the gated pipeline
The `risk-analysis` skill SHALL instruct the agent through six phases (context, aspects, elicit, score, mitigate, emit) where every phase names its entry/exit criteria and the exact `qrisk` commands to run, and every gate requires explicit human confirmation before any `human:` principal event is recorded. It SHALL restate the output contracts (max 6 aspects, capped top risks, mandatory residual notes) and the evidence rule: risks without repo evidence are speculative and must be grounded or dropped at the phase-2 gate; evidence paths must never be invented.

#### Scenario: Phases and gates documented
- **WHEN** the skill content is read
- **THEN** all six phases appear with human gates at aspects selection, top-risk selection, contested scores, and mitigation acceptance

#### Scenario: Determinism boundary stated
- **WHEN** the scoring guidance is read
- **THEN** it directs factor values + rubric anchors to be written to the register and `qrisk score` to compute all derived priorities, never the model

### Requirement: Elicitation recipes reference the catalog
The skill's elicitation material SHALL define at least five divergent passes (guideword sweep, pre-mortem, persona lenses, inside-out code-anchored, outside-in catalog match) and reference catalog entries by id only (no duplicated entry text). All referenced catalog ids SHALL resolve against the packaged packs.

#### Scenario: Referenced ids resolve
- **WHEN** catalog entry ids are extracted from all skill files
- **THEN** every id resolves via the catalog loader

#### Scenario: Referenced commands exist
- **WHEN** `qrisk` subcommands are extracted from all skill files
- **THEN** every subcommand exists in the CLI parser

### Requirement: risk-quickscan is gate-free and self-limiting
The `risk-quickscan` skill SHALL scope analysis to a specific change/diff, write only `proposed` risks with provenance, never modify workflow phase or risk status, and end by recommending a full risk-analysis session when it found three or more plausible risks or any severity-9 candidate.

#### Scenario: Quickscan constraints stated
- **WHEN** the quickscan skill is read
- **THEN** it forbids phase/status changes and defines the escalation recommendation rule
