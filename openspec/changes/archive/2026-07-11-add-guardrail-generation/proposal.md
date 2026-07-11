# Proposal: add-guardrail-generation

## Why

The register already knows a project's risks, their mitigations, *and why each mitigation exists* — including a bow-tie `barrier` (prevent/detect/recover) and the evidence paths that locate the risk. Those barriers map almost one-to-one onto the control surfaces of a coding agent (permissions, hooks, AGENTS.md rules, pre-commit/CI). So the assessment can drive the very guardrails that harden the coding agent against the risks it found — secret leakage, thin test coverage, quality slippage — tailored per project and, uniquely, **traceable to the risk that justifies each rule**. This turns the register from a passive document into an active source of enforcement, and gives risqlet a sharp adoption pitch: point it at your repo and it hardens your coding agent to your actual risks.

## What Changes

- New vetted **guardrail template library** (package data): parameterized templates for secret-scan hooks, path denials, coverage checks, lint/format hooks, AGENTS.md rules, and pre-commit/CI snippets — each declaring its surface, enforcement level (hard/soft), and the barrier it satisfies.
- New `risqlet guardrails generate|diff|install`: read accepted/mitigating risks, select and parameterize templates by barrier + evidence paths + tags, and propose a guardrail plan; every emitted rule carries a `risqlet:<risk-id>:<barrier>` provenance marker; install is an explicit human action, never automatic.
- **Honesty labeling**: each guardrail is marked hard (enforcing) or soft (advisory); a high-severity accepted risk covered only by soft guardrails is flagged "advisory-only — not enforced" (advisory note, does not block) — the same honesty as the human-principal gate and detection-evidence notes.
- **Portability tiers**: AGENTS.md (cross-agent, soft), Claude Code hooks/permissions (hard, premium), pre-commit/CI (universal) — reusing the skills/MCP tiering.
- Skills gain a guardrails reference; the mitigate phase notes that `barrier` drives generation.
- Dogfooded on tshirt-shop-om's security register.

## Capabilities

### New Capabilities

- `guardrail-generation`: the template library, barrier→surface selection, the generate/diff/install commands with risk-provenance markers, hard/soft honesty labeling, and the human-gated install boundary.

### Modified Capabilities

- `agent-skills`: the mitigate-phase guidance notes barrier-driven guardrail generation.

## Impact

- New `src/risqlet/guardrails/` (template library as package data + selection/render/diff engine), CLI `guardrails` group, optional `config.constraints.guardrail_min_priority`, `skills/risk-analysis/references/guardrails.md`, dogfood prompt + artifacts.
- No register schema change; guardrail files live in the *target* project's `.claude/`, `AGENTS.md`, `.pre-commit-config`, etc., never in `.risqlet/`. `risqlet validate` and the register format are unaffected.
- Independent of `add-release-prep` (does not block it; naturally sequenced after publication).
