# risqlet

Agent-facing risk analysis, mitigation and test-strategy toolkit for software projects.

`risqlet` gives coding agents and humans a shared, repo-native risk register (`.risqlet/`)
plus a deterministic CLI that owns everything an LLM must never do by itself:
schema validation, score arithmetic, priority ranking, lifecycle gates, and exports.
Semantic work — eliciting risks, phrasing statements, proposing mitigations — stays
with the host agent (the *framework-provider* pattern).

It also generates repo-grounded test strategies, ingests test results to keep
mitigations honest, re-assesses risk at the PR/CI boundary, and turns accepted
mitigations into coding-agent guardrails. The architecture is fixed by the two
deep-research reports in `docs/`; design history lives in `openspec/`.

## Design in one paragraph

All state lives in files under `.risqlet/` (file-per-risk YAML, append-only decision
log, config) — no server, no sessions, git is the database. Any coding agent that can
run a shell command can use it; Agent Skills, hooks and an MCP adapter layer on top.
Risk lifecycle transitions require a named human principal recorded in the event log:
agents propose, humans decide.

## Quick start

```bash
pip install risqlet        # or: uv tool install risqlet
risqlet setup              # configure your coding agents (skills, MCP, rules)
risqlet init               # scaffold .risqlet/ in your project
risqlet status             # where the analysis stands
```

`risqlet setup` is the one-command onboarding. It detects your coding agents and
wires each one up at project or global scope, then `risqlet setup --remove`
cleanly reverses it. It works both interactively and headlessly:

```bash
risqlet setup                                   # interactive: pick agents + scope
risqlet setup --agents claude,cursor --yes      # scriptable / CI (no prompts)
risqlet setup --all-detected --scope global     # configure every detected agent
risqlet setup --status                          # what's installed where
risqlet setup --remove                          # clean uninstall
```

Supported agents: **Claude Code** (full — skills, MCP, instructions, hooks,
commands) plus an instructions + MCP tier (and skills where supported) for
**Cursor, opencode, Codex, Copilot, kilo, pi**. Each gets exactly what it
supports, reported honestly; MCP-global-only agents (Codex, pi) are flagged.

Core workflow once set up:

```bash
risqlet validate            # schema + lifecycle + gate checks
risqlet score --all         # compute derived priorities from the active policy pack
risqlet export --fmt strategy-md
risqlet catalog list        # browse the knowledge packs
```

## The `.risqlet/` register format

```
.risqlet/
├── config.yaml       # project, active catalogs, scoring policy, phase, constraints,
│                     # selected quality aspects (max 6 by default)
├── register/
│   └── R-0001.yaml   # one risk per file: statement, aspects, elicited_by provenance,
│                     # scores (values + rubric_anchors; derived is CLI-owned),
│                     # status lifecycle, embedded mitigations (residual_note required)
├── events.jsonl      # append-only decision log; status/phase transitions need
│                     # a `human:` principal — agents propose, humans decide
├── policies/         # optional user scoring-policy packs (shadow packaged ones)
└── strategy.md       # conventional target for `risqlet export --fmt strategy-md -o`
```

JSON Schemas for all file types are published in `src/risqlet/schemas/` (generated
from the models via `python -m risqlet.model.schema_gen`). Unknown extra fields are
warnings, not errors — the format is open for forward-compatible annotation.

Every file is **UTF-8 with `\n` line endings**, on every platform — risqlet states
the encoding rather than inheriting the host's locale, so a register written on
Windows is byte-identical to one written on Linux and survives a round trip through
either. This is part of the on-disk contract: the register is meant to be diffed,
reviewed, and merged in git, which only works if the bytes do not depend on who
wrote them.

Scoring policies are data, not code (`src/risqlet/policies/packs/`): ordinal factors
plus derived fields via a `product` formula or a top-down first-match lookup table.
Default is `sod-ap-v1` (Severity×Occurrence×Detection with severity-dominant
Action-Priority bands); `li-v1` is a lightweight 3×3 likelihood×impact profile.

## Knowledge catalogs

Six packaged packs, all original clean-room text. Four are enabled by default:
`iso25010` quality aspects, `techniques`, `heuristics` (including consistency
oracles), and `guidewords` (element × guideword elicitation sets). Two are
opt-in for security-heavy products (add them to `config.catalogs`):
`mitre-attack` (adversary-tactic sweep, ATT&CK tactic names as facts, with the
MITRE attribution notice) and `owasp-web` (the ten web risk categories).
Entries are stable, citable ids (`techniques.stress-testing`) used by register
provenance fields. `risqlet catalog licenses` lists every loaded pack's license,
attribution, and any required notice. User packs in `.risqlet/catalogs/` load the
same way and may shadow packaged ones — including licensed decks you own (we
never distribute those).

