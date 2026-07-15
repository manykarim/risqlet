## Context

`risqlet setup` installs a Claude Code `PostToolUse` hook that re-checks a file
against the risk register after each Write/Edit. Today that hook is
(`setup/render.py`):

```
f="$(python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"; risqlet check --files "$f" --json 2>/dev/null || true
```

with `SETUP_HOOK_TOOLS = ["risqlet", "python3", "bash"]`, and a `HOOK_MARKER` of
`# risqlet:check` appended to the command as a shell comment.

Everything before `risqlet check` exists only to pull one string out of the JSON
Claude Code writes to stdin. That is a Python job, and `risqlet` is a Python CLI
that is necessarily on PATH — the hook shells out to a second Python to prepare an
argument for the first.

On Windows this fails three ways at once: no `bash`; `python3` is typically
`python` or a launcher shim; and the POSIX quoting has no cmd.exe/PowerShell
equivalent. `verify_setup_hook()` correctly refuses to install it, producing the
reported `skip claude/hooks: hook failed verification: bash not on PATH`. The gate
is doing its job — the hook is the defect.

Two constraints shape the fix:

- **The `hook-verification` spec currently mandates `bash -n`** as a preflight
  check, so a shell-free hook is unverifiable until that requirement generalizes.
- **The marker is a shell comment.** With no shell, `# risqlet:check` would be
  passed to `risqlet` as literal argv and break the command, so identification must
  change alongside the command.

A second hook, `ci/templates/claude-hooks.json`, reads `$CLAUDE_TOOL_FILE_PATH` —
an environment variable Claude Code does not set. It has never worked on any
platform. It is fixed here so one command string exists in the codebase.

## Goals / Non-Goals

**Goals:**

- `risqlet setup` installs a working check hook on Windows, macOS, and Linux.
- One hook command, one code path, no platform branches, no second variant.
- No new runtime dependency.
- Preserve today's effective behavior: the hook reports and never breaks the loop.
- Keep the verification gate meaningful — do not weaken it into a no-op to pass.
- Upgrades from the old hook are clean: replaced, not duplicated or orphaned.

**Non-Goals:**

- Making `risqlet guardrails` work on Windows. Its templates are POSIX shell
  (`grep`, `awk`) and `guardrails/verify.py` uses `bash -c` plus
  `os.killpg`/`os.getpgid`, which do not exist on Windows. That is a larger design
  problem; this change does not claim to solve it and must not pretend it has.
- Changing `check`'s behavior for `--files`, `--stdin`, or git-diff invocations.
- Supporting hook formats for agents other than Claude Code (the flag is named to
  leave room, but only `claude` is implemented).

## Decisions

### 1. Fold payload parsing into the CLI, rather than adding a second hook language

`risqlet check --hook-input claude --json` needs no shell, no `python3`, no `node`,
no PowerShell. The shell was only ever plumbing between stdin and a CLI that could
read stdin itself.

- **Over Node hooks:** this is a pure-Python project (no `package.json`). Node
  would add a runtime dependency that pip/uv users may not have — trading a missing
  `bash` for a missing `node`, plus a JS file to ship and version.
- **Over parallel PowerShell hooks:** doubles the implementation, verify, and
  removal surface, requires install-time platform detection, and still leaves the
  `python3`-vs-`python` half of the bug unfixed on Windows.

The chosen option *removes* an interpreter dependency instead of adding one, and is
the only option where the bug class cannot recur.

### 2. A new `--hook-input <agent>` flag, not an overload of `--stdin`

`--stdin` means "newline-separated paths" (`changeset.changed_files`). A Claude hook
payload is JSON. Same stream, different grammar — overloading `--stdin` with format
sniffing would make behavior depend on content and silently misread a path that
happens to look like JSON. A separate, agent-named flag keeps both contracts sharp
and leaves room for other agent formats.

### 3. Hook mode always exits 0

The old command ended `2>/dev/null || true`, so the hook could never fail an edit.
With no shell, that suppression has to move into the CLI or the behavior silently
changes: a `ci_gate: block` register would start failing the agent's Write/Edit —
a regression introduced by a portability fix.

