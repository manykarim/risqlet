# Spec delta: risk-register (add-catalog)

## ADDED Requirements

### Requirement: Catalog-aware reference validation
When a risk references an aspect `ns.slug` whose namespace `ns` matches a loaded catalog pack, an unknown `slug` SHALL produce a validation warning (not an error). The same soft check SHALL apply to `technique_ref` and `prompt_ref` values of the form `ns.slug` when `ns` is a loaded pack; refs using other syntaxes (e.g. `guideword:LATE`, `persona:ops`) remain free-form. Aspects in namespaces that are not loaded packs SHALL continue to be format-checked only.

#### Scenario: Unknown slug in loaded catalog warns
- **WHEN** the iso25010 pack is loaded and a risk references aspect `iso25010.typo-aspect`
- **THEN** validate emits a warning naming the aspect and still exits 0

#### Scenario: Known slug passes silently
- **WHEN** a risk references aspect `iso25010.security` and the pack contains security
- **THEN** no catalog finding is emitted

#### Scenario: Unloaded namespace unchanged
- **WHEN** a risk references aspect `companyx.internal-aspect` and no such pack is loaded
- **THEN** only the format check applies, as before
