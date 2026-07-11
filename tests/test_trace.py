"""Tests for the trace loop: parsers, resolver, coverage, detection evidence."""

import pytest

from risqlet.store import Store, init_register
from risqlet.trace import (
    TraceError,
    ingest,
    mitigation_state,
    parse_report,
    read_results,
    ref_key,
    result_key,
    trace_report,
)
from risqlet.validate import validate_register

RF_XML = """<?xml version="1.0"?>
<robot>
  <suite name="Reconciliation">
    <test name="Nightly Settlement Match"><status status="PASS"/></test>
    <test name="Intraday Check"><status status="FAIL"/></test>
    <suite name="Sub">
      <test name="Nested Case"><status status="SKIP"/></test>
    </suite>
  </suite>
</robot>
"""

JUNIT_XML = """<?xml version="1.0"?>
<testsuite name="pkg">
  <testcase classname="tests.test_pay" name="test_ok" time="0.1"/>
  <testcase classname="tests.test_pay" name="test_bad" time="0.2">
    <failure message="boom">trace</failure>
  </testcase>
  <testcase classname="tests.test_pay" name="test_err"><error/></testcase>
  <testcase classname="tests.test_pay" name="test_skip"><skipped/></testcase>
</testsuite>
"""


@pytest.fixture
def store(tmp_path):
    return Store(init_register(tmp_path, "demo"))


