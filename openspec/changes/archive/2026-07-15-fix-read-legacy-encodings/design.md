## Context

A Windows user upgraded to the encoding fix and `risqlet setup` died:

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 377
  render.apply_md_section -> path.read_text(encoding="utf-8")
```

`0x97` is cp1252's em-dash, and it is in *risqlet's own* text: `INSTRUCTIONS_BODY`
ends "agents propose, humans decide —". An older risqlet on Windows wrote `CLAUDE.md`
in the host locale, so the fixed version cannot read what the broken version wrote.
Reproduced on Linux by encoding that section as cp1252 and running current `setup`
against it — same byte, same traceback.

`fix-text-encoding` said "no on-disk format changed: every file was already UTF-8".
That was true of the *format* and false of the *encoding*, on exactly the platform the
change existed to fix. Making reads strict without asking what was already on disk
turned a silent-corruption bug into a hard-failure bug, for the same users.

What is and is not at risk, checked rather than assumed:

| Written by old risqlet | Encoding on Windows | At risk |
|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | cp1252 — `INSTRUCTIONS_BODY` has an em-dash | **yes** |
| `register/*.yaml`, `config.yaml` | cp1252 whenever a risk statement had non-ASCII | **yes** |
| `.mcp.json`, `settings.json` | ASCII — `json.dumps` defaults to `ensure_ascii=True` | no |
| `events.jsonl` | ASCII — same reason | no |
| `.codex/config.toml` | our block is ASCII; the user's content may not be | user's only |

## Goals / Non-Goals

**Goals:**

- A Windows user who ran the old version can upgrade and have `setup` work.
- Their content survives — no replacement characters, no truncation.
- Files converge to UTF-8 by being used, with no migration command.
- The repair is visible, not silent.

**Non-Goals:**

- Encoding auto-detection (chardet). Two candidates cover the bytes risqlet emitted.
- A migration/`fix-encodings` command. A file heals when next written.
- Relaxing what risqlet *writes*: still UTF-8, `\n`, no BOM.

## Decisions

### 1. Fall back to cp1252, not to "the host locale"

The tempting symmetry is "read it back in whatever the locale is", since the locale
is what wrote it. Rejected: it makes behaviour platform-dependent and untestable
where we develop. On Linux the locale is UTF-8, so the fallback would retry the
encoding that just failed and raise anyway — the bug would be unreproducible and
unfixable on the dev host, which is how it shipped in the first place.

cp1252 is a fixed target: it is what Windows locale encoding *is* for these users, it
decodes deterministically on every platform, and a Linux test exercises the identical
code path a Windows user hits. Being able to reproduce is worth more than being
theoretically general.

### 2. Recover, don't replace

`errors="replace"` would also stop the crash, and would be much worse: risqlet
rewrites these files, so every unmappable byte would be written back as `U+FFFD`. The
user's content would be silently destroyed by the tool that was supposed to repair it.
Decoding as cp1252 recovers the actual characters, so the rewrite is lossless.

### 3. Do not extend the fallback to the JSON paths

`events.jsonl` and the JSON agent configs go through `json.dumps`, which escapes
non-ASCII to `\uXXXX` by default — risqlet has provably never written a non-ASCII
byte there. A fallback on those paths could therefore never fire for a file we wrote;
it could only mask genuine corruption from somewhere else, converting real news into
plausible nonsense. Tolerance is only justified where we caused the problem.

This is the difference between "be robust" and "be robust about a specific thing that
actually happened".

### 4. Report every fallback

A quiet fallback is indistinguishable from the mojibake bug just fixed: both produce
a working command and wrong-looking text. The user is also about to have their file's
encoding changed, which they did not ask for. Saying so costs one line and makes the
repair auditable.

### 5. One helper, used at every tolerant read site

`read_text_tolerant(path)` lives beside the other file primitives and is used by
`render.py` and `store.py`. Keeping it single means the fallback policy — and the
report — cannot drift between the register and the agent configs.

## Risks / Trade-offs

- **cp1252 decodes almost anything**, so genuinely corrupt files will now decode to
  nonsense instead of raising. → Accepted for the paths where risqlet caused the
  problem; explicitly not applied to the JSON paths, where a raise is still correct.
  The report is what keeps this from being invisible.

- **A user's file silently changes encoding** on next write. → It changes to UTF-8,
  which is what the file should have been, and only when risqlet was rewriting it
  anyway. The alternative — preserving cp1252 on write — would re-break the moment our
  own section contained a character cp1252 cannot encode, and would keep the file
  fragile forever.

- **The fallback is a compatibility shim for a bug with a known blast radius.** It
  should not become permanent robustness theatre. → It is documented as such; once no
  pre-fix registers plausibly remain, it can be dropped, and the tests name exactly
  what they are protecting.

- **This is the second Windows bug found by a user rather than by CI**, after a matrix
  that runs `setup` on Windows every push. It passed because CI always starts from a
  clean checkout: no test had a *pre-existing* file, so no test had an old file. The
  regression test added here is what closes that, and the general lesson —
  clean-slate tests cannot catch upgrade bugs — is worth more than the fix.

## Migration Plan

1. Add the helper and the failing regression test first (the exact reported bytes).
2. Apply it at the render.py read sites — the reported crash.
3. Apply it at the store.py register/config reads — the same exposure, not yet
   reported only because fewer people have a Windows register.
4. Verify on all three matrix legs; Windows is where it matters.

Rollback: the helper is additive; reverting restores strict reads (and the crash).

## Open Questions

- Should `setup` proactively rewrite a recovered file even when nothing else changed,
  to heal it? Recommend no: touching a file risqlet was not otherwise editing is
  surprising, and the merge already rewrites the files that matter here.
- Should the fallback eventually be removed? Yes, once pre-fix registers are
  implausible — but that is a judgement about the field, not a code change to make now.
