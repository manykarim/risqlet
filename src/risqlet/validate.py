"""The validate pipeline: schema, referential integrity, lifecycle, derived checks.

``risqlet validate`` is the single gate command agents run constantly; it
aggregates every finding across the register instead of failing fast, and
separates errors (exit 1) from warnings (informational, exit 0).
"""

from __future__ import annotations

import re

from pydantic import ValidationError

from risqlet import lifecycle
from risqlet.findings import Finding, Severity, has_errors
from risqlet.model import ASPECT_ID_PATTERN, Config, Risk
from risqlet.policies.engine import Policy, PolicyError, load_policy
from risqlet.store import Store, StoreError

_ASPECT_RE = re.compile(ASPECT_ID_PATTERN)


def _pydantic_findings(exc: ValidationError, file_label: str) -> list[Finding]:
    out = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "<root>"
        out.append(Finding(Severity.ERROR, file_label, loc, err["msg"]))
    return out


def _extra_field_warnings(model, file_label: str, prefix: str = "") -> list[Finding]:
    """Recursively surface unknown fields kept by the open-world models."""
    out = []
    for name in model.extra_fields():
        out.append(
            Finding(
                Severity.WARNING,
                file_label,
                f"{prefix}{name}",
                "unknown field (tolerated; not part of the schema)",
            )
        )
    for field_name in type(model).model_fields:
        value = getattr(model, field_name, None)
        children = value if isinstance(value, list) else [value]
        for i, child in enumerate(children):
            if hasattr(child, "extra_fields"):
                child_prefix = (
                    f"{prefix}{field_name}[{i}]." if isinstance(value, list)
                    else f"{prefix}{field_name}."
                )
                out.extend(_extra_field_warnings(child, file_label, child_prefix))
    return out


class ValidationReport:
    def __init__(self, findings: list[Finding]):
        self.findings = findings

    @property
    def passed(self) -> bool:
        return not has_errors(self.findings)

    def to_dict(self) -> dict:
        return {
            "pass": self.passed,
            "errors": sum(1 for f in self.findings if f.severity == Severity.ERROR),
            "warnings": sum(1 for f in self.findings if f.severity == Severity.WARNING),
            "findings": [f.to_dict() for f in self.findings],
        }


