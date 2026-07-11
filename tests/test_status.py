"""Tests for risqlet status (spec: session-status)."""

import json

from risqlet.cli import main
from risqlet.scoring import score_risks
from risqlet.status import build_status
from risqlet.store import Store, init_register
from tests.conftest import append_raw_event


def snapshot(store: Store) -> dict:
    return {p.name: p.read_text() for p in store.root.rglob("*") if p.is_file()}


class TestBuildStatus:
    def test_empty_register(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        report = build_status(store)
        assert report["project"] == "demo"
        assert report["phase"] == "context"
        assert report["risks"] == {}
        assert report["pending"] == []
        assert report["last_event"] is None

    def test_mid_session(self, populated_register):
        report = build_status(populated_register)
        assert report["risks"] == {"proposed": 2}
        assert report["scoring"] == {"scored": 0, "unscored": 2}
        assert len(report["top_risks"]) == 2
        # R-0002 has no evidence -> speculative hint
        assert any("speculative" in h for h in report["pending"])

    def test_scored_risks_ranked_first(self, populated_register):
        score_risks(populated_register)
        report = build_status(populated_register)
        assert report["scoring"]["scored"] == 2
        assert report["top_risks"][0]["priority"] != "unscored"

    def test_reviewed_awaiting_scoring_hint(self, populated_register):
        append_raw_event(
            populated_register, ts="t", type="status_change", risk="R-0001",
            principal="human:many", note="", to="reviewed", **{"from": "proposed"})
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace("status: proposed", "status: reviewed"))
        report = build_status(populated_register)
        assert any("await scoring" in h and "R-0001" in h for h in report["pending"])

    def test_uncovered_accepted_hint(self, populated_register):
        path = populated_register.register_dir / "R-0002.yaml"
        path.write_text(path.read_text().replace("status: proposed", "status: accepted"))
        report = build_status(populated_register)
        assert any("lack mitigations" in h and "R-0002" in h for h in report["pending"])
        assert report["mitigation"]["uncovered"] == ["R-0002"]

    def test_phase_without_risks_hint(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        cfg["phase"] = "elicit"
        store.save_config_raw(cfg)
        report = build_status(store)
        assert any("no risks" in h for h in report["pending"])

    def test_aspects_phase_hint(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        cfg["phase"] = "aspects"
        store.save_config_raw(cfg)
        assert any("no quality aspects" in h for h in build_status(store)["pending"])

    def test_invalid_file_tolerated_and_named(self, populated_register):
        (populated_register.register_dir / "R-0099.yaml").write_text("id: nope\n")
        report = build_status(populated_register)
        assert "R-0099.yaml" in report["invalid_files"]
        assert any("unparseable" in h for h in report["pending"])
        assert report["risks"] == {"proposed": 2}  # valid files still counted

    def test_read_only(self, populated_register):
        before = snapshot(populated_register)
        build_status(populated_register)
        assert snapshot(populated_register) == before

    def test_last_event(self, populated_register):
        append_raw_event(
            populated_register, ts="2026-07-10T12:00:00Z", type="phase_change",
            principal="human:many", note="", to="aspects", **{"from": "context"})
        cfg = populated_register.load_config_raw()
        cfg["phase"] = "aspects"
        cfg["aspects"] = [{"id": "iso25010.security", "rank": 1, "rationale": "x"}]
        populated_register.save_config_raw(cfg)
        report = build_status(populated_register)
        assert report["last_event"]["principal"] == "human:many"
        assert report["aspects"] == [{"rank": 1, "id": "iso25010.security"}]


class TestStatusCli:
    def test_json_shape(self, populated_register, capsys):
        assert main(["status", "--dir", str(populated_register.root), "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert set(report) >= {"project", "phase", "aspects", "risks", "scoring",
                               "mitigation", "top_risks", "pending", "last_event",
                               "invalid_files"}

    def test_human_output(self, populated_register, capsys):
        assert main(["status", "--dir", str(populated_register.root)]) == 0
        out = capsys.readouterr().out
        assert "phase: context" in out and "R-0001" in out

    def test_missing_register_fails(self, tmp_path, capsys):
        assert main(["status", "--dir", str(tmp_path)]) == 1
