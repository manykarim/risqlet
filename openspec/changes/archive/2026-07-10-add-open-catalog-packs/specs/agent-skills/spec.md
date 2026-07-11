# Spec delta: agent-skills (add-open-catalog-packs)

## ADDED Requirements

### Requirement: elicitation references the security packs
The risk-analysis skill's elicitation guidance SHALL note that security-relevant products can enable the `mitre-attack` and `owasp-web` packs via `config.catalogs` and match risks against their entries, referencing them by id. Drift guards SHALL resolve those ids against the packaged packs.

#### Scenario: Security pack guidance present
- **WHEN** the elicitation reference is read
- **THEN** it names the mitre-attack and owasp-web packs and how to enable them

#### Scenario: Referenced ids resolve
- **WHEN** the drift guards extract catalog ids from the skills
- **THEN** any mitre-attack or owasp-web ids resolve against the packaged packs
