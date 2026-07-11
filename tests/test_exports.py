"""Tests for the export renderers (spec: risqlet-cli, export requirement)."""

from risqlet.exports.renderers import (
    render_register_yaml,
    render_strategy_md,
    render_trace_matrix_csv,
)
from risqlet.scoring import score_risks
from tests.conftest import RISK_2


class TestStrategyMd:
    def test_sections_present(self, populated_register):
        score_risks(populated_register)
        md = render_strategy_md(populated_register)
        assert "# Test Strategy: demo" in md
        assert "## Quality aspects" in md
        assert "## Top risks" in md
        assert "## Mitigations" in md
        assert "## What this does not cover" in md

    def test_residual_notes_aggregated(self, populated_register):
        md = render_strategy_md(populated_register)
        assert "chargebacks initiated at the issuer" in md
        assert "M-0001" in md

    def test_residual_section_without_mitigations(self, populated_register):
        # strip mitigations from R-0001
        path = populated_register.register_dir / "R-0001.yaml"
        text = path.read_text()
        path.write_text(text[: text.index("mitigations:")] + "mitigations: []\n")
        md = render_strategy_md(populated_register)
        assert "## What this does not cover" in md
        assert "remains unmitigated residual risk" in md

    def test_ranking_by_priority(self, populated_register):
        score_risks(populated_register)
        md = render_strategy_md(populated_register)
        # R-0002 (S9 -> HIGH, rpn 162) vs R-0001 (S7/O5 -> HIGH, rpn 280):
        # same band, higher rpn wins the tiebreak
        assert md.index("R-0001") < md.index("R-0002")

    def test_constraint_capping(self, populated_register):
        score_risks(populated_register)
        for i in range(3, 15):
            (populated_register.register_dir / f"R-{i:04d}.yaml").write_text(
                RISK_2.replace("R-0002", f"R-{i:04d}")
            )
        md = render_strategy_md(populated_register)
        assert "_4 further risk(s) are tracked in the register" in md

    def test_speculative_risks_listed(self, populated_register):
        md = render_strategy_md(populated_register)
        assert "Speculative (evidence-free) risks" in md
        assert "R-0002" in md.split("Speculative")[1]

    def test_deterministic(self, populated_register):
        score_risks(populated_register)
        assert render_strategy_md(populated_register) == render_strategy_md(populated_register)


class TestOtherFormats:
    def test_register_yaml_bundle(self, populated_register):
        out = render_register_yaml(populated_register)
        assert "R-0001" in out and "R-0002" in out and "project: demo" in out
        assert render_register_yaml(populated_register) == out  # deterministic

    def test_trace_matrix(self, populated_register):
        out = render_trace_matrix_csv(populated_register)
        lines = out.strip().splitlines()
        assert lines[0] == "aspect,risk,mitigation,test,result"
        expected = ("iso25010.reliability,R-0001,M-0001,"
                    "rf:suites/reconciliation.robot::Nightly Settlement Match")
        row = next(line for line in lines if expected in line)
        # no results ingested yet -> the charter/real ref shows "none"
        assert row.endswith(",none")
        # risk without mitigations still appears
        assert any(line.startswith("iso25010.security,R-0002,,,") for line in lines)
