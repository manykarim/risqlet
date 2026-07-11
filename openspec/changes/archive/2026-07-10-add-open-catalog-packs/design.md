# Design: add-open-catalog-packs

## Context

Queue item 5, final. The catalog engine, clean-room protocol, and `catalog list/show/search` exist. IP boundary (research Part 3): concept/category NAMES and taxonomy structure are facts; specific text is not; MITRE ATT&CK is royalty-free with a mandatory attribution notice; OWASP category names are facts (their text is share-alike — not reproduced here). This change adds two opt-in security packs authored to those rules and makes per-pack obligations visible.

## Goals / Non-Goals

**Goals:** two more permissively-licensed, original packs covering adversary tactics and web risks; a first-class way to see each pack's license/notice; clean-room + notice discipline documented; proven usable in a security dogfood.

**Non-Goals:** full ATT&CK technique/sub-technique import, ATT&CK IDs, CWE/CAPEC packs, CVE lookup, MCP tools, and — explicitly — publication, final naming, and legal review (still gated on human decisions, queue item 6).

## Decisions

### D1. `notice` field and `qrisk catalog licenses`

`CatalogPack.notice: str = ""` (optional; schema regenerated). It holds required reproduction text (MITRE's permission statement). `catalog show` prints it when non-empty; `catalog licenses [--json]` lists every loaded pack's `{id, title, license, attribution, notice}` so a redistributor sees all obligations at once. Loaded packs = packaged + configured + user (reuse `load_available`).

### D2. `mitre-attack` pack (opt-in)

One `guideword-set` entry `enterprise-tactics` whose `words` are the 12 Enterprise tactic names (reconnaissance, resource-development…impact) as an adversary-coverage checklist, plus a handful of `technique`-kind entries framing how to *use* the tactic lens (e.g. `tactic-sweep`, `initial-access-review`, `exfiltration-paths`) — all descriptions and prompts original. `license: "MITRE ATT&CK terms (royalty-free, attribution required)"`; `notice: "This work reproduces the names of MITRE ATT&CK tactics as factual references. ATT&CK® and MITRE ATT&CK® are registered trademarks of The MITRE Corporation. © 2015–2026 The MITRE Corporation. This material is reproduced and distributed with attribution; no ATT&CK descriptive text or technique identifiers are reproduced."` No technique text, no `Txxxx` IDs — tactic names only.

Tactic-name list (12, the standard Enterprise set): reconnaissance, resource-development, initial-access, execution, persistence, privilege-escalation, defense-evasion, credential-access, discovery, lateral-movement, collection, command-and-control, exfiltration, impact — note: that is 14; the proposal's 12 omit resource-development and command-and-control. Decision: ship the full standard 14 Enterprise tactic names (more complete, still just facts); the spec asserts ≥12 tactic words including the core set, so 14 satisfies it.

### D3. `owasp-web` pack (opt-in)

Ten `heuristic` entries over the established web risk categories (broken-access-control, cryptographic-failures, injection, insecure-design, security-misconfiguration, vulnerable-and-outdated-components, identification-and-authentication-failures, software-and-data-integrity-failures, security-logging-and-monitoring-failures, server-side-request-forgery) with original definitions and 2 prompts each; `provenance` credits OWASP as the concept origin; `license: CC-BY-4.0` (our original text) with a `notice` clarifying category names follow OWASP's widely-known taxonomy and no OWASP text is reproduced. Slugs are stable public ids usable in `prompt_ref`.

### D4. Defaults unchanged

`init` still enables only the four core packs. The security packs are enabled per-project by adding them to `config.catalogs`. Documented in README and skills. Catalog-aware validation resolves their slugs once configured (existing soft-check machinery).

### D5. Skills

`elicitation.md` Pass E gains a sentence: for security-relevant products, enable `mitre-attack` and `owasp-web` in `config.catalogs` and match against `mitre-attack.enterprise-tactics` and the `owasp-web.*` categories (reference by id). The hostile-actor persona note (Pass C) cross-references them. Budgets hold; drift guard resolves the new ids (they must exist once packs ship).

### D6. Dogfood on rf-mcp

`scripts/prompts/security-catalog.md`: quickscan-style, security-framed, with `mitre-attack` + `owasp-web` added to `config.catalogs` (the harness seeds a minimal register/config or the agent runs `qrisk init` then edits catalogs — simplest: agent `qrisk init`, append the two packs to config, proceed). The agent scans rf-mcp's security surface (a default-credential command channel, MCP tool exposure, desktop automation) using the security guideword/heuristic entries as `prompt_ref`s; check catalog-aware validation shows **no unknown-slug warnings** for those refs (proves the packs resolve). Metrics: risks, security prompt_refs used, validate warnings (expect 0 catalog warnings), licenses output captured.

## Risks / Trade-offs

- [Accidental reproduction of ATT&CK/OWASP text] → clean-room rule 2 + a review that entry text shares no sentence with source; only names/structure as facts; notice states this.
- [Drift guard CATALOG_ID_RE only matches core-pack namespaces] → extend the regex to include `mitre-attack` and `owasp-web` so skill refs to them are checked.
- [Trademark caution] → notice includes the ATT&CK trademark statement; product does not brand itself with the marks.

## Migration Plan

Additive; opt-in packs, defaults unchanged, `notice` optional (open-world).

## Open Questions

- None blocking. Publication/naming/legal remain the queue-6 human-gated items; this change deliberately stops short of them.
