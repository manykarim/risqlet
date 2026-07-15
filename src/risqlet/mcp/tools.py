"""MCP tool functions — plain, fully testable, no `mcp` import.

Framework-provider contract: these functions return structure, validation
results, and guidance text; all semantic analysis happens in the client LLM.
Every function is stateless and takes an explicit ``project_dir``; all state
lives in that project's ``.risqlet/`` files.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from risqlet.catalog import CatalogError, load_available, resolve_entry
from risqlet.catalog import search as catalog_search
from risqlet.exports.renderers import FORMATS, ExportError, render
from risqlet.model import Event, Mitigation, Risk, Status
from risqlet.scoring import score_risks as _score_risks
from risqlet.skills import skills_root
from risqlet.store import RiskFile, Store, StoreError, find_register, init_register
from risqlet.validate import validate_register


class ToolError(Exception):
    """Raised with an actionable message; server wiring maps it to an MCP error."""


def _store(project_dir: str) -> Store:
    try:
        return Store(find_register(explicit=Path(project_dir)))
    except StoreError as exc:
        raise ToolError(f"{exc} — call init_register first") from exc


# -- core (CLI mirrors) --------------------------------------------------------

def tool_init_register(project_dir: str, project_name: str | None = None) -> dict:
    try:
        risqlet = init_register(Path(project_dir), project_name)
    except StoreError as exc:
        raise ToolError(str(exc)) from exc
    return {"created": str(risqlet)}


def tool_validate_register(project_dir: str) -> dict:
    return validate_register(_store(project_dir)).to_dict()


def tool_score_risks(project_dir: str, risk_id: str | None = None) -> dict:
    updated, findings = _score_risks(_store(project_dir), risk_id)
    return {"updated": updated, "findings": [f.to_dict() for f in findings]}


def tool_export_register(project_dir: str, fmt: str) -> dict:
    try:
        content = render(_store(project_dir), fmt)
    except ExportError as exc:
        raise ToolError(str(exc)) from exc
    return {"format": fmt, "content": content}


# -- catalog and guidance ------------------------------------------------------

def tool_browse_catalog(
    project_dir: str | None = None,
    action: str = "list",
    pack: str | None = None,
    entry_id: str | None = None,
    terms: list[str] | None = None,
) -> dict:
    store = None
    if project_dir:
        try:
            store = _store(project_dir)
        except ToolError:
            store = None  # packaged packs still available without a register
    try:
        packs = load_available(store)
    except CatalogError as exc:
        raise ToolError(str(exc)) from exc

    if action == "list":
        if pack is not None:
            if pack not in packs:
                raise ToolError(f"no catalog pack named {pack!r} "
                                f"(available: {', '.join(sorted(packs))})")
            packs = {pack: packs[pack]}
        return {
            "entries": [
                {"id": f"{p.id}.{e.slug}", "kind": str(e.kind), "summary": e.summary}
                for p in packs.values() for e in p.entries
            ]
        }
    if action == "show":
        if not entry_id:
            raise ToolError("action 'show' requires entry_id (e.g. techniques.stress-testing)")
        entry = resolve_entry(entry_id, packs)
        if entry is None:
            raise ToolError(f"no catalog entry {entry_id!r}")
        return {"id": entry_id, **entry.model_dump(mode="json")}
    if action == "search":
        if not terms:
            raise ToolError("action 'search' requires terms")
        return {
            "results": [
                {"id": rid, "summary": e.summary, "hits": hits}
                for rid, e, hits in catalog_search(packs, terms)
            ]
        }
    raise ToolError(f"unknown action {action!r} (list | show | search)")


GUIDANCE_TOPICS = {
    "overview": ("risk-analysis", "SKILL.md"),
    "phases": ("risk-analysis", "references/phases.md"),
    "elicitation": ("risk-analysis", "references/elicitation.md"),
    "scoring": ("risk-analysis", "references/scoring-rubrics.md"),
    "risk-writing": ("risk-analysis", "references/risk-writing.md"),
    "mitigation": ("risk-analysis", "references/mitigation.md"),
    "quickscan": ("risk-quickscan", "SKILL.md"),
}


def tool_get_guidance(topic: str) -> dict:
    if topic not in GUIDANCE_TOPICS:
        raise ToolError(
            f"unknown topic {topic!r} (valid: {', '.join(sorted(GUIDANCE_TOPICS))})"
        )
    skill, relative = GUIDANCE_TOPICS[topic]
    return {"topic": topic,
            "content": (skills_root() / skill / relative).read_text(encoding="utf-8")}


# -- register writes (gate-preserving) ----------------------------------------

def tool_upsert_risk(
    project_dir: str,
    statement: str,
    aspects: list[str],
    elicited_by: dict,
    risk_id: str | None = None,
    scores: list[dict] | None = None,
    **extra,
) -> dict:
    if "status" in extra or (scores and any("derived" in s for s in scores)):
        raise ToolError(
            "upsert_risk writes 'proposed' risks only: do not pass status or "
            "derived values — statuses change via record_decision, priorities "
            "via score_risks"
        )
    if extra:
        raise ToolError(f"unknown fields: {', '.join(sorted(extra))}")
    store = _store(project_dir)

    existing = None
    if risk_id is not None:
        for candidate in store.load_risk_files():
            if candidate.data.get("id") == risk_id:
                existing = candidate
                break
        if existing is None:
            raise ToolError(f"no risk with id {risk_id} (omit risk_id to create)")
        if existing.data.get("status", "proposed") != Status.PROPOSED:
            raise ToolError(
                f"{risk_id} is {existing.data.get('status')!r}; only 'proposed' risks "
                f"may be edited via upsert_risk"
            )
    new_id = risk_id or store.next_risk_id()
    payload = {
        "schema_version": 1,
        "id": new_id,
        "statement": statement,
        "aspects": aspects,
        "elicited_by": elicited_by,
        "scores": scores or [],
        "status": "proposed",
        "mitigations": (existing.data.get("mitigations") if existing else []) or [],
    }
    try:
        risk = Risk.model_validate(payload)
    except ValidationError as exc:
        raise ToolError(f"invalid risk: {exc}") from exc

    if existing is not None:
        for key in ("statement", "aspects", "elicited_by", "scores"):
            existing.data[key] = payload[key]
        store.save_risk(existing)
        path = existing.path
    else:
        path = store.register_dir / f"{new_id}.yaml"
        store.save_risk(RiskFile(path=path, data=risk.model_dump(mode="json")))
    warnings = [
        f.to_dict() for f in validate_register(store).findings
        if f.file.endswith(path.name)
    ]
    return {"id": new_id, "path": str(path), "warnings": warnings}


def tool_add_mitigation(
    project_dir: str,
    risk_id: str,
    treatment: str,
    lever: str,
    barrier: str,
    concrete: str,
    residual_note: str,
    technique_ref: str = "",
    tests: list[str] | None = None,
) -> dict:
    store = _store(project_dir)
    target = None
    for candidate in store.load_risk_files():
        if candidate.data.get("id") == risk_id:
            target = candidate
            break
    if target is None:
        raise ToolError(f"no risk with id {risk_id}")
    mitigation_id = store.next_mitigation_id()
    payload = {
        "id": mitigation_id,
        "risk_ids": [risk_id],
        "treatment": treatment,
        "lever": lever,
        "barrier": barrier,
        "technique_ref": technique_ref,
        "concrete": concrete,
        "residual_note": residual_note,
        "tests": tests or [],
    }
    try:
        Mitigation.model_validate(payload)
    except ValidationError as exc:
        raise ToolError(f"invalid mitigation: {exc}") from exc
    mitigations = target.data.get("mitigations")
    if mitigations is None:
        target.data["mitigations"] = mitigations = []
    mitigations.append(payload)
    store.save_risk(target)
    return {"id": mitigation_id, "risk_id": risk_id}


def tool_record_decision(
    project_dir: str,
    type: str,  # noqa: A002 - mirrors the event schema field
    from_state: str,
    to_state: str,
    principal: str,
    note: str = "",
    risk_id: str | None = None,
    ts: str | None = None,
) -> dict:
    if not principal.startswith("human:"):
        raise ToolError(
            "decisions require a human principal (human:<name>). Record this only "
            "after the human explicitly confirmed in conversation."
        )
    if type == "status_change" and not risk_id:
        raise ToolError("status_change requires risk_id")
    store = _store(project_dir)
    if ts is None:
        from datetime import UTC, datetime

        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        event = Event.model_validate({
            "ts": ts, "type": type, "risk": risk_id,
            "from": from_state, "to": to_state,
            "principal": principal, "note": note,
        })
    except ValidationError as exc:
        raise ToolError(f"invalid event: {exc}") from exc
    store.append_event(event)

    # mechanical pair: keep the file state in sync with the recorded decision
    if type == "status_change":
        for candidate in store.load_risk_files():
            if candidate.data.get("id") == risk_id:
                candidate.data["status"] = to_state
                store.save_risk(candidate)
                break
    elif type == "phase_change":
        config = store.load_config_raw()
        config["phase"] = to_state
        store.save_config_raw(config)

    return {"recorded": True, "validate": validate_register(store).to_dict()}


ALL_TOOLS = {
    "init_register": tool_init_register,
    "validate_register": tool_validate_register,
    "score_risks": tool_score_risks,
    "export_register": tool_export_register,
    "browse_catalog": tool_browse_catalog,
    "get_guidance": tool_get_guidance,
    "upsert_risk": tool_upsert_risk,
    "add_mitigation": tool_add_mitigation,
    "record_decision": tool_record_decision,
}

EXPORT_FORMATS = FORMATS
