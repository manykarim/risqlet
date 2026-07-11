# Spec: dogfood-harness

## ADDED Requirements

### Requirement: Repeatable target preparation and cleanup
The harness SHALL prepare a target repo (install skills into the target's `.claude/skills/`, make `qrisk` invocable) and SHALL restore it afterwards: experiment artifacts (`.qrisk/`, installed skills) are removed, and the target's `git status --porcelain` after cleanup SHALL match the recorded baseline, with any residue reported loudly rather than silently left.

#### Scenario: Clean round trip
- **WHEN** prepare, run, collect, cleanup execute against a target
- **THEN** the target's git status matches its pre-experiment baseline

### Requirement: Constrained headless runs
Each experiment run SHALL invoke the Claude Code CLI headlessly with a stored prompt file, a wall-clock timeout, restricted allowed tools (read/search, qrisk commands, read-only git, writes scoped to the register), and captured full output saved under `docs/experiments/<target>/<experiment>/`.

#### Scenario: Timeboxed capture
- **WHEN** a run exceeds its timeout
- **THEN** it is terminated and the partial transcript is saved and marked as timed out

### Requirement: Register capture and mechanical metrics
After each run the harness SHALL copy the produced `.qrisk/` into the experiment directory and compute metrics mechanically: risk count, validate pass/errors/warnings, speculative ratio, evidence-path existence checks, statement-format compliance, provenance (`prompt_ref`) usage, and wall-clock. Metrics SHALL be stored as JSON alongside the register copy.

#### Scenario: Evidence spot-check
- **WHEN** metrics are computed for a register citing evidence paths
- **THEN** each cited path is checked for existence in the target repo and misses are counted and listed

### Requirement: Evaluation report with findings dispositions
`docs/experiments/dogfooding-report.md` SHALL tabulate all runs' metrics, describe qualitative observations (skill adherence, gate behavior including the simulated-gate labeling of scripted sessions), and list every finding with a disposition: fixed-here, future-change, or wontfix with reason. Success criteria (validate-passing register with ≥3 evidenced risks per target; ≥1 applied fix) SHALL be evaluated explicitly in the report.

#### Scenario: Simulated gates labeled
- **WHEN** the scripted full-session experiment is reported
- **THEN** the report states that human gates were simulated by scripted confirmations

#### Scenario: Findings actioned
- **WHEN** the report is finalized
- **THEN** each finding carries a disposition and fixed-here items are implemented in this change
