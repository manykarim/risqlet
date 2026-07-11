"""Risk status state machine and human-principal gates.

Files are the source of truth for *content*; events.jsonl is the source of
truth for *who authorized transitions*. Agents may freely create and edit
risks in ``proposed`` status; every step beyond that — and every workflow
phase change — must replay from an event authored by a ``human:`` principal.
"""

from __future__ import annotations

from risqlet.findings import Finding, Severity
from risqlet.model import EventType, Phase, Status

LEGAL_TRANSITIONS: dict[str, set[str]] = {
    Status.PROPOSED: {Status.REVIEWED, Status.REJECTED},
    Status.REVIEWED: {Status.ACCEPTED, Status.REJECTED},
    Status.ACCEPTED: {Status.MITIGATING},
    Status.MITIGATING: {Status.CLOSED},
    Status.CLOSED: set(),
    Status.REJECTED: set(),
}

EVENTS_FILE_LABEL = ".risqlet/events.jsonl"


def _is_human(principal: str) -> bool:
    return isinstance(principal, str) and principal.startswith("human:")


def check_events(events: list[tuple[int, dict]]) -> list[Finding]:
    """Structural checks on the raw event stream (principals, transition legality)."""
    findings: list[Finding] = []
    for lineno, raw in events:
        where = f"{EVENTS_FILE_LABEL}:{lineno}"
        etype = raw.get("type")
        if etype not in (EventType.STATUS_CHANGE, EventType.PHASE_CHANGE):
            findings.append(
                Finding(Severity.ERROR, where, "type", f"unknown event type {etype!r}")
            )
            continue
        principal = raw.get("principal", "")
        if not _is_human(principal):
            findings.append(
                Finding(
                    Severity.ERROR,
                    where,
                    "principal",
                    f"transitions require a human principal, got {principal!r}",
                )
            )
        if etype == EventType.STATUS_CHANGE:
            src, dst = raw.get("from"), raw.get("to")
            if src not in LEGAL_TRANSITIONS or dst not in LEGAL_TRANSITIONS.get(src, set()):
                findings.append(
                    Finding(
                        Severity.ERROR,
                        where,
                        "from/to",
                        f"illegal status transition {src!r} -> {dst!r}",
                    )
                )
            if not raw.get("risk"):
                findings.append(
                    Finding(Severity.ERROR, where, "risk", "status_change event missing risk id")
                )
        else:
            valid_phases = {p.value for p in Phase}
            for key in ("from", "to"):
                if raw.get(key) not in valid_phases:
                    findings.append(
                        Finding(
                            Severity.ERROR, where, key, f"unknown phase {raw.get(key)!r}"
                        )
                    )
    return findings


def replay_status(risk_id: str, events: list[tuple[int, dict]]) -> str:
    """Fold status_change events for one risk from the initial ``proposed`` state."""
    status = Status.PROPOSED.value
    for _lineno, raw in events:
        if raw.get("type") == EventType.STATUS_CHANGE and raw.get("risk") == risk_id:
            if raw.get("from") == status:
                status = raw.get("to", status)
            # mismatched "from" is reported by check_risk_consistency below
    return status


def check_risk_consistency(
    risk_id: str, file_status: str, file_label: str, events: list[tuple[int, dict]]
) -> list[Finding]:
    """The event history for a risk must replay exactly to the status in its file."""
    findings: list[Finding] = []
    status = Status.PROPOSED.value
    for lineno, raw in events:
        if raw.get("type") != EventType.STATUS_CHANGE or raw.get("risk") != risk_id:
            continue
        if raw.get("from") != status:
            findings.append(
                Finding(
                    Severity.ERROR,
                    f"{EVENTS_FILE_LABEL}:{lineno}",
                    "from",
                    f"{risk_id}: event claims transition from {raw.get('from')!r} "
                    f"but replayed status is {status!r}",
                )
            )
        status = raw.get("to", status)
    if status != file_status:
        findings.append(
            Finding(
                Severity.ERROR,
                file_label,
                "status",
                f"{risk_id}: file status {file_status!r} does not match event replay "
                f"{status!r} — transitions beyond 'proposed' require recorded "
                f"human-principal events",
            )
        )
    return findings


def check_phase_consistency(
    config_phase: str, events: list[tuple[int, dict]]
) -> list[Finding]:
    """config.yaml's phase must replay from ``context`` via phase_change events."""
    phase = Phase.CONTEXT.value
    findings: list[Finding] = []
    for lineno, raw in events:
        if raw.get("type") != EventType.PHASE_CHANGE:
            continue
        if raw.get("from") != phase:
            findings.append(
                Finding(
                    Severity.ERROR,
                    f"{EVENTS_FILE_LABEL}:{lineno}",
                    "from",
                    f"phase event claims transition from {raw.get('from')!r} "
                    f"but replayed phase is {phase!r}",
                )
            )
        phase = raw.get("to", phase)
    if phase != config_phase:
        findings.append(
            Finding(
                Severity.ERROR,
                ".risqlet/config.yaml",
                "phase",
                f"config phase {config_phase!r} does not match event replay {phase!r} "
                f"— phase changes require recorded human-principal events",
            )
        )
    return findings
