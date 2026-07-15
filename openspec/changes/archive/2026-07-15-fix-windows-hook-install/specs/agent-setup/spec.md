## ADDED Requirements

### Requirement: the installed check hook runs on every supported platform
The hook `risqlet setup` installs SHALL run on every platform risqlet supports
(Linux, macOS, Windows) without requiring a shell or any interpreter beyond
`risqlet` itself. Its command SHALL be a single executable invocation with literal
arguments: no shell metacharacters (`$(...)`, `"`, `|`, `;`, `&&`, `||`,
redirections), no `bash`, and no separate `python3`/`node`/PowerShell process. Any
payload parsing the hook needs SHALL live in the `risqlet` CLI, not in the hook
string. risqlet SHALL NOT ship a second, platform-specific variant of this hook.

#### Scenario: Hook installs on a host without bash
- **WHEN** `risqlet setup` installs the Claude Code hook component on a host where
  `bash` is not on PATH
- **THEN** the hook passes verification and is written, rather than being skipped
  with "hook failed verification: bash not on PATH"

#### Scenario: Hook command is shell-free
- **WHEN** the command written to `.claude/settings.json` is inspected
- **THEN** it contains no shell metacharacters and invokes only `risqlet`

#### Scenario: Hook does not depend on the interpreter's name
- **WHEN** the host provides Python as `python` rather than `python3`
- **THEN** the hook still verifies and runs, because it spawns no interpreter itself

### Requirement: installed hooks are identifiable without a shell comment
risqlet SHALL be able to recognize the hooks it installed in order to remove them
without touching a user's own hooks. Because a shell-free command cannot carry a
trailing `# risqlet:check` comment — the comment would be passed to the executable
as literal arguments — the hook SHALL be identified by its own invocation rather
than by an appended comment.

Removal SHALL also recognize hooks written by earlier risqlet versions, which carry
the shell command and its trailing comment marker, so that upgrading does not orphan
a hook that can never be cleaned up. Re-running `risqlet setup` SHALL replace a
previously installed hook rather than leaving a stale one beside the new one.

#### Scenario: Marker is not passed to the executable
- **WHEN** the installed hook command is run
- **THEN** no marker text reaches `risqlet` as an argument and the command succeeds

#### Scenario: Hook installed by an older version is still removable
- **WHEN** `risqlet setup --remove` runs against a settings file whose hook was
  installed by an earlier version carrying the old marker
- **THEN** that hook is removed and the user's own hooks are left intact

#### Scenario: Re-running setup replaces rather than duplicates
- **WHEN** `risqlet setup` runs on a project that already has an older risqlet hook
- **THEN** the settings file ends with exactly one risqlet hook, the current one
