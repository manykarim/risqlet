"""Unit tests for the scoring policy engine and packaged packs."""

import pytest

from risqlet.policies.engine import Policy, PolicyError, ScoringError, load_policy


def anchors(n):
    return [f"anchor-{i}" for i in range(n)]


@pytest.fixture
def sod_policy():
    return load_policy("sod-ap-v1")


@pytest.fixture
def li_policy():
    return load_policy("li-v1")


class TestPackagedSodAp:
    @pytest.fixture
    def policy(self, sod_policy):
        return sod_policy

    def test_factors(self, policy):
        assert set(policy.factors) == {"severity", "occurrence", "detection"}
        assert policy.factors["severity"] == (1, 10)

    def test_severity_dominance(self, policy):
        derived = policy.compute(
            {"severity": 9, "occurrence": 1, "detection": 1}, anchors(3)
        )
        assert derived["action_priority"] == "HIGH"
        assert derived["rpn"] == 9

    def test_equal_rpn_different_ap(self, policy):
        a = policy.compute({"severity": 9, "occurrence": 2, "detection": 5}, anchors(3))
        b = policy.compute({"severity": 2, "occurrence": 9, "detection": 5}, anchors(3))
        assert a["rpn"] == b["rpn"] == 90
        assert a["action_priority"] == "HIGH"
        assert b["action_priority"] == "MEDIUM"

    def test_band_table_cases(self, policy):
        cases = [
            ({"severity": 7, "occurrence": 4, "detection": 1}, "HIGH"),
            ({"severity": 7, "occurrence": 3, "detection": 5}, "MEDIUM"),
            ({"severity": 7, "occurrence": 3, "detection": 4}, "LOW"),
            ({"severity": 8, "occurrence": 1, "detection": 8}, "MEDIUM"),
            ({"severity": 5, "occurrence": 7, "detection": 1}, "HIGH"),
            ({"severity": 5, "occurrence": 5, "detection": 5}, "MEDIUM"),
            ({"severity": 1, "occurrence": 10, "detection": 10}, "LOW"),
        ]
        for values, expected in cases:
            assert policy.compute(values, anchors(3))["action_priority"] == expected, values

    def test_out_of_range_rejected(self, policy):
        with pytest.raises(ScoringError, match="outside range"):
            policy.compute({"severity": 11, "occurrence": 1, "detection": 1}, anchors(3))

    def test_missing_factor_rejected(self, policy):
        with pytest.raises(ScoringError, match="missing factor"):
            policy.compute({"severity": 5, "occurrence": 5}, anchors(3))

    def test_undeclared_factor_rejected(self, policy):
        with pytest.raises(ScoringError, match="not declared"):
            policy.compute(
                {"severity": 5, "occurrence": 5, "detection": 5, "luck": 1}, anchors(4)
            )

    def test_anchorless_refused(self, policy):
        with pytest.raises(ScoringError, match="rubric_anchors"):
            policy.compute({"severity": 5, "occurrence": 5, "detection": 5}, [])

    def test_deterministic(self, policy):
        values = {"severity": 6, "occurrence": 4, "detection": 6}
        assert policy.compute(values, anchors(3)) == policy.compute(values, anchors(3))

    def test_ranking(self, policy):
        high = policy.compute({"severity": 9, "occurrence": 9, "detection": 9}, anchors(3))
        low = policy.compute({"severity": 1, "occurrence": 1, "detection": 1}, anchors(3))
        assert policy.rank_key(high) < policy.rank_key(low)


class TestPackagedLi:
    @pytest.fixture
    def policy(self, li_policy):
        return li_policy

    def test_matrix_corners(self, policy):
        matrix = {
            (3, 3): "critical",
            (3, 2): "high",
            (2, 3): "high",
            (2, 2): "medium",
            (3, 1): "medium",
            (1, 3): "medium",
            (2, 1): "low",
            (1, 2): "low",
            (1, 1): "low",
        }
        for (likelihood, impact), expected in matrix.items():
            derived = policy.compute(
                {"likelihood": likelihood, "impact": impact}, anchors(2)
            )
            assert derived["priority"] == expected, (likelihood, impact)


class TestPackLoading:
    def test_unknown_policy(self):
        with pytest.raises(PolicyError, match="no policy pack"):
            load_policy("nope-v9")

    def test_user_pack_override(self, tmp_path):
        (tmp_path / "custom-v1.yaml").write_text(
            "id: custom-v1\n"
            "factors:\n  effort: {min: 1, max: 5}\n"
            "derived:\n  bucket:\n    type: lookup\n    bands:\n"
            "      - {when: {effort: '>=4'}, value: BIG}\n"
            "      - {default: SMALL}\n"
        )
        policy = load_policy("custom-v1", user_dir=tmp_path)
        assert policy.compute({"effort": 5}, anchors(1))["bucket"] == "BIG"

    def test_undeclared_band_factor_rejected(self):
        with pytest.raises(PolicyError, match="undeclared factor"):
            Policy.from_dict(
                {
                    "id": "bad",
                    "factors": {"a": {"min": 1, "max": 5}},
                    "derived": {
                        "x": {
                            "type": "lookup",
                            "bands": [
                                {"when": {"b": ">=2"}, "value": "Y"},
                                {"default": "N"},
                            ],
                        }
                    },
                }
            )

    def test_missing_default_band_rejected(self):
        with pytest.raises(PolicyError, match="default band"):
            Policy.from_dict(
                {
                    "id": "bad",
                    "factors": {"a": {"min": 1, "max": 5}},
                    "derived": {
                        "x": {"type": "lookup", "bands": [{"when": {"a": "1"}, "value": "Y"}]}
                    },
                }
            )

    def test_bad_condition_syntax_rejected(self):
        with pytest.raises(PolicyError, match="condition"):
            Policy.from_dict(
                {
                    "id": "bad",
                    "factors": {"a": {"min": 1, "max": 5}},
                    "derived": {
                        "x": {
                            "type": "lookup",
                            "bands": [
                                {"when": {"a": "~3"}, "value": "Y"},
                                {"default": "N"},
                            ],
                        }
                    },
                }
            )

    def test_id_mismatch_rejected(self, tmp_path):
        (tmp_path / "alias.yaml").write_text(
            "id: other\nfactors:\n  a: {min: 1, max: 2}\n"
        )
        with pytest.raises(PolicyError, match="does not match"):
            load_policy("alias", user_dir=tmp_path)
