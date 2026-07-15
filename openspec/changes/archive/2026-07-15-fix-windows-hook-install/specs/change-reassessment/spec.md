## ADDED Requirements

### Requirement: check accepts an agent hook payload
`risqlet check --hook-input claude` SHALL read Claude Code's hook JSON envelope
from stdin and resolve the edited file path from it (`tool_input.file_path`),
using that as the changed-file set. This input format is distinct from `--stdin`
(newline-separated paths) and SHALL NOT alter `--stdin` semantics. The flag SHALL
name the agent format so further formats can be added without overloading it.

Because a hook runs inside an agent's edit loop, `--hook-input` mode SHALL be
non-failing by contract: it SHALL exit 0 regardless of gate mode, malformed or
absent stdin, an unresolvable path, or an internal error, and SHALL NOT write a
traceback to the agent's session. It reports; it never blocks. A payload carrying
no usable file path SHALL be a silent no-op rather than a check of the empty path.

#### Scenario: Payload resolves the edited file
- **WHEN** a Claude PostToolUse payload with `tool_input.file_path` set to a file
  touching a tracked risk is piped to `risqlet check --hook-input claude --json`
- **THEN** the report names that risk and the command exits 0

#### Scenario: Block mode does not break the agent loop
- **WHEN** gate mode is `block`, the payload's file flags a risk, and check runs
  with `--hook-input claude`
- **THEN** the flags are reported and the command still exits 0

#### Scenario: Malformed payload is a silent no-op
- **WHEN** stdin is empty, not JSON, or carries no `tool_input.file_path`
- **THEN** the command exits 0, emits no traceback, and checks nothing

#### Scenario: Existing stdin mode is unchanged
- **WHEN** newline-separated paths are piped to `risqlet check --stdin`
- **THEN** they are treated as the changed-file list exactly as before, and the
  `ci_gate` exit contract still applies

## MODIFIED Requirements

### Requirement: ci init emits templates
`risqlet ci init --target github|gitlab|claude-hooks|<path>` SHALL write a ready, valid CI template (GitHub Actions workflow, GitLab CI job) or Claude Code hooks snippet from shipped package data to its conventional location or a given path, refusing to overwrite without `--force`. Emitted GitHub/GitLab templates SHALL be valid YAML and the hooks snippet valid JSON, and SHALL only reference `risqlet` subcommands that exist.

The emitted `claude-hooks` snippet SHALL carry a command that actually resolves the
edited file under Claude Code's real hook contract (a JSON payload on stdin). It
SHALL NOT depend on an environment variable that Claude Code does not set, and
SHALL match the command `risqlet setup` installs, so the two hook surfaces cannot
drift. Like the installed hook, the emitted command SHALL be runnable on every
platform risqlet supports without a shell.

#### Scenario: GitHub workflow written
- **WHEN** `risqlet ci init --target github` runs
- **THEN** a valid workflow YAML exists at .github/workflows and references risqlet validate and check

#### Scenario: Overwrite protection
- **WHEN** the target file exists and --force is absent
- **THEN** the command exits non-zero and changes nothing

#### Scenario: Hooks snippet resolves the edited file
- **WHEN** `risqlet ci init --target claude-hooks` runs and the emitted command is
  fed a Claude hook payload naming an edited file
- **THEN** the command checks that file, rather than reading an environment
  variable Claude Code never sets and checking nothing

#### Scenario: Emitted and installed hook commands agree
- **WHEN** the `claude-hooks` template is compared to the command `risqlet setup`
  writes into `.claude/settings.json`
- **THEN** they invoke the same command
