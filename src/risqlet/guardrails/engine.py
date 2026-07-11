"""Guardrail selection, rendering, diff, and install.

Divergence-to-LLM, convergence-to-code applies here too: the *what to guard*
comes from the human-reviewed register; the *how* is deterministic selection
and parameterization of vetted templates. Guardrails live in the target
project's agent-config files, never in ``.risqlet/``; nothing here mutates the
register, and ``risqlet validate`` is unaffected.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from risqlet.changeset import _components  # noqa: PLC2701 (shared path helper)
from risqlet.ensemble import evidence_path
from risqlet.guardrails.models import GuardrailTemplate, RenderedGuardrail
from risqlet.model import Risk, Status
from risqlet.store import Store

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
LOCK_FILE = ".risqlet-guardrails.lock.json"
HIGH_SEVERITY = 8  # sod-ap-v1 severity >= this (or li impact == 3) is "high"

# Claude Code delivers the tool payload as JSON on stdin (not an env var);
# pull out the changed file path into a variable the hook command can use.
CLAUDE_FILE_FROM_STDIN = (
    "python3 -c 'import json,sys;"
    'print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))\' 2>/dev/null'
)

_ACCEPTED = {Status.ACCEPTED.value, Status.MITIGATING.value}


class GuardrailError(Exception):
    pass


def load_templates() -> list[GuardrailTemplate]:
    yaml = YAML(typ="safe")
    out = []
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        try:
            out.append(GuardrailTemplate.model_validate(yaml.load(path.read_text())))
        except ValidationError as exc:
            raise GuardrailError(f"{path.name}: invalid guardrail template: {exc}") from exc
    return out


def _strip_ref(ref: str) -> str:
    return (ref or "").split(":", 1)[0] if "." in (ref or "") else ""


def _evidence_dirs(risk: Risk) -> list[str]:
    dirs: set[str] = set()
    for item in risk.elicited_by.evidence:
        norm = evidence_path(item)
        parts = _components(norm)
        if not parts:
            continue
        # a file (has an extension) contributes its parent dir; a dir contributes itself
        if "." in parts[-1]:
            parent = "/".join(parts[:-1])
        else:
            parent = "/".join(parts)
        dirs.add(parent or ".")
    return sorted(dirs) or ["."]


def _matches(template: GuardrailTemplate, risk: Risk, mitigation, refs: set[str]) -> bool:
    if mitigation.barrier not in template.barriers:
        return False
    sel = template.selectors
    if sel.match_any:
        return True
    if set(risk.aspects) & set(sel.aspects):
        return True
    if refs & set(sel.catalog_refs):
        return True
    return False


def _high_severity(risk: Risk) -> bool:
    for score in risk.scores:
        if score.policy == "sod-ap-v1" and (score.values.get("severity") or 0) >= HIGH_SEVERITY:
            return True
        if score.policy == "li-v1" and (score.values.get("impact") or 0) >= 3:
            return True
    return False


def _detect_test_command(store: Store) -> str | None:
    root = store.root.parent
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() \
            or (root / "tests").is_dir():
        return "pytest -q"
    if (root / "package.json").exists():
        return "npm test"
    makefile = root / "Makefile"
    if makefile.exists() and re.search(r"^test:", makefile.read_text(), flags=re.M):
        return "make test"
    return None


def _render_text(text: str, dirs: list[str], test_command: str | None) -> str:
    # path globs use *dir/* so they match absolute paths agents pass ('.' -> '*')
    case = "|".join("*" if d == "." else f"*{d}/*" for d in dirs)
    text = text.replace("{{paths_case}}", case)
    text = text.replace("{{paths}}", " ".join(f"{d}/" for d in dirs))
    if test_command is not None:
        text = text.replace("{{test-command}}", test_command)
    return text


def _render(template: GuardrailTemplate, dirs: list[str],
            test_command: str | None = None) -> str:
    return _render_text(template.body, dirs, test_command).rstrip("\n")


@dataclass
class Plan:
    guardrails: list[RenderedGuardrail] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def by_surface(self) -> dict[str, list[RenderedGuardrail]]:
        out: dict[str, list[RenderedGuardrail]] = {}
        for g in self.guardrails:
            out.setdefault(g.surface, []).append(g)
        return out

    def to_dict(self) -> dict:
        return {
            "guardrails": [g.model_dump(mode="json") for g in self.guardrails],
            "advisories": self.advisories,
            "notes": self.notes,
            "summary": {
                "count": len(self.guardrails),
                "surfaces": sorted({g.surface for g in self.guardrails}),
                "hard": sum(1 for g in self.guardrails if g.enforcement == "hard"),
                "soft": sum(1 for g in self.guardrails if g.enforcement == "soft"),
            },
        }


def build_plan(store: Store, min_priority: str | None = None) -> Plan:
    templates = load_templates()
    config = store.load_config_raw() or {}
    if min_priority is None:
        min_priority = (config.get("constraints") or {}).get("guardrail_min_priority")

    risks: list[Risk] = []
    for rf in store.load_risk_files():
        try:
            risks.append(Risk.model_validate(rf.data))
        except ValidationError:
            continue

    deduped: dict[tuple, RenderedGuardrail] = {}
    per_risk: dict[str, list[RenderedGuardrail]] = {}
    plan_notes: list[str] = []

    for risk in sorted(risks, key=lambda r: r.id):
        if str(risk.status) not in _ACCEPTED:
            continue  # only human-reviewed risks earn guardrails
        refs = {_strip_ref(risk.elicited_by.prompt_ref)}
        dirs = _evidence_dirs(risk)
        for mitigation in risk.mitigations:
            refs_m = refs | {_strip_ref(mitigation.technique_ref)}
            refs_m.discard("")
            for template in templates:
                if not _matches(template, risk, mitigation, refs_m):
                    continue
                test_command = None
                if "test-command" in template.params:
                    test_command = _detect_test_command(store)
                    if test_command is None:
                        plan_notes.append(
                            f"{template.id} for {risk.id} skipped — no test command "
                            f"detected (declare one to enable this Stop guardrail)")
                        continue
                content = _render(template, dirs, test_command)
                command = (_render_text(template.command, dirs, test_command).strip()
                           if template.command else "")
                marker = f"risqlet:{risk.id}:{mitigation.barrier}:{template.id}"
                params = {"paths": dirs} if "paths" in template.params else {}
                rg = RenderedGuardrail(
                    template_id=template.id, surface=str(template.surface),
                    enforcement=str(template.enforcement), params=params,
                    content=content, markers=[marker], risks=[risk.id],
                    command=command, verify=template.verify,
                )
                key = rg.dedupe_key()
                if key in deduped:
                    existing = deduped[key]
                    if marker not in existing.markers:
                        existing.markers.append(marker)
                    if risk.id not in existing.risks:
                        existing.risks.append(risk.id)
                    per_risk.setdefault(risk.id, []).append(existing)
                else:
                    deduped[key] = rg
                    per_risk.setdefault(risk.id, []).append(rg)

    plan = Plan(
        guardrails=sorted(deduped.values(), key=lambda g: (g.surface, g.template_id)),
        notes=plan_notes)

    # honesty: a high-severity accepted risk covered only by soft guardrails is not enforced
    for risk in risks:
        if str(risk.status) not in _ACCEPTED or not _high_severity(risk):
            continue
        mine = per_risk.get(risk.id, [])
        if mine and all(g.enforcement == "soft" for g in mine):
            plan.advisories.append(
                f"{risk.id} is high-severity and accepted but covered only by advisory "
                f"(soft) guardrails — an AGENTS.md rule suggests, it does not enforce. "
                f"Add a hard hook/permission or accept the residual."
            )
    return plan


# -- install / diff -------------------------------------------------------------

BEGIN = "<!-- risqlet:guardrails:begin -->"
END = "<!-- risqlet:guardrails:end -->"


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _lock_path(root: Path) -> Path:
    return root / LOCK_FILE


def _read_lock(root: Path) -> list[dict]:
    path = _lock_path(root)
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _write_lock(root: Path, plan: Plan) -> None:
    entries = []
    for g in plan.guardrails:
        entries.append({
            "template_id": g.template_id, "surface": g.surface,
            "enforcement": g.enforcement, "markers": g.markers,
            "risks": g.risks, "hash": _content_hash(g.content),
        })
    _lock_path(root).write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")


def _render_section(plan: Plan) -> str:
    lines = [BEGIN, "## Risk guardrails (generated by risqlet — manage with `risqlet guardrails`)"]
    for g in plan.guardrails:
        lines.append("")
        lines.append(f"<!-- {' '.join(g.markers)} -->")
        lines.append(f"### {g.template_id} [{g.surface}/{g.enforcement}] — {', '.join(g.risks)}")
        lines.append(g.content)
    lines.append("")
    lines.append(END)
    return "\n".join(lines) + "\n"


def verify_plan(plan: Plan, cwd: Path) -> list:
    """Verify every executable (hook/pre-commit) guardrail in a plan."""
    from risqlet.guardrails.verify import verify_guardrail

    return [verify_guardrail(g, cwd) for g in plan.guardrails if g.verify is not None]


def _gate_by_verification(plan: Plan, cwd: Path, force: bool) -> tuple[Plan, list[dict]]:
    """Drop hooks that fail verification (unless force). Returns (gated_plan, skips)."""
    from dataclasses import replace

    results = {r.template_id: r for r in verify_plan(plan, cwd)}
    kept, skips = [], []
    for g in plan.guardrails:
        r = results.get(g.template_id)
        if r is None or r.ok:
            kept.append(g)
        elif force:
            kept.append(g)
            skips.append({"template_id": g.template_id, "forced": True,
                          "failed": [c.name for c in r.failed()]})
        else:
            skips.append({"template_id": g.template_id, "forced": False,
                          "failed": [c.name for c in r.failed()],
                          "detail": "; ".join(c.detail for c in r.failed() if c.detail)})
    return replace(plan, guardrails=kept), skips


def install_plan(store: Store, plan: Plan, target: str, root: Path,
                 force: bool = False, verify: bool = True) -> dict:
    """Write guardrails for a surface/target. Never writes under .risqlet/.

    For live-hook targets (claude-project, pre-commit) each hook is verified in
    the target environment first; a hook that fails is skipped unless force.
    """
    root = root.resolve()
    if ".risqlet" in root.parts:
        raise GuardrailError("guardrails must not be installed inside a .risqlet/ register")

    verify_skips: list[dict] = []
    if verify and target in ("claude-project", "pre-commit"):
        plan, verify_skips = _gate_by_verification(plan, root, force)

    if target in ("agents-md", "path", "pre-commit"):
        dest = (
            root / "AGENTS.md" if target == "agents-md"
            else root if target == "path" and root.suffix
            else root / ("guardrails.md" if target == "path" else "risqlet-guardrails.md")
        )
        section = _render_section(plan)
        existing = dest.read_text() if dest.exists() else ""
        if BEGIN in existing and END in existing:
            # replace the managed section in place; everything else is preserved
            pre = existing.split(BEGIN)[0]
            post = existing.split(END, 1)[1]
            new = pre.rstrip("\n") + ("\n\n" if pre.strip() else "") + section + post.lstrip("\n")
        elif target == "path" and existing.strip() and not force:
            # a standalone bundle file with foreign content — do not clobber without consent
            raise GuardrailError(f"{dest} exists and is not risqlet-managed — use --force")
        elif existing.strip():
            # append a clearly-delimited managed section, preserving the user's content
            new = existing.rstrip("\n") + "\n\n" + section
        else:
            new = section
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new)
        lock_root = dest.parent
    elif target == "claude-project":
        dest = _install_claude(root, plan, force)
        lock_root = root
    else:
        raise GuardrailError(
            f"unknown target {target!r} (agents-md | claude-project | pre-commit | a path)"
        )

    _write_lock(lock_root, plan)
    return {"target": target, "written": str(dest), "guardrails": len(plan.guardrails),
            "lock": str(_lock_path(lock_root)), "verify_skipped": verify_skips}


def _install_claude(root: Path, plan: Plan, force: bool) -> Path:
    settings = root / ".claude" / "settings.json"
    data = json.loads(settings.read_text()) if settings.exists() else {}
    # remove any previously risqlet-managed hooks (command carries a marker comment)
    hooks = data.get("hooks", {})
    for event in list(hooks):
        for entry in list(hooks[event]):
            entry.setdefault("hooks", [])
            entry["hooks"] = [h for h in entry["hooks"]
                              if "# risqlet:" not in h.get("command", "")]
        hooks[event] = [e for e in hooks[event] if e.get("hooks")]
        if not hooks[event]:
            del hooks[event]
    perms = data.setdefault("permissions", {})
    perms["deny"] = [d for d in perms.get("deny", []) if not str(d).startswith("Read(**/.env")]

    for g in plan.guardrails:
        if g.surface == "claude-hook" and g.command:
            marker = g.markers[0]
            file_input = g.verify is not None and g.verify.input == "file"
            # Claude Code passes the tool payload as JSON on stdin, NOT an env var —
            # extract tool_input.file_path into RISQLET_HOOK_FILE (empty => hook no-ops safely)
            prefix = (f"RISQLET_HOOK_FILE=\"$({CLAUDE_FILE_FROM_STDIN})\"; "
                      if file_input else "")
            command = f"{prefix}{g.command}  # {marker}"
            if file_input:  # PostToolUse on writes
                hooks.setdefault("PostToolUse", []).append({
                    "matcher": "Write|Edit",
                    "hooks": [{"type": "command", "command": command}]})
            else:  # Stop-style hook (no file input)
                hooks.setdefault("Stop", []).append({
                    "hooks": [{"type": "command", "command": command}]})
        elif g.surface == "claude-permission":
            perms.setdefault("deny", []).extend(
                ["Read(**/.env)", "Read(**/.env.*)"])
    if hooks:
        data["hooks"] = hooks
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return settings


def diff_target(store: Store, root: Path, min_priority: str | None = None) -> dict:
    plan = build_plan(store, min_priority)
    plan_by_marker = {}
    for g in plan.guardrails:
        for m in g.markers:
            plan_by_marker[m] = g
    lock = _read_lock(root.resolve())
    lock_markers = {m: e for e in lock for m in e["markers"]}

    stale, missing, drift = [], [], []
    for marker, g in plan_by_marker.items():
        if marker not in lock_markers:
            missing.append(marker)
        elif lock_markers[marker]["hash"] != _content_hash(g.content):
            drift.append(marker)
    for marker in lock_markers:
        if marker not in plan_by_marker:
            stale.append(marker)
    return {"stale": sorted(stale), "missing": sorted(missing), "drift": sorted(drift)}