def write_report(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return p


class TestParsers:
    def test_robot(self, tmp_path):
        results = parse_report(write_report(tmp_path, "output.xml", RF_XML))
        by_name = {r.name: r.outcome for r in results}
        assert by_name == {"Nightly Settlement Match": "pass",
                           "Intraday Check": "fail", "Nested Case": "skip"}

    def test_junit(self, tmp_path):
        results = parse_report(write_report(tmp_path, "j.xml", JUNIT_XML))
        by_name = {r.name: r.outcome for r in results}
        assert by_name == {"test_ok": "pass", "test_bad": "fail",
                           "test_err": "fail", "test_skip": "skip"}

    def test_unknown_root(self, tmp_path):
        with pytest.raises(TraceError, match="unrecognized root"):
            parse_report(write_report(tmp_path, "x.xml", "<other/>"))

    def test_malformed(self, tmp_path):
        with pytest.raises(TraceError, match="malformed"):
            parse_report(write_report(tmp_path, "x.xml", "<robot><unclosed>"))


class TestResolver:
    def test_rf_ref(self):
        assert ref_key("rf:suites/reconciliation.robot::Nightly Settlement Match") == \
            ("reconciliation", "nightly settlement match")

    def test_pytest_ref(self):
        assert ref_key("pytest:tests/test_pay.py::test_bad") == ("test_pay", "test_bad")

    def test_junit_ref(self):
        assert ref_key("junit:tests.test_pay::test_bad") == ("test_pay", "test_bad")

    def test_charter_never_matches(self):
        assert ref_key("charter:reconcile settlement vs journal") is None

    def test_cross_convention_match(self):
        assert ref_key("rf:suites/reconciliation.robot::Nightly Settlement Match") == \
            result_key("Reconciliation", "Nightly Settlement Match")
        assert ref_key("junit:tests.test_pay::test_bad") == \
            result_key("tests.test_pay", "test_bad")


def mitigation(mid, tests, lever="detection"):
    return {"id": mid, "risk_ids": ["R-0001"], "treatment": "reduce", "lever": lever,
            "barrier": "detect", "concrete": "x", "residual_note": "gap", "tests": tests}


class TestCoverage:
    def test_states(self, store, tmp_path):
        ingest(store, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        results = read_results(store)
        assert mitigation_state(mitigation("M1", []), results) == "untested"
        assert mitigation_state(
            mitigation("M2", ["charter:do a thing"]), results) == "charter-only"
        assert mitigation_state(
            mitigation("M3", ["pytest:tests/test_pay.py::test_ok"]), results) == "covered-passing"
        assert mitigation_state(
            mitigation("M4", ["pytest:tests/test_pay.py::test_bad"]), results) == "covered-failing"
        # real ref, no result yet
        assert mitigation_state(
            mitigation("M5", ["pytest:tests/test_pay.py::test_absent"]), results) == "charter-only"

    def test_failing_dominates(self, store, tmp_path):
        ingest(store, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        results = read_results(store)
        state = mitigation_state(mitigation(
            "M", ["pytest:tests/test_pay.py::test_ok",
                  "pytest:tests/test_pay.py::test_bad"]), results)
        assert state == "covered-failing"

    def test_ingest_history_and_append(self, store, tmp_path):
        ingest(store, [write_report(tmp_path, "a.xml", JUNIT_XML)], ts="t1")
        ingest(store, [write_report(tmp_path, "b.xml", JUNIT_XML)], ts="t2")
        results = read_results(store)
        assert len(results) == 8  # 4 tests x 2 ingests
        assert {r["ts"] for r in results} == {"t1", "t2"}


RISK_WITH_DETECTION = """\
schema_version: 1
id: R-0007
statement: Because logs leak tokens, replay may occur, causing takeover
aspects: [iso25010.security]
elicited_by: {{method: stride, evidence: ["src/x.py"]}}
scores:
  - policy: sod-ap-v1
    values: {{severity: 8, occurrence: 3, detection: 3}}
    rubric_anchors: ["s", "o", "d"]
status: accepted
mitigations:
  - id: M-0001
    risk_ids: [R-0007]
    treatment: reduce
    lever: detection
    barrier: detect
    concrete: alert on token in logs
    residual_note: window remains
    tests: ["{test}"]
"""


class TestDetectionEvidence:
    def test_failing_detection_flagged(self, store, tmp_path):
        (store.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_DETECTION.format(test="pytest:tests/test_pay.py::test_bad"))
        ingest(store, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        report = trace_report(store)
        assert report["detection_notes"]
        note = report["detection_notes"][0]
        assert "R-0007" in note and "detection scored 3" in note and "failed" in note

    def test_charter_detection_flagged(self, store, tmp_path):
        (store.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_DETECTION.format(test="charter:write the alert test"))
        report = trace_report(store)
        assert any("not earned" in n for n in report["detection_notes"])

    def test_passing_detection_not_flagged(self, store, tmp_path):
        (store.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_DETECTION.format(test="pytest:tests/test_pay.py::test_ok"))
        ingest(store, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        assert trace_report(store)["detection_notes"] == []

    def test_rollup_and_failing_risks(self, store, tmp_path):
        (store.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_DETECTION.format(test="pytest:tests/test_pay.py::test_bad"))
        ingest(store, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        report = trace_report(store)
        assert report["failing_risks"] == ["R-0007"]


class TestIntegration:
    def test_validate_unaffected_by_results(self, populated_register, tmp_path):
        before = validate_register(populated_register).to_dict()
        ingest(populated_register, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        after = validate_register(populated_register).to_dict()
        assert before == after

    def test_status_failing_hint(self, populated_register, tmp_path):
        from risqlet.status import build_status

        # accept R-0001 and point its mitigation at a failing test
        path = populated_register.register_dir / "R-0001.yaml"
        text = path.read_text().replace("status: proposed", "status: accepted")
        text = text.replace(
            'tests: ["rf:suites/reconciliation.robot::Nightly Settlement Match"]',
            'tests: ["pytest:tests/test_pay.py::test_bad"]')
        path.write_text(text)
        ingest(populated_register, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        report = build_status(populated_register)
        assert any("failing mitigation tests" in h and "R-0001" in h
                   for h in report["pending"])

    def test_strategy_failing_subsection(self, populated_register, tmp_path):
        from risqlet.exports.renderers import render_strategy_md

        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            'tests: ["rf:suites/reconciliation.robot::Nightly Settlement Match"]',
            'tests: ["pytest:tests/test_pay.py::test_bad"]'))
        ingest(populated_register, [write_report(tmp_path, "j.xml", JUNIT_XML)], ts="t")
        md = render_strategy_md(populated_register)
        assert "### Mitigations with failing or missing tests" in md
        assert "covered-failing" in md
