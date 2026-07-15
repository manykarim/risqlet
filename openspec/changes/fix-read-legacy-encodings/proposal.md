## Why

`fix-text-encoding` made risqlet read every file as strict UTF-8. That is right for
files risqlet writes from now on, and wrong for files that already exist — because
the files that already exist include **the ones risqlet itself wrote in cp1252
before that fix landed**.

A Windows user upgrading to the fixed version now gets a traceback on `risqlet
setup`:

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 377: invalid start byte
  ... render.apply_md_section -> path.read_text(encoding="utf-8")
```

Byte `0x97` is cp1252's em-dash. It is in *risqlet's own* instructions block —
`INSTRUCTIONS_BODY` contains "agents propose, humans decide —", and an older risqlet
on Windows wrote `CLAUDE.md` in the host locale. So the new version cannot read the
file the old version produced. Reproduced exactly on Linux by writing that section as
cp1252 and running the current `setup` against it.

The previous change fixed the *write* side and never asked what to do about bytes
already on disk. That was the gap: "no on-disk format changed" was true of the format
and false of the encoding, precisely on the platform being fixed.

This is not a rare edge. It hits **every** Windows user who ran `risqlet setup`
before the fix — the exact population the fix was for — and it hits them at the
moment they upgrade to get it.

## What Changes

- **Reads tolerate a non-UTF-8 file instead of crashing.** Text reads try UTF-8 and,
  on `UnicodeDecodeError`, fall back to cp1252 — the encoding that actually produced
  these bytes. The text is recovered intact, and the next write normalizes the file
  to UTF-8, so a file heals on first touch rather than failing forever.
- **The fallback is cp1252 specifically, not "the host locale".** A locale-dependent
  fallback would behave differently on Linux and Windows and could not be tested on
  the platform we develop on. cp1252 is deterministic, is what wrote these bytes, and
  is testable everywhere.
- **The fallback is reported, not silent.** When a file is recovered this way,
  risqlet says so — it is repairing damage it caused, and the user's file is about to
  change encoding. Silence here would be indistinguishable from the mojibake bug we
  just fixed.
- **Scoped by evidence, not by sympathy: tolerate exactly where risqlet's own output
  contained non-ASCII.** Checked per surface rather than assumed:

  | Surface | risqlet's own bytes | Rule |
  |---|---|---|
  | `CLAUDE.md` / `AGENTS.md` | `INSTRUCTIONS_BODY` has an em-dash | tolerate |
  | `config.yaml` | `_STARTER_CONFIG` has an em-dash | tolerate |
  | `register/*.yaml` | risk statements carry the user's text | tolerate |
  | `.mcp.json`, `settings.json`, `events.jsonl` | ASCII (`json.dumps` escapes) | strict |
  | `.codex/config.toml` | our block is ASCII | strict |

  The strict surfaces stay strict for two reinforcing reasons: risqlet cannot have
  written a non-UTF-8 byte there, and JSON and TOML both mandate UTF-8 by
  specification. A decode error on those is a malformed file — real news — and
  recovering it as cp1252 would turn that into plausible nonsense. Tolerance is
  justified only where we caused the problem.

### Not in scope

- Guessing arbitrary encodings (chardet-style detection). Two candidates cover the
  bytes risqlet produced; anything more is speculation dressed as robustness.
- Rewriting files that risqlet is not otherwise touching. A file heals when it is
  next written, not by a migration pass.

## Capabilities

### Modified Capabilities

- `risk-register`: the UTF-8 requirement currently describes only what risqlet writes.
  It must also say what happens when a file on disk is *not* UTF-8 — that the content
  is recovered rather than the command dying, since risqlet produced those bytes.
- `agent-setup`: setup merges into files it does not own and must not fail on a
  pre-existing file's encoding — least of all one it wrote itself.

## Impact

- `src/risqlet/setup/render.py` — the crash site; all reads of agent configs.
- `src/risqlet/store.py` — register and config reads.
- `tests/` — a regression test reproducing the exact reported traceback.
- No spec-level change to what risqlet *writes*: still UTF-8 with `\n`.

Behavior change: a file that previously crashed now loads and is rewritten as UTF-8.
On any all-UTF-8 install (every Linux and macOS user, and any Windows user who never
ran the old version) nothing changes — the fallback never fires.

Risk: the fallback makes a class of genuine corruption survivable-looking. cp1252
maps almost every byte, so a truly mangled file will decode to nonsense rather than
raise. Mitigated by reporting every fallback, and by keeping it off the paths
(`events.jsonl`, JSON configs) where risqlet has provably never emitted a non-ASCII
byte — there, a decode error is real news and should still raise.
