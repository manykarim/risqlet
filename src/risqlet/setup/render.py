"""Render the canonical MCP spec and instructions into each agent's format.

Every write is marker-scoped so it can be reversed without touching a user's own
config. JSON/JSONC merges add a single ``risqlet`` key; TOML and markdown use
delimited blocks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MCP_COMMAND = "risqlet"
MCP_ARGS = ["mcp"]

MD_BEGIN = "<!-- risqlet:setup:begin -->"
MD_END = "<!-- risqlet:setup:end -->"
TOML_BEGIN = "# risqlet:mcp:begin"
TOML_END = "# risqlet:mcp:end"
HOOK_MARKER = "# risqlet:check"

INSTRUCTIONS_BODY = """\
## risqlet (risk analysis)

This project uses **risqlet** for risk analysis and test strategy. The risk
register lives in `.risqlet/`.

- Run `risqlet status` to see where the analysis stands and resume there.
- Use the `risk-analysis` skill for a full session, `risk-quickscan` for a
  change-scoped scan.
- Agents propose; humans decide — lifecycle transitions need a `human:`
  principal in the event log. Validate with `risqlet validate`.
"""

COMMAND_FILES = {
    "risk-analysis.md": "Use the risk-analysis skill to run a gated risk-analysis "
                        "session for this project (see risqlet).\n",
    "risk-quickscan.md": "Use the risk-quickscan skill to scan the current change "
                         "for risks (see risqlet).\n",
}


def expand(path_template: str, project_root: Path) -> Path:
    p = path_template
    if p.startswith("~"):
        return Path(p).expanduser()
    return (project_root / p)


def _mcp_entry(key: str) -> dict:
    if key == "mcp":  # opencode / kilo local-server shape
        return {"type": "local", "command": [MCP_COMMAND, *MCP_ARGS], "enabled": True}
    return {"command": MCP_COMMAND, "args": MCP_ARGS}


def _strip_jsonc(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|\s)//[^\n]*", r"\1", text)
    return text


# -- apply ---------------------------------------------------------------------

def apply_json_merge(path: Path, key: str, jsonc: bool = False) -> None:
    data = {}
    if path.exists():
        raw = path.read_text()
        data = json.loads(_strip_jsonc(raw) if jsonc else raw) if raw.strip() else {}
    data.setdefault(key, {})["risqlet"] = _mcp_entry(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def apply_toml_merge(path: Path) -> None:
    block = (f"{TOML_BEGIN}\n[mcp_servers.risqlet]\n"
             f'command = "{MCP_COMMAND}"\nargs = {json.dumps(MCP_ARGS)}\n{TOML_END}\n')
    existing = path.read_text() if path.exists() else ""
    if TOML_BEGIN in existing:
        existing = _strip_block(existing, TOML_BEGIN, TOML_END)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + block)


def apply_md_section(path: Path) -> bool:
    """Returns True if the file was created."""
    section = f"{MD_BEGIN}\n{INSTRUCTIONS_BODY.rstrip()}\n{MD_END}\n"
    created = not path.exists()
    existing = path.read_text() if path.exists() else ""
    if MD_BEGIN in existing and MD_END in existing:
        pre = existing.split(MD_BEGIN)[0]
        post = existing.split(MD_END, 1)[1]
        new = pre.rstrip("\n") + ("\n\n" if pre.strip() else "") + section + post.lstrip("\n")
    elif existing.strip():
        new = existing.rstrip("\n") + "\n\n" + section
    else:
        new = section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new)
    return created


def apply_copy_commands(target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, body in COMMAND_FILES.items():
        (target_dir / name).write_text(body)
        written.append(target_dir / name)
    return written


def apply_json_hooks(path: Path) -> None:
    data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
    hooks = data.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])
    if not any(HOOK_MARKER in h.get("command", "")
               for e in post for h in e.get("hooks", [])):
        post.append({"matcher": "Write|Edit", "hooks": [{
            "type": "command",
            "command": f'risqlet check --files "$CLAUDE_TOOL_FILE_PATH" --json '
                       f'2>/dev/null || true  {HOOK_MARKER}'}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# -- remove --------------------------------------------------------------------

def _strip_block(text: str, begin: str, end: str) -> str:
    if begin not in text or end not in text:
        return text
    pre = text.split(begin)[0]
    post = text.split(end, 1)[1]
    return (pre.rstrip("\n") + "\n" + post.lstrip("\n")).strip("\n") + "\n"


def remove_json_merge(path: Path, key: str, jsonc: bool = False) -> None:
    if not path.exists():
        return
    raw = path.read_text()
    if not raw.strip():
        return
    data = json.loads(_strip_jsonc(raw) if jsonc else raw)
    if key in data and isinstance(data[key], dict):
        data[key].pop("risqlet", None)
        if not data[key]:
            del data[key]
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n")
    else:
        path.unlink()


def remove_toml_merge(path: Path) -> None:
    if not path.exists():
        return
    new = _strip_block(path.read_text(), TOML_BEGIN, TOML_END)
    if new.strip():
        path.write_text(new)
    else:
        path.unlink()


def remove_md_section(path: Path, created: bool) -> None:
    if not path.exists():
        return
    new = _strip_block(path.read_text(), MD_BEGIN, MD_END)
    if created and not new.strip():
        path.unlink()
    else:
        path.write_text(new)


def remove_json_hooks(path: Path) -> None:
    if not path.exists() or not path.read_text().strip():
        return
    data = json.loads(path.read_text())
    hooks = data.get("hooks", {})
    for event in list(hooks):
        for entry in hooks[event]:
            entry["hooks"] = [h for h in entry.get("hooks", [])
                              if HOOK_MARKER not in h.get("command", "")]
        hooks[event] = [e for e in hooks[event] if e.get("hooks")]
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n")
    else:
        path.unlink()