So `--hook-input` mode catches its own errors and exits 0 unconditionally. This is
deliberately a property of hook mode only; `check`'s `block` contract is untouched
for CI use, where a nonzero exit is the whole point.

Stderr is *not* globally swallowed the way `2>/dev/null` did — the mode simply does
not raise or print tracebacks. Suppressing errors and having none are different, and
the latter is what a hook should aim for.

### 4. The command self-identifies; no comment marker

`# risqlet:check` cannot survive on a shell-free command. The hook is instead
recognized by its own invocation — the `risqlet check --hook-input` substring —
which no user hook would plausibly contain. This removes the marker as a separate
concept rather than relocating it.

`engine._marker("json-hooks", ...)` and `render.HOOK_MARKER` change together, and
`remove_json_hooks` must match **both** the new invocation and the legacy
`# risqlet:check` string.

### 5. Verification runs the hook instead of syntax-checking it

For a shell-free command there is no shell syntax to check, so `bash -n` is
replaced by something stronger: execute the real command with a synthetic Claude
payload on stdin and assert exit 0. That proves resolvable-on-PATH, runnable, and
honoring the never-fail contract — a superset of what `bash -n` proved.

Preflight reduces to `SETUP_HOOK_TOOLS = ["risqlet"]`. `shutil.which("risqlet")`
handles Windows `PATHEXT`/`.exe` resolution natively.

This is why the `hook-verification` spec changes: the requirement must key the
static check to the command's *form*, so shell hooks still demand `bash` while
shell-free hooks are not failed for its absence. The gate gets narrower in what it
assumes and stricter in what it proves.

## Risks / Trade-offs

- **We cannot test the actual failure here.** This environment is Linux; the bug is
  Windows-only. → Tests assert the property that fixes it (the command is
  shell-free, spawns no interpreter, tools list is `["risqlet"]`) rather than
  asserting an OS we cannot exercise. A Windows CI runner is the only honest proof;
  until one exists, the fix is argued, not demonstrated, and should be said that way.

- **Upgrade orphans a hook.** Manifests from older versions record marker
  `# risqlet:check`; if `HOOK_MARKER` changes without back-compat, `remove` silently
  fails to match and leaves a broken bash hook in `settings.json` forever. → Removal
  matches legacy and current markers; a test covers removing an
  old-format hook, and re-running setup over an old hook must leave exactly one.

- **Exit-0-always can mask a real breakage.** A hook that never fails also never
  tells you it stopped working. → This is not new (`|| true` did the same), and it is
  the right trade for a hook inside an edit loop. `guardrails verify` remains the
  place drift is detectable, and verification-at-install proves it worked once.

- **Claude's payload shape could change.** `tool_input.file_path` is an external
  contract we do not own. → Parsing lives in one function with a no-op fallback, so
  a shape change degrades to "checks nothing" rather than erroring in the loop. The
  `ci init` template and installed hook share the command, so they cannot drift
  apart.

- **Windows remains half-supported.** `setup` will work; `guardrails install` will
  not. → Explicit non-goal, stated in the proposal rather than papered over. A user
  fixing their `setup` failure should not be led to believe `guardrails` follows.

## Migration Plan

1. Ship the CLI flag before changing the hook string — the new command must exist
   as a valid `risqlet` invocation before anything writes it into a settings file.
2. `risqlet setup` re-run replaces an old hook in place (match legacy marker →
   remove → write current). Result: exactly one risqlet hook.
3. `risqlet setup --remove` recognizes both marker generations.
4. Users who never re-run setup keep a working bash hook on POSIX; nothing breaks
   for them. Windows users go from "skipped" to "installed".

Rollback: revert the `render.py` command constant. The `--hook-input` flag is
additive and can stay — it breaks nothing on its own.

## Open Questions

- Should a Windows CI job be added in this change or a follow-up? Without one, the
  reported bug has no regression test on the platform it occurs on. Recommendation:
  add it here, even minimal (`risqlet setup --dry-run` + the hook verify path), or
  the fix is unproven where it matters.
- Should `guardrails verify`'s POSIX-only process handling (`killpg`) degrade with a
  clear "not supported on this platform" message rather than an `AttributeError`?
  Out of scope to fix properly, but a crash is a bad way to learn it is unsupported.
