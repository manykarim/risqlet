# Tasks: add-dogfooding-experiments

## 1. Harness

- [x] 1.1 Implement scripts/dogfood.py (prepare/run/collect/cleanup subcommands, baseline+residue git checks, timeout, output capture, metrics computation incl. evidence-path checks and statement-format regex)
- [x] 1.2 Write scripts/prompts/quickscan.md and scripts/prompts/session.md (simulated-gate protocol, human:many pre-authorizations, note labeling)

## 2. Experiments

- [x] 2.1 Run Experiment 1a: risk-quickscan on rf-mcp (prepare → run → collect → cleanup); artifacts under docs/experiments/rf-mcp/quickscan/
- [x] 2.2 Run Experiment 1b: risk-quickscan on robotframework-javaui; artifacts under docs/experiments/robotframework-javaui/quickscan/
- [x] 2.3 Run Experiment 2: abbreviated risk-analysis session (phases 0-2, simulated gates) on rf-mcp; artifacts under docs/experiments/rf-mcp/session/

## 3. Evaluation and fixes

- [x] 3.1 Write docs/experiments/dogfooding-report.md (metrics tables, qualitative assessment, findings list with dispositions, success-criteria verdict)
- [x] 3.2 Apply fixed-here findings (skill wording, CLI messages, small validation gaps) with tests where applicable
- [x] 3.3 Full pytest + ruff; commit