def validate_register(store: Store) -> ValidationReport:
    findings: list[Finding] = []
    config_label = ".risqlet/config.yaml"

    # -- config ---------------------------------------------------------------
    config: Config | None = None
    try:
        raw_config = store.load_config_raw()
    except Exception as exc:  # unreadable YAML
        findings.append(Finding(Severity.ERROR, config_label, "<root>", str(exc)))
        raw_config = None
    if raw_config is not None:
        try:
            config = Config.model_validate(raw_config)
        except ValidationError as exc:
            findings.extend(_pydantic_findings(exc, config_label))
    if config is not None:
        findings.extend(_extra_field_warnings(config, config_label))
        if len(config.aspects) > config.constraints.max_aspects:
            findings.append(
                Finding(
                    Severity.ERROR,
                    config_label,
                    "aspects",
                    f"{len(config.aspects)} aspects selected, constraint allows "
                    f"{config.constraints.max_aspects} — prioritize",
                )
            )
        ranks = [a.rank for a in config.aspects]
        for rank in {r for r in ranks if ranks.count(r) > 1}:
            findings.append(
                Finding(Severity.ERROR, config_label, "aspects", f"duplicate rank {rank}")
            )
        for aspect in config.aspects:
            if aspect.rank > config.constraints.max_aspects:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        config_label,
                        "aspects",
                        f"{aspect.id}: rank {aspect.rank} exceeds max_aspects",
                    )
                )

    # -- configured catalogs ---------------------------------------------------
    from risqlet.catalog import CatalogError, load_pack

    loaded_packs = {}
    if config is not None:
        for catalog_id in config.catalogs:
            try:
                loaded_packs[catalog_id] = load_pack(catalog_id, store)
            except CatalogError as exc:
                findings.append(
                    Finding(Severity.ERROR, config_label, "catalogs", str(exc))
                )

    def check_catalog_ref(value: str, label: str, field_name: str) -> None:
        """Soft check: ns.slug refs into loaded packs must resolve (warning).

        Provenance refs may carry a guideword suffix (``guidewords.data-shapes:huge``);
        the suffix is validated against the entry's word list when present.
        """
        if "." not in value:
            return
        namespace, slug = value.split(".", 1)
        word = None
        if ":" in slug:
            slug, word = slug.split(":", 1)
        pack = loaded_packs.get(namespace)
        if pack is None:
            return
        entry = pack.get(slug)
        if entry is None:
            findings.append(
                Finding(
                    Severity.WARNING, label, field_name,
                    f"{value!r}: no entry {slug!r} in loaded catalog "
                    f"{namespace!r} — typo or custom id?",
                )
            )
        elif word and entry.words and word not in entry.words:
            findings.append(
                Finding(
                    Severity.WARNING, label, field_name,
                    f"{value!r}: {word!r} is not a word of {namespace}.{slug} "
                    f"(has: {', '.join(entry.words)})",
                )
            )

    # -- events ---------------------------------------------------------------
    try:
        events = store.read_events()
    except StoreError as exc:
        findings.append(Finding(Severity.ERROR, ".risqlet/events.jsonl", "<root>", str(exc)))
        events = []
    findings.extend(lifecycle.check_events(events))

    # -- risks ------------------------------------------------------------------
    risks: list[tuple[str, Risk]] = []
    seen_risk_ids: dict[str, str] = {}
    seen_mitigation_ids: dict[str, str] = {}
    policy_cache: dict[str, Policy | None] = {}

    def get_policy(policy_id: str) -> Policy | None:
        if policy_id not in policy_cache:
            try:
                policy_cache[policy_id] = load_policy(
                    policy_id, user_dir=store.user_policies_dir
                )
            except PolicyError as exc:
                findings.append(
                    Finding(Severity.ERROR, config_label, "scoring_policy", str(exc))
                )
                policy_cache[policy_id] = None
        return policy_cache[policy_id]

    for risk_file in store.load_risk_files():
        label = f".risqlet/register/{risk_file.path.name}"
        try:
            risk = Risk.model_validate(risk_file.data)
        except ValidationError as exc:
            findings.extend(_pydantic_findings(exc, label))
            continue
        risks.append((label, risk))
        findings.extend(_extra_field_warnings(risk, label))

        if risk.id in seen_risk_ids:
            findings.append(
                Finding(
                    Severity.ERROR, label, "id",
                    f"duplicate id {risk.id} (also in {seen_risk_ids[risk.id]})",
                )
            )
        seen_risk_ids.setdefault(risk.id, label)
        if risk_file.path.stem != risk.id:
            findings.append(
                Finding(
                    Severity.WARNING, label, "id",
                    f"filename {risk_file.path.name} does not match id {risk.id}",
                )
            )
        for aspect in risk.aspects:
            if not _ASPECT_RE.match(aspect):
                findings.append(
                    Finding(
                        Severity.ERROR, label, "aspects",
                        f"{aspect!r} is not a namespaced catalog.slug id",
                    )
                )
            else:
                check_catalog_ref(aspect, label, "aspects")
        if risk.elicited_by.prompt_ref:
            check_catalog_ref(risk.elicited_by.prompt_ref, label, "elicited_by.prompt_ref")
        for mitigation in risk.mitigations:
            if mitigation.technique_ref:
                check_catalog_ref(mitigation.technique_ref, label, "technique_ref")
        if not risk.elicited_by.evidence:
            findings.append(
                Finding(
                    Severity.WARNING, label, "elicited_by.evidence",
                    f"{risk.id}: no evidence linked — flagged speculative",
                )
            )
        for mitigation in risk.mitigations:
            if mitigation.id in seen_mitigation_ids:
                findings.append(
                    Finding(
                        Severity.ERROR, label, "mitigations",
                        f"duplicate mitigation id {mitigation.id} "
                        f"(also in {seen_mitigation_ids[mitigation.id]})",
                    )
                )
            seen_mitigation_ids.setdefault(mitigation.id, label)

        # derived recomputation: engine-owned values must match
        for i, score in enumerate(risk.scores):
            policy = get_policy(score.policy)
            if policy is None:
                continue
            problems = policy.check_values(score.values) + policy.check_anchors(
                score.rubric_anchors
            )
            if problems:
                findings.extend(
                    Finding(Severity.ERROR, label, f"scores[{i}]", f"{risk.id}: {p}")
                    for p in problems
                )
                continue
            expected = policy.compute(score.values, score.rubric_anchors)
            if score.derived and dict(score.derived) != expected:
                findings.append(
                    Finding(
                        Severity.ERROR, label, f"scores[{i}].derived",
                        f"{risk.id}: stored derived {dict(score.derived)} does not match "
                        f"policy computation {expected} — run `risqlet score`",
                    )
                )

        # disagreement is engine-owned, like derived
        if config is not None:
            active = get_policy(config.scoring_policy)
            if active is not None:
                from risqlet.scoring import compute_disagreement

                expected_disagreement = compute_disagreement(
                    [s.model_dump(mode="json") for s in risk.scores], active
                )
                stored_disagreement = (
                    dict(risk.disagreement) if risk.disagreement else None
                )
                if stored_disagreement != expected_disagreement:
                    findings.append(
                        Finding(
                            Severity.ERROR, label, "disagreement",
                            f"{risk.id}: stored disagreement {stored_disagreement} does "
                            f"not match computation {expected_disagreement} — run "
                            f"`risqlet score`",
                        )
                    )

        findings.extend(
            lifecycle.check_risk_consistency(risk.id, str(risk.status), label, events)
        )

    # referential integrity: mitigation risk_ids must resolve
    for label, risk in risks:
        for mitigation in risk.mitigations:
            for ref in mitigation.risk_ids:
                if ref not in seen_risk_ids:
                    findings.append(
                        Finding(
                            Severity.ERROR, label, "mitigations",
                            f"{mitigation.id}: references unknown risk {ref}",
                        )
                    )

    if config is not None:
        findings.extend(lifecycle.check_phase_consistency(str(config.phase), events))

    return ValidationReport(findings)
