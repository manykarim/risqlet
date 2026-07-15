## Why

risqlet reads and writes every file — the register, `config.yaml`, `events.jsonl`,
catalog packs, agent configs — in Python's *locale* encoding, because ~48 call sites
use `read_text()` / `write_text()` / `open()` with no `encoding=`. On Linux and macOS
that locale is UTF-8, so it has never mattered. On Windows it is cp1252.

The repo's own data is UTF-8: 15 shipped files contain non-ASCII, including an
em-dash in every catalog pack. Two distinct failures follow, both verified:

- **Reads corrupt silently.** Decoding UTF-8 as cp1252 does not raise for the bytes
  we ship — `—` simply becomes `â€"`. The catalog *is* the product's knowledge
  content, so on Windows it renders as mojibake in every `catalog list`, `catalog
  show`, and skill lookup, with nothing failing. This already leaks into our own
  output: the Windows CI log renders this project's skip reason as `... runner image
  � Windows runners ship Git Bash`.
- **Writes crash hard.** cp1252 cannot encode `→`, CJK, or emoji, so
  `write_text()` raises `UnicodeEncodeError: 'charmap' codec can't encode character`.
  A risk statement like `request → timeout` — ordinary phrasing for this tool —
  makes `risqlet` traceback on Windows. `events.jsonl` appends through the same
  unencoded path, so the append-only log is equally exposed.

The just-landed cross-platform CI does not catch either one, and would not have: no
test writes or asserts a non-ASCII risk statement, so Windows stays green while the
data is wrong. That is the specific reason to fix this now rather than wait for a
bug report — the platform is now claimed as supported and proven by a suite that is
blind here.

Reading is also the more dangerous half. A crash is loud and gets reported; silent
mojibake gets committed to a user's register and propagates.

## What Changes

- **Every text read and write in `src/risqlet` specifies `encoding="utf-8"`.** The
  register, config, event log, catalog packs, policy packs, agent configs, CI and
  guardrail templates, and bundled skills are UTF-8 on every platform regardless of
  the host locale.
- **Text writes pin `newline="\n"`.** Python's text mode translates `\n` to `\r\n` on
  Windows, so today the same `risqlet export` produces different bytes on different
  platforms. risqlet's specs require deterministic output; that cannot be true while
  the line ending depends on the OS. This makes the register and exports
  byte-identical everywhere.
- **Two complementary guards, because neither is sufficient alone:**
  - `ruff` rule `PLW1514` (`unspecified-encoding`) — static, catches unexecuted
    code. Measured: it flags only 20 of the ~48 sites, because it cannot infer the
    type through an attribute like `self.config_path.open()`, so it misses
    `store.py` — the most important file — entirely.
  - `PYTHONWARNDEFAULTENCODING=1` with `-W error::EncodingWarning` in the test run —
    runtime, catches any executed call regardless of type inference, including
    `store.py`. Verified to flag only our own code, with no third-party noise from
    ruamel or pydantic.
- **A test that round-trips non-ASCII through the store** (`→`, an em-dash, CJK) and
  asserts the bytes on disk are UTF-8 — the coverage whose absence let this survive.
- **`.gitattributes`** pinning the repo's text files to LF, so a Windows checkout
  with the default `core.autocrlf=true` cannot rewrite the YAML fixtures and data
  the tests and catalog loader read.

### Not in scope

- Changing the encoding of anything on disk. All existing files are already UTF-8;
  this makes risqlet *read them as what they are*.
- Locale-aware output formatting, translation, or console code-page handling.
  Terminal rendering of a correctly-decoded string is the terminal's business.
- `risqlet guardrails` on Windows, which remains POSIX-only.

## Capabilities

### New Capabilities

None. This corrects how existing capabilities do file I/O; it adds no capability.

### Modified Capabilities

- `risk-register`: the register's files are defined by layout and schema but not by
  encoding, which leaves the on-disk contract dependent on the host locale. Register
  files must be UTF-8, and writing a risk whose text is outside the platform's locale
  encoding must not fail.
- `cross-platform-support`: "supported" must mean the data is intact, not merely that
  the process exits 0. A platform whose reads mojibake is not supported, and the
  suite must be able to fail on that rather than stay green.

## Impact

Affected code (~48 call sites across 13 files):

- `src/risqlet/store.py` — register, config, and `events.jsonl` I/O (the highest-value
  file, and the one `ruff` cannot see).
- `src/risqlet/setup/render.py` — the largest cluster (18 sites): agent config merges.
- `src/risqlet/guardrails/engine.py`, `src/risqlet/setup/engine.py`,
  `src/risqlet/trace.py`, `src/risqlet/ci/__init__.py`, `src/risqlet/skills.py`,
  `src/risqlet/catalog/loader.py`, `src/risqlet/policies/engine.py`,
  `src/risqlet/mcp/tools.py`, `src/risqlet/cli.py`, `src/risqlet/model/schema_gen.py`,
  `src/risqlet/guardrails/verify.py`.
- `pyproject.toml` — enable `PLW1514`; note it is a ruff *preview* rule, which is a
  deliberate trade (see design).
- `.github/workflows/test.yml` — `PYTHONWARNDEFAULTENCODING=1` for the test step.
- `.gitattributes` — new.
- `tests/` — the non-ASCII round-trip test; existing fixtures unaffected.

Behavior change: on Linux and macOS, none — the locale was already UTF-8, so every
byte read and written is identical. The change is entirely a Windows correctness fix
plus a determinism fix for line endings. The `newline="\n"` pin does change bytes
written *on Windows* (LF instead of CRLF), which is the point.

Risk: a mechanical edit across 48 sites is easy to get subtly wrong (e.g. adding
`encoding` to a binary handle). The guards catch omissions, not over-application, so
the test suite passing on all three platforms is the check that matters.
