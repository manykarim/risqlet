"""`risqlet status` — read-only session-state projection for resuming work.

Must succeed on messy mid-session registers: schema-invalid files are named,
not fatal. Validation stays `risqlet validate`'s job; this is a view.
"""

from __future__ import annotations

from pydantic import ValidationError

from risqlet.model import Risk, Status
from risqlet.policies.engine import PolicyError, load_policy
from risqlet.store import Store

TERMINAL = {Status.CLOSED.value, Status.REJECTED.value}
NEEDS_MITIGATION = {Status.ACCEPTED.value, Status.MITIGATING.value}


def build_status(store: Store) -> dict:
    config = store.load_config_raw() or {}
    policy_id = config.get("scoring_policy", "sod-ap-v1")
    try:
        policy = load_policy(policy_id, user_dir=store.user_policies_dir)
    except PolicyError:
        policy = None

    risks: list[Risk] = []
    invalid_files: list[str] = []
    for risk_file in store.load_risk_files():
        try:
            risks.append(Risk.model_validate(risk_file.data))
        except ValidationError:
            invalid_files.append(risk_file.path.name)

    counts: dict[str, int] = {}
    for risk in risks:
        counts[str(risk.status)] = counts.get(str(risk.status), 0) + 1

    open_risks = [r for r in risks if str(r.status) not in TERMINAL]

    def has_derived(risk: Risk) -> bool:
        return any(s.policy == policy_id and s.derived for s in risk.scores)

    scored = [r for r in open_risks if has_derived(r)]
    unscored = [r for r in open_risks if not has_derived(r)]

    needing = [r for r in risks if str(r.status) in NEEDS_MITIGATION]
    uncovered = [r.id for r in needing if not r.mitigations]

    def rank_key(risk: Risk):
        if policy is not None:
            for score in risk.scores:
                if score.policy == policy_id and score.derived:
                    return (0, policy.rank_key(dict(score.derived)), risk.id)
        return (1, (), risk.id)

    cap = int((config.get("constraints") or {}).get("max_top_risks") or 10)
    top = sorted(open_risks, key=rank_key)[:cap]

    def priority_of(risk: Risk) -> str:
        for score in risk.scores:
            if score.policy == policy_id and score.derived:
                return ", ".join(f"{k}={v}" for k, v in sorted(dict(score.derived).items()))
        return "unscored"

    events = []
    try:
        events = store.read_events()
    except Exception:
        invalid_files.append("events.jsonl")
    last_event = None
    if events:
        _lineno, raw = events[-1]
        last_event = {"ts": raw.get("ts"), "type": raw.get("type"),
                      "principal": raw.get("principal")}

    phase = config.get("phase", "context")
    aspects = [{"rank": a.get("rank"), "id": a.get("id")}
               for a in sorted(config.get("aspects") or [], key=lambda a: a.get("rank", 0))]

    pending: list[str] = []
    if phase == "aspects" and not aspects:
        pending.append("phase is 'aspects' but no quality aspects are selected yet")
    if phase in ("elicit", "score", "mitigate", "emit") and not risks:
        pending.append(f"phase is '{phase}' but the register holds no risks")
    reviewed_unscored = [r.id for r in unscored if str(r.status) == Status.REVIEWED.value]
    if reviewed_unscored:
        pending.append(
            f"{len(reviewed_unscored)} reviewed risk(s) await scoring: "
            f"{', '.join(sorted(reviewed_unscored))}"
        )
    if uncovered:
        pending.append(
            f"{len(uncovered)} accepted/mitigating risk(s) lack mitigations: "
            f"{', '.join(sorted(uncovered))}"
        )
    if phase == "emit" and not (store.root / "strategy.md").exists():
        pending.append("phase is 'emit' but .risqlet/strategy.md has not been exported")
    if invalid_files:
        pending.append(f"unparseable file(s): {', '.join(sorted(set(invalid_files)))}")
    from risqlet.trace import mitigation_state, read_results

    trace_results = read_results(store)
    if trace_results:
        failing = []
        for risk in risks:
            if str(risk.status) not in ("accepted", "mitigating"):
                continue
            if any(mitigation_state(m.model_dump(mode="json"), trace_results) == "covered-failing"
                   for m in risk.mitigations):
                failing.append(risk.id)
        if failing:
            pending.append(
                f"{len(failing)} risk(s) have failing mitigation tests: "
                f"{', '.join(sorted(failing))}"
            )

    contested = [
        r.id for r in open_risks
        if str(r.status) in ("proposed", "reviewed", "accepted")
        and r.disagreement and (r.disagreement.get("value") or 0) > 0.25
    ]
    if contested:
        pending.append(
            f"{len(contested)} risk(s) have contested scores (disagreement > 0.25): "
            f"{', '.join(sorted(contested))} — resolve at the gate"
        )
    speculative = [r.id for r in open_risks if not r.elicited_by.evidence]
    if speculative:
        pending.append(
            f"{len(speculative)} risk(s) are speculative (no evidence): "
            f"{', '.join(sorted(speculative))}"
        )

    return {
        "project": config.get("project"),
        "phase": phase,
        "catalogs": list(config.get("catalogs") or []),
        "scoring_policy": policy_id,
        "aspects": aspects,
        "risks": counts,
        "scoring": {"scored": len(scored), "unscored": len(unscored)},
        "mitigation": {"covered": len(needing) - len(uncovered), "uncovered": sorted(uncovered)},
        "top_risks": [
            {"id": r.id, "priority": priority_of(r), "status": str(r.status),
             "statement": (r.statement[:77] + "...") if len(r.statement) > 80 else r.statement}
            for r in top
        ],
        "pending": pending,
        "last_event": last_event,
        "invalid_files": sorted(set(invalid_files)),
    }


def format_status(report: dict) -> str:
    lines = [
        f"project: {report['project']}   phase: {report['phase']}   "
        f"policy: {report['scoring_policy']}",
    ]
    if report["aspects"]:
        lines.append("aspects: " + ", ".join(f"{a['rank']}.{a['id']}" for a in report["aspects"]))
    else:
        lines.append("aspects: (none selected)")
    counts = ", ".join(f"{k}={v}" for k, v in sorted(report["risks"].items())) or "none"
    lines.append(f"risks: {counts}   scored: {report['scoring']['scored']}/"
                 f"{report['scoring']['scored'] + report['scoring']['unscored']}")
    if report["top_risks"]:
        lines.append("top risks:")
        for r in report["top_risks"]:
            lines.append(f"  {r['id']} [{r['status']}] {r['priority']} — {r['statement']}")
    if report["last_event"]:
        e = report["last_event"]
        lines.append(f"last event: {e['type']} by {e['principal']} at {e['ts']}")
    if report["pending"]:
        lines.append("pending:")
        lines.extend(f"  ! {hint}" for hint in report["pending"])
    else:
        lines.append("pending: nothing — state is consistent with the current phase")
    return "\n".join(lines)
