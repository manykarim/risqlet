## ADDED Requirements

### Requirement: register files are UTF-8 on every platform
risqlet SHALL read and write every text file — `config.yaml`, the `register/*.yaml` risk documents, `events.jsonl`, and shipped data such as catalog and policy packs — as UTF-8 explicitly, independent of the host's locale encoding, and SHALL NOT rely on Python's default text encoding (UTF-8 on Linux and macOS, cp1252 on Windows).

Writing a risk SHALL NOT fail because its text contains characters outside the
platform's locale encoding: a statement containing `→`, an em-dash, CJK, or an emoji
SHALL round-trip through the register unchanged on every supported platform. Reading
SHALL NOT silently substitute characters — a register written on one platform and
read on another SHALL yield identical text.

Text writes SHALL use `\n` line endings on every platform. Python's text mode
translates `\n` to `\r\n` on Windows, which would make otherwise-deterministic
output differ by host.

#### Scenario: Non-ASCII risk round-trips
- **WHEN** a risk whose statement contains `→`, an em-dash, and CJK is saved and
  read back
- **THEN** the statement is unchanged, and the bytes on disk decode as UTF-8

#### Scenario: Locale encoding does not reach the register
- **WHEN** risqlet runs on a host whose locale encoding is cp1252
- **THEN** the register is still written and read as UTF-8, and no
  `UnicodeEncodeError` or silent character substitution occurs

#### Scenario: Event log accepts non-ASCII
- **WHEN** an event whose rationale contains non-ASCII text is appended to
  `events.jsonl`
- **THEN** the append succeeds and the log remains valid UTF-8 JSONL

#### Scenario: Line endings do not depend on the host
- **WHEN** the same register is written on Windows and on Linux
- **THEN** the files are byte-identical, using `\n` in both
