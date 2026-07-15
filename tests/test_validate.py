"""Tests for the validate pipeline and the score operation."""

from risqlet.findings import Severity
from risqlet.scoring import score_risks
from risqlet.validate import validate_register
from tests.conftest import append_raw_event, read_utf8


def errors(report):
    return [f for f in report.findings if f.severity == Severity.ERROR]


def warnings(report):
    return [f for f in report.findings if f.severity == Severity.WARNING]


class TestValidatePipeline:
    def test_populated_register_passes(self, populated_register):
        report = validate_register(populated_register)
        assert report.passed, [f.message for f in errors(report)]

    def test_speculative_warning_does_not_fail(self, populated_register):
        report = validate_register(populated_register)
        assert report.passed
        speculative = [f for f in warnings(report) if "speculative" in f.message]
        assert len(speculative) == 1
        assert "R-0002" in speculative[0].message

    def test_aggregates_multiple_findings(self, populated_register):
        # schema error in one file + lifecycle violation in another, one run
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("treatment: reduce",
                                                                 "treatment: wish"),
                                                                 encoding="utf-8")
        path2 = populated_register.register_dir / "R-0002.yaml"
        path2.write_text(path2.read_text(encoding="utf-8").replace("status: proposed",
                                                                   "status: accepted"),
                                                                   encoding="utf-8")
        report = validate_register(populated_register)
        assert not report.passed
        messages = [f.message for f in errors(report)]
        assert any("wish" in m or "treatment" in f.field
                   for m, f in zip(messages, errors(report), strict=True))
        assert any("does not match event replay" in m for m in messages)

    def test_dangling_mitigation_reference(self, populated_register):
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("risk_ids: [R-0001]",
                                                                 "risk_ids: [R-0009]"),
                                                                 encoding="utf-8")
        report = validate_register(populated_register)
        assert any("unknown risk R-0009" in f.message for f in errors(report))

    def test_duplicate_risk_id(self, populated_register):
        dup = (populated_register.register_dir / "R-0002.yaml").read_text(encoding="utf-8")
        (populated_register.register_dir / "R-0003.yaml").write_text(dup, encoding="utf-8")
        report = validate_register(populated_register)
        assert any("duplicate id R-0002" in f.message for f in errors(report))
        assert any("does not match id" in f.message for f in warnings(report))

    def test_tampered_derived_detected(self, populated_register):
        score_risks(populated_register)
        path = populated_register.register_dir / "R-0002.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("action_priority: HIGH",
                                                                 "action_priority: LOW"),
                                                                 encoding="utf-8")
        report = validate_register(populated_register)
        assert any("does not match policy computation" in f.message for f in errors(report))

    def test_unknown_extra_field_warns(self, populated_register):
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "x_annotation: from-a-future-layer\n",
                                       encoding="utf-8")
        report = validate_register(populated_register)
        assert report.passed
        assert any(f.field == "x_annotation" for f in warnings(report))

    def test_bad_aspect_format(self, populated_register):
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(
            path.read_text(encoding="utf-8").replace("[iso25010.reliability]", "['Reliability!']")
        , encoding="utf-8")
        report = validate_register(populated_register)
        assert any("namespaced catalog.slug" in f.message for f in errors(report))

    def test_agent_transition_rejected(self, populated_register):
        append_raw_event(
            populated_register,
            ts="2026-07-10T12:00:00Z", type="status_change", risk="R-0001",
            principal="agent:helper", note="", to="reviewed", **{"from": "proposed"},
        )
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("status: proposed",
                                                                 "status: reviewed"),
                                                                 encoding="utf-8")
        report = validate_register(populated_register)
        assert any("human principal" in f.message for f in errors(report))

    def test_human_transition_accepted(self, populated_register):
        append_raw_event(
            populated_register,
            ts="2026-07-10T12:00:00Z", type="status_change", risk="R-0001",
            principal="human:many", note="workshop", to="reviewed", **{"from": "proposed"},
        )
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("status: proposed",
                                                                 "status: reviewed"),
                                                                 encoding="utf-8")
        assert validate_register(populated_register).passed

    def test_aspect_constraint_enforced(self, populated_register):
        cfg = populated_register.load_config_raw()
        cfg["aspects"] = [
            {"id": f"iso25010.a{i}", "rank": i, "rationale": "r"} for i in range(1, 8)
        ]
        populated_register.save_config_raw(cfg)
        report = validate_register(populated_register)
        assert any("prioritize" in f.message for f in errors(report))

    def test_json_report_shape(self, populated_register):
        report = validate_register(populated_register).to_dict()
        assert report["pass"] is True
        assert set(report) == {"pass", "errors", "warnings", "findings"}
        for finding in report["findings"]:
            assert set(finding) == {"severity", "file", "field", "message"}


class TestScoreOperation:
    def test_batch_scoring_writes_derived_only(self, populated_register):
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        path = populated_register.register_dir / "R-0001.yaml"
        before = yaml.load(path.read_text(encoding="utf-8"))
        updated, findings = score_risks(populated_register)
        assert updated == 2 and not findings
        after = yaml.load(path.read_text(encoding="utf-8"))
        assert after["scores"][0].pop("derived") == {"rpn": 280, "action_priority": "HIGH"}
        assert after == before  # semantically nothing but derived changed

    def test_single_risk_scoring(self, populated_register):
        updated, findings = score_risks(populated_register, "R-0002")
        assert updated == 1 and not findings
        assert "derived" not in read_utf8(populated_register.register_dir / "R-0001.yaml")

    def test_unknown_risk_id(self, populated_register):
        updated, findings = score_risks(populated_register, "R-9999")
        assert updated == 0
        assert findings and "no risk with id" in findings[0].message

    def test_idempotent(self, populated_register):
        score_risks(populated_register)
        text = (populated_register.register_dir / "R-0001.yaml").read_text(encoding="utf-8")
        updated, _ = score_risks(populated_register)
        assert updated == 0
        assert (populated_register.register_dir / "R-0001.yaml").read_text(encoding="utf-8") == text

    def test_validate_after_score_passes(self, populated_register):
        score_risks(populated_register)
        assert validate_register(populated_register).passed
