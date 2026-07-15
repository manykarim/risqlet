## 1. Add the guards first

Ordered first deliberately: the guards enumerate the work. A grep found ~48 sites
and ruff found 20 — neither is trustworthy as the definition of done, so let the
machines produce the list before editing anything.

- [x] 1.1 Enable ruff `PLW1514` in `pyproject.toml`. It is a **preview** rule, so
  `preview = true` is required under `[tool.ruff.lint]`; note in a comment that it is
  preview and why the risk is accepted (it is the redundant guard).
- [x] 1.2 Add `PYTHONWARNDEFAULTENCODING=1` and `-W error::EncodingWarning` to the
  test configuration (`[tool.pytest.ini_options]` `filterwarnings` cannot set the env
  var — set it in the workflow, and add the `-W` via `addopts` or `filterwarnings`).
  Confirm it fails today on our own code and produces no third-party noise.
- [x] 1.3 Record the two lists (ruff's and the runtime's) before fixing — the union is
  the work; their difference is the evidence for design decision 3.

## 2. Fix the call sites

- [x] 2.1 `src/risqlet/store.py` (7) — register, `config.yaml`, `events.jsonl`. Highest
  value and invisible to ruff; do it first so the runtime guard goes quiet here.
- [x] 2.2 `src/risqlet/setup/render.py` (18) — the largest cluster; agent config merges.
- [x] 2.3 `src/risqlet/guardrails/engine.py` (8) and `src/risqlet/setup/engine.py` (3).
- [x] 2.4 Remaining files: `trace.py`, `ci/__init__.py`, `skills.py`,
  `catalog/loader.py`, `policies/engine.py`, `mcp/tools.py`, `cli.py`,
  `model/schema_gen.py`, `guardrails/verify.py`.
- [x] 2.5 Add `newline="\n"` to every text **write** (not reads — universal newlines
  on read is correct and should stay).
- [x] 2.6 Review the diff specifically for handles that must NOT get `encoding`:
  binary modes (`rb`/`wb`), `subprocess`, `zipfile`. The guards catch omissions, not
  over-application, so this is a manual pass.
- [x] 2.7 Both guards clean: `ruff check --preview` and the suite under
  `PYTHONWARNDEFAULTENCODING=1 -W error::EncodingWarning`.

## 3. The test that would have caught it

- [x] 3.1 Round-trip a risk whose statement contains `→` (crashes cp1252), an em-dash
  (silently mojibakes), and CJK: save, reload, assert the string is unchanged.
- [x] 3.2 Assert the on-disk **bytes** decode as UTF-8 and contain the expected
  characters — reading back through the same wrong assumption that wrote them would
  pass even when both are broken.
- [x] 3.3 Cover `events.jsonl`: append an event with non-ASCII text, assert the log
  is valid UTF-8 JSONL.
- [x] 3.4 Prove the test is meaningful rather than trivially green: force a
  non-UTF-8 encoding (monkeypatch `locale.getpreferredencoding` / write via cp1252)
  and confirm the assertion fails without the fix.
- [x] 3.5 Assert writes use `\n`: read the written file in binary and confirm no
  `\r\n`.

## 4. Line endings in the repo

- [x] 4.1 Add `.gitattributes` with `* text=auto eol=lf` so a Windows checkout with
  the default `core.autocrlf=true` cannot rewrite YAML fixtures and catalog data.
- [x] 4.2 Confirm no tracked file changes as a result (`git add --renormalize .`
  should be a no-op on this tree); if it is not, say what changed and why.

## 5. Docs

- [x] 5.1 CHANGELOG: reads were silently corrupting non-ASCII on Windows and writes
  crashed on `→`/CJK/emoji; output is now byte-identical across platforms. Say plainly
  that this affected Windows only and that no on-disk format changed.
- [x] 5.2 Note the UTF-8 contract where the register format is documented (README's
  `.risqlet/` section) — the file format is part of the product's contract.

## 6. Verify

- [x] 6.1 Full suite + lint green on Linux, including the new guards.
- [x] 6.2 Simulate the Windows failure locally as far as possible: confirm the
  round-trip test fails when the locale encoding is forced to cp1252, and passes with
  the fix. This is the closest thing to proof available from this host.
- [x] 6.3 `openspec validate fix-text-encoding --strict`.
- [ ] 6.4 Push and read all three matrix legs. **Windows is the only leg that can
  disprove anything here** — until it is green, this is unverified where it matters,
  and should be reported that way.
