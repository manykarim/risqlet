# Proposal: add-catalog

## Why

The research reports identify a rich, permissively licensed risk/quality catalog as the scarce differentiating asset in this space (IriusRisk's moat is its proprietary 200+ threat library; open threat-modeling tools ship an order of magnitude less, and none cover quality breadth). The foundation change shipped the register and deterministic engine; agents now need the knowledge layer — quality aspects, techniques, heuristics, guidewords — as addressable, citable entries that `elicited_by.prompt_ref` and `technique_ref` can point at, without violating TestSphere/RiskStorming/HTSM/ISO copyrights.

## What Changes

- New catalog pack format: YAML packs with metadata (id/namespace, title, license, attribution) and entries (slug, name, kind, summary, prompts, tags, one-line provenance, optional guideword lists and related refs); JSON Schema published alongside the register schemas.
- Four packaged clean-room packs, ~75 entries of entirely original text: `iso25010` (quality aspects; characteristic names as facts, definitions ours), `techniques` (~25 test techniques), `heuristics` (~20 thinking tools and consistency oracles), `guidewords` (~8 guideword sets with word lists).
- New catalog engine: loads packaged packs plus user packs from `.qrisk/catalogs/`, validates pack structure.
- New CLI command group: `qrisk catalog list|show|search` (keyword+tag convenience search only — semantic risk→technique mapping deliberately stays with the host LLM).
- `validate` integration: `config.catalogs` entries must resolve to loadable packs (error); risk aspects whose namespace matches a loaded pack but whose slug is unknown produce warnings.
- Licensing/governance: catalog content under CC BY 4.0 (`LICENSE-CATALOG`), authoring rules in `CLEAN-ROOM.md`, dual-license note in README.

## Capabilities

### New Capabilities

- `catalog-packs`: The pack file format, the clean-room content rules (original text, per-entry provenance, attribution-as-facts), and the four packaged packs with their coverage expectations.
- `catalog-cli`: Loading/validation of packs, the `qrisk catalog` command group, and the validate-pipeline integration for catalog references.

### Modified Capabilities

- `risk-register`: aspect references gain catalog-aware validation (unknown slug in a loaded catalog namespace → warning; unresolvable configured catalog → error). Requirement-level change to the "Config document" and aspect validation behavior.

## Impact

- New source: `src/qrisk/catalog/` (models, loader, search), `src/qrisk/catalog/packs/*.yaml`, schema addition to `src/qrisk/schemas/`.
- CLI: new `catalog` subcommand; `validate` pipeline extended.
- New top-level files: `CLEAN-ROOM.md`, `LICENSE-CATALOG`.
- Downstream: change 3 (agent skills) will reference entry ids in playbooks; the dogfooding change will exercise `prompt_ref`/`technique_ref` against these ids — slugs chosen here become stable public identifiers.
