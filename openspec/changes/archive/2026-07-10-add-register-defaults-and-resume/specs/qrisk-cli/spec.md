# Spec delta: qrisk-cli (add-register-defaults-and-resume)

## MODIFIED Requirements

### Requirement: init scaffolds a register
`qrisk init` SHALL create the `.qrisk/` layout with a commented starter `config.yaml`, empty `register/`, and empty `events.jsonl`. The starter config SHALL enable the packaged catalogs (`iso25010`, `techniques`, `heuristics`, `guidewords`) by default with a comment explaining the soft reference checks and how to disable them. It SHALL refuse to overwrite an existing non-empty `.qrisk/` directory.

#### Scenario: Fresh init
- **WHEN** `qrisk init` runs in a project without `.qrisk/`
- **THEN** the layout is created and `qrisk validate` immediately passes on it

#### Scenario: Catalogs active out of the box
- **WHEN** a fresh register is validated
- **THEN** the four packaged catalogs are loaded and catalog-aware reference checks apply

#### Scenario: Existing register protected
- **WHEN** `qrisk init` runs where `.qrisk/register/` already contains files
- **THEN** the command exits non-zero without modifying anything
