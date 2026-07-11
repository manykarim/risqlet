# Tasks: add-ensemble-tooling

## 1. Ensemble core

- [x] 1.1 Implement src/qrisk/ensemble.py: token normalization (statement stopword-filtered tokens, evidence path stripping shared with harness), weighted pairwise similarity, threshold from config constraints (default 0.5), connected-component clustering, survivor suggestion
- [x] 1.2 Implement merge: refusals (non-proposed duplicate, terminal survivor, unknown ids — register untouched), evidence/aspect union, mitigation move with risk_ids rewrite, merged_from on survivor, duplicate file deletion
- [x] 1.3 Add Risk.disagreement and Risk.merged_from optional model fields; regenerate schemas
- [x] 1.4 Implement disagreement computation in scoring (>=2 qualifying score sets; mean normalized spread; removal when <2) and validate recompute check
- [x] 1.5 status: contested-scores pending hint (>0.25, statuses proposed/reviewed/accepted)
- [x] 1.6 CLI wiring: `qrisk dedupe [--json]`, `qrisk merge <survivor> <dup...>`

## 2. Tests

- [x] 2.1 Dedupe: near-dup clustered, unrelated not, evidence-overlap weighting, threshold config, determinism, read-only
- [x] 2.2 Merge: full mechanics + validate passes after, each refusal leaves register byte-identical
- [x] 2.3 Disagreement: spread math (incl. 0.44 severity case), removal, mixed-policy ignored, validate mismatch detection, status hint
- [x] 2.4 Skills drift guards green with new subcommands

## 3. Skill content

- [x] 3.1 Write skills/risk-analysis/references/ensemble.md and wire SKILL.md phase 2/3 pointers (budget 210 if needed)

## 4. Dogfood on tshirt-shop-om

- [x] 4.1 Write scripts/prompts/ensemble-quickstart.md (two independent passes, dedupe, true-dup merges, simulated top-5 gate, labeled events)
- [x] 4.2 Run: prepare tshirt-shop-om → run → collect (incl. cluster/merge counts) → cleanup to baseline
- [x] 4.3 Evaluate + append findings to dogfooding report; apply small fixes

## 5. Wrap-up

- [x] 5.1 Full pytest + ruff (unpiped exit codes); commit
