"""Adversarial-review verdict: the deterministic half of the QE-court pattern.

The host convenes an independent review panel that challenges a decision and emits
structured *charges*; risqlet computes a SHIP / REMAND / BLOCK verdict from them and
nothing else — no LLM, no I/O in the compute, byte-identical for identical input.
The verdict is advisory: it is recorded for audit, but only a human-principal event
moves a risk's lifecycle state.

The load-bearing rule is corroboration by DISTINCT reviewers: a charge counts only
when at least two independent reviewers raise the same category. A rule that instead
counted one reviewer's repeated objections would flag everything and be useless — the
distinction is what makes the gate discriminating (verified experimentally).
"""

from __future__ import annotations

import json
from pathlib import Path

from risqlet.store import Store

REVIEWS_FILE = "reviews.jsonl"
SEVERITIES = ("fatal", "major", "minor")
VERDICTS = ("SHIP", "REMAND", "BLOCK")


class ReviewError(Exception):
    pass


def reviews_path(store: Store) -> Path:
    return store.root / REVIEWS_FILE


def _validate_reviews(reviews: list[dict]) -> list[str]:
    """Return the distinct reviewer roster, raising ReviewError on a malformed panel."""
    if not isinstance(reviews, list):
        raise ReviewError("reviews must be a list of {reviewer, charges} objects")
    roster: list[str] = []
    for r in reviews:
        reviewer = (r or {}).get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ReviewError("each review needs a non-empty reviewer id")
        if reviewer in roster:
            raise ReviewError(f"reviewer {reviewer!r} appears more than once")
        roster.append(reviewer)
        for c in (r.get("charges") or []):
            sev = (c or {}).get("severity")
            if sev not in SEVERITIES:
                raise ReviewError(
                    f"charge severity {sev!r} must be one of {', '.join(SEVERITIES)}")
            if not isinstance(c.get("category"), str) or not c["category"].strip():
                raise ReviewError("each charge needs a non-empty category")
    return roster


def compute_verdict(decision_author: str, reviews: list[dict]) -> dict:
    """Deterministic SHIP/REMAND/BLOCK verdict over a panel's charges.

    reviews: [{reviewer: str, charges: [{category, severity, reproducible, claim}]}].
    A reviewer with no charges is a clean vote (they still count toward the roster).
    Raises ReviewError if the panel is invalid (< 2 distinct reviewers, or the
    decision's author sits on it).
    """
    roster = _validate_reviews(reviews)
    if len(roster) < 2:
        raise ReviewError("a valid panel needs at least two independent reviewers")
    if decision_author and decision_author in roster:
        raise ReviewError(
            f"the decision's author ({decision_author}) may not sit on the panel")

    # distinct reviewers per category, over reproducible charges only
    cat_reviewers: dict[str, set[str]] = {}
    cat_severities: dict[str, set[str]] = {}
    lone_fatal = False
    for r in reviews:
        for c in (r.get("charges") or []):
            if not c.get("reproducible"):
                continue
            if c["severity"] == "fatal":
                lone_fatal = True
            cat_reviewers.setdefault(c["category"], set()).add(r["reviewer"])
            cat_severities.setdefault(c["category"], set()).add(c["severity"])

    surviving = sorted(cat for cat, revs in cat_reviewers.items() if len(revs) >= 2)
    surviving_fatal = any("fatal" in cat_severities[cat] for cat in surviving)
    surviving_major = any(
        cat_severities[cat] & {"fatal", "major"} for cat in surviving)

    if surviving_fatal:
        verdict = "BLOCK"
    elif surviving_major or lone_fatal:
        verdict = "REMAND"
    else:
        verdict = "SHIP"

    return {"verdict": verdict, "surviving": surviving, "reviewers": roster}


def record_review(store: Store, decision_id: str, decision_author: str,
                  reviews: list[dict]) -> dict:
    """Compute and append a verdict record. Never changes any risk's state."""
    result = compute_verdict(decision_author, reviews)
    record = {
        "decision": decision_id,
        "author": decision_author,
        "reviewers": result["reviewers"],
        "reviews": reviews,
        "verdict": result["verdict"],
        "surviving": result["surviving"],
    }
    path = reviews_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_reviews(store: Store) -> list[dict]:
    path = reviews_path(store)
    if not path.exists():
        return []
    out = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ReviewError(f"{path}:{lineno}: malformed review line") from exc
    return out
