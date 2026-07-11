"""Skill discovery and installation.

Canonical skills live in the repo's ``skills/`` directory and ship in the
wheel as package data (``risqlet/data/skills``). They are plain cross-vendor
Agent Skills (SKILL.md + frontmatter); installation is just a copy — the
target platform handles discovery.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML


class SkillsError(Exception):
    pass


def skills_root() -> Path:
    package_data = Path(__file__).resolve().parent / "data" / "skills"
    if package_data.is_dir():
        return package_data
    repo_root = Path(__file__).resolve().parents[2] / "skills"
    if repo_root.is_dir():
        return repo_root
    raise SkillsError("no bundled skills found (package data or repo skills/)")


@dataclass
class SkillInfo:
    name: str
    description: str
    path: Path


def _parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text()
    if not text.startswith("---"):
        raise SkillsError(f"{skill_md}: missing YAML frontmatter")
    try:
        _, block, _rest = text.split("---", 2)
    except ValueError as exc:
        raise SkillsError(f"{skill_md}: unterminated frontmatter") from exc
    data = YAML(typ="safe").load(block) or {}
    if not data.get("name") or not data.get("description"):
        raise SkillsError(f"{skill_md}: frontmatter needs name and description")
    return data


def list_skills() -> list[SkillInfo]:
    out = []
    for directory in sorted(skills_root().iterdir()):
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = _parse_frontmatter(skill_md)
        out.append(
            SkillInfo(
                name=str(meta["name"]),
                description=" ".join(str(meta["description"]).split()),
                path=directory,
            )
        )
    return out


TARGET_ALIASES = {
    "claude-project": Path(".claude/skills"),
    "claude-user": Path("~/.claude/skills"),
}


def resolve_target(target: str) -> Path:
    return TARGET_ALIASES.get(target, Path(target)).expanduser()


def install(
    names: list[str] | None, target: str, force: bool = False
) -> list[tuple[str, Path]]:
    available = {s.name: s for s in list_skills()}
    if names:
        unknown = [n for n in names if n not in available]
        if unknown:
            raise SkillsError(
                f"unknown skill(s): {', '.join(unknown)} "
                f"(available: {', '.join(sorted(available))})"
            )
        chosen = [available[n] for n in names]
    else:
        chosen = list(available.values())

    target_dir = resolve_target(target)
    conflicts = [s.name for s in chosen if (target_dir / s.name).exists()]
    if conflicts and not force:
        raise SkillsError(
            f"already installed at {target_dir}: {', '.join(conflicts)} "
            f"(use --force to overwrite)"
        )
    installed = []
    for skill in chosen:
        destination = target_dir / skill.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(skill.path, destination)
        installed.append((skill.name, destination))
    return installed
