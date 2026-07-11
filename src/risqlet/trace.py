"""Close the loop: aspect -> risk -> mitigation -> test -> RESULT.

Ingests Robot Framework and JUnit XML (stdlib only), matches results to
mitigation ``tests[]`` refs by normalized key, and reports coverage plus
Detection-evidence notes. Results live in ``.risqlet/results.jsonl``, outside
the register schema — telemetry, not truth-of-record; `validate` ignores them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from risqlet.model import Risk
from risqlet.store import Store

RESULTS_FILE = "results.jsonl"
HISTORY_N = 5
DETECTION_CLAIM_THRESHOLD = 4  # detection <= this means "we claim good detection"

Outcome = str  # "pass" | "fail" | "skip"


class TraceError(Exception):
    pass


# -- ref / result key normalization -------------------------------------------

def _basename_key(locator: str) -> str:
    """Reduce a suite/file locator to a lowercased basename without extension."""
    base = re.split(r"[\\/]", locator.strip())[-1]
    base = re.sub(r"\.(robot|py|xml|class)$", "", base, flags=re.I)
    return base.lower()


def ref_key(test_ref: str) -> tuple[str, str] | None:
    """Normalize a mitigation tests[] ref to (suite/file, test) or None (charter/invalid)."""
    if ":" not in test_ref:
        return None
    kind, _, rest = test_ref.partition(":")
    kind = kind.lower()
    if kind == "charter":
        return None
    if "::" in rest:
        locator, name = rest.split("::", 1)
    else:
        locator, name = rest, ""
    if kind in ("rf", "pytest", "junit"):
        # junit classname may be dotted (tests.suite): treat dots as path separators
        norm = locator.replace(".", "/") if kind == "junit" else locator
        return (_basename_key(norm), name.strip().lower())
    return None


def result_key(suite_or_class: str, name: str) -> tuple[str, str]:
    return (_basename_key(suite_or_class.replace(".", "/")), name.strip().lower())


# -- parsers -------------------------------------------------------------------

@dataclass
class ParsedResult:
    suite: str
    name: str
    outcome: Outcome
    duration: float | None = None


def parse_report(path: Path) -> list[ParsedResult]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise TraceError(f"{path}: malformed XML ({exc})") from exc
    tag = root.tag.lower()
    if tag == "robot":
        return _parse_robot(root)
    if tag in ("testsuite", "testsuites"):
        return _parse_junit(root)
    raise TraceError(
        f"{path}: unrecognized root <{root.tag}> — expected Robot Framework "
        f"<robot> or JUnit <testsuite>/<testsuites>"
    )


def _parse_robot(root: ET.Element) -> list[ParsedResult]:
    out: list[ParsedResult] = []

    def walk(suite_el: ET.Element, prefix: str):
        name = suite_el.get("name", "")
        suite_path = f"{prefix}.{name}" if prefix else name
        for test in suite_el.findall("test"):
            status = test.find("status")
            raw = (status.get("status") if status is not None else "") or ""
            outcome = {"PASS": "pass", "FAIL": "fail", "SKIP": "skip",
                       "NOT RUN": "skip"}.get(raw.upper(), "fail")
            out.append(ParsedResult(suite=suite_path, name=test.get("name", ""),
                                    outcome=outcome))
        for child in suite_el.findall("suite"):
            walk(child, suite_path)

    for suite in root.findall("suite"):
        walk(suite, "")
    return out


def _parse_junit(root: ET.Element) -> list[ParsedResult]:
    out: list[ParsedResult] = []
    suites = root.findall(".//testsuite") if root.tag.lower() == "testsuites" else [root]
    for suite in suites:
        for case in suite.findall("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                outcome = "fail"
            elif case.find("skipped") is not None:
                outcome = "skip"
            else:
                outcome = "pass"
            duration = None
            try:
                duration = float(case.get("time")) if case.get("time") else None
            except ValueError:
                pass
            out.append(ParsedResult(
                suite=case.get("classname") or suite.get("name", ""),
                name=case.get("name", ""), outcome=outcome, duration=duration))
    return out


# -- store I/O -----------------------------------------------------------------

def results_path(store: Store) -> Path:
    return store.root / RESULTS_FILE


def ingest(store: Store, paths: list[Path], ts: str, source_names: list[str] | None = None
           ) -> dict:
    lines = []
    per_file = {}
    for i, path in enumerate(paths):
        results = parse_report(path)
        source = (source_names[i] if source_names else None) or path.name
        per_file[source] = len(results)
        for r in results:
            key = result_key(r.suite, r.name)
            lines.append({
                "ts": ts, "test_ref": f"{r.suite}::{r.name}", "key": list(key),
                "outcome": r.outcome, "source": source, "duration": r.duration,
            })
    with results_path(store).open("a") as f:
        for line in lines:
            f.write(json.dumps(line, sort_keys=True) + "\n")
    return {"ingested": len(lines), "per_source": per_file}


def read_results(store: Store) -> list[dict]:
    path = results_path(store)
    if not path.exists():
        return []
    out = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise TraceError(f"{path}:{lineno}: malformed result line") from exc
    return out


def history_for(results: list[dict], key: tuple[str, str]) -> list[dict]:
    return [r for r in results if tuple(r.get("key") or []) == key]


# -- coverage ------------------------------------------------------------------

STATE_ORDER = {"covered-failing": 0, "untested": 1, "charter-only": 2, "covered-passing": 3}


def _latest_outcome(results: list[dict], key: tuple[str, str]) -> str | None:
    hist = history_for(results, key)
    return hist[-1]["outcome"] if hist else None


def mitigation_state(mitigation: dict, results: list[dict]) -> str:
    tests = mitigation.get("tests") or []
    if not tests:
        return "untested"
    keys = [ref_key(t) for t in tests]
    real = [k for k in keys if k is not None]
    if not real:
        return "charter-only"
    outcomes = [_latest_outcome(results, k) for k in real]
    if any(o == "fail" for o in outcomes):
        return "covered-failing"
    if any(o == "pass" for o in outcomes):
        return "covered-passing"
    return "charter-only"  # real refs but no results yet


def _active_detection(risk: Risk, policy_id: str) -> int | None:
    for score in risk.scores:
        if score.policy == policy_id:
            return score.values.get("detection")
    return None


def trace_report(store: Store) -> dict:
    results = read_results(store)
    config = store.load_config_raw() or {}
    policy_id = config.get("scoring_policy", "sod-ap-v1")

    risks_out = []
    detection_notes = []
    for rf in store.load_risk_files():
        try:
            risk = Risk.model_validate(rf.data)
        except Exception:
            continue
        mit_states = []
        for mitigation in risk.mitigations:
            state = mitigation_state(mitigation.model_dump(mode="json"), results)
            mit_states.append({"id": mitigation.id, "lever": str(mitigation.lever),
                               "state": state})
            if str(mitigation.lever) == "detection" and state in (
                "covered-failing", "untested", "charter-only"
            ):
                detection = _active_detection(risk, policy_id)
                if detection is not None and detection <= DETECTION_CLAIM_THRESHOLD:
                    detection_notes.append(_detection_note(
                        risk, mitigation, detection, results))
        rollup = (min((s["state"] for s in mit_states), key=lambda s: STATE_ORDER[s])
                  if mit_states else "untested")
        risks_out.append({"risk": risk.id, "status": str(risk.status),
                          "rollup": rollup, "mitigations": mit_states})

    failing_risks = [r["risk"] for r in risks_out if r["rollup"] == "covered-failing"]
    return {
        "results_present": bool(results),
        "risks": risks_out,
        "failing_risks": failing_risks,
        "detection_notes": detection_notes,
    }


def _detection_note(risk: Risk, mitigation, detection: int, results: list[dict]) -> str:
    refs = [ref_key(t) for t in (mitigation.tests or [])]
    real = [(t, k) for t, k in zip(mitigation.tests or [], refs, strict=True) if k]
    if not real:
        return (f"{risk.id} detection scored {detection} but mitigation {mitigation.id} "
                f"has no concrete test (charter only) — detection is not earned")
    test_ref, key = real[0]
    hist = history_for(results, key)
    if not hist:
        detail = "has no results"
    else:
        window = hist[-HISTORY_N:]
        fails = sum(1 for h in window if h["outcome"] == "fail")
        detail = f"failed {fails} of last {len(window)} runs"
    return (f"{risk.id} detection scored {detection} but covering test {test_ref} "
            f"{detail} — re-score detection or fix the test")


def latest_result_for_ref(test_ref: str, results: list[dict]) -> str:
    key = ref_key(test_ref)
    if key is None:
        return "charter"
    outcome = _latest_outcome(results, key)
    return outcome or "none"
