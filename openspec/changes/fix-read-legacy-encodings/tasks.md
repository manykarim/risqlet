## 1. Reproduce first

- [x] 1.1 Add a regression test that builds a `CLAUDE.md` containing risqlet's own
  instructions section encoded as **cp1252** — what a pre-fix risqlet on Windows
  wrote — and runs `setup --components instructions` against it. It must fail with the
  reported `UnicodeDecodeError: ... byte 0x97 ...` before the fix.
- [x] 1.2 Same for the register: a `register/*.yaml` whose statement has a
  cp1252-encoded em-dash must currently raise on load.

## 2. The tolerant read

- [x] 2.1 Add `read_text_tolerant(path)`: decode UTF-8; on `UnicodeDecodeError`
  decode cp1252 and report the recovery. Fixed fallback, never the host locale
  (design decision 1) — a locale fallback is untestable on Linux and would have let
  this ship again.
- [x] 2.2 Report the fallback to stderr, once per file, naming the path and that it
  will be rewritten as UTF-8. Silent repair is indistinguishable from the mojibake bug.
- [x] 2.3 Use it in `src/risqlet/setup/render.py` for the markdown reads only —
  `apply_md_section` and `remove_md_section`. **Corrected during implementation:** as
  first written this task also listed `apply_toml_merge` / `apply_json_merge` /
  `apply_json_hooks`, which contradicts 2.5. Checking each surface showed risqlet's
  own output only ever contained non-ASCII in the markdown section and the YAML
  (em-dashes in `INSTRUCTIONS_BODY` and `_STARTER_CONFIG`); its JSON and TOML writes
  are ASCII. So those stay strict, per design decision 3.
- [x] 2.4 Use it in `src/risqlet/store.py` for `config.yaml` and `register/*.yaml`.
- [x] 2.5 Do **not** use it for `events.jsonl` or the JSON agent configs — `json.dumps`
  escapes to ASCII, so risqlet never wrote a non-ASCII byte there; a decode error is
  real corruption and must still raise (design decision 3).
- [x] 2.6 Confirm writes are unchanged: still UTF-8 + `newline="\n"`, so a recovered
  file is normalized on the next write.

## 3. Prove content survives

- [x] 3.1 Assert the *user's* own cp1252 prose in `CLAUDE.md` round-trips with its
  characters intact — not `U+FFFD`. `errors="replace"` would also stop the crash while
  destroying the file; this is the test that tells the two apart.
- [x] 3.2 Assert the file is UTF-8 after the merge (the heal-on-write property).
- [x] 3.3 Assert `setup --remove` works against a cp1252 config and leaves the user's
  content intact.
- [x] 3.4 Assert the register recovers a cp1252 risk statement with the em-dash
  present, and re-saves as UTF-8.
- [x] 3.5 Assert a *corrupt* `events.jsonl` still raises rather than decoding to
  nonsense — the negative case that keeps the tolerance scoped.

## 4. The CI gap this exposes

- [x] 4.1 Note in the test module why CI missed this: every job starts from a clean
  checkout, so no test ever had a *pre-existing* file from an older version. Upgrade
  paths need fixtures, not a fresh install.
- [x] 4.2 Check whether any other test asserts behaviour against a file risqlet
  wrote in a *previous* version; if none, say so plainly rather than implying the
  class is now covered by this one test.

## 5. Docs

- [x] 5.1 CHANGELOG: the previous release's strict reads broke `setup` for Windows
  users upgrading, because risqlet had written those files in cp1252 itself. Say that
  it was a regression, not a pre-existing bug.

## 6. Verify

- [x] 6.1 The reproduction from 1.1 passes with the fix and fails without it.
- [x] 6.2 Full suite + lint green on Linux, both encoding guards still armed.
- [x] 6.3 `openspec validate fix-read-legacy-encodings --strict`.
- [ ] 6.4 Push; all three matrix legs green. Windows is the one that counts.
- [x] 6.5 Reproduce the user's exact invocation end-to-end (`setup` over a cp1252
  `CLAUDE.md`) and confirm it now completes.
