# Design: add-agent-skills

## Context

Research decisions D1/D2 (hybrid skills+small tool surface; framework-provider pattern) and the platform strategy (Claude Code premium, CLI-portable everywhere) require the workflow knowledge to ship as portable Agent Skills that drive the `qrisk` CLI. Evidence constraints to honor: elicitation quality is bounded by context grounding (persona/domain-collapse findings; Zalando's 40% hallucination rate ⇒ evidence-linking discipline), constraint-first outputs (max-6 aspects) fight completeness theater, and human gates are enforced by the register's event/validate machinery — the skill must *use* that machinery, not reinvent it.

## Goals / Non-Goals

**Goals:**
- A capable agent with shell access + these skills can run a complete, gated, auditable risk analysis producing a validated `.qrisk/` register and strategy export.
- Skills stay portable: plain SKILL.md + markdown references, no Claude-specific features required (subagent parallelism mentioned as an optional enhancement, never a dependency).
- Progressive disclosure: SKILL.md is a lean router; depth lives in reference files loaded on demand.
- Content drift is mechanically guarded (catalog ids and CLI commands referenced by skills are tested against the packages).

**Non-Goals:**
- MCP adapter (change 4); hooks-based gate hard-enforcement; persona-subagent orchestration configs; multi-agent ensemble automation (the skill describes the independent-then-merge protocol for a human/agent to follow, but no platform-specific automation ships here).

## Decisions

### D1. Layout and packaging

```
skills/
├── risk-analysis/
│   ├── SKILL.md              # frontmatter + workflow router (~150 lines max)
│   └── references/
│       ├── phases.md         # per-phase protocol: entry/exit criteria, gates, CLI calls
│       ├── elicitation.md    # pass recipes (guideword sweep, premortem, personas,
│       │                     #   inside-out, outside-in) with catalog entry ids
│       ├── scoring-rubrics.md# original anchor tables for sod-ap-v1 and li-v1 factors
│       ├── risk-writing.md   # statement format, provenance fields, evidence rules
│       └── mitigation.md     # treatment/lever/barrier guide, residual-note discipline
└── risk-quickscan/
    └── SKILL.md              # self-contained single-pass scan
```

Canonical source is `skills/` at repo root. It is included in the wheel via hatch `force-include` under `qrisk/data/skills/` so `qrisk skills install` works from an installed package (resolved via `importlib.resources`, falling back to the repo directory in editable installs).

### D2. Skill content principles

- **Frontmatter**: `name` + `description` tuned for discovery ("risk analysis, risk-based test strategy, RiskStorming-style session, FMEA scoring…" phrasing in description, since description drives skill triggering).
- **The CLI is the state machine.** Every phase section ends with the exact `qrisk` commands to run (`validate` after every mutation; `score --all` after scoring; event append via documented JSON line format written by the *human-instructed* agent — the skill instructs the agent to ask the human before recording any `human:` event, restating the accountability convention).
- **Evidence discipline**: a risk without repo evidence must be labeled speculative in conversation and either grounded or dropped at the phase-2 gate; the skill forbids inventing evidence paths (validate warns on empty evidence; the skill adds the behavioral rule).
- **Output contracts**: max 6 aspects, max ~10 top risks, every mitigation needs a residual note — restated as hard rules with the rationale (one line each) so the agent doesn't rationalize around them.
- **Catalog by reference**: skills cite entry ids (`qrisk catalog show techniques.stress-testing`) instead of duplicating entry text — single source of truth, and it exercises the CLI.
- **Quickscan**: scoped to a diff/PR; passes = (changed-element × relevant guideword sets) + dependency check; emits `proposed` risks with `elicited_by.method: inside-out`; never touches phase/status; ends by recommending a full session if it found ≥3 plausible risks or any severity-9 candidate.

### D3. `qrisk skills` CLI

- `qrisk skills list [--json]` — names + descriptions from frontmatter.
- `qrisk skills install [SKILL ...] --target claude-project|claude-user|PATH [--force]`:
  - `claude-project` → `./.claude/skills/<name>/` (default target)
  - `claude-user` → `~/.claude/skills/<name>/`
  - arbitrary `PATH` → `<path>/<name>/` (opencode/kilo/copilot/pi users point at their skill dir)
  - copies recursively, refuses to overwrite existing skill dirs without `--force`, prints what was installed.

Frontmatter parsing: minimal YAML-frontmatter reader over the existing ruamel dependency (no new deps).

### D4. Drift-guard tests

- Parse frontmatter of every skill (name/description present, name matches directory).
- Regex-extract catalog entry ids (`\b(?:iso25010|techniques|heuristics|guidewords)\.[a-z0-9-]+\b`) from all skill markdown; each must resolve via the loader.
- Regex-extract `qrisk <subcommand>` mentions; each subcommand must exist in the argparse parser.
- SKILL.md line budget: risk-analysis ≤ 200 lines, quickscan ≤ 150 (progressive disclosure).
- `qrisk skills install --target <tmp>` round-trip test (also from package-data path).

## Risks / Trade-offs

- [Skill text and CLI/catalog drift apart] → drift-guard tests fail CI on rename/removal.
- [Agents on weaker platforms skip gates] → the register still refuses invalid state (validate fails); skill states plainly that gate-skipping produces a register that fails validation.
- [Fake `human:` events by an over-eager agent] → skill contains an explicit behavioral prohibition + points to the audit trail; hard enforcement remains a later hooks change (documented limit).
- [SKILL.md grows into a monolith] → line-budget test; references structure.

## Migration Plan

Additive. No register or catalog changes.

## Open Questions

- Whether `skills install` should also emit platform-specific wrappers (e.g. Copilot prompt files). Deferred: plain directories cover the named targets; wrappers can be a later contribution.
