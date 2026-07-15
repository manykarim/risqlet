"""Continuous re-assessment at the change boundary.

`diff` maps changed files to the register risks they touch; `check` turns that
into a CI gate. Both are read-only and deterministic — the register is never
mutated from CI. Matching reuses the ensemble/trace normalization helpers.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import PurePosixPath

from risqlet.ensemble import evidence_path, statement_tokens
from risqlet.model import Risk, Status
from risqlet.policies.engine import PolicyError, load_policy
from risqlet.store import Store
from risqlet.trace import mitigation_state, read_results, ref_key

CI_MODES = ("off", "warn", "block")


class ChangesetError(Exception):
    pass


# Claude Code writes a JSON envelope to a hook's stdin (it sets no env var for the
# edited path), so the CLI parses it directly rather than making the hook shell out
# to an interpreter to dig the path out.
def parse_claude_hook_payload(text: str | None) -> list[str]:
    """Changed files named by a Claude Code hook payload.

    Total by design: a hook runs inside an agent's edit loop, so an unusable
    payload yields no files rather than an error. Callers treat [] as "nothing
    to check" — see the never-fail contract in cmd_check.
    """
    if not text or not text.strip():
        return []
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, dict):
        return []
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path.strip():
        return []
    return [path.strip()]


def changed_files(store_dir, base: str | None, files: list[str] | None,
                  stdin_text: str | None) -> list[str]:
    if files:
        return [f.strip() for f in files if f.strip()]
    if stdin_text:
        return [line.strip() for line in stdin_text.splitlines() if line.strip()]
    ref = base or "HEAD~1"
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{ref}...HEAD"],
        cwd=store_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ChangesetError(
            f"git diff failed (base {ref!r}): {result.stderr.strip()} — "
            f"pass --files or pipe paths on stdin in non-git contexts"
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _components(path: str) -> list[str]:
    p = PurePosixPath(path.replace("\\", "/"))
    return [c.lower() for c in p.parts]


def _path_match(reference: str, changed: str) -> str | None:
    """Return 'file' for exact/basename path match, 'dir' for a directory-prefix
    signal, else None."""
    if not reference:
        return None
    ref = reference.rstrip("/")
    if ref == changed:
        return "file"
    ref_parts = _components(ref)
    changed_parts = _components(changed)
    # basename equality (same file, different roots)
    if ref_parts and changed_parts and ref_parts[-1] == changed_parts[-1] and "." in ref_parts[-1]:
        return "file"
    # directory prefix: evidence points at a dir containing the changed file
    if reference.endswith("/") or "." not in ref_parts[-1]:
        if changed_parts[: len(ref_parts)] == ref_parts:
            return "dir"
    return None


def _match_risk(risk: Risk, changed: list[str]) -> list[dict]:
    reasons: list[dict] = []
    evidences = [evidence_path(e) for e in risk.elicited_by.evidence]
    test_paths = []
    for m in risk.mitigations:
        for t in m.tests or []:
            key = ref_key(t)
            if key:
                test_paths.append((t, key[0]))  # (ref, file-basename-key)
    tokens = {t for t in statement_tokens(risk.statement) if len(t) >= 4}

    for path in changed:
        # evidence (high)
        for ev in evidences:
            kind = _path_match(ev, path)
            if kind == "file":
                reasons.append({"path": path, "reason": f"evidence:{ev}",
                                "confidence": "high"})
                break
            elif kind == "dir":
                reasons.append({"path": path, "reason": f"evidence-dir:{ev}",
                                "confidence": "medium"})
                break
        else:
            # test refs (high) — match basename
            changed_base = _components(path)[-1] if _components(path) else ""
            changed_stem = changed_base.rsplit(".", 1)[0]
            matched_test = next(
                (ref for ref, base in test_paths if base and base == changed_stem), None
            )
            if matched_test:
                reasons.append({"path": path, "reason": f"test:{matched_test}",
                                "confidence": "high"})
                continue
            # statement tokens (low): >=2 tokens appear as path components
            comps = set(_components(path)) | {
                c.rsplit(".", 1)[0] for c in _components(path)
            }
            hit = sorted(tokens & comps)
            if len(hit) >= 2:
                reasons.append({"path": path, "reason": f"statement:{','.join(hit[:4])}",
                                "confidence": "low"})
    return reasons


def _priority(risk: Risk, policy, policy_id: str) -> str:
    for score in risk.scores:
        if score.policy == policy_id and score.derived:
            return ", ".join(f"{k}={v}" for k, v in sorted(dict(score.derived).items()))
    return "unscored"


def _suggested_action(risk: Risk, worst_mit_state: str | None) -> str:
    if str(risk.status) == Status.PROPOSED.value:
        return "re-elicit this area (risk still proposed)"
    if worst_mit_state in ("covered-failing", "untested", "charter-only"):
        return "verify coverage (mitigation test failing or missing)"
    if not any(s.derived for s in risk.scores):
        return "re-score (touched but unscored)"
    return "re-score if the change alters likelihood or detectability"


def build_diff(store: Store, base: str | None = None, files: list[str] | None = None,
               stdin_text: str | None = None, top_untouched: int = 5) -> dict:
    changed = changed_files(store.root.parent, base, files, stdin_text)
    config = store.load_config_raw() or {}
    policy_id = config.get("scoring_policy", "sod-ap-v1")
    try:
        policy = load_policy(policy_id, user_dir=store.user_policies_dir)
    except PolicyError:
        policy = None
    results = read_results(store)

    ci_paths = (config.get("constraints") or {}).get("ci_paths") or []
    if ci_paths:
        kept = [c for c in changed if any(fnmatch.fnmatch(c, g) for g in ci_paths)]
    else:
        kept = changed
    excluded = len(changed) - len(kept)

    risks = []
    for rf in store.load_risk_files():
        try:
            risks.append(Risk.model_validate(rf.data))
        except Exception:
            continue

    touched = []
    for risk in risks:
        reasons = _match_risk(risk, kept)
        if not reasons:
            continue
        states = [mitigation_state(m.model_dump(mode="json"), results)
                  for m in risk.mitigations]
        worst = min(states, key=lambda s: {"covered-failing": 0, "untested": 1,
                                           "charter-only": 2, "covered-passing": 3}[s],
                    default=None)
        touched.append({
            "risk": risk.id, "status": str(risk.status),
            "priority": _priority(risk, policy, policy_id),
            "reasons": reasons,
            "confidence": "high" if any(r["confidence"] == "high" for r in reasons)
            else ("medium" if any(r["confidence"] == "medium" for r in reasons) else "low"),
            "coverage": worst,
            "suggested_action": _suggested_action(risk, worst),
        })

    touched_ids = {t["risk"] for t in touched}

    def rank_key(risk: Risk):
        if policy is not None:
            for score in risk.scores:
                if score.policy == policy_id and score.derived:
                    return (0, policy.rank_key(dict(score.derived)), risk.id)
        return (1, (), risk.id)

    untouched_high = [
        {"risk": r.id, "priority": _priority(r, policy, policy_id), "status": str(r.status)}
        for r in sorted(risks, key=rank_key)
        if r.id not in touched_ids
        and str(r.status) not in (Status.REJECTED.value, Status.CLOSED.value)
        and any(s.derived for s in r.scores)
    ][:top_untouched]

    return {
        "changed_files": len(changed),
        "considered_files": len(kept),
        "excluded_paths": excluded,
        "touched": sorted(touched, key=lambda t: t["risk"]),
        "untouched_high_priority": untouched_high,
    }


def run_check(store: Store, base: str | None = None, files: list[str] | None = None,
              stdin_text: str | None = None) -> dict:
    config = store.load_config_raw() or {}
    mode = (config.get("constraints") or {}).get("ci_gate", "warn")
    if mode not in CI_MODES:
        mode = "warn"
    diff = build_diff(store, base=base, files=files, stdin_text=stdin_text)

    flagged = []
    for t in diff["touched"]:
        status, coverage = t["status"], t["coverage"]
        high_or_med = t["confidence"] in ("high", "medium")
        if status in (Status.ACCEPTED.value, Status.MITIGATING.value) and coverage in (
            "covered-failing", "untested", "charter-only"
        ):
            flagged.append({**t, "flag": f"{status} risk with {coverage} coverage"})
        elif status in (Status.REVIEWED.value, Status.ACCEPTED.value) and high_or_med \
                and coverage != "covered-passing":
            flagged.append({**t, "flag": f"{status} risk touched, coverage {coverage}"})

    exit_code = 1 if (mode == "block" and flagged) else 0
    return {"mode": mode, "flagged": flagged, "excluded_paths": diff["excluded_paths"],
            "considered_files": diff["considered_files"], "exit": exit_code}
