"""Tests for dedupe clustering, mechanical merge, and scoring disagreement."""

import pytest

from risqlet.ensemble import EnsembleError, find_clusters, merge, similarity
from risqlet.scoring import score_risks
from risqlet.status import build_status
from risqlet.store import Store, init_register
from risqlet.validate import validate_register
from tests.conftest import read_utf8

RISK_TEMPLATE = """\
schema_version: 1
id: {id}
statement: {statement}
aspects: [{aspects}]
elicited_by:
  method: {method}
  prompt_ref: "{prompt_ref}"
  evidence: [{evidence}]
scores: {scores}
status: {status}
mitigations: {mitigations}
"""


def write_risk(store, id, statement, aspects="iso25010.reliability", method="manual",
               prompt_ref="", evidence='"src/pay/terminal.py"', scores="[]",
               status="proposed", mitigations="[]"):
    (store.register_dir / f"{id}.yaml").write_text(RISK_TEMPLATE.format(
        id=id, statement=statement, aspects=aspects, method=method,
        prompt_ref=prompt_ref, evidence=evidence, scores=scores,
        status=status, mitigations=mitigations), encoding="utf-8")


@pytest.fixture
def store(tmp_path):
    return Store(init_register(tmp_path, "demo"))


NEAR_DUP_A = ("Because the payment terminal acknowledges asynchronously, a late "
              "confirmation may be recorded as failed, causing double charges")
NEAR_DUP_B = ("Because the terminal acknowledges payment asynchronously, late "
              "confirmations may be recorded as failed, causing customers double charges")
UNRELATED = ("Because session tokens appear in debug logs, an attacker may replay "
             "sessions, causing account takeover")


