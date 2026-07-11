# skills-cli Specification

## Purpose
TBD - created by archiving change add-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: skills list
`risqlet skills list` SHALL print each shipped skill's name and description from frontmatter; `--json` SHALL emit them structurally. The command SHALL work both from a source checkout and from an installed package (skills shipped as package data).

#### Scenario: List shows both skills
- **WHEN** `risqlet skills list` runs
- **THEN** risk-analysis and risk-quickscan appear with descriptions

### Requirement: skills install
`risqlet skills install [SKILL ...]` SHALL copy the named skills (default: all) into a target directory: `--target claude-project` → `./.claude/skills/` (default), `--target claude-user` → `~/.claude/skills/`, or `--target <path>` for any other agent platform. Existing skill directories SHALL NOT be overwritten unless `--force` is given. The command SHALL report what was installed and exit 1 on unknown skill names.

#### Scenario: Project install
- **WHEN** `risqlet skills install --target claude-project` runs in a project
- **THEN** `.claude/skills/risk-analysis/SKILL.md` and reference files exist afterwards

#### Scenario: Arbitrary path install
- **WHEN** `risqlet skills install risk-quickscan --target /some/dir` runs
- **THEN** `/some/dir/risk-quickscan/SKILL.md` exists and no other skill was copied

#### Scenario: No silent overwrite
- **WHEN** the target already contains a skill directory and `--force` is absent
- **THEN** the command exits 1 naming the conflict and changes nothing

#### Scenario: Unknown skill
- **WHEN** `risqlet skills install nope` runs
- **THEN** exit code is 1 and the message names the unknown skill

