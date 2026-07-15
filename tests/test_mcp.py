"""Tests for the MCP adapter: tool functions, gates, server guard, e2e."""

import pytest

from risqlet.mcp import tools as t
from risqlet.skills import skills_root
from tests.conftest import read_utf8


@pytest.fixture
def project(tmp_path):
    t.tool_init_register(str(tmp_path), "mcp-demo")
    return str(tmp_path)


def make_risk(project, statement="Because X, Y may occur, causing Z", **kw):
    return t.tool_upsert_risk(
        project,
        statement=statement,
        aspects=kw.pop("aspects", ["iso25010.reliability"]),
        elicited_by=kw.pop(
            "elicited_by",
            {"method": "manual", "evidence": ["docs/x.md"]},
        ),
        **kw,
    )


class TestCoreTools:
    def test_init_and_validate(self, tmp_path):
        result = t.tool_init_register(str(tmp_path))
        assert result["created"].endswith(".risqlet")
        report = t.tool_validate_register(str(tmp_path))
        assert report["pass"] is True

    def test_init_refuses_existing(self, project):
        with pytest.raises(t.ToolError, match="refusing to overwrite"):
            t.tool_init_register(project)

    def test_missing_register_actionable(self, tmp_path):
        with pytest.raises(t.ToolError, match="init_register first"):
            t.tool_validate_register(str(tmp_path))

    def test_score_and_export_parity(self, project):
        make_risk(project, scores=[{
            "policy": "sod-ap-v1",
            "values": {"severity": 7, "occurrence": 5, "detection": 8},
            "rubric_anchors": ["s", "o", "d"],
        }])
        result = t.tool_score_risks(project)
        assert result == {"updated": 1, "findings": []}
        one = t.tool_export_register(project, "strategy-md")
        two = t.tool_export_register(project, "strategy-md")
        assert one == two
        assert "action_priority=HIGH" in one["content"]

    def test_export_unknown_format(self, project):
        with pytest.raises(t.ToolError, match="unknown format"):
            t.tool_export_register(project, "pdf")


class TestCatalogAndGuidance:
    def test_browse_list_pack(self, project):
        result = t.tool_browse_catalog(project, action="list", pack="guidewords")
        assert all(e["id"].startswith("guidewords.") for e in result["entries"])

    def test_browse_search(self):
        result = t.tool_browse_catalog(action="search", terms=["reconciliation"])
        assert any(r["id"] == "techniques.data-reconciliation" for r in result["results"])

    def test_browse_show_and_errors(self):
        entry = t.tool_browse_catalog(action="show", entry_id="heuristics.premortem")
        assert entry["name"] == "Pre-mortem"
        with pytest.raises(t.ToolError, match="no catalog entry"):
            t.tool_browse_catalog(action="show", entry_id="heuristics.nope")
        with pytest.raises(t.ToolError, match="unknown action"):
            t.tool_browse_catalog(action="recommend")

    def test_guidance_parity_with_skills(self):
        result = t.tool_get_guidance("phases")
        expected = read_utf8(skills_root() / "risk-analysis/references/phases.md")
        assert result["content"] == expected

    def test_guidance_unknown_topic(self):
        with pytest.raises(t.ToolError, match="valid:"):
            t.tool_get_guidance("magic")

    def test_all_topics_resolve(self):
        for topic in t.GUIDANCE_TOPICS:
            assert t.tool_get_guidance(topic)["content"]


