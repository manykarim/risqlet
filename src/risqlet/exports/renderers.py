"""Deterministic export renderers: register bundle, strategy page, trace matrix.

Identical register state must produce byte-identical output — no timestamps,
no environment-dependent content, stable sort orders everywhere.
"""

from __future__ import annotations

import csv
import io

from pydantic import ValidationError
from ruamel.yaml import YAML

from risqlet.model import Config, Risk, Status
from risqlet.policies.engine import Policy, PolicyError, load_policy
from risqlet.store import Store

FORMATS = ("register-yaml", "strategy-md", "trace-matrix-csv")


class ExportError(Exception):
    pass


def _load(store: Store) -> tuple[Config, list[Risk]]:
    try:
        config = Config.model_validate(store.load_config_raw())
        risks = [Risk.model_validate(rf.data) for rf in store.load_risk_files()]
    except ValidationError as exc:
        raise ExportError(f"register does not validate — run `risqlet validate`: {exc}") from exc
    return config, sorted(risks, key=lambda r: r.id)


def _active_policy(store: Store, config: Config) -> Policy | None:
    try:
        return load_policy(config.scoring_policy, user_dir=store.user_policies_dir)
    except PolicyError:
        return None


def _rank(risks: list[Risk], policy: Policy | None, policy_id: str) -> list[Risk]:
    """Order risks by the active policy's ranking; unscored risks sort last."""

    def key(risk: Risk):
        if policy is not None:
            for score in risk.scores:
                if score.policy == policy_id and score.derived:
                    return (0, policy.rank_key(dict(score.derived)), risk.id)
        return (1, (), risk.id)

    return sorted(risks, key=key)


def _derived_summary(risk: Risk, policy_id: str) -> str:
    for score in risk.scores:
        if score.policy == policy_id and score.derived:
            return ", ".join(f"{k}={v}" for k, v in sorted(dict(score.derived).items()))
    return "unscored"


def render_register_yaml(store: Store) -> str:
    config, risks = _load(store)
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    yaml.sort_base_mapping_type_on_output = True  # type: ignore[assignment]
    bundle = {
        "config": config.model_dump(mode="json"),
        "risks": [r.model_dump(mode="json") for r in risks],
    }
    buf = io.StringIO()
    yaml.dump(bundle, buf)
    return buf.getvalue()


def render_trace_matrix_csv(store: Store) -> str:
    from risqlet.trace import latest_result_for_ref, read_results

    _config, risks = _load(store)
    results = read_results(store)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["aspect", "risk", "mitigation", "test", "result"])
    for risk in risks:
        aspects = risk.aspects or [""]
        rows = []
        for mitigation in risk.mitigations:
            for test in mitigation.tests or [""]:
                result = latest_result_for_ref(test, results) if test else ""
                rows.append((mitigation.id, test, result))
        if not rows:
            rows = [("", "", "")]
        for aspect in sorted(aspects):
            for mitigation_id, test, result in rows:
                writer.writerow([aspect, risk.id, mitigation_id, test, result])
    return buf.getvalue()


def render_strategy_md(store: Store) -> str:
    config, risks = _load(store)
    policy = _active_policy(store, config)
    policy_id = config.scoring_policy

    active = [r for r in risks if r.status not in (Status.REJECTED, Status.CLOSED)]
    ranked = _rank(active, policy, policy_id)
    cap = config.constraints.max_top_risks
    top, overflow = ranked[:cap], ranked[cap:]

    lines: list[str] = []
    add = lines.append
    add(f"# Test Strategy: {config.project}")
    add("")
    add(f"Scoring policy: `{policy_id}` · Workflow phase: `{config.phase}` · "
        f"Register: {len(risks)} risks ({len(active)} open)")
    add("")

    add("## Quality aspects (why we test)")
    add("")
    if config.aspects:
        for aspect in sorted(config.aspects, key=lambda a: a.rank):
            add(f"{aspect.rank}. **{aspect.id}** — {aspect.rationale}")
    else:
        add("_No quality aspects selected yet (phase 'aspects' pending)._")
    add("")

    add(f"## Top risks (max {cap})")
    add("")
    if top:
        add("| # | Risk | Aspects | Priority | Status |")
        add("|---|------|---------|----------|--------|")
        for i, risk in enumerate(top, start=1):
            statement = risk.statement.replace("|", "\\|")
            add(
                f"| {i} | **{risk.id}** {statement} | "
                f"{', '.join(risk.aspects)} | {_derived_summary(risk, policy_id)} | "
                f"{risk.status} |"
            )
        if overflow:
            add("")
            add(f"_{len(overflow)} further risk(s) are tracked in the register "
                f"but not listed here._")
    else:
        add("_No open risks recorded._")
    add("")

    add("## Mitigations (how we test)")
    add("")
    mitigation_rows = [
        (risk, m) for risk in top for m in risk.mitigations
    ]
    if mitigation_rows:
        add("| Mitigation | Risk(s) | Treatment | Lever | Barrier | Action | Tests |")
        add("|------------|---------|-----------|-------|---------|--------|-------|")
        for _risk, m in mitigation_rows:
            concrete = m.concrete.replace("|", "\\|")
            tests = ", ".join(f"`{t}`" for t in m.tests) or "—"
            add(
                f"| {m.id} | {', '.join(m.risk_ids)} | {m.treatment} | {m.lever} | "
                f"{m.barrier} | {concrete} | {tests} |"
            )
    else:
        add("_No mitigations recorded for the top risks._")
    add("")

    add("## What this does not cover")
    add("")
    residuals = [(m.id, m.residual_note) for risk in active for m in risk.mitigations]
    if residuals:
        for mitigation_id, note in residuals:
            add(f"- **{mitigation_id}**: {note}")
    else:
        add("- No mitigations are recorded yet, so all identified risk currently "
            "remains unmitigated residual risk.")
    speculative = [r.id for r in active if not r.elicited_by.evidence]
    if speculative:
        add(f"- Speculative (evidence-free) risks needing grounding: "
            f"{', '.join(sorted(speculative))}.")
    add("- This register reflects recorded analysis only; unknown risks remain unknown.")
    add("")

    from risqlet.trace import mitigation_state, read_results

    results = read_results(store)
    if results:
        flagged = []
        for risk in active:
            for m in risk.mitigations:
                state = mitigation_state(m.model_dump(mode="json"), results)
                if state in ("covered-failing", "charter-only", "untested"):
                    flagged.append((m.id, risk.id, state))
        if flagged:
            add("### Mitigations with failing or missing tests")
            add("")
            for mitigation_id, risk_id, state in flagged:
                add(f"- **{mitigation_id}** ({risk_id}): {state}")
            add("")
    return "\n".join(lines)


def render(store: Store, fmt: str) -> str:
    if fmt == "register-yaml":
        return render_register_yaml(store)
    if fmt == "strategy-md":
        return render_strategy_md(store)
    if fmt == "trace-matrix-csv":
        return render_trace_matrix_csv(store)
    raise ExportError(f"unknown format {fmt!r} (choose from {', '.join(FORMATS)})")
