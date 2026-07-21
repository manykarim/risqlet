"""Adversarial-review verdict rules (spec: adversarial-review).

The corroboration rule (distinct reviewers, not charge count) is load-bearing: the
experiment showed a charge-count rule flags everything, while distinct-reviewer
corroboration ships the sound decisions and flags only the weak ones.
"""

import json

import pytest

from risqlet.review import (
    ReviewError,
    compute_verdict,
    read_reviews,
    record_review,
    reviews_path,
)
from risqlet.store import Store, init_register


def rev(reviewer, *charges):
    """A review: reviewer id + charges as (category, severity, reproducible) tuples."""
    return {"reviewer": reviewer, "charges": [
        {"category": c, "severity": s, "reproducible": rp, "claim": "x"}
        for c, s, rp in charges]}


AUTHOR = "agent:writer"


class TestVerdictRules:
    def test_corroborated_fatal_blocks(self):
        v = compute_verdict(AUTHOR, [
            rev("a", ("hollow-test", "fatal", True)),
            rev("b", ("hollow-test", "fatal", True))])
        assert v["verdict"] == "BLOCK" and v["surviving"] == ["hollow-test"]

    def test_corroborated_major_remands(self):
        v = compute_verdict(AUTHOR, [
            rev("a", ("evidence-mismatch", "major", True)),
            rev("b", ("evidence-mismatch", "major", True))])
        assert v["verdict"] == "REMAND"

    def test_uncorroborated_charges_ship(self):
        # three different categories, each from one reviewer, no fatal -> SHIP
        v = compute_verdict(AUTHOR, [
            rev("a", ("wrong-priority", "major", True)),
            rev("b", ("evidence-mismatch", "major", True)),
            rev("c", ("unsupported-status", "major", True))])
        assert v["verdict"] == "SHIP" and v["surviving"] == []

    def test_one_reviewers_two_charges_do_not_corroborate(self):
        """The decisive flip: charge COUNT must not substitute for distinct reviewers."""
        v = compute_verdict(AUTHOR, [
            rev("a", ("evidence-mismatch", "major", True),
                     ("evidence-mismatch", "minor", True)),  # same reviewer, twice
            rev("b")])  # clean vote
        assert v["verdict"] == "SHIP"  # not REMAND — one reviewer is not corroboration

    def test_lone_fatal_remands(self):
        # one reviewer's reproducible fatal, uncorroborated -> REMAND (not SHIP, not BLOCK)
        v = compute_verdict(AUTHOR, [
            rev("a", ("dead-code-misread", "fatal", True)),
            rev("b"), rev("c")])
        assert v["verdict"] == "REMAND" and v["surviving"] == []

    def test_all_minor_ships(self):
        v = compute_verdict(AUTHOR, [
            rev("a", ("nit", "minor", True)),
            rev("b", ("nit", "minor", True))])  # even corroborated, minor never moves it
        assert v["verdict"] == "SHIP"

    def test_non_reproducible_charges_ignored(self):
        # two reviewers agree on a fatal, but neither marked it reproducible -> SHIP
        v = compute_verdict(AUTHOR, [
            rev("a", ("suspicion", "fatal", False)),
            rev("b", ("suspicion", "fatal", False))])
        assert v["verdict"] == "SHIP"

    def test_block_precedence_over_major(self):
        # a surviving fatal category wins over a surviving major category
        v = compute_verdict(AUTHOR, [
            rev("a", ("hollow-test", "fatal", True), ("evidence-mismatch", "major", True)),
            rev("b", ("hollow-test", "fatal", True), ("evidence-mismatch", "major", True))])
        assert v["verdict"] == "BLOCK"

    def test_deterministic(self):
        panel = [rev("a", ("x", "major", True)), rev("b", ("x", "major", True))]
        assert compute_verdict(AUTHOR, panel) == compute_verdict(AUTHOR, panel)


class TestPanelValidity:
    def test_fewer_than_two_reviewers_rejected(self):
        with pytest.raises(ReviewError, match="two independent reviewers"):
            compute_verdict(AUTHOR, [rev("a", ("x", "fatal", True))])

    def test_author_cannot_sit_on_panel(self):
        with pytest.raises(ReviewError, match="author"):
            compute_verdict(AUTHOR, [rev(AUTHOR, ("x", "major", True)), rev("b")])

    def test_duplicate_reviewer_rejected(self):
        with pytest.raises(ReviewError, match="more than once"):
            compute_verdict(AUTHOR, [rev("a"), rev("a")])

    def test_bad_severity_rejected(self):
        with pytest.raises(ReviewError, match="severity"):
            compute_verdict(AUTHOR, [
                {"reviewer": "a", "charges": [
                    {"category": "x", "severity": "catastrophic", "reproducible": True}]},
                rev("b")])

    def test_empty_reviewer_rejected(self):
        with pytest.raises(ReviewError, match="reviewer id"):
            compute_verdict(AUTHOR, [{"reviewer": "", "charges": []}, rev("b")])


