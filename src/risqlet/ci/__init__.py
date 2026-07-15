"""CI template emission for risqlet continuous re-assessment."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class CIError(Exception):
    pass


# target -> (template filename, conventional output path, prints-only)
TARGETS = {
    "github": ("github.yml", ".github/workflows/risqlet.yml", False),
    "gitlab": ("gitlab.yml", ".gitlab-ci.risqlet.yml", False),
    "claude-hooks": ("claude-hooks.json", None, True),
}


def templates_root() -> Path:
    if TEMPLATES_DIR.is_dir():
        return TEMPLATES_DIR
    raise CIError("no bundled CI templates found")


def template_text(target: str) -> str:
    if target not in TARGETS:
        raise CIError(f"unknown target {target!r}")
    return (templates_root() / TARGETS[target][0]).read_text(encoding="utf-8")


def init(target: str, project_dir: Path, explicit_path: Path | None = None,
         force: bool = False) -> dict:
    """Write (or, for claude-hooks, return) the template. Returns a result dict."""
    if target in TARGETS:
        filename, conventional, prints_only = TARGETS[target]
        text = template_text(target)
        if prints_only:
            return {"target": target, "content": text, "printed": True}
        dest = explicit_path or (project_dir / conventional)
        return _write(dest, text, force)

    # arbitrary path target: only if it actually looks like a path
    if "/" not in target and "\\" not in target and not Path(target).suffix:
        raise CIError(
            f"unknown target {target!r} (github | gitlab | claude-hooks | a file path)"
        )
    dest = Path(target).expanduser()
    text = template_text("gitlab" if dest.suffix in (".yml", ".yaml") else "github")
    return _write(dest, text, force)


def _write(dest: Path, text: str, force: bool) -> dict:
    if dest.exists() and not force:
        raise CIError(f"{dest} already exists (use --force to overwrite)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")
    return {"written": str(dest), "printed": False}
