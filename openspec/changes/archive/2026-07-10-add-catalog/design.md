# Design: add-catalog

## Context

Foundation (archived change `add-foundation`) established: file-per-risk register, `catalog.slug` namespaced references (`aspects`, `elicited_by.prompt_ref`, `technique_ref`), open-world validation, policies-as-data. This change adds the knowledge layer the same way — catalogs as data packs — under hard IP constraints documented in `docs/prior-art-architecture-ip-research.md` Part 3: game mechanics and concept names are free, card/standard *text* is not; ISO explicitly forbids reuse of its text; MoT card content is seat-licensed.

## Goals / Non-Goals

**Goals:**
- Addressable, citable knowledge entries with stable ids (`techniques.stress-testing`) usable in register provenance fields.
- 100% original entry text with per-entry provenance attribution (clean-room).
- Pack format open for user/company packs (`.qrisk/catalogs/`) including licensed decks they own (never distributed by us).
- Keyword/tag search as a *convenience*; semantic mapping stays with the host LLM (framework-provider pattern; exp-002 in agentic-riskstorming showed keyword-only mapping tops out at 27% relevance — we don't rebuild that dead end).

**Non-Goals:**
- Embedding-based recommendation or any risk→technique ranking engine.
- OWASP/MITRE-derived packs (share-alike/attribution logistics deferred to a later change; the format supports them).
- Skills/playbooks that *use* the catalog (change 3).

## Decisions

### D1. Pack file format

One YAML file per pack in `src/qrisk/catalog/packs/` (user packs: `.qrisk/catalogs/*.yaml`):

```yaml
id: techniques              # namespace; entry ids are "<id>.<slug>"
title: Test techniques
version: 1
license: CC-BY-4.0
attribution: >
  Original text (c) qrisk contributors. Entries express long-established,
  uncopyrightable testing concepts; originators credited per entry.
entries:
  - slug: stress-testing
    name: Stress testing
    kind: technique          # aspect | technique | heuristic | guideword-set
    summary: Push the system past expected load until it degrades or fails,
      to learn where and how it breaks.
    prompts:
      - What is the first component to fall over when traffic doubles, and does
        it fail loudly or silently?
      - After the overload ends, does the system recover on its own?
    tags: [performance, reliability, load]
    provenance: Established performance-testing practice; no single originator.
    related: [techniques.soak-testing, iso25010.performance-efficiency]
    words: []                # only for kind: guideword-set
```

Rationale: mirrors the policy-pack pattern (data, not code); `related` uses full entry ids so cross-pack links work; `words` keeps guideword sets in the same shape instead of a second format.

### D2. Clean-room discipline (CLEAN-ROOM.md)

Rules encoded as a written protocol: (1) concept names, mnemonic letters, and originator citations may be used as facts; (2) no source card text, standard text, or licensed document may be open/consulted while writing entry text; (3) every entry carries a one-line `provenance`; (4) PR checklist item affirms rule 2; (5) ISO characteristic *names* appear as facts with the note that definitions are original and not endorsed by ISO; (6) the TestSphere/RiskStorming/Would-Heu-Risk-It products are named only in attribution context, never mined for text. The four packs in this change are authored under this protocol.

### D3. Pack coverage (≈75 entries)

- `iso25010` (~20): 9 characteristic names (2023 revision) as facts — functional-suitability, performance-efficiency, compatibility, interaction-capability, reliability, security, maintainability, flexibility, safety — plus high-value sub-aspects (data-integrity, availability, recoverability, fault-tolerance, scalability, testability, confidentiality, accessibility, operability, install-and-update, observability*). *observability is our extension, marked as such.
- `techniques` (~25): boundary-value, equivalence-partitioning, state-transition, decision-tables, crud-sweep, exploratory-tours, stress-testing, load-testing, soak-testing, chaos-experiments, fuzzing, property-based, mutation-testing, security-probing, dependency-audit, accessibility-audit, usability-walkthrough, contract-testing, integration-paths, recovery-failover, compatibility-matrix, data-reconciliation, monitoring-checks, regression-selection, api-negative-testing.
- `heuristics` (~20): consistency oracles (history, claims, comparable-products, user-expectations, standards-and-statutes, internal-consistency, purpose — FEW-HICCUPPS-informed, attributed to Bolton/Bach), zero-one-many, goldilocks-sizing, boundary-hunting, interruption-resume, resource-starvation, multi-user-contention, dependency-variation, sequence-shuffling, clock-and-timezone, configuration-drift, persona-switching, follow-the-data, premortem (Klein-attributed), test-the-testing.
- `guidewords` (~8 sets): flow-deviations (HAZOP-informed: none, more, less, reverse, early, late, other-than, intermittent), threat-categories (STRIDE names as facts, Microsoft-attributed), product-dimensions (structure, function, data, interfaces, platform, operations, time — HTSM/SFDIPOT-attributed), data-shapes (empty, huge, malformed, duplicate, unicode-extremes, boundary-dates, injection-strings), environment-shifts (network-loss, disk-full, clock-skew, locale-change, permission-loss), lifecycle-moments (install, upgrade, migrate, rollback, decommission), user-extremes (novice, expert, impaired, hostile, automated), scale-shifts (zero-load, 10x, burst, sustained).

### D4. Engine and CLI

`src/qrisk/catalog/`: pydantic models (`CatalogPack`, `CatalogEntry`) with the same open-world stance; loader resolves pack id → packaged file or `.qrisk/catalogs/` (user shadows packaged, like policies); `search` = case-insensitive substring/tag match over name/summary/tags returning entry ids + summaries. CLI: `qrisk catalog list [--pack ID]`, `show <entry-id>`, `search <terms...>` — all with `--json`. Entry JSON Schema generated into `src/qrisk/schemas/catalog.schema.json` via the existing schema_gen mechanism.

### D5. Validate integration (soft references)

- Each `config.catalogs` id must load and schema-validate → error otherwise.
- Risk aspect `ns.slug`: if `ns` matches a loaded pack and `slug` is not in it → warning ("unknown aspect in loaded catalog — typo or custom?"). Unloaded namespaces stay format-checked only (v1 behavior preserved).
- Same soft check for `technique_ref`/`prompt_ref` values of the form `ns.slug` when `ns` is loaded; refs in other syntaxes (e.g. `guideword:LATE`) remain free-form.

## Risks / Trade-offs

- [Entry text drifts toward remembered source phrasing] → clean-room protocol + review checklist; summaries kept structurally different (question-driven prompts, not card-style one-liners).
- [Slug churn breaks provenance refs later] → slugs declared stable public identifiers in the spec; renames require an `aliases` field (format supports via open-world extra fields) rather than deletion.
- [75 entries is a lot of hand-authored content to keep consistent] → pack schema validation in CI (pytest loads every packaged pack); prompts capped at 3 per entry.
- [Keyword search gets mistaken for a recommender] → CLI help text states its purpose; spec pins the framework-provider boundary.

## Migration Plan

Additive — no register format changes. Existing registers validate identically until they opt into `config.catalogs`.

## Open Questions

- Whether `iso25010.` is the right namespace or a neutral `quality.` would age better (decided: keep `iso25010` for recognizability; the pack attribution clarifies the definitions are original and unaffiliated).
