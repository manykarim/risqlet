## 1. Parse the Claude hook payload (CLI side)

Ordered first by design decision: the new command must be a valid `risqlet`
invocation *before* anything writes it into a settings file.

- [x] 1.1 Add `parse_claude_hook_payload(text: str) -> list[str]` to
  `src/risqlet/changeset.py`: extract `tool_input.file_path` from the JSON
  envelope, return `[]` for empty/malformed/non-JSON input or a missing/blank
  path. Never raises — a bad payload is an empty file list, not an error.
- [x] 1.2 Add `--hook-input` to the `check` subparser in `src/risqlet/cli.py`
  (`choices=["claude"]`, default `None`). Leave `--stdin` semantics untouched.
- [x] 1.3 Wire `cmd_check`: when `--hook-input` is set, read stdin, resolve files
  via 1.1, and skip the check entirely (silent, exit 0) when the list is empty.
- [x] 1.4 Enforce the never-fail contract in `cmd_check`: in `--hook-input` mode
  wrap the run so any exception and any `ci_gate: block` nonzero result still
  returns exit 0, with no traceback reaching the agent session.
- [x] 1.5 Unit-test 1.1 against: a real payload shape, `{}`, `""`, non-JSON,
  `tool_input` absent, and `file_path: ""`. Each returns `[]` without raising.
- [x] 1.6 Test the CLI contract: payload naming a risk-touching file reports that
  risk and exits 0; `ci_gate: block` with flags still exits 0 in hook mode; block
  mode via `--files` still exits 1 (proves the contract is scoped to hook mode).

## 2. Make the installed hook shell-free

- [x] 2.1 Replace `SETUP_HOOK_COMMAND` in `src/risqlet/setup/render.py` with
  `risqlet check --hook-input claude --json` and set
  `SETUP_HOOK_TOOLS = ["risqlet"]`.
- [x] 2.2 Change `HOOK_MARKER` to the self-identifying invocation substring
  (`risqlet check --hook-input`) and add `LEGACY_HOOK_MARKER = "# risqlet:check"`.
- [x] 2.3 Update `apply_json_hooks` to append the bare command with no trailing
  comment marker.
- [x] 2.4 Make `apply_json_hooks` replace a legacy hook rather than skip it: if an
  entry matches `LEGACY_HOOK_MARKER`, drop it before appending the current hook, so
  re-running setup leaves exactly one risqlet hook.
- [x] 2.5 Update `remove_json_hooks` to match **either** marker, so hooks written by
  older versions are still removable and never orphaned.
- [x] 2.6 Update `_marker()` in `src/risqlet/setup/engine.py` for the `json-hooks`
  method to return the new marker.

## 3. Rework hook verification

- [x] 3.1 Rewrite `verify_setup_hook()` in `render.py`: drop the `bash -n` branch;
  preflight only that `risqlet` resolves via `shutil.which` (which handles Windows
  `PATHEXT`).
- [x] 3.2 Add the behavioral check — run the real command with a synthetic Claude
  payload on stdin (no shell, `shell=False`, list argv), assert exit 0, bounded by a
  timeout. Failure returns a reason string, consistent with today's contract.
- [x] 3.3 Confirm `apply_plan`'s existing skip/`--force`/`--no-verify` gate still
  behaves with the new reasons (no signature change expected).
- [x] 3.4 Generalize the static check in `src/risqlet/guardrails/verify.py` to key
  off the command's form: shell commands keep `bash -n` and treat `bash` as a
  required tool; a shell-free command skips the syntax check and is executed
  directly. Do not attempt broader Windows support for guardrails here.

## 4. Fix the ci init template

- [x] 4.1 Replace the `$CLAUDE_TOOL_FILE_PATH` command in
  `src/risqlet/ci/templates/claude-hooks.json` with the same bare command, and
  refresh `_comment` to describe the real stdin-payload contract.
- [x] 4.2 Add a test asserting the template's command equals
  `render.SETUP_HOOK_COMMAND`, so the two hook surfaces cannot drift.

## 5. Tests for the platform properties

These assert the properties that fix the bug, since the Windows failure itself is
not reproducible on this Linux host.

- [x] 5.1 Assert `SETUP_HOOK_COMMAND` is shell-free: contains none of
  `$ " ' | ; & > <` and no `bash`/`python3`/`node`, and that its first token is
  `risqlet`.
- [x] 5.2 Assert `SETUP_HOOK_TOOLS == ["risqlet"]` — the hook declares no
  interpreter dependency.
- [x] 5.3 Test that the marker is never passed to the executable: parse the command
  written to `.claude/settings.json` with `shlex.split` and assert every token is a
  real flag/value (no `#` token).
- [x] 5.4 Test legacy removal: seed a `settings.json` with an old bash hook carrying
  `# risqlet:check` plus a user's own unrelated hook, run remove, assert the risqlet
  hook is gone and the user's hook is intact.
- [x] 5.5 Test legacy replacement: seed an old hook, run setup, assert exactly one
  risqlet hook remains and it is the new command.
- [x] 5.6 Update the existing hook expectations in `tests/test_setup.py` that assume
  the bash command or the `bash`/`python3` tool list.

## 6. Prove it on Windows

Per the design's open question — without this the reported bug has no regression
test on the platform where it occurs.

- [x] 6.1 Add a Windows job to CI running the setup/hook test suite plus a real
  `risqlet setup --dry-run`, asserting no `hook failed verification` skip appears.
- [x] 6.2 If 6.1 is deferred rather than done, say so explicitly in the PR
  description — do not describe the Windows fix as verified when it was only
  argued.

## 7. Docs and changelog

- [x] 7.1 Add a CHANGELOG entry: setup hook now installs on Windows; the
  `ci init --target claude-hooks` template never resolved the edited file and now
  does (a fix on all platforms, not just Windows).
- [x] 7.2 Note in the changelog that `guardrails install` remains unsupported on
  Windows, so the entry cannot be read as "risqlet now works on Windows".
- [x] 7.3 Check `skills/risk-analysis/references/continuous.md` and
  `guardrails.md` for hook-command references and update any that show the old
  command.

## 8. Verify

- [x] 8.1 Run the full suite plus lint; confirm no regression in the existing
  `check`/`ci`/`setup` tests.
- [x] 8.2 End-to-end on this host: `risqlet setup` into a scratch project, pipe a
  real Claude payload into the installed command, confirm it reports the touched
  risk and exits 0.
- [x] 8.3 Run `openspec validate --change fix-windows-hook-install --strict`.
