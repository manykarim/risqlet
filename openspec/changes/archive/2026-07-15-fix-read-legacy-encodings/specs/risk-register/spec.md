## MODIFIED Requirements

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

Reading SHALL tolerate a file that is not valid UTF-8 rather than failing the
command, because risqlet itself produced such files: versions before the encoding fix
wrote the register in the host locale, so a Windows register containing an em-dash is
cp1252 on disk. A file that does not decode as UTF-8 SHALL be decoded as cp1252, its
text recovered intact, and the recovery SHALL be reported rather than performed
silently. The next write SHALL normalize the file to UTF-8, so a file is repaired by
being used rather than by a migration step.

The fallback SHALL be a fixed encoding, not the host's locale, so that behaviour and
tests are identical on every platform. It SHALL NOT apply to files risqlet has only
ever written as ASCII (`events.jsonl`, whose JSON escapes non-ASCII): there, a decode
error indicates real corruption and SHALL still be raised.

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

#### Scenario: A register an older version wrote in cp1252 still loads
- **WHEN** a register file containing a cp1252-encoded em-dash — as a pre-fix risqlet
  on Windows wrote it — is read
- **THEN** the text is recovered intact, the recovery is reported, and the command
  succeeds instead of raising `UnicodeDecodeError`

#### Scenario: A recovered file is normalized on write
- **WHEN** a file recovered from cp1252 is subsequently written
- **THEN** it is written as UTF-8, so the file stops being non-UTF-8 once used
