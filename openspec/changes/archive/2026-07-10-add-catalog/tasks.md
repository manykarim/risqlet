# Tasks: add-catalog

## 1. Pack format and engine

- [x] 1.1 Implement CatalogEntry/CatalogPack pydantic models (kinds, slug uniqueness, guideword words rule, mandatory provenance), add catalog.schema.json to schema_gen
- [x] 1.2 Implement loader: packaged packs dir + .qrisk/catalogs/ user packs (user shadows packaged), pack-id resolution, aggregate load of configured + present packs
- [x] 1.3 Implement keyword/tag search over loaded entries (case-insensitive, ranked by match count)
- [x] 1.4 Unit tests: valid/invalid packs, duplicate slug, guideword words rule, provenance mandatory, user shadowing, search behavior

## 2. Governance files

- [x] 2.1 Write CLEAN-ROOM.md (authoring protocol, per-entry provenance, PR affirmation) and LICENSE-CATALOG (CC BY 4.0); update README dual-license section

## 3. Packaged packs (clean-room content)

- [x] 3.1 Author iso25010 pack (~20 aspect entries: 9 characteristics + key sub-aspects, original definitions, attribution note)
- [x] 3.2 Author techniques pack (~25 entries)
- [x] 3.3 Author heuristics pack (~20 entries incl. attributed consistency oracles and premortem)
- [x] 3.4 Author guidewords pack (8 guideword-set entries with word lists)
- [x] 3.5 Pack integrity tests: all packaged packs schema-valid, ≥70 combined entries, ≥18 aspects incl. the nine characteristic slugs, every entry has provenance, all `related` refs resolve

## 4. CLI and validate integration

- [x] 4.1 Implement `qrisk catalog list [--pack] / show <id> / search <terms...>` with --json; search help text states the framework-provider boundary
- [x] 4.2 Extend validate: configured catalogs must load (error); catalog-aware soft checks for aspects and ns.slug-style technique_ref/prompt_ref (warnings)
- [x] 4.3 Tests: CLI behaviors (list/show/search/unknown id), validate catalog errors/warnings, unloaded namespace unchanged

## 5. Wrap-up

- [x] 5.1 Full pytest + ruff; update README quick start with catalog commands; commit