class TestDedupe:
    def test_near_duplicates_clustered(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0002", NEAR_DUP_B)
        write_risk(store, "R-0003", UNRELATED, aspects="iso25010.security",
                   evidence='"src/auth/logging.py"')
        clusters = find_clusters(store)
        assert len(clusters) == 1
        assert clusters[0].members == ["R-0001", "R-0002"]
        assert "R-0001~R-0002" in clusters[0].pairs

    def test_unrelated_not_clustered(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0003", UNRELATED, aspects="iso25010.security",
                   evidence='"src/auth/logging.py"')
        assert find_clusters(store) == []

    def test_evidence_overlap_contributes(self, store):
        base = "Because X happens in the flow, Y may occur, causing Z for users"
        other = "Because Q diverges under load, W may occur, causing V downstream"
        write_risk(store, "R-0001", base)
        write_risk(store, "R-0002", other)  # same evidence + aspects, different words
        score = similarity(
            store.load_risk_files()[0].data, store.load_risk_files()[1].data
        )
        # aspects (0.2) + evidence (0.2) present, tokens low
        assert 0.3 < score < 0.5

    def test_threshold_configurable(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0002", NEAR_DUP_B)
        assert find_clusters(store)  # clustered at default 0.5
        cfg = store.load_config_raw()
        cfg["constraints"]["dedupe_threshold"] = 0.95
        store.save_config_raw(cfg)
        assert find_clusters(store) == []

    def test_survivor_prefers_more_evidence(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0002", NEAR_DUP_B,
                   evidence='"src/pay/terminal.py", "docs/adr/007.md"')
        clusters = find_clusters(store)
        assert clusters[0].suggested_survivor == "R-0002"

    def test_deterministic_and_read_only(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0002", NEAR_DUP_B)
        before = {p.name: p.read_text(encoding="utf-8") for p in store.register_dir.iterdir()}
        first = [c.to_dict() for c in find_clusters(store)]
        second = [c.to_dict() for c in find_clusters(store)]
        assert first == second
        assert {p.name: read_utf8(p) for p in store.register_dir.iterdir()} == before


class TestMerge:
    def _mitigation(self, mid, rid):
        return (f'[{{id: {mid}, risk_ids: [{rid}], treatment: reduce, lever: detection, '
                f'barrier: detect, concrete: check things, '
                f'residual_note: some gap remains, tests: []}}]')

    def test_full_merge(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A,
                   mitigations=self._mitigation("M-0001", "R-0001"))
        write_risk(store, "R-0002", NEAR_DUP_B, prompt_ref="heuristics.premortem",
                   evidence='"docs/adr/007.md"',
                   mitigations=self._mitigation("M-0002", "R-0002"))
        result = merge(store, "R-0001", ["R-0002"])
        assert result == {"survivor": "R-0001", "merged": ["R-0002"],
                          "moved_mitigations": 1}
        assert not (store.register_dir / "R-0002.yaml").exists()
        survivor = store.load_risk_files()[0].data
        assert survivor["elicited_by"]["evidence"] == [
            "src/pay/terminal.py", "docs/adr/007.md"]
        assert [m["id"] for m in survivor["mitigations"]] == ["M-0001", "M-0002"]
        assert survivor["mitigations"][1]["risk_ids"] == ["R-0001"]
        assert survivor["merged_from"][0]["id"] == "R-0002"
        assert survivor["merged_from"][0]["prompt_ref"] == "heuristics.premortem"
        report = validate_register(store)
        assert report.passed, [f.message for f in report.findings]

    def test_reviewed_duplicate_refused(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        write_risk(store, "R-0002", NEAR_DUP_B, status="reviewed")
        before = {p.name: p.read_text(encoding="utf-8") for p in store.register_dir.iterdir()}
        with pytest.raises(EnsembleError, match="only 'proposed'"):
            merge(store, "R-0001", ["R-0002"])
        assert {p.name: read_utf8(p) for p in store.register_dir.iterdir()} == before

    def test_terminal_survivor_refused(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, status="rejected")
        write_risk(store, "R-0002", NEAR_DUP_B)
        with pytest.raises(EnsembleError, match="terminal"):
            merge(store, "R-0001", ["R-0002"])

    def test_unknown_ids_refused(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A)
        with pytest.raises(EnsembleError, match="no risk"):
            merge(store, "R-0001", ["R-0009"])
        with pytest.raises(EnsembleError, match="no risk"):
            merge(store, "R-0009", ["R-0001"])
        with pytest.raises(EnsembleError, match="own duplicate"):
            merge(store, "R-0001", ["R-0001"])


TWO_SCORES = """
  - policy: sod-ap-v1
    values: {severity: 4, occurrence: 5, detection: 5}
    rubric_anchors: ["sev4: a", "occ5: b", "det5: c"]
    scored_by: ["agent:ux-persona"]
  - policy: sod-ap-v1
    values: {severity: 8, occurrence: 5, detection: 5}
    rubric_anchors: ["sev8: a", "occ5: b", "det5: c"]
    scored_by: ["agent:security-persona"]
"""


class TestDisagreement:
    def test_spread_computed(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, scores=TWO_SCORES)
        updated, findings = score_risks(store)
        assert updated == 1 and not findings
        data = store.load_risk_files()[0].data
        assert data["disagreement"]["factors"]["severity"] == 0.44
        assert data["disagreement"]["factors"]["occurrence"] == 0.0
        assert data["disagreement"]["value"] == round((0.44 + 0 + 0) / 3, 2)
        assert validate_register(store).passed

    def test_single_set_no_disagreement(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, scores="""
  - policy: sod-ap-v1
    values: {severity: 4, occurrence: 5, detection: 5}
    rubric_anchors: ["a", "b", "c"]
""")
        score_risks(store)
        assert "disagreement" not in store.load_risk_files()[0].data

    def test_removed_when_sets_drop(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, scores=TWO_SCORES)
        score_risks(store)
        rf = store.load_risk_files()[0]
        del rf.data["scores"][1]
        store.save_risk(rf)
        score_risks(store)
        assert "disagreement" not in store.load_risk_files()[0].data

    def test_other_policy_ignored(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, scores="""
  - policy: sod-ap-v1
    values: {severity: 4, occurrence: 5, detection: 5}
    rubric_anchors: ["a", "b", "c"]
  - policy: li-v1
    values: {likelihood: 3, impact: 3}
    rubric_anchors: ["a", "b"]
""")
        score_risks(store)
        assert "disagreement" not in store.load_risk_files()[0].data

    def test_tampered_disagreement_detected(self, store):
        write_risk(store, "R-0001", NEAR_DUP_A, scores=TWO_SCORES)
        score_risks(store)
        path = store.register_dir / "R-0001.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("value: 0.15", "value: 0.01"),
                                                                 encoding="utf-8")
        report = validate_register(store)
        assert any("disagreement" in f.field for f in report.findings
                   if f.severity == "error")

    def test_status_contested_hint(self, store):
        # widen the spread so value > 0.25: severity 1 vs 10 -> 1.0; mean 0.33
        write_risk(store, "R-0001", NEAR_DUP_A, scores=TWO_SCORES.replace(
            "severity: 4", "severity: 1").replace("severity: 8", "severity: 10"))
        score_risks(store)
        report = build_status(store)
        assert any("contested scores" in h and "R-0001" in h for h in report["pending"])
