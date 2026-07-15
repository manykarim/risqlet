# Continuous re-assessment at the change boundary

A risk register goes stale the moment code moves on. The cheap fix is to
re-check it where change happens — the PR, and the coding session itself.
Two read-only commands drive this; neither mutates the register.

## `risqlet diff` — scope a change

`risqlet diff --base <ref>` maps the changed files to the register risks they
touch (by evidence path, mitigation test ref, or — lower confidence —
statement tokens), each with a reason and a suggested action. Use it to:

- **Scope before eliciting** (quickscan step 1): see which existing risks
  already cover this change so you extend them instead of writing duplicates.
- **Prompt re-scoring**: a touched, already-scored risk may now have a
  different likelihood or detectability — bring it to the score gate.

It also lists untouched high-priority risks as a "still worth attention"
reminder — a change that touches nothing important is itself information.

## `risqlet check` — gate a change

`risqlet check --base <ref>` is the CI gate. It flags a change when it touches
an accepted/mitigating risk whose mitigation coverage is failing or missing,
or a reviewed+ risk left without passing coverage. Behavior follows
`config.constraints.ci_gate`: `off` (silent), `warn` (print, pass — default),
`block` (fail the build on any flag). `config.constraints.ci_paths` (globs)
filters which changed paths count, keeping noise low — most PRs touch nothing
risk-relevant and should sail through.

## The two loops

- **PR-time**: `risqlet ci init --target github` (or `gitlab`) drops in a
  workflow that runs `risqlet validate` + `risqlet check` on every PR and writes a
  summary. Set `ci_gate: block` once the register is trusted enough to gate on.
- **In-session**: `risqlet ci init --target claude-hooks` prints a settings.json
  hook so that, after each file edit, `risqlet check` surfaces the risks that
  edit touches — the Semgrep-style continuous signal while you code. The hook is
  `risqlet check --hook-input claude --json`, which reads Claude's stdin payload
  itself: no shell, so it runs on Windows too. It reports only and always exits 0,
  even under `ci_gate: block` — an editor hook must never break the edit loop.

Both loops are advisory feedback, not a substitute for the gated session: they
tell you *when* the register needs another look, not *what* the answer is.
