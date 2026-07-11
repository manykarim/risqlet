# Design: add-dogfooding-experiments

## Context

Stack complete (register/CLI, catalogs, skills, MCP). The Claude Code CLI (v2.x) supports headless runs (`claude -p`) with `--permission-mode`, `--allowedTools`, `--add-dir`, and JSON output. Targets are live local repos we must not disturb: `/home/user/workspace/rf-mcp` (Python) and `/home/user/workspace/robotframework-javaui` (Rust/Java).

## Goals / Non-Goals

**Goals:** prove skill-following, well-formedness, and evidence quality with a real agent on unfamiliar repos; produce a metrics-backed report; harvest fixes. Repeatability: one script, parameterized by target.

**Non-Goals:** benchmarking vs. human analysis, CI integration, publishing example registers, MCP-path dogfooding (CLI+skills path only — it is the primary integration).

## Decisions

### D1. Harness (`scripts/dogfood.py`)

Python (stdlib only) with subcommands per phase so partial re-runs are possible:

- `prepare <target>`: verify target is a git repo with clean-enough state (record `git status --porcelain` baseline); `qrisk skills install --target <target>/.claude/skills --force`; ensure `qrisk` resolvable (`uv tool install --force .` or PATH shim to `uv run qrisk` wrapper).
- `run <target> <experiment>`: execute `claude -p <prompt> --permission-mode acceptEdits --allowedTools <safe set> --output-format json` with `cwd=<target>`, `timeout` (default 15 min), prompt text from `scripts/prompts/<experiment>.md`; save stdout JSON + extracted result text to `docs/experiments/<target-name>/<experiment>/`.
- `collect <target>`: copy `<target>/.qrisk/` into the experiment dir; run `qrisk validate --json` + `qrisk export` on the copy; record metrics JSON.
- `cleanup <target>`: remove `.qrisk/` and installed skills from the target; verify `git status --porcelain` matches the baseline (report any residue loudly).

Safety: never `git commit` in targets; `--allowedTools` grants Read/Grep/Glob/LS plus Bash restricted to `qrisk *` commands and read-only git (`git log`, `git diff`, `git status`), plus Write/Edit only within `.qrisk/` (enforced via prompt instruction; acceptEdits scope is the run cwd — residue check backstops).

### D2. Prompts

Stored under `scripts/prompts/` for reproducibility:
- `quickscan.md`: "Use the risk-quickscan skill on <module/diff>…" — names the target module chosen per repo (rf-mcp: its MCP server core; javaui: its agent/bridge layer), requires final `qrisk validate --json` output in the answer.
- `session.md`: abbreviated risk-analysis phases 0–2 with **simulated gates**: the prompt itself contains the pre-authorized human decisions ("I am human:many; when you reach the aspects gate, I confirm your top-ranked proposal…") and instructs the agent to mark events' notes with `simulated-gate: scripted confirmation`. The report labels these runs accordingly — this measures protocol-following, not real facilitation value.

### D3. Metrics (collected by `collect`, tabulated in the report)

Per run: risks written; validate pass/errors/warnings; speculative ratio (evidence-free / total); evidence spot-check (every cited path checked for existence — script does this mechanically, plus manual sense-check of 3 samples); statement-format compliance (regex: `Because .* may .*, causing .*` tolerant match, manual review of misses); catalog/provenance usage (share of risks with `prompt_ref`); wall-clock; turns/cost if reported by CLI JSON.

### D4. Findings → fixes loop

Report section listing every friction/failure with disposition: `fixed-here` (small: skill wording, error messages, prompt gaps), `future-change` (requirement-level), `wontfix` (with reason). Success criteria per proposal; if a run fails outright, the failure analysis itself is a primary deliverable — document, fix what is fixable, re-run once.

## Risks / Trade-offs

- [Headless runs are nondeterministic] → capture full transcripts; metrics framed as observations of N=1..2 runs, not statistics; re-run budget capped at one retry per experiment.
- [Agent writes outside .qrisk/ in targets] → baseline/residue git check + cleanup step; report any residue.
- [`claude -p` invoked from inside a Claude Code session] → runs are plain subprocesses with their own context; guard with timeout; if nested execution proves impossible in this environment, fall back to documenting the exact commands for the user to run and evaluate whatever artifacts exist (report notes the limitation).
- [Skills not discovered headlessly] → project-level `.claude/skills` is the documented discovery path; if discovery fails, prompt explicitly instructs reading the SKILL.md file — recorded as a finding.

## Migration Plan

Additive; experiment artifacts live in `docs/experiments/`.

## Open Questions

- Whether `uv tool install` or a PATH shim is more reliable for exposing `qrisk` inside target repos — the harness tries tool-install first and falls back (decided at implementation, recorded in the report).
