## ADDED Requirements

### Requirement: setup does not fail on a pre-existing markdown file's encoding
`risqlet setup` SHALL NOT fail to merge its instructions section because the target markdown file (`CLAUDE.md`, `AGENTS.md`) is not valid UTF-8. Earlier risqlet versions wrote that section through the host locale, and its text contains an em-dash, so a Windows user's file is cp1252 on disk and was produced by risqlet itself. Markdown mandates no encoding, so a user's editor may equally have written cp1252 prose around it.

Such a file SHALL be decoded as cp1252, its content preserved, and the marker-scoped
merge applied to the recovered text. The rewritten file SHALL be UTF-8, and the
recovery SHALL be reported. Setup SHALL NOT discard, replace, or mangle the user's
surrounding content in the process.

The tolerance SHALL be scoped to where risqlet's own output could have produced
non-UTF-8 bytes. The JSON and TOML agent configs SHALL stay strict: risqlet writes
them via `json.dumps`, whose `ensure_ascii` default emits pure ASCII, and both
formats mandate UTF-8 by specification — so a decode error there is a malformed file,
not risqlet's residue, and SHALL be raised rather than guessed at.

#### Scenario: A JSON agent config is not silently reinterpreted
- **WHEN** setup reads a `.mcp.json` or `settings.json` that is not valid UTF-8
- **THEN** it raises rather than decoding it as cp1252, because JSON requires UTF-8
  and risqlet cannot have written those bytes

#### Scenario: An instructions file written by an older risqlet still installs
- **WHEN** setup merges into a `CLAUDE.md` whose risqlet section contains a
  cp1252-encoded em-dash, as a pre-fix risqlet on Windows wrote it
- **THEN** setup completes, the section is updated, and the file is rewritten as
  UTF-8 — rather than raising `UnicodeDecodeError` and configuring nothing

#### Scenario: The user's own non-UTF-8 content survives
- **WHEN** setup merges into an instructions file whose *user-authored* prose is
  cp1252-encoded
- **THEN** that prose is preserved with its characters intact, not replaced or
  dropped

#### Scenario: Removal also tolerates it
- **WHEN** `risqlet setup --remove` runs against a non-UTF-8 config it previously
  wrote
- **THEN** the risqlet section is removed and the user's content is left intact
