"""Render the canonical MCP spec and instructions into each agent's format.

Every write is marker-scoped so it can be reversed without touching a user's own
config. JSON/JSONC merges add a single ``risqlet`` key; TOML and markdown use
delimited blocks.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from risqlet.textio import read_text_tolerant

MCP_COMMAND = "risqlet"
MCP_ARGS = ["mcp"]

MD_BEGIN = "<!-- risqlet:setup:begin -->"
MD_END = "<!-- risqlet:setup:end -->"
TOML_BEGIN = "# risqlet:mcp:begin"
TOML_END = "# risqlet:mcp:end"
# The hook's own invocation is its provenance marker — a shell-free command cannot
# carry a trailing comment. Defined next to SETUP_HOOK_COMMAND below.
HOOK_MARKER = "risqlet check --hook-input"

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
        raw = path.read_text(encoding="utf-8")
        data = json.loads(_strip_jsonc(raw) if jsonc else raw) if raw.strip() else {}
    data.setdefault(key, {})["risqlet"] = _mcp_entry(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def apply_toml_merge(path: Path) -> None:
    block = (f"{TOML_BEGIN}\n[mcp_servers.risqlet]\n"
             f'command = "{MCP_COMMAND}"\nargs = {json.dumps(MCP_ARGS)}\n{TOML_END}\n')
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if TOML_BEGIN in existing:
        existing = _strip_block(existing, TOML_BEGIN, TOML_END)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + block,
                    encoding="utf-8", newline="\n")


def apply_md_section(path: Path) -> bool:
    """Returns True if the file was created."""
    section = f"{MD_BEGIN}\n{INSTRUCTIONS_BODY.rstrip()}\n{MD_END}\n"
    created = not path.exists()
    # tolerant: our own section contains an em-dash, so a pre-encoding-fix risqlet on
    # Windows left this file cp1252 — and a user's editor may have too. Rewritten as
    # UTF-8 below, so the file heals the first time setup touches it.
    existing = read_text_tolerant(path) if path.exists() else ""
    if MD_BEGIN in existing and MD_END in existing:
        pre = existing.split(MD_BEGIN)[0]
        post = existing.split(MD_END, 1)[1]
        new = pre.rstrip("\n") + ("\n\n" if pre.strip() else "") + section + post.lstrip("\n")
    elif existing.strip():
        new = existing.rstrip("\n") + "\n\n" + section
    else:
        new = section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8", newline="\n")
    return created


def apply_copy_commands(target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, body in COMMAND_FILES.items():
        (target_dir / name).write_text(body, encoding="utf-8", newline="\n")
        written.append(target_dir / name)
    return written


# Claude Code passes the tool payload as JSON on stdin (not an env var). `check
# --hook-input` parses that itself, so the hook needs no shell and no second
# interpreter — it runs as-is on Windows, where bash and `python3` are absent.
# Keep this shell-free: no metacharacters, no marker comment (it would reach
# risqlet as argv). See tests in test_setup.py::TestHookIsPlatformIndependent.
SETUP_HOOK_COMMAND = "risqlet check --hook-input claude --json"
SETUP_HOOK_TOOLS = ["risqlet"]

# The command identifies itself; hooks from before the shell-free rewrite carry a
# trailing comment marker instead, which removal must still recognize.
LEGACY_HOOK_MARKER = "# risqlet:check"

VERIFY_TIMEOUT_S = 10
_VERIFY_PAYLOAD = '{"tool_input": {"file_path": ""}}'


def verify_setup_hook() -> list[str]:
    """Verify the setup check hook; returns a list of failure reasons (empty = ok).

    Runs the real command against a synthetic payload rather than syntax-checking
    a shell string: it proves the hook resolves, runs, and honors its exit-0
    contract — which subsumes what `bash -n` proved for the old shell hook.
    """
    fails = []
    for tool in SETUP_HOOK_TOOLS:
        if shutil.which(tool) is None:
            fails.append(f"{tool} not on PATH")
    if fails:
        return fails
    try:
        proc = subprocess.run(shlex.split(SETUP_HOOK_COMMAND), input=_VERIFY_PAYLOAD,
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=VERIFY_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        fails.append(f"hook did not finish within {VERIFY_TIMEOUT_S}s")
    except OSError as exc:
        fails.append(f"hook could not run: {exc}")
    else:
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:120]
            fails.append(f"hook exited {proc.returncode}"
                         + (f": {detail}" if detail else ""))
    return fails


def _is_risqlet_hook(hook: dict) -> bool:
    command = hook.get("command", "")
    return HOOK_MARKER in command or LEGACY_HOOK_MARKER in command


def apply_json_hooks(path: Path) -> None:
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    data = json.loads(raw) if raw.strip() else {}
    hooks = data.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])
    # drop any hook of ours first (including a pre-rewrite shell one), so an
    # upgrade replaces rather than leaving a stale hook beside the new one
    _drop_risqlet_hooks(post)
    post.append({"matcher": "Write|Edit", "hooks": [{
        "type": "command", "command": SETUP_HOOK_COMMAND}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def _drop_risqlet_hooks(entries: list) -> None:
    """Strip our hooks from one event's entries, leaving the user's untouched."""
    for entry in entries:
        entry["hooks"] = [h for h in entry.get("hooks", []) if not _is_risqlet_hook(h)]
    entries[:] = [e for e in entries if e.get("hooks")]


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
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return
    data = json.loads(_strip_jsonc(raw) if jsonc else raw)
    if key in data and isinstance(data[key], dict):
        data[key].pop("risqlet", None)
        if not data[key]:
            del data[key]
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    else:
        path.unlink()


def remove_toml_merge(path: Path) -> None:
    if not path.exists():
        return
    new = _strip_block(path.read_text(encoding="utf-8"), TOML_BEGIN, TOML_END)
    if new.strip():
        path.write_text(new, encoding="utf-8", newline="\n")
    else:
        path.unlink()


def remove_md_section(path: Path, created: bool) -> None:
    if not path.exists():
        return
    new = _strip_block(read_text_tolerant(path), MD_BEGIN, MD_END)
    if created and not new.strip():
        path.unlink()
    else:
        path.write_text(new, encoding="utf-8", newline="\n")


def remove_json_hooks(path: Path) -> None:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    for event in list(hooks):
        _drop_risqlet_hooks(hooks[event])
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    else:
        path.unlink()
