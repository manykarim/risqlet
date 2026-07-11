"""Deterministic convergence for divergent elicitation: dedupe and merge.

Divergence belongs to the LLM, convergence to code: clustering is a pure
function of register content (token overlap — no embeddings, works offline),
and the tool only *proposes*. Merge decisions stay with agent + human;
`merge` executes them mechanically and refuses anything that would erase a
recorded human decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from risqlet.model import Status
from risqlet.store import RiskFile, Store, StoreError

DEFAULT_THRESHOLD = 0.5

_STOPWORDS = frozenset(
    "a an and are as at be because but by can causing could for from has have if in is it "
    "its may might of on or that the their then this to was when which while will with".split()
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")


class EnsembleError(Exception):
    pass


def statement_tokens(statement: str) -> frozenset[str]:
    return frozenset(
        t for t in _WORD_RE.findall(str(statement).lower()) if t not in _STOPWORDS
    )


def evidence_path(item: str) -> str:
    """Normalize an evidence item to its path core (annotations stripped)."""
    candidate = re.sub(r"\s*\(.*\)$", "", str(item)).strip()
    return re.split(r"[:#\s]", candidate, maxsplit=1)[0]


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(risk_a: dict, risk_b: dict) -> float:
    tokens = _jaccard(
        statement_tokens(risk_a.get("statement", "")),
        statement_tokens(risk_b.get("statement", "")),
    )
    aspects = _jaccard(
        frozenset(risk_a.get("aspects") or []), frozenset(risk_b.get("aspects") or [])
    )
    def evidence_set(risk: dict) -> frozenset[str]:
        return frozenset(
            evidence_path(e) for e in (risk.get("elicited_by") or {}).get("evidence") or []
        )

    evidence = _jaccard(evidence_set(risk_a), evidence_set(risk_b))
    return round(0.6 * tokens + 0.2 * aspects + 0.2 * evidence, 4)


@dataclass
class Cluster:
    members: list[str]
    pairs: dict[str, float]  # "R-0001~R-0002" -> score
    suggested_survivor: str

    def to_dict(self) -> dict:
        return {
            "members": self.members,
            "pairs": self.pairs,
            "suggested_survivor": self.suggested_survivor,
        }


def _suggest_survivor(members: list[str], by_id: dict[str, dict]) -> str:
    def key(risk_id: str):
        risk = by_id[risk_id]
        evidence = (risk.get("elicited_by") or {}).get("evidence") or []
        return (-len(evidence), -len(str(risk.get("statement", ""))), risk_id)

    return sorted(members, key=key)[0]


def find_clusters(store: Store, threshold: float | None = None) -> list[Cluster]:
    if threshold is None:
        config = store.load_config_raw() or {}
        threshold = float(
            (config.get("constraints") or {}).get("dedupe_threshold") or DEFAULT_THRESHOLD
        )
    risks = [rf.data for rf in store.load_risk_files() if rf.data.get("id")]
    by_id = {r["id"]: r for r in risks}
    ids = sorted(by_id)

    # connected components over pairs >= threshold
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pair_scores: dict[tuple[str, str], float] = {}
    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1:]:
            score = similarity(by_id[id_a], by_id[id_b])
            if score >= threshold:
                pair_scores[(id_a, id_b)] = score
                root_a, root_b = find(id_a), find(id_b)
                if root_a != root_b:
                    parent[max(root_a, root_b)] = min(root_a, root_b)

    groups: dict[str, list[str]] = {}
    for risk_id in ids:
        groups.setdefault(find(risk_id), []).append(risk_id)

    clusters = []
    for members in sorted(groups.values()):
        if len(members) < 2:
            continue
        pairs = {
            f"{a}~{b}": s for (a, b), s in sorted(pair_scores.items())
            if a in members and b in members
        }
        clusters.append(
            Cluster(
                members=members,
                pairs=pairs,
                suggested_survivor=_suggest_survivor(members, by_id),
            )
        )
    return clusters


def _ordered_union(first: list, second: list) -> list:
    out = list(first)
    for item in second:
        if item not in out:
            out.append(item)
    return out


def merge(store: Store, survivor_id: str, duplicate_ids: list[str]) -> dict:
    """Mechanically merge proposed duplicates into a survivor. All-or-nothing."""
    files = {rf.data.get("id"): rf for rf in store.load_risk_files()}

    survivor = files.get(survivor_id)
    if survivor is None:
        raise EnsembleError(f"no risk with id {survivor_id}")
    survivor_status = survivor.data.get("status", "proposed")
    if survivor_status in (Status.CLOSED.value, Status.REJECTED.value):
        raise EnsembleError(f"survivor {survivor_id} is terminal ({survivor_status})")

    duplicates: list[RiskFile] = []
    for dup_id in duplicate_ids:
        if dup_id == survivor_id:
            raise EnsembleError("survivor cannot be its own duplicate")
        dup = files.get(dup_id)
        if dup is None:
            raise EnsembleError(f"no risk with id {dup_id}")
        if dup.data.get("status", "proposed") != Status.PROPOSED.value:
            raise EnsembleError(
                f"{dup_id} is {dup.data.get('status')!r} — only 'proposed' risks can be "
                f"merged away (recorded decisions must not be erased)"
            )
        duplicates.append(dup)

    moved_mitigations = 0
    for dup in duplicates:
        dup_elicited = dup.data.get("elicited_by") or {}
        survivor_elicited = survivor.data.setdefault("elicited_by", {})
        survivor_elicited["evidence"] = _ordered_union(
            list(survivor_elicited.get("evidence") or []),
            list(dup_elicited.get("evidence") or []),
        )
        survivor.data["aspects"] = _ordered_union(
            list(survivor.data.get("aspects") or []), list(dup.data.get("aspects") or [])
        )
        for mitigation in dup.data.get("mitigations") or []:
            mitigation["risk_ids"] = [
                survivor_id if rid == dup.data.get("id") else rid
                for rid in (mitigation.get("risk_ids") or [])
            ]
            survivor.data.setdefault("mitigations", []).append(mitigation)
            moved_mitigations += 1
        merged_from = survivor.data.setdefault("merged_from", [])
        merged_from.append({
            "id": dup.data.get("id"),
            "method": dup_elicited.get("method"),
            "prompt_ref": dup_elicited.get("prompt_ref", ""),
        })

    store.save_risk(survivor)
    for dup in duplicates:
        dup.path.unlink()

    return {
        "survivor": survivor_id,
        "merged": [d.data.get("id") for d in duplicates],
        "moved_mitigations": moved_mitigations,
    }


__all__ = [
    "Cluster",
    "EnsembleError",
    "StoreError",
    "evidence_path",
    "find_clusters",
    "merge",
    "similarity",
]