class TestRecordAndRead:
    @pytest.fixture
    def store(self, tmp_path):
        return Store(init_register(tmp_path, "demo"))

    def test_record_appends_and_reads_back(self, store):
        panel = [rev("a", ("hollow-test", "fatal", True)),
                 rev("b", ("hollow-test", "fatal", True))]
        rec = record_review(store, "R-0001", AUTHOR, panel)
        assert rec["verdict"] == "BLOCK"
        back = read_reviews(store)
        assert len(back) == 1 and back[0]["decision"] == "R-0001"
        # the record carries the charges, so the verdict is recomputable
        assert back[0]["reviews"] == panel

    def test_record_is_utf8_lf(self, store):
        record_review(store, "R-0001", AUTHOR,
                      [rev("a", ("café — mismatch", "major", True)),
                       rev("b", ("café — mismatch", "major", True))])
        raw = reviews_path(store).read_bytes()
        raw.decode("utf-8")  # raises if not utf-8
        assert b"\r\n" not in raw

    def test_malformed_line_raises_with_context(self, store):
        reviews_path(store).write_text("{not json\n", encoding="utf-8")
        with pytest.raises(ReviewError, match="malformed review line"):
            read_reviews(store)

    def test_no_reviews_file_is_empty(self, store):
        assert read_reviews(store) == []


class TestReviewCLI:
    def _project(self, tmp_path):
        from risqlet.cli import main
        assert main(["init", "--dir", str(tmp_path)]) == 0
        (tmp_path / ".risqlet" / "register" / "R-0001.yaml").write_text(
            "schema_version: 1\nid: R-0001\n"
            "statement: Because tokens are logged, replay may occur, causing takeover\n"
            "aspects: [iso25010.security]\n"
            'elicited_by: {method: stride, evidence: ["src/a.py"]}\n'
            "scores: []\nstatus: proposed\nmitigations: []\n", encoding="utf-8")
        return main

    def test_block_exits_1_ship_exits_0(self, tmp_path):
        main = self._project(tmp_path)
        block = tmp_path / "block.json"
        block.write_text(json.dumps({"decision": "R-0001", "author": "agent:w", "reviews": [
            rev("a", ("hollow-test", "fatal", True)),
            rev("b", ("hollow-test", "fatal", True))]}), encoding="utf-8")
        assert main(["review", "--charges", str(block), "--dir", str(tmp_path)]) == 1
        ship = tmp_path / "ship.json"
        ship.write_text(json.dumps({"decision": "R-0001", "author": "agent:w",
                                    "reviews": [rev("a", ("nit", "minor", True)), rev("b")]}),
                        encoding="utf-8")
        assert main(["review", "--charges", str(ship), "--dir", str(tmp_path)]) == 0

    def test_review_does_not_change_risk_status(self, tmp_path):
        main = self._project(tmp_path)
        risk = tmp_path / ".risqlet" / "register" / "R-0001.yaml"
        before = risk.read_bytes()
        block = tmp_path / "block.json"
        block.write_text(json.dumps({"decision": "R-0001", "author": "agent:w", "reviews": [
            rev("a", ("hollow-test", "fatal", True)),
            rev("b", ("hollow-test", "fatal", True))]}), encoding="utf-8")
        main(["review", "--charges", str(block), "--dir", str(tmp_path)])
        assert risk.read_bytes() == before  # advisory — no state change

    def test_invalid_panel_is_clean_error_not_traceback(self, tmp_path, capsys):
        main = self._project(tmp_path)
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"decision": "R-0001", "reviews": [
            rev("a", ("x", "fatal", True))]}), encoding="utf-8")  # only 1 reviewer
        assert main(["review", "--charges", str(bad), "--dir", str(tmp_path)]) == 1
        err = capsys.readouterr().err
        assert "Traceback" not in err and "error:" in err

    def test_validate_catches_tampered_verdict(self, tmp_path):
        from risqlet.cli import main as cli_main
        main = self._project(tmp_path)
        block = tmp_path / "block.json"
        block.write_text(json.dumps({"decision": "R-0001", "author": "agent:w", "reviews": [
            rev("a", ("hollow-test", "fatal", True)),
            rev("b", ("hollow-test", "fatal", True))]}), encoding="utf-8")
        main(["review", "--charges", str(block), "--dir", str(tmp_path)])
        assert cli_main(["validate", "--dir", str(tmp_path)]) == 0  # honest verdict passes
        # tamper: flip the recorded BLOCK to SHIP
        rj = tmp_path / ".risqlet" / "reviews.jsonl"
        rj.write_text(rj.read_text(encoding="utf-8").replace('"BLOCK"', '"SHIP"'),
                      encoding="utf-8")
        assert cli_main(["validate", "--dir", str(tmp_path)]) == 1  # mismatch caught
