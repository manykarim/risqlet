"""The `risqlet score` operation: refresh engine-owned derived fields in place."""

from __future__ import annotations

from risqlet.findings import Finding, Severity
from risqlet.policies.engine import Policy, PolicyError, ScoringError, load_policy
from risqlet.store import Store


def compute_disagreement(score_sets: list[dict], policy: Policy) -> dict | None:
    """Normalized factor spread across >=2 valid score sets for one policy.

    Ensemble insight: spread is signal for the gate, never averaged away.
    """
    qualifying = []
    for score in score_sets or []:
        if score.get("policy") != policy.id:
            continue
        values = dict(score.get("values") or {})
        if policy.check_values(values) or policy.check_anchors(
            list(score.get("rubric_anchors") or [])
        ):
            continue
        qualifying.append(values)
    if len(qualifying) < 2:
        return None
    factors = {}
    for name, (lo, hi) in policy.factors.items():
        observed = [v[name] for v in qualifying]
        factors[name] = round((max(observed) - min(observed)) / (hi - lo), 2)
    value = round(sum(factors.values()) / len(factors), 2)
    return {"policy": policy.id, "value": value, "factors": factors}


def score_risks(store: Store, risk_id: str | None = None) -> tuple[int, list[Finding]]:
    """Compute derived values for one risk or all; returns (files_updated, findings).

    Factor values are never created or modified — only the ``derived`` mapping
    is written, and only when it changed. Round-trip saves preserve comments.
    """
    findings: list[Finding] = []
    updated = 0
    matched = False
    config = store.load_config_raw() or {}
    active_policy_id = config.get("scoring_policy", "sod-ap-v1")
    try:
        active_policy = load_policy(active_policy_id, user_dir=store.user_policies_dir)
    except PolicyError:
        active_policy = None
    for risk_file in store.load_risk_files():
        label = f".risqlet/register/{risk_file.path.name}"
        current_id = risk_file.data.get("id")
        if risk_id is not None and current_id != risk_id:
            continue
        matched = True
        changed = False
        for i, score in enumerate(risk_file.data.get("scores") or []):
            policy_id = score.get("policy", "")
            try:
                policy = load_policy(policy_id, user_dir=store.user_policies_dir)
                derived = policy.compute(
                    dict(score.get("values") or {}), list(score.get("rubric_anchors") or [])
                )
            except (PolicyError, ScoringError) as exc:
                findings.append(
                    Finding(Severity.ERROR, label, f"scores[{i}]", f"{current_id}: {exc}")
                )
                continue
            if dict(score.get("derived") or {}) != derived:
                score["derived"] = derived
                changed = True
        if active_policy is not None:
            disagreement = compute_disagreement(
                list(risk_file.data.get("scores") or []), active_policy
            )
            stored = risk_file.data.get("disagreement")
            if disagreement is None and stored is not None:
                del risk_file.data["disagreement"]
                changed = True
            elif disagreement is not None and dict(stored or {}) != disagreement:
                risk_file.data["disagreement"] = disagreement
                changed = True
        if changed:
            store.save_risk(risk_file)
            updated += 1
    if risk_id is not None and not matched:
        findings.append(
            Finding(Severity.ERROR, ".risqlet/register/", "id", f"no risk with id {risk_id}")
        )
    return updated, findings
