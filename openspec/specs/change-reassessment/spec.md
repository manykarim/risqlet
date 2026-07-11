# change-reassessment Specification

## Purpose
TBD - created by archiving change add-ci-reassessment. Update Purpose after archive.
## Requirements
### Requirement: diff maps changed files to touched risks
`risqlet diff` SHALL determine changed files (from `git diff --name-only <base>...HEAD`, or `--files`, or newline stdin) and report which register risks they touch, where a risk is touched by a changed path matching one of its evidence paths (high confidence), a mitigation test ref path (high), or two or more of its statement tokens as path components (low). Each touched risk SHALL carry its match reasons, confidence, status, priority, and a suggested action. It SHALL also list top untouched high-priority risks as a reminder. It SHALL be read-only and deterministic.

#### Scenario: Evidence path match
- **WHEN** a changed file equals a risk's evidence path
- **THEN** that risk is reported touched with a high-confidence evidence reason

#### Scenario: Test ref match
- **WHEN** a changed file matches a mitigation's test ref path
- **THEN** the mitigation's risk is reported touched via that test

#### Scenario: Read-only
- **WHEN** diff runs
- **THEN** no file under .risqlet/ changes

### Requirement: check gates the change
`risqlet check` SHALL flag a change when a touched risk is accepted or mitigating with failing or missing mitigation coverage, or is reviewed-or-accepted and touched but lacks passing coverage. Its behavior SHALL follow `config.constraints.ci_gate`: `off` (exit 0, silent), `warn` (print flags, exit 0; default), `block` (print flags, exit 1 if any flags). Changed paths not matching any glob in `config.constraints.ci_paths` (when non-empty) SHALL be excluded before mapping.

#### Scenario: Block mode fails on flag
- **WHEN** gate mode is block and a changed file touches an accepted risk with an untested mitigation
- **THEN** check exits non-zero naming the risk

#### Scenario: Warn mode never fails
- **WHEN** gate mode is warn and flags exist
- **THEN** check prints them and exits 0

#### Scenario: Path filter excludes noise
- **WHEN** ci_paths is set and a changed file matches no glob
- **THEN** that file is excluded and cannot flag anything

### Requirement: ci init emits templates
`risqlet ci init --target github|gitlab|claude-hooks|<path>` SHALL write a ready, valid CI template (GitHub Actions workflow, GitLab CI job) or Claude Code hooks snippet from shipped package data to its conventional location or a given path, refusing to overwrite without `--force`. Emitted GitHub/GitLab templates SHALL be valid YAML and the hooks snippet valid JSON, and SHALL only reference `risqlet` subcommands that exist.

#### Scenario: GitHub workflow written
- **WHEN** `risqlet ci init --target github` runs
- **THEN** a valid workflow YAML exists at .github/workflows and references risqlet validate and check

#### Scenario: Overwrite protection
- **WHEN** the target file exists and --force is absent
- **THEN** the command exits non-zero and changes nothing

#### Scenario: Templates reference real commands
- **WHEN** each shipped template is inspected
- **THEN** every risqlet subcommand it invokes exists in the CLI

