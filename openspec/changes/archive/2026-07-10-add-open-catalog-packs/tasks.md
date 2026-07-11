# Tasks: add-open-catalog-packs

## 1. Notice field + licenses command

- [x] 1.1 Add optional CatalogPack.notice field; regenerate catalog schema; render notice in catalog show
- [x] 1.2 Implement `qrisk catalog licenses [--json]` (id/title/license/attribution/notice for all loaded packs)

## 2. Security packs (clean-room)

- [x] 2.1 Author src/qrisk/catalog/packs/mitre-attack.yaml: enterprise-tactics guideword set (>=12 tactic names) + tactic-lens technique entries; original text; MITRE notice; no technique text/IDs
- [x] 2.2 Author src/qrisk/catalog/packs/owasp-web.yaml: 10 web risk categories as heuristic entries; original definitions/prompts; OWASP-credited provenance; notice
- [x] 2.3 Confirm init defaults unchanged (four core packs only)

## 3. Governance + skills

- [x] 3.1 Update CLEAN-ROOM.md (names-as-facts rule, notice-reproduction requirement); README lists all six packs + licenses
- [x] 3.2 elicitation.md Pass E + persona note reference the security packs by id; extend drift-guard CATALOG_ID_RE to include the new namespaces

## 4. Tests

- [x] 4.1 Both packs schema-valid + load; tactic/category coverage counts; every entry original+provenance; MITRE notice present with no technique IDs
- [x] 4.2 licenses command output shape (text + --json); notice rendered in catalog show
- [x] 4.3 packs absent from init defaults, loadable when configured, validation resolves their slugs (no unknown-slug warnings); skills drift guards green

## 5. Dogfood on rf-mcp

- [x] 5.1 Write scripts/prompts/security-catalog.md (init, enable mitre-attack+owasp-web, security-framed scan using their entries as prompt_refs, validate shows no catalog warnings, capture licenses)
- [x] 5.2 Run: prepare rf-mcp, run, collect into docs/experiments/rf-mcp/security-catalog/, cleanup to baseline
- [x] 5.3 Evaluate + append findings to dogfooding report; apply small fixes

## 6. Wrap-up

- [x] 6.1 Update MEMORY with final roadmap state (all queue items 1-5 done)
- [x] 6.2 Full pytest + ruff (unpiped); commit
