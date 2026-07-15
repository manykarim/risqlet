"""Generic scoring-policy engine.

Policies are pure YAML data packs (ordinal factors + derived fields via a
``product`` formula or a top-down first-match ``lookup`` band table). The
engine validates pack structure at load time and computes derived values
deterministically; nothing here is policy-specific, so new policies require
no code changes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

PACKS_DIR = Path(__file__).resolve().parent / "packs"

_CONDITION_RE = re.compile(r"^(?:(?P<lo>\d+)-(?P<hi>\d+)|(?P<op>>=|<=)(?P<bound>\d+)|(?P<eq>\d+))$")


class PolicyError(Exception):
    """Malformed policy pack."""


class ScoringError(Exception):
    """Score set cannot be computed under the policy."""


def _parse_condition(expr: str | int, factor: str, band_index: int):
    match = _CONDITION_RE.match(str(expr).strip())
    if not match:
        raise PolicyError(
            f"band {band_index}: condition {expr!r} on factor {factor!r} is not "
            f"'N', 'N-M', '>=N' or '<=N'"
        )
    if match["lo"] is not None:
        lo, hi = int(match["lo"]), int(match["hi"])
        return lambda v: lo <= v <= hi
    if match["op"] == ">=":
        bound = int(match["bound"])
        return lambda v: v >= bound
    if match["op"] == "<=":
        bound = int(match["bound"])
        return lambda v: v <= bound
    eq = int(match["eq"])
    return lambda v: v == eq


@dataclass
class _Band:
    predicates: dict[str, object]
    value: str
    is_default: bool = False


@dataclass
class Policy:
    id: str
    description: str
    factors: dict[str, tuple[int, int]]
    derived_products: list[str] = field(default_factory=list)
    lookups: dict[str, list[_Band]] = field(default_factory=dict)
    ranking_field: str | None = None
    ranking_order: list[str] = field(default_factory=list)
    ranking_tiebreaker: str | None = None

    @classmethod
    def from_dict(cls, data: dict, source: str = "<pack>") -> Policy:
        try:
            policy_id = data["id"]
            raw_factors = data["factors"]
        except (KeyError, TypeError) as exc:
            raise PolicyError(f"{source}: pack must define 'id' and 'factors'") from exc
        factors: dict[str, tuple[int, int]] = {}
        for name, bounds in raw_factors.items():
            try:
                lo, hi = int(bounds["min"]), int(bounds["max"])
            except (KeyError, TypeError, ValueError) as exc:
                raise PolicyError(f"{source}: factor {name!r} needs integer min/max") from exc
            if lo >= hi:
                raise PolicyError(f"{source}: factor {name!r} min must be < max")
            factors[name] = (lo, hi)

        policy = cls(id=policy_id, description=data.get("description", ""), factors=factors)

        for derived_name, spec in (data.get("derived") or {}).items():
            if spec.get("formula") == "product":
                policy.derived_products.append(derived_name)
            elif spec.get("type") == "lookup":
                policy.lookups[derived_name] = cls._parse_bands(
                    spec.get("bands"), factors, source, derived_name
                )
            else:
                raise PolicyError(
                    f"{source}: derived {derived_name!r} must be formula: product "
                    f"or type: lookup"
                )

        ranking = data.get("ranking") or {}
        if ranking:
            policy.ranking_field = ranking.get("field")
            policy.ranking_order = list(ranking.get("order") or [])
            policy.ranking_tiebreaker = ranking.get("tiebreaker")
            derived_names = set(policy.derived_products) | set(policy.lookups)
            if policy.ranking_field not in derived_names:
                raise PolicyError(
                    f"{source}: ranking field {policy.ranking_field!r} is not a derived field"
                )
        return policy

    @staticmethod
    def _parse_bands(bands, factors, source, derived_name) -> list[_Band]:
        if not bands:
            raise PolicyError(f"{source}: lookup {derived_name!r} has no bands")
        parsed: list[_Band] = []
        has_default = False
        for i, band in enumerate(bands):
            if "default" in band:
                parsed.append(_Band(predicates={}, value=band["default"], is_default=True))
                has_default = True
                continue
            when = band.get("when") or {}
            if "value" not in band or not when:
                raise PolicyError(
                    f"{source}: lookup {derived_name!r} band {i} needs 'when' + 'value' "
                    f"or 'default'"
                )
            predicates = {}
            for factor_name, expr in when.items():
                if factor_name not in factors:
                    raise PolicyError(
                        f"{source}: lookup {derived_name!r} band {i} references "
                        f"undeclared factor {factor_name!r}"
                    )
                predicates[factor_name] = _parse_condition(expr, factor_name, i)
            parsed.append(_Band(predicates=predicates, value=band["value"]))
        if not has_default:
            raise PolicyError(f"{source}: lookup {derived_name!r} must end with a default band")
        return parsed

    # -- scoring -------------------------------------------------------------

    def check_values(self, values: dict) -> list[str]:
        """Return problems with a factor-value dict (empty list = OK)."""
        problems = []
        for name, (lo, hi) in self.factors.items():
            if name not in values:
                problems.append(f"missing factor {name!r}")
            elif not isinstance(values[name], int) or isinstance(values[name], bool):
                problems.append(f"factor {name!r} must be an integer")
            elif not lo <= values[name] <= hi:
                problems.append(f"factor {name!r}={values[name]} outside range {lo}-{hi}")
        for name in values:
            if name not in self.factors:
                problems.append(f"factor {name!r} is not declared by policy {self.id!r}")
        return problems

    def check_anchors(self, rubric_anchors: list) -> list[str]:
        if len(rubric_anchors or []) < len(self.factors):
            return [
                f"rubric_anchors requires at least one anchor per factor "
                f"({len(self.factors)} needed, {len(rubric_anchors or [])} given)"
            ]
        return []

    def compute(self, values: dict, rubric_anchors: list) -> dict:
        problems = self.check_values(values) + self.check_anchors(rubric_anchors)
        if problems:
            raise ScoringError("; ".join(problems))
        derived: dict = {}
        for name in self.derived_products:
            derived[name] = math.prod(values[f] for f in self.factors)
        for name, bands in self.lookups.items():
            for band in bands:
                if band.is_default or all(
                    pred(values[f]) for f, pred in band.predicates.items()
                ):
                    derived[name] = band.value
                    break
        return derived

    def rank_key(self, derived: dict):
        """Sort key: best priority first (band order, then tiebreaker descending)."""
        if not self.ranking_field:
            return (0,)
        value = derived.get(self.ranking_field)
        index = (
            self.ranking_order.index(value)
            if value in self.ranking_order
            else len(self.ranking_order)
        )
        tiebreak = -(derived.get(self.ranking_tiebreaker) or 0) if self.ranking_tiebreaker else 0
        return (index, tiebreak)


def load_policy(policy_id: str, user_dir: Path | None = None) -> Policy:
    """Load a policy pack by id: user packs (``.risqlet/policies/``) shadow packaged ones."""
    candidates = []
    if user_dir is not None:
        candidates.append(user_dir / f"{policy_id}.yaml")
    candidates.append(PACKS_DIR / f"{policy_id}.yaml")
    yaml = YAML(typ="safe")
    for path in candidates:
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                data = yaml.load(f)
            policy = Policy.from_dict(data, source=str(path))
            if policy.id != policy_id:
                raise PolicyError(f"{path}: pack id {policy.id!r} does not match {policy_id!r}")
            return policy
    searched = ", ".join(str(c) for c in candidates)
    raise PolicyError(f"no policy pack named {policy_id!r} (searched {searched})")
