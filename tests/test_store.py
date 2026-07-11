"""Unit tests for the store layer (discovery, round-trip, ids, events)."""

import pytest

from risqlet.model import Event
from risqlet.store import Store, StoreError, find_register, init_register

RISK_WITH_COMMENTS = """\
# reviewed in workshop 2026-07-01
schema_version: 1
id: R-0001
statement: Because the EC terminal acknowledges asynchronously, late confirmations may be lost
aspects:
  - iso25010.reliability   # ranked #1 this quarter
elicited_by:
  method: hazop
  prompt_ref: "guideword:LATE"
  evidence: []
scores:
  - policy: sod-ap-v1
    values: {severity: 7, occurrence: 5, detection: 8}
    rubric_anchors: ["sev7: revenue impact", "occ5: weekly", "det8: no check"]
status: proposed
mitigations: []
"""


@pytest.fixture
def register(tmp_path):
    risqlet = init_register(tmp_path, "demo")
    return Store(risqlet)


class TestInit:
    def test_scaffold(self, tmp_path):
        risqlet = init_register(tmp_path, "demo")
        assert (risqlet / "config.yaml").exists()
        assert (risqlet / "register").is_dir()
        assert (risqlet / "events.jsonl").exists()

    def test_refuses_existing_register(self, tmp_path):
        init_register(tmp_path, "demo")
        with pytest.raises(StoreError, match="refusing to overwrite"):
            init_register(tmp_path, "demo")


class TestDiscovery:
    def test_walk_up_from_subdirectory(self, tmp_path):
        risqlet = init_register(tmp_path, "demo")
        deep = tmp_path / "src" / "pkg" / "module"
        deep.mkdir(parents=True)
        assert find_register(start=deep) == risqlet

    def test_explicit_dir(self, tmp_path):
        risqlet = init_register(tmp_path, "demo")
        assert find_register(explicit=tmp_path) == risqlet
        assert find_register(explicit=risqlet) == risqlet

    def test_missing_register(self, tmp_path):
        with pytest.raises(StoreError, match="risqlet init"):
            find_register(start=tmp_path)
        with pytest.raises(StoreError, match="no .risqlet"):
            find_register(explicit=tmp_path)


class TestRoundTrip:
    def test_comments_preserved_on_rewrite(self, register):
        path = register.register_dir / "R-0001.yaml"
        path.write_text(RISK_WITH_COMMENTS)
        rf = register.load_risk_files()[0]
        rf.data["scores"][0]["derived"] = {"rpn": 280, "action_priority": "HIGH"}
        register.save_risk(rf)
        text = path.read_text()
        assert "# reviewed in workshop 2026-07-01" in text
        assert "# ranked #1 this quarter" in text
        assert "rpn: 280" in text

    def test_config_round_trip(self, register):
        cfg = register.load_config_raw()
        cfg["phase"] = "aspects"
        register.save_config_raw(cfg)
        text = register.config_path.read_text()
        assert "phase: aspects" in text
        assert "forced prioritization" in text  # starter comment survives


class TestIdAllocation:
    def test_first_ids(self, register):
        assert register.next_risk_id() == "R-0001"
        assert register.next_mitigation_id() == "M-0001"

    def test_allocation_after_gaps(self, register):
        (register.register_dir / "R-0002.yaml").write_text(
            RISK_WITH_COMMENTS.replace("R-0001", "R-0002")
        )
        (register.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_COMMENTS.replace("R-0001", "R-0007")
        )
        assert register.next_risk_id() == "R-0008"


class TestEvents:
    def test_append_and_read(self, register):
        register.append_event(
            Event.model_validate(
                {
                    "ts": "2026-07-10T12:00:00Z",
                    "type": "status_change",
                    "risk": "R-0001",
                    "from": "proposed",
                    "to": "reviewed",
                    "principal": "human:many",
                }
            )
        )
        events = register.read_events()
        assert len(events) == 1
        lineno, raw = events[0]
        assert lineno == 1
        assert raw["from"] == "proposed"
        assert raw["principal"] == "human:many"

    def test_malformed_line_raises_with_location(self, register):
        register.events_path.write_text('{"ok": 1}\nnot json\n')
        with pytest.raises(StoreError, match="events.jsonl:2"):
            register.read_events()


class TestInitDefaults:
    def test_fresh_init_enables_packaged_catalogs(self, tmp_path):
        from risqlet.validate import validate_register

        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        assert cfg["catalogs"] == ["iso25010", "techniques", "heuristics", "guidewords"]
        assert validate_register(store).passed
        # catalog-aware checks are active: a typo'd aspect in a loaded pack warns
        (store.register_dir / "R-0001.yaml").write_text(
            "schema_version: 1\nid: R-0001\nstatement: Because a, b may occur, causing c\n"
            "aspects: [iso25010.typo-aspect]\n"
            "elicited_by: {method: manual, evidence: [x.md]}\n"
            "status: proposed\nmitigations: []\n"
        )
        report = validate_register(store)
        assert report.passed
        assert any("typo-aspect" in f.message for f in report.findings)
