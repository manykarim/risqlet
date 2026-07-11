# Tasks: add-hook-verification

## 1. Template command + verify metadata

- [x] 1.1 Extend guardrail template model: optional `command` + `verify` {tools, blocking, input, benign, violation}; regenerate any schema; loader validates
- [x] 1.2 Add command+verify to executable templates: secret-scan-posttool, lint-format-posttool, precommit-secret-scan; commands read the changed file via RISQLET_HOOK_FILE
- [x] 1.3 Rewrite coverage-check-stop: derive test command (pytest/npm/Makefile test target) or render no command (skip with note); verify.input none

## 2. Verification engine

- [x] 2.1 Implement src/risqlet/guardrails/verify.py: preflight (tools on PATH, bash -n syntax) + behavioral (benign->0, blocking violation->nonzero, input file/none, timeout with process-group kill, temp cwd); VerifyResult with per-check detail
- [x] 2.2 Render the command (paths substitution) in build_plan; carry command+verify on RenderedGuardrail

## 3. Install gate + real commands + verify command

- [x] 3.1 guardrails install: verify each hook, install only passing by default; --no-verify skips; --force installs failing with warning; report skips
- [x] 3.2 Fix _install_claude to write the REAL rendered command (with marker) instead of the `true` placeholder
- [x] 3.3 `risqlet guardrails verify` subcommand: re-verify installed hooks, read-only, report per hook
- [x] 3.4 setup: verify the check hook before install (same gate); wire --no-verify/--force on setup hooks

## 4. Tests

- [x] 4.1 verify.py: good hook passes (benign 0 + violation nonzero); missing tool fails; syntax error fails; false-block fails; hang times out and is killed; input none path
- [x] 4.2 templates: executable ones have command+verify and render; advisory ones have none; coverage-check-stop detects/parks test command
- [x] 4.3 install gate: failing hook skipped by default, --force installs with warning, --no-verify skips; _install_claude writes real command (not `true`); non-hook guardrails unaffected
- [x] 4.4 guardrails verify command reports pass/fail incl. drift (missing tool); setup hook verified/skipped

## 5. Dogfood (installed agents, project scope, temp dirs only)

- [x] 5.1 Deterministic end-to-end: install a verified secret-scan hook into a temp Claude project; drive `claude -p` (haiku/sonnet) to (a) write a benign file -> allowed, (b) attempt to write a file containing a fake secret -> hook blocks; also confirm a deliberately-broken hook is rejected at install; opencode structural check; NEVER global, NEVER a real repo
- [x] 5.2 Record results in docs/experiments/hook-verification/ (local); append summary to dogfooding report

## 6. Wrap-up

- [x] 6.1 CHANGELOG note (hooks now real + verified — behavior change from placeholder); full pytest + ruff (unpiped); commit
