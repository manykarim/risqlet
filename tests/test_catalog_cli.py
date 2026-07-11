"""CLI + validate integration tests for the catalog layer."""

import json

from risqlet.cli import main
from risqlet.validate import validate_register


class TestCatalogCli:
    def test_list_all(self, tmp_path, capsys):
        assert main(["catalog", "list", "--dir", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        for eid in ["iso25010.security", "techniques.stress-testing",
                    "heuristics.premortem", "guidewords.flow-deviations"]:
            assert eid in out

    def test_list_one_pack(self, capsys, tmp_path):
        assert main(["catalog", "list", "--pack", "guidewords", "--dir", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "guidewords.threat-categories" in out
        assert "techniques." not in out

    def test_show_entry(self, capsys, tmp_path):
        assert main(["catalog", "show", "techniques.stress-testing",
                     "--dir", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "Stress testing" in out and "provenance:" in out

    def test_show_unknown(self, capsys, tmp_path):
        assert main(["catalog", "show", "techniques.nope", "--dir", str(tmp_path)]) == 1
        assert "techniques.nope" in capsys.readouterr().err

    def test_search_hit(self, capsys, tmp_path):
        assert main(["catalog", "search", "reconciliation", "--dir", str(tmp_path),
                     "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert any(r["id"] == "techniques.data-reconciliation" for r in payload["results"])

    def test_search_no_match(self, capsys, tmp_path):
        assert main(["catalog", "search", "zzzunmatched", "--dir", str(tmp_path),
                     "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["results"] == []


class TestValidateCatalogIntegration:
    def _enable_catalogs(self, store, catalogs):
        cfg = store.load_config_raw()
        cfg["catalogs"] = catalogs
        store.save_config_raw(cfg)

    def test_missing_configured_pack_errors(self, populated_register):
        self._enable_catalogs(populated_register, ["does-not-exist"])
        report = validate_register(populated_register)
        assert not report.passed
        assert any("does-not-exist" in f.message for f in report.findings
                   if f.severity == "error")

    def test_unknown_slug_in_loaded_catalog_warns(self, populated_register):
        self._enable_catalogs(populated_register, ["iso25010"])
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            "[iso25010.reliability]", "[iso25010.typo-aspect]"))
        report = validate_register(populated_register)
        assert report.passed  # warning, not error
        assert any("typo-aspect" in f.message for f in report.findings
                   if f.severity == "warning")

    def test_known_slug_silent(self, populated_register):
        self._enable_catalogs(populated_register, ["iso25010"])
        report = validate_register(populated_register)
        assert report.passed
        assert not any("no entry" in f.message for f in report.findings)

    def test_unloaded_namespace_unchanged(self, populated_register):
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            "[iso25010.reliability]", "[companyx.internal-aspect]"))
        report = validate_register(populated_register)
        assert report.passed
        assert not any("companyx" in f.message for f in report.findings)

    def test_technique_ref_soft_checked(self, populated_register):
        self._enable_catalogs(populated_register, ["techniques"])
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            'technique_ref: ""', "technique_ref: techniques.nope-technique"))
        report = validate_register(populated_register)
        assert report.passed
        assert any("nope-technique" in f.message for f in report.findings
                   if f.severity == "warning")


class TestGuidewordSuffixRefs:
    """Regression tests from dogfooding: prompt_ref with :word suffixes."""

    def _enable(self, store, catalogs):
        cfg = store.load_config_raw()
        cfg["catalogs"] = catalogs
        store.save_config_raw(cfg)

    def test_valid_word_suffix_silent(self, populated_register):
        self._enable(populated_register, ["guidewords"])
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            'prompt_ref: "guideword:LATE"',
            "prompt_ref: guidewords.flow-deviations:late"))
        report = validate_register(populated_register)
        assert report.passed
        assert not any("flow-deviations" in f.message for f in report.findings)

    def test_unknown_word_suffix_warns(self, populated_register):
        self._enable(populated_register, ["guidewords"])
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            'prompt_ref: "guideword:LATE"',
            "prompt_ref: guidewords.flow-deviations:sideways"))
        report = validate_register(populated_register)
        assert report.passed
        assert any("'sideways' is not a word" in f.message for f in report.findings)

    def test_unknown_slug_with_suffix_warns(self, populated_register):
        self._enable(populated_register, ["guidewords"])
        path = populated_register.register_dir / "R-0001.yaml"
        path.write_text(path.read_text().replace(
            'prompt_ref: "guideword:LATE"',
            "prompt_ref: guidewords.nope-set:late"))
        report = validate_register(populated_register)
        assert report.passed
        assert any("no entry 'nope-set'" in f.message for f in report.findings)
