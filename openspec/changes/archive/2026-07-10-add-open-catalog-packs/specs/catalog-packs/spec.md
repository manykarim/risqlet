# Spec delta: catalog-packs (add-open-catalog-packs)

## ADDED Requirements

### Requirement: opt-in security packs
The distribution SHALL include two additional opt-in packs, `mitre-attack` and `owasp-web`, not enabled by `qrisk init` defaults but loadable when listed in `config.catalogs`. `mitre-attack` SHALL provide an adversary-tactic guideword set whose words are at least the twelve core ATT&CK Enterprise tactic names (as facts) and SHALL carry a `notice` with MITRE's attribution/trademark statement; it SHALL reproduce no ATT&CK technique text or identifiers. `owasp-web` SHALL provide at least the ten established web risk categories as heuristic entries crediting OWASP as concept origin. Every entry in both packs SHALL be original text with provenance.

#### Scenario: Security packs load when configured
- **WHEN** config.catalogs includes mitre-attack and owasp-web
- **THEN** both packs load and their entries are addressable, and catalog-aware validation resolves their slugs without unknown-slug warnings

#### Scenario: Not in default init
- **WHEN** a fresh register is created
- **THEN** its config catalogs list does not include mitre-attack or owasp-web

#### Scenario: MITRE notice present, no technique ids
- **WHEN** the mitre-attack pack is loaded
- **THEN** it has a non-empty notice naming The MITRE Corporation and no entry contains an ATT&CK technique identifier

#### Scenario: Tactic and category coverage
- **WHEN** the packs load
- **THEN** mitre-attack's tactic words include at least twelve tactic names and owasp-web has at least ten category entries
