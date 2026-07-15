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
        path.write_text(RISK_WITH_COMMENTS, encoding="utf-8")
        rf = register.load_risk_files()[0]
        rf.data["scores"][0]["derived"] = {"rpn": 280, "action_priority": "HIGH"}
        register.save_risk(rf)
        text = path.read_text(encoding="utf-8")
        assert "# reviewed in workshop 2026-07-01" in text
        assert "# ranked #1 this quarter" in text
        assert "rpn: 280" in text

    def test_config_round_trip(self, register):
        cfg = register.load_config_raw()
        cfg["phase"] = "aspects"
        register.save_config_raw(cfg)
        text = register.config_path.read_text(encoding="utf-8")
        assert "phase: aspects" in text
        assert "forced prioritization" in text  # starter comment survives


class TestTextEncoding:
    """spec: risk-register — register files are UTF-8 on every platform.

    The suite could not catch the locale-encoding bug because nothing ever put a
    non-ASCII character through the store: on Linux/macOS the locale is UTF-8, so
    the omission was invisible, while on Windows (cp1252) `→` raised
    UnicodeEncodeError on write and `—` silently became `â€"` on read.
    """

    # → and 決済 cannot be encoded in cp1252 at all (hard crash);
    # — and “ ” can, but decode back as mojibake (silent corruption)
    NON_ASCII = "Because the flow reverts — request → timeout, 決済 may be “lost”"

    def test_non_ascii_risk_round_trips(self, register):
        path = register.register_dir / "R-0001.yaml"
        path.write_text(RISK_WITH_COMMENTS, encoding="utf-8")
        rf = register.load_risk_files()[0]
        rf.data["statement"] = self.NON_ASCII
        register.save_risk(rf)

        reloaded = register.load_risk_files()[0]
        assert reloaded.data["statement"] == self.NON_ASCII

    def test_risk_bytes_on_disk_are_utf8(self, register):
        """Reading back through the same wrong assumption that wrote it would pass
        even when both halves are broken — so assert the bytes, not the round-trip."""
        path = register.register_dir / "R-0001.yaml"
        path.write_text(RISK_WITH_COMMENTS, encoding="utf-8")
        rf = register.load_risk_files()[0]
        rf.data["statement"] = self.NON_ASCII
        register.save_risk(rf)

        raw = path.read_bytes()
        assert self.NON_ASCII in raw.decode("utf-8")  # not the host's locale
        with pytest.raises(UnicodeDecodeError):
            raw.decode("ascii")  # proves the fixture is actually exercising non-ASCII

    def test_writes_use_lf_not_the_host_line_ending(self, register):
        """Deterministic output cannot depend on the OS: text mode would emit CRLF
        on Windows for the same register."""
        path = register.register_dir / "R-0001.yaml"
        path.write_text(RISK_WITH_COMMENTS, encoding="utf-8")
        rf = register.load_risk_files()[0]
        register.save_risk(rf)
        assert b"\r\n" not in path.read_bytes()

    def test_config_non_ascii_round_trips(self, register):
        cfg = register.load_config_raw()
        cfg["project"] = "決済 — order → flow"
        register.save_config_raw(cfg)
        assert register.load_config_raw()["project"] == "決済 — order → flow"
        assert b"\r\n" not in register.config_path.read_bytes()

    def test_event_log_accepts_non_ascii(self, register):
        """The log round-trips non-ASCII, though not for the reason you'd expect.

        `json.dumps` defaults to ensure_ascii=True, so events.jsonl is written as
        pure ASCII with \\uXXXX escapes — which means it was never exposed to the
        locale-encoding bug, unlike the YAML register beside it. This test pins
        that: if someone ever passes ensure_ascii=False for readability, the file
        gains real non-ASCII bytes and the encoding on the handle starts to matter.
        """
        register.append_event(Event(
            ts="2026-07-15T00:00:00Z", type="status_change", risk="R-0001",
            **{"from": "proposed"}, to="reviewed", principal="human:tester",
            note=self.NON_ASCII))
        raw = register.events_path.read_bytes()
        assert register.read_events()[0][1]["note"] == self.NON_ASCII
        assert b"\r\n" not in raw

    def test_guard_is_armed(self, register, tmp_path):
        """The fix is only real if writing this text through the *locale* encoding
        would actually have failed — otherwise these assertions prove nothing."""
        probe = tmp_path / "probe.txt"
        with pytest.raises(UnicodeEncodeError):
            probe.write_text(self.NON_ASCII, encoding="cp1252")


class TestIdAllocation:
    def test_first_ids(self, register):
        assert register.next_risk_id() == "R-0001"
        assert register.next_mitigation_id() == "M-0001"

    def test_allocation_after_gaps(self, register):
        (register.register_dir / "R-0002.yaml").write_text(
            RISK_WITH_COMMENTS.replace("R-0001", "R-0002")
        , encoding="utf-8")
        (register.register_dir / "R-0007.yaml").write_text(
            RISK_WITH_COMMENTS.replace("R-0001", "R-0007")
        , encoding="utf-8")
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
        register.events_path.write_text('{"ok": 1}\nnot json\n', encoding="utf-8")
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
        , encoding="utf-8")
        report = validate_register(store)
        assert report.passed
        assert any("typo-aspect" in f.message for f in report.findings)
