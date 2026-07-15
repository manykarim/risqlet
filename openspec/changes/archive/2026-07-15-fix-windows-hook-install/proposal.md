## Why

`risqlet setup` cannot install the Claude Code check hook on Windows. It reports:

```
skip claude/hooks: hook failed verification: bash not on PATH
```

The hook is a POSIX shell one-liner that spawns `python3` purely to pull
`tool_input.file_path` out of the JSON payload Claude Code writes to stdin, then
passes it back to `risqlet` — a Python CLI that is already on PATH and is the very
tool being installed. The verification gate is working exactly as designed here: it
correctly refuses to install a hook that cannot run. The defect is the hook's
shape, not the gate.

Windows breaks this hook in three independent ways, so patching any one of them
leaves it broken: `bash` is absent, the interpreter is `python`/a launcher shim
rather than `python3`, and the POSIX quoting (`"$(...)"`, `2>/dev/null || true`)
has no cmd.exe or PowerShell equivalent. The fix is to stop needing a shell at all:
teach `risqlet check` to read Claude's hook payload directly, which reduces the
hook to a single bare command that runs identically on every platform.

While mapping the surface we found a second, separately-broken hook: the template
emitted by `risqlet ci init --target claude-hooks` reads `$CLAUDE_TOOL_FILE_PATH`,
an environment variable Claude Code does not set. That hook silently checks an
empty path on *every* platform, Linux included — it has never worked. Both hooks
are fixed here so a single command string exists in the codebase.

## What Changes

- **`risqlet check` learns to parse an agent hook payload.** A new
  `--hook-input claude` flag reads Claude Code's JSON envelope from stdin and
  extracts the edited file path itself, replacing the `bash`+`python3` extraction.
  This is a distinct input format from the existing `--stdin` (newline-separated
  paths), so it is a separate flag rather than a change to `--stdin` semantics.
- **The installed hook becomes shell-free.** `risqlet check --hook-input claude
  --json` — no `bash`, no `python3`, no `node`, no PowerShell, no shell
  metacharacters. One command, one code path, every platform.
- **Hook mode never breaks the agent loop.** The old command ended in
  `2>/dev/null || true`; with no shell, that suppression must move into the CLI.
  `--hook-input` mode swallows its own errors and always exits 0, preserving today's
  effective behavior rather than newly surfacing errors into the agent's session.
- **Hook verification stops mandating `bash`.** Preflight currently runs `bash -n`
  on the command. For a shell-free hook there is no shell to syntax-check, so the
  setup hook is instead verified by *actually running it* against a synthetic
  payload and asserting exit 0 — a stronger check than the syntax check it replaces.
- **The provenance marker moves out of the command string.** The marker is today a
  trailing `# risqlet:check` shell comment. Without a shell that comment would be
  passed to `risqlet` as literal arguments, so the hook must self-identify by its
  invocation instead. Removal must continue to recognize hooks installed by prior
  versions, which carry the old marker.
- **`ci init --target claude-hooks` emits the same working command**, replacing the
  `$CLAUDE_TOOL_FILE_PATH` env-var read that never fired.
- No new runtime dependency. Node was considered and rejected: this is a pure-Python
  project (no `package.json`), and pip/uv users cannot be assumed to have a Node
  runtime. Parallel PowerShell hooks were also rejected — they double the
  implementation, verify, and removal surface, and still would not resolve the
  `python3`-vs-`python` half of the bug.

### Not in scope

`risqlet guardrails install` is also broken on Windows, and more deeply: its hook
templates are POSIX shell one-liners (`grep`, `awk`), and
`guardrails/verify.py` runs `bash -c` and calls `os.killpg`/`os.getpgid`, which do
not exist on Windows. Making arbitrary shell guardrail templates
platform-independent is a substantially larger design problem than the reported
failure and is deliberately left to a follow-up change. This change fixes the hook
risqlet itself ships via `setup`; it does not claim `guardrails` works on Windows.

## Capabilities

### New Capabilities

None. This change fixes the shape of an existing hook and extends an existing
command's input handling; it introduces no new capability.

### Modified Capabilities

- `change-reassessment`: `check` gains a Claude hook-payload input mode that is
  non-failing by contract; the `claude-hooks` template emitted by `ci init` must
  carry a command that actually resolves the edited file.
- `hook-verification`: preflight generalizes from a hardcoded `bash -n` syntax
  check to a check appropriate to the command's form, so a shell-free hook is
  verifiable (by execution) rather than being failed for lacking a shell.
- `agent-setup`: the hook `setup` installs must run on every platform risqlet
  supports, depending only on `risqlet` itself.

## Impact

Affected code:

- `src/risqlet/cli.py` — `--hook-input` flag on the `check` subparser; non-failing
  exit contract in `cmd_check` for that mode.
- `src/risqlet/changeset.py` — parse the Claude payload into a file list.
- `src/risqlet/setup/render.py` — `SETUP_HOOK_COMMAND`, `SETUP_HOOK_TOOLS`,
  `verify_setup_hook`, `HOOK_MARKER`, `apply_json_hooks`, `remove_json_hooks`.
- `src/risqlet/setup/engine.py` — `_marker` for the `json-hooks` method.
- `src/risqlet/ci/templates/claude-hooks.json` — the stale env-var command.
- `tests/test_setup.py` — hook verification and marker tests.

Migration: hooks installed by earlier versions carry the old bash command and the
old `# risqlet:check` marker. Re-running `risqlet setup` must replace them, and
`risqlet setup --remove` must still recognize them — otherwise an upgrade orphans a
hook that no longer matches the current marker and can never be cleaned up.

Behavior preserved: exit-code semantics for existing `check` invocations
(`--files`, `--stdin`, git-diff) are untouched; the `ci_gate` block/warn/off
contract still governs non-hook use.

Risk: none of this is verifiable on Windows from this environment (Linux). CI
coverage on a Windows runner is the only honest proof the reported failure is
gone; tests must assert the command is shell-free rather than assert it runs on a
platform we cannot exercise here.