| Pack | Default | License |
|---|---|---|
| iso25010, techniques, heuristics, guidewords | on | CC BY 4.0 |
| owasp-web | opt-in | CC BY 4.0 (category names per OWASP taxonomy) |
| mitre-attack | opt-in | MITRE ATT&CK terms (royalty-free, attribution required) |

## Agent skills

Two portable playbooks (cross-vendor Agent Skills format) ship in `skills/`:

- **risk-analysis** — the full six-phase facilitation: context grounding,
  aspect selection (max 6), multi-pass elicitation, rubric-anchored scoring,
  mitigation mapping, strategy export — with human gates recorded in the
  register's event log.
- **risk-quickscan** — a diff/PR-scoped single-pass scan that adds `proposed`
  risks and recommends a full session when warranted.

Install them where your agent looks:

```bash
uv run risqlet skills install                          # ./.claude/skills (Claude Code project)
uv run risqlet skills install --target claude-user     # ~/.claude/skills
uv run risqlet skills install --target /path/to/dir    # opencode, kilo, Copilot, pi, ...
```

The skills drive the `risqlet` CLI, so any agent that can run shell commands can
follow them; a skipped human gate simply leaves a register that fails
`risqlet validate`.

## MCP server

For MCP-connected clients without repo shell access (Claude Desktop,
restricted setups), `risqlet mcp` runs a stateless stdio server exposing nine
tools over the same core — validation, scoring, exports, catalog browsing,
the playbooks as `get_guidance` topics, and gate-preserving register writes
(risks enter as `proposed`; decisions require a `human:` principal).

```bash
uv sync --extra mcp        # or: pip install 'risqlet[mcp]'
```

`.mcp.json` / Claude Desktop config:

```json
{
  "mcpServers": {
    "risqlet": {"command": "uv", "args": ["run", "risqlet", "mcp"]}
  }
}
```

Rule of thumb: coding agents with shell access get the best experience from
the CLI + skills; use MCP when the client cannot run shell commands.

## Platform support

Linux, macOS, and Windows. Each is exercised on every push by the test matrix
([`.github/workflows/test.yml`](.github/workflows/test.yml)), which runs the full
suite plus a clean install of the built wheel and `risqlet setup` for every agent
adapter — so what is claimed here is what CI actually runs.

| Component | Linux | macOS | Windows |
|---|---|---|---|
| CLI, register, `validate` / `score` / `export` | ✅ | ✅ | ✅ |
| `diff` / `check` and the CI gate | ✅ | ✅ | ✅ |
| `setup` (agent skills, MCP, instructions, commands) | ✅ | ✅ | ✅ |
| The `setup` check hook | ✅ | ✅ | ✅ |
| `guardrails` (shell hook templates) | ✅ | ✅ | ❌ |

`risqlet guardrails` is POSIX-only: its hook templates are shell one-liners and its
verifier uses POSIX process handling. On Windows it reports the guardrail as
unsupported rather than installing a hook that would not work. Everything else,
including the `setup` check hook, is shell-free and runs the same everywhere.

## Honest limits

The human-principal gate is a *convention enforced by validation*, not authentication:
an agent could write a `human:` event. On Claude Code, hooks add real enforcement;
elsewhere, the audit trail plus code review is the control. Scores are ordinal
heuristics for sorting attention, never measurements of "true" risk.

`guardrails` on Windows is a real gap, not a design stance — closing it means moving
each guardrail's logic out of its shell template and into the CLI, the way the check
hook already works.

## Project

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup and the clean-room affirmation
- [SECURITY.md](SECURITY.md) — reporting vulnerabilities
- [CHANGELOG.md](CHANGELOG.md) · [RELEASING.md](RELEASING.md) · [docs/release-checklist.md](docs/release-checklist.md)

## License

Code: Apache-2.0 (`LICENSE`). Catalog pack content (`src/risqlet/catalog/packs/`): CC BY 4.0 (`LICENSE-CATALOG`), authored under the clean-room protocol in `CLEAN-ROOM.md` — original text expressing established concepts, originators credited per entry.