class TestGatePreservingWrites:
    def test_upsert_creates_proposed(self, project):
        result = make_risk(project)
        assert result["id"] == "R-0001"
        report = t.tool_validate_register(project)
        assert report["pass"] is True

    def test_status_smuggling_rejected(self, project):
        with pytest.raises(t.ToolError, match="proposed"):
            make_risk(project, status="accepted")
        with pytest.raises(t.ToolError, match="derived"):
            make_risk(project, scores=[{
                "policy": "sod-ap-v1",
                "values": {"severity": 1, "occurrence": 1, "detection": 1},
                "rubric_anchors": ["a", "b", "c"],
                "derived": {"action_priority": "HIGH"},
            }])

    def test_upsert_rejects_non_proposed_target(self, project):
        rid = make_risk(project)["id"]
        t.tool_record_decision(
            project, type="status_change", risk_id=rid,
            from_state="proposed", to_state="reviewed", principal="human:many",
        )
        with pytest.raises(t.ToolError, match="only 'proposed'"):
            make_risk(project, risk_id=rid, statement="Because A, B may occur, causing C")

    def test_upsert_update_existing(self, project):
        rid = make_risk(project)["id"]
        updated = make_risk(project, risk_id=rid,
                            statement="Because A2, B2 may occur, causing C2")
        assert updated["id"] == rid
        content = t.tool_export_register(project, "register-yaml")["content"]
        assert "A2" in content and content.count("R-0001") >= 1

    def test_add_mitigation_requires_residual(self, project):
        rid = make_risk(project)["id"]
        with pytest.raises(t.ToolError, match="residual_note"):
            t.tool_add_mitigation(
                project, rid, treatment="reduce", lever="detection",
                barrier="detect", concrete="do the thing", residual_note="",
            )
        result = t.tool_add_mitigation(
            project, rid, treatment="reduce", lever="detection", barrier="detect",
            concrete="nightly check", residual_note="only catches next-day",
        )
        assert result == {"id": "M-0001", "risk_id": rid}

    def test_record_decision_rejects_agent_principal(self, project):
        rid = make_risk(project)["id"]
        with pytest.raises(t.ToolError, match="human principal"):
            t.tool_record_decision(
                project, type="status_change", risk_id=rid,
                from_state="proposed", to_state="reviewed",
                principal="agent:helper",
            )

    def test_record_decision_keeps_register_consistent(self, project):
        rid = make_risk(project)["id"]
        result = t.tool_record_decision(
            project, type="status_change", risk_id=rid,
            from_state="proposed", to_state="reviewed",
            principal="human:many", note="review meeting",
        )
        assert result["recorded"] and result["validate"]["pass"] is True
        bundle = t.tool_export_register(project, "register-yaml")["content"]
        assert "status: reviewed" in bundle

    def test_illegal_transition_surfaced(self, project):
        rid = make_risk(project)["id"]
        result = t.tool_record_decision(
            project, type="status_change", risk_id=rid,
            from_state="proposed", to_state="closed", principal="human:many",
        )
        assert result["validate"]["pass"] is False


class TestServerGuard:
    def test_exactly_nine_tools(self):
        import anyio

        from risqlet.mcp.server import build_server

        tools = anyio.run(build_server().list_tools)
        assert sorted(tool.name for tool in tools) == sorted(t.ALL_TOOLS)
        assert len(tools) == 9


class TestMcpOnlyWorkflow:
    def test_end_to_end(self, tmp_path):
        project = str(tmp_path)
        assert "phases" in t.tool_get_guidance("overview")["content"].lower()
        t.tool_init_register(project, "e2e")
        r1 = make_risk(project, scores=[{
            "policy": "sod-ap-v1",
            "values": {"severity": 7, "occurrence": 5, "detection": 8},
            "rubric_anchors": ["sev7: x", "occ5: y", "det8: z"],
        }])["id"]
        r2 = make_risk(
            project,
            statement="Because tokens are logged, replay may occur, causing takeover",
            aspects=["iso25010.security"],
            elicited_by={"method": "stride",
                         "prompt_ref": "guidewords.threat-categories:spoofing",
                         "evidence": []},
        )["id"]
        assert t.tool_score_risks(project)["updated"] == 1
        t.tool_record_decision(project, type="status_change", risk_id=r1,
                               from_state="proposed", to_state="reviewed",
                               principal="human:many")
        t.tool_add_mitigation(
            project, r1, treatment="reduce", lever="detection", barrier="detect",
            concrete="nightly reconciliation", residual_note="intra-day gap remains",
            tests=["charter:reconcile settlement vs journal"],
        )
        report = t.tool_validate_register(project)
        assert report["pass"] is True
        assert any("speculative" in f["message"] for f in report["findings"]
                   if f["severity"] == "warning" and r2 in f["message"])
        strategy = t.tool_export_register(project, "strategy-md")["content"]
        assert "intra-day gap remains" in strategy
