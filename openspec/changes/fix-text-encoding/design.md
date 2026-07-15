## Context

~48 text I/O call sites in `src/risqlet` omit `encoding=`. Python then uses
`locale.getpreferredencoding(False)`: UTF-8 on Linux/macOS, **cp1252** on Windows.

Measured, not assumed:

- 15 shipped data files contain non-ASCII; every catalog pack has an em-dash.
- Decoding our UTF-8 data as cp1252 raises for **0** files and mojibakes **15**.
  cp1252 has no undefined byte in the sequences we ship (`—` = `E2 80 94` maps to
  `â`, `€`, `"`), so the corruption is silent by construction.
- Encoding as cp1252 *does* raise for `→` (U+2192), CJK, and emoji —
  `UnicodeEncodeError: 'charmap' codec can't encode character`.

So the two halves fail differently: reads corrupt quietly, writes crash loudly. The
quiet half is worse — a mojibaked register gets committed and propagates.

The new cross-platform CI is blind to this. No test writes or asserts a non-ASCII
risk statement, so Windows reports `405 passed` while `catalog list` would render
garbage. The corruption is already visible in our own CI output: the Windows job
prints this project's skip reason as `... runner image � Windows runners ship Git
Bash`.

Nothing on disk is wrong. Every file is already UTF-8. The bug is entirely that
risqlet asks the OS what encoding to use instead of stating the one it means.

## Goals / Non-Goals

**Goals:**

- Register, config, event log, and shipped data are UTF-8 on every platform.
- Non-ASCII risk text round-trips unchanged, and never crashes a write.
- Output is byte-identical across platforms (line endings included).
- The next omitted `encoding=` is caught by a machine, not a reviewer.

**Non-Goals:**

- Re-encoding anything on disk — it is already UTF-8.
- Console/terminal code-page rendering. Once a string is decoded correctly, how a
  terminal draws it is the terminal's problem.
- Locale-aware formatting or i18n.
- Guardrails on Windows (still POSIX-only).

## Decisions

### 1. `encoding="utf-8"` explicitly, not `PYTHONUTF8=1`

Python's UTF-8 mode (`PYTHONUTF8=1` / `-X utf8`) would fix every call site at once
with a one-line change. Rejected: it is an *environment* fix for a *library* bug.
risqlet is imported as a library and driven by an MCP adapter and agent hooks; we
do not control the interpreter flags of every process that imports us, and a user
whose environment lacks the flag would silently get the broken behavior back. An
env var also cannot be reviewed in a diff.

Stating the encoding at each call site makes the contract local and true regardless
of how the process was started. (Python 3.15 makes UTF-8 the default, which will
make this redundant — and harmless.)

### 2. Pin `newline="\n"` on writes, not just encoding

Encoding alone leaves a second host dependency: text mode translates `\n` to `\r\n`
on Windows. risqlet's specs require deterministic, reproducible output — the same
register and the same export must be the same bytes. That is not true today across
platforms; it merely looks true because only one platform was ever used.

This is in scope because it is the same defect in the same call sites: relying on a
platform default instead of stating what we mean. Fixing encoding while leaving
line endings host-dependent would be fixing half of one bug.

### 3. Two guards, because each alone is provably insufficient

Measured, not assumed:

- **`ruff` PLW1514** flags 20 of ~48 sites. It resolves `Path(...).read_text()` and
  tracked locals, but not `self.config_path.open()` — so it misses `store.py`
  entirely, the single most important file here. It is also a **preview** rule,
  so it can change under us.
- **`PYTHONWARNDEFAULTENCODING=1` + `-W error::EncodingWarning`** catches any call
  the tests execute, regardless of type inference — including `store.py`. Verified
  to flag only our code: no ruamel or pydantic noise. But it cannot see unexecuted
  branches.

They fail in complementary directions: static misses what it cannot type, runtime
misses what it does not run. Using both covers each other's blind spot. Taking the
preview-rule risk is acceptable *because* it is the redundant half — if PLW1514
churns, the runtime guard still holds the line, and the failure mode is a lint
error, not shipped corruption.

### 4. A test that would have caught this

The guards prevent regressions in *our* code; they do not prove the data is right.
One test writes a risk containing `→`, an em-dash, and CJK, reads it back, and
asserts both the string round-trips and the on-disk bytes decode as UTF-8. That is
the assertion whose absence let a Windows-green suite coexist with mojibake, and it
is the one that fails if someone reintroduces a locale-dependent read.

### 5. `.gitattributes` pins text to LF

With `core.autocrlf=true` (the Windows default), git rewrites checked-out text
files to CRLF. Our YAML fixtures and catalog packs are read as data, and tests
compare rendered text. Pinning `* text=auto eol=lf` keeps the working tree matching
what the tests and loader expect, so a Windows contributor's checkout is not subtly
different from CI's.

## Risks / Trade-offs

- **A 48-site mechanical edit invites subtle error** — e.g. adding `encoding` to a
  binary handle (`TypeError`) or to a `subprocess` call. → The guards catch
  *omissions*, not over-application, so the three-platform suite is the real check.
  Reviewing the diff for `rb`/`wb` handles is a specific step, not a general hope.

- **PLW1514 is a ruff preview rule** and may change or move. → Accepted knowingly:
  it is the redundant guard, and its worst failure is lint noise. If it destabilizes,
  drop it; the runtime guard is the load-bearing one.

- **`newline="\n"` changes bytes written on Windows** (LF where CRLF was). → That is
  the intent, and no user has a Windows-written register today worth preserving,
  since writing non-ASCII there crashes. On Linux/macOS the output is unchanged.

- **`-W error::EncodingWarning` could turn a third-party warning into a red suite**
  on a dependency upgrade. → Verified clean today across the whole suite. If a
  dependency later trips it, the fix is a targeted `filterwarnings` entry naming
  that module, not disabling the guard.

- **The fix cannot be proven on Windows from the dev host.** → The round-trip test
  runs on all three legs of the existing matrix; Windows is where it means something.
  Until that run is green, this is unverified there — the same honesty that applied
  to the hook fix applies here.

## Migration Plan

1. Add the guards **first**, so they fail loudly and enumerate the work rather than
   trusting a grep to have found everything.
2. Fix the call sites until both guards are clean.
3. Add the round-trip test — it must fail before the fix if simulated under a
   non-UTF-8 locale, and pass after.
4. Push and read all three matrix legs. Windows is the only one that can disprove
   anything here.

Rollback: each call site is independent; the guards can be disabled without
reverting the fixes. Nothing on disk changes format, so there is no data migration
and no forward/backward compatibility concern.

## Open Questions

- Should `PYTHONWARNDEFAULTENCODING=1` be set for the whole test job or only a
  dedicated leg? Recommend the whole job: the warning is free, and a dedicated leg
  would only be run by people who remember it exists.
- Should risqlet write a UTF-8 BOM for Windows tooling that expects one? Recommend
  no — a BOM breaks YAML/JSON parsers that do not strip it, and it would make output
  non-byte-identical across platforms, undoing decision 2.
