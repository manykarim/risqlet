# Proposal: add-open-catalog-packs

## Why

The research names a rich, permissively-licensed risk/quality catalog as the scarce differentiating asset. The four core packs cover general quality; security-heavy products need adversary-tactic and web-risk coverage, and those established taxonomies (ATT&CK tactic names, OWASP category names) are usable as *facts* under a clean-room approach with proper attribution. Shipping two more open packs — and making per-pack licensing/notice obligations first-class — grows the asset and prepares the catalog for eventual public release.

## What Changes

- Pack metadata gains an optional `notice` field (required reproduction notices, e.g. MITRE's permission statement); rendered by `catalog show` and a new `qrisk catalog licenses` command.
- New packaged pack `mitre-attack`: original clean-room guideword/technique entries over the 12 ATT&CK Enterprise tactic *names* as an adversary-coverage checklist, with MITRE's attribution notice; no technique text or IDs reproduced.
- New packaged pack `owasp-web`: original clean-room heuristic entries over the 10 well-established web risk category *names*, crediting OWASP as concept origin; no OWASP text reproduced.
- Both packs opt-in (not in `init` defaults); catalog schema regenerated.
- CLEAN-ROOM.md gains the names-as-facts + notice-reproduction rules; README lists all six packs and licenses.
- Skills note the security packs; dogfooded on rf-mcp with them enabled.

## Capabilities

### New Capabilities

- `catalog-licensing`: the `notice` field, `qrisk catalog licenses`, and its rendering.

### Modified Capabilities

- `catalog-packs`: two new packaged packs and the notice field on the pack format.
- `agent-skills`: elicitation guidance points to the security packs.

## Impact

- New `src/qrisk/catalog/packs/mitre-attack.yaml`, `owasp-web.yaml`; `notice` on `CatalogPack` (schema regenerated); `qrisk catalog licenses` command; CLEAN-ROOM.md/README updates; dogfood prompt + artifacts; MEMORY update.
- No register schema change; new packs are opt-in, defaults unchanged.
