"""Setup engine: detect, plan, apply, remove, update, status.

Orchestrates the existing installers (skills, ci hooks) plus per-agent config
writes, all marker-scoped and recorded in a manifest so removal is exact and
never touches a user's own config.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ruamel.yaml import YAML

from risqlet import __version__
from risqlet.setup import render
from risqlet.setup.models import (
    AgentAdapter,
    Manifest,
    ManifestEntry,
    Plan,
    PlannedAction,
    Scope,
    SkippedItem,
)

ADAPTERS_DIR = Path(__file__).resolve().parent / "adapters"
MANIFEST_NAME = "agents.lock"
SKILL_NAMES = ["risk-analysis", "risk-quickscan"]


class SetupError(Exception):
    pass


def load_adapters() -> dict[str, AgentAdapter]:
    yaml = YAML(typ="safe")
    out = {}
    for path in sorted(ADAPTERS_DIR.glob("*.yaml")):
        out[path.stem] = AgentAdapter.model_validate(yaml.load(path.read_text()))
    return out


def detect(adapters: dict[str, AgentAdapter]) -> list[str]:
    found = []
    for aid, ad in adapters.items():
        binary = bool(ad.detect.binary) and shutil.which(ad.detect.binary) is not None
        dirs = any(Path(d).expanduser().exists() for d in ad.detect.dirs)
        if binary or dirs:
            found.append(aid)
    return found


def _marker(method: str, key: str) -> str:
    if method in ("json-merge", "jsonc-merge"):
        return f"{key}.risqlet"
    if method == "toml-merge":
        return "mcp_servers.risqlet"
    if method == "md-section":
        return "risqlet:setup"
    if method == "json-hooks":
        return render.HOOK_MARKER
    return ""


def build_plan(adapters: dict[str, AgentAdapter], agent_ids: list[str], scope: str,
               components: list[str] | None, project_root: Path) -> Plan:
    plan = Plan(scope=scope)
    for aid in agent_ids:
        ad = adapters.get(aid)
        if ad is None:
            raise SetupError(f"unknown agent {aid!r} (known: {', '.join(sorted(adapters))})")
        requested = components or list(ad.components)
        for comp in requested:
            spec = ad.components.get(comp)
            if spec is None:
                if components:  # only note explicit requests the agent can't do
                    plan.skipped.append(SkippedItem(
                        agent=aid, component=comp, reason="not supported by this agent"))
                continue
            if scope not in spec.scopes:
                other = "global" if scope == Scope.PROJECT else "project"
                reason = spec.note or (
                    f"{comp} for {ad.name} is {other}-only — run with --scope {other}")
                plan.skipped.append(SkippedItem(agent=aid, component=comp, reason=reason))
                continue
            target = render.expand(spec.path_for(scope), project_root)
            plan.actions.append(PlannedAction(
                agent=aid, component=comp, scope=scope, target=str(target),
                method=spec.method, key=spec.key, marker=_marker(spec.method, spec.key)))
    return plan


# -- apply ---------------------------------------------------------------------

def _apply_action(action: PlannedAction, force: bool) -> ManifestEntry:
    from risqlet.skills import install as skills_install

    path = Path(action.target)
    created = not path.exists()
    m = action.method
    if m == "json-merge":
        render.apply_json_merge(path, action.key, jsonc=False)
    elif m == "jsonc-merge":
        render.apply_json_merge(path, action.key, jsonc=True)
    elif m == "toml-merge":
        render.apply_toml_merge(path)
    elif m == "md-section":
        created = render.apply_md_section(path)
    elif m == "json-hooks":
        render.apply_json_hooks(path)
    elif m == "copy-skills":
        skills_install(None, str(path), force=True)
    elif m == "copy-commands":
        render.apply_copy_commands(path)
    else:
        raise SetupError(f"unknown method {m!r}")
    return ManifestEntry(
        agent=action.agent, component=action.component, scope=action.scope,
        target=action.target, method=m, key=action.key, marker=action.marker,
        created_file=created)


def manifest_path(scope: str, project_root: Path) -> Path:
    root = Path("~/.risqlet").expanduser() if scope == Scope.GLOBAL else project_root / ".risqlet"
    return root / MANIFEST_NAME


def read_manifest(scope: str, project_root: Path) -> Manifest:
    path = manifest_path(scope, project_root)
    if not path.exists():
        return Manifest()
    return Manifest.model_validate_json(path.read_text())


def write_manifest(scope: str, project_root: Path, manifest: Manifest) -> None:
    path = manifest_path(scope, project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.model_dump(), indent=2) + "\n")


def _merge_manifest(existing: Manifest, new_entries: list[ManifestEntry],
                    agents: list[str]) -> Manifest:
    # drop prior entries for the agents we just (re)installed, then add fresh ones
    kept = [e for e in existing.entries if e.agent not in agents]
    return Manifest(risqlet_version=__version__, entries=kept + new_entries)


def apply_plan(plan: Plan, project_root: Path, force: bool = False,
               verify: bool = True) -> dict:
    # verify hook components in the target environment before writing them
    hook_skips = []
    actions = []
    if verify:
        fails = render.verify_setup_hook()
    else:
        fails = []
    for a in plan.actions:
        if a.method == "json-hooks" and fails and not force:
            hook_skips.append({"agent": a.agent, "component": a.component,
                               "reason": "hook failed verification: " + "; ".join(fails)})
            continue
        actions.append(a)
    entries = [_apply_action(a, force) for a in actions]
    existing = read_manifest(plan.scope, project_root)
    agents = sorted({a.agent for a in actions})
    write_manifest(plan.scope, project_root, _merge_manifest(existing, entries, agents))
    return {"installed": len(entries), "agents": agents, "scope": plan.scope,
            "skipped": [s.model_dump() for s in plan.skipped] + hook_skips}


# -- remove --------------------------------------------------------------------

def remove(scope: str, project_root: Path, agent_ids: list[str] | None = None) -> dict:
    manifest = read_manifest(scope, project_root)
    to_remove = [e for e in manifest.entries
                 if agent_ids is None or e.agent in agent_ids]
    remaining = [e for e in manifest.entries if e not in to_remove]

    for e in to_remove:
        path = Path(e.target)
        m = e.method
        # refcount: a shared config file/key kept if another remaining entry uses it
        shared = any(r.target == e.target and r.key == e.key and r.method == m
                     for r in remaining)
        if m in ("json-merge", "jsonc-merge"):
            if not shared:
                render.remove_json_merge(path, e.key, jsonc=(m == "jsonc-merge"))
        elif m == "toml-merge":
            if not shared:
                render.remove_toml_merge(path)
        elif m == "md-section":
            if not shared:
                render.remove_md_section(path, e.created_file)
        elif m == "json-hooks":
            render.remove_json_hooks(path)
        elif m == "copy-skills":
            for name in SKILL_NAMES:
                d = path / name
                if d.exists():
                    shutil.rmtree(d)
            if path.exists() and not any(path.iterdir()):
                path.rmdir()
        elif m == "copy-commands":
            for name in render.COMMAND_FILES:
                f = path / name
                if f.exists():
                    f.unlink()

    write_manifest(scope, project_root,
                   Manifest(risqlet_version=__version__, entries=remaining))
    return {"removed": len(to_remove), "remaining": len(remaining), "scope": scope}


def status(scope: str, project_root: Path) -> dict:
    manifest = read_manifest(scope, project_root)
    by_agent: dict[str, list[dict]] = {}
    for e in manifest.entries:
        by_agent.setdefault(e.agent, []).append(
            {"component": e.component, "scope": e.scope, "target": e.target})
    return {"scope": scope, "risqlet_version": manifest.risqlet_version,
            "agents": by_agent}
