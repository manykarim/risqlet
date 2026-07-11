# Spec: catalog-licensing

## ADDED Requirements

### Requirement: packs carry an optional notice
The catalog pack format SHALL support an optional `notice` field holding required reproduction text (e.g. a rights-holder's permission statement). `qrisk catalog show` SHALL print a pack's notice when it applies to the shown entry's pack and the notice is non-empty. The published catalog JSON Schema SHALL include the field.

#### Scenario: Notice rendered
- **WHEN** an entry from a pack with a notice is shown
- **THEN** the notice text appears in the output

### Requirement: catalog licenses lists obligations
`qrisk catalog licenses` SHALL list every loaded pack's id, title, license, attribution, and notice; `--json` SHALL emit them structurally. Loaded packs SHALL include packaged packs plus any configured or user packs.

#### Scenario: Licenses listed
- **WHEN** `qrisk catalog licenses` runs
- **THEN** each loaded pack appears with its license and any notice

#### Scenario: Configured pack included
- **WHEN** a security pack is enabled in config and licenses runs
- **THEN** that pack's license and notice are listed
