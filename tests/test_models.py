"""Unit tests for the register document models (spec: risk-register)."""

import pytest
from pydantic import ValidationError

from risqlet.model import Config, Event, Mitigation, Risk
from risqlet.model.schema_gen import generate


def valid_risk_data(**overrides):
    data = {
        "id": "R-0001",
        "statement": "Because X, Y may occur, causing Z",
        "aspects": ["iso25010.security"],
        "elicited_by": {"method": "manual", "evidence": ["docs/adr-1.md"]},
        "status": "proposed",
    }
    data.update(overrides)
    return data


def valid_mitigation_data(**overrides):
    data = {
        "id": "M-0001",
        "risk_ids": ["R-0001"],
        "treatment": "reduce",
        "lever": "detection",
        "barrier": "detect",
        "concrete": "nightly reconciliation check",
        "residual_note": "chargebacks undetected until settlement",
    }
    data.update(overrides)
    return data


class TestRisk:
    def test_valid_risk_accepted(self):
        risk = Risk.model_validate(valid_risk_data())
        assert risk.id == "R-0001"
        assert risk.status == "proposed"

    @pytest.mark.parametrize("bad_id", ["R-12", "R-00001", "M-0001", "r-0001", ""])
    def test_malformed_id_rejected(self, bad_id):
        with pytest.raises(ValidationError):
            Risk.model_validate(valid_risk_data(id=bad_id))

    def test_empty_statement_rejected(self):
        with pytest.raises(ValidationError):
            Risk.model_validate(valid_risk_data(statement=""))

    def test_unknown_method_rejected(self):
        with pytest.raises(ValidationError):
            Risk.model_validate(valid_risk_data(elicited_by={"method": "vibes"}))

    def test_unknown_status_rejected(self):
        with pytest.raises(ValidationError):
            Risk.model_validate(valid_risk_data(status="wontfix"))

    def test_extra_fields_tolerated_and_reported(self):
        risk = Risk.model_validate(valid_risk_data(x_custom="annotation"))
        assert risk.extra_fields() == {"x_custom": "annotation"}


class TestMitigation:
    def test_valid_mitigation(self):
        m = Mitigation.model_validate(valid_mitigation_data())
        assert m.residual_note

    @pytest.mark.parametrize("field", ["residual_note", "concrete"])
    def test_mandatory_text_fields(self, field):
        with pytest.raises(ValidationError):
            Mitigation.model_validate(valid_mitigation_data(**{field: ""}))
        data = valid_mitigation_data()
        del data[field]
        with pytest.raises(ValidationError):
            Mitigation.model_validate(data)

    def test_empty_risk_ids_rejected(self):
        with pytest.raises(ValidationError):
            Mitigation.model_validate(valid_mitigation_data(risk_ids=[]))

    def test_malformed_id_rejected(self):
        with pytest.raises(ValidationError):
            Mitigation.model_validate(valid_mitigation_data(id="MIT-1"))


class TestConfig:
    def test_defaults(self):
        cfg = Config.model_validate({"project": "demo"})
        assert cfg.scoring_policy == "sod-ap-v1"
        assert cfg.constraints.max_aspects == 6
        assert cfg.constraints.max_top_risks == 10
        assert cfg.phase == "context"

    def test_aspect_requires_rationale_and_rank(self):
        with pytest.raises(ValidationError):
            Config.model_validate(
                {"project": "demo", "aspects": [{"id": "iso25010.security", "rank": 1}]}
            )
        with pytest.raises(ValidationError):
            Config.model_validate(
                {
                    "project": "demo",
                    "aspects": [{"id": "iso25010.security", "rank": 0, "rationale": "x"}],
                }
            )

    def test_aspect_id_format(self):
        with pytest.raises(ValidationError):
            Config.model_validate(
                {"project": "demo", "aspects": [{"id": "Security!", "rank": 1, "rationale": "x"}]}
            )


class TestEvent:
    def test_from_alias_round_trip(self):
        e = Event.model_validate(
            {
                "ts": "2026-07-10T12:00:00Z",
                "type": "status_change",
                "risk": "R-0001",
                "from": "proposed",
                "to": "reviewed",
                "principal": "human:many",
            }
        )
        assert e.from_ == "proposed"
        assert e.model_dump(by_alias=True)["from"] == "proposed"

    @pytest.mark.parametrize("bad", ["many", "root", "human", "bot:x:"[:4]])
    def test_principal_format(self, bad):
        with pytest.raises(ValidationError):
            Event.model_validate(
                {
                    "ts": "2026-07-10T12:00:00Z",
                    "type": "status_change",
                    "from": "proposed",
                    "to": "reviewed",
                    "principal": bad,
                }
            )


class TestSchemaGeneration:
    def test_deterministic(self):
        assert generate() == generate()

    def test_committed_schemas_up_to_date(self):
        from risqlet.model.schema_gen import SCHEMAS_DIR

        for filename, text in generate().items():
            committed = (SCHEMAS_DIR / filename).read_text(encoding="utf-8")
            assert committed == text, \
                f"{filename} is stale — run python -m risqlet.model.schema_gen"
