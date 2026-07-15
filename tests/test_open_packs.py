"""Tests for the opt-in security packs and catalog licensing."""

import json
import re

from risqlet.catalog import load_pack, packaged_pack_ids
from risqlet.cli import main
from risqlet.store import Store, init_register

TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}\b")


class TestSecurityPacks:
    def test_both_load_and_schema_valid(self):
        assert "mitre-attack" in packaged_pack_ids()
        assert "owasp-web" in packaged_pack_ids()
        load_pack("mitre-attack")
        load_pack("owasp-web")

    def test_tactic_coverage(self):
        pack = load_pack("mitre-attack")
        sweep = next(e for e in pack.entries if e.kind == "guideword-set")
        assert len(sweep.words) >= 12
        for tactic in ["initial-access", "privilege-escalation", "credential-access",
                       "lateral-movement", "exfiltration", "impact"]:
            assert tactic in sweep.words

    def test_owasp_category_coverage(self):
        pack = load_pack("owasp-web")
        assert len(pack.entries) >= 10
        slugs = {e.slug for e in pack.entries}
        for cat in ["broken-access-control", "injection", "cryptographic-failures",
                    "server-side-request-forgery"]:
            assert cat in slugs

    def test_mitre_notice_present_no_ids(self):
        pack = load_pack("mitre-attack")
        assert "MITRE" in pack.notice
        for entry in pack.entries:
            blob = " ".join([entry.summary, *entry.prompts, *entry.words])
            assert not TECHNIQUE_ID_RE.search(blob), entry.slug

    def test_every_entry_has_provenance(self):
        for pid in ("mitre-attack", "owasp-web"):
            for entry in load_pack(pid).entries:
                assert entry.provenance.strip()

    def test_not_in_init_defaults(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        catalogs = store.load_config_raw()["catalogs"]
        assert "mitre-attack" not in catalogs
        assert "owasp-web" not in catalogs

    def test_loadable_when_configured_no_warnings(self, tmp_path):
        from risqlet.validate import validate_register

        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        cfg["catalogs"] = list(cfg["catalogs"]) + ["mitre-attack", "owasp-web"]
        store.save_config_raw(cfg)
        (store.register_dir / "R-0001.yaml").write_text(
            "schema_version: 1\nid: R-0001\n"
            "statement: Because auth is missing, takeover may occur, causing loss\n"
            "aspects: [owasp-web.broken-access-control]\n"
            "elicited_by: {method: stride, "
            "prompt_ref: 'mitre-attack.enterprise-tactics:initial-access', "
            "evidence: ['src/x.py']}\n"
            "status: proposed\nmitigations: []\n"
        , encoding="utf-8")
        report = validate_register(store)
        assert report.passed
        # the security refs resolve -> no unknown-slug/word catalog warnings
        assert not any("no entry" in f.message or "not a word" in f.message
                       for f in report.findings)


class TestCatalogLicenses:
    def test_text_output(self, capsys, tmp_path):
        assert main(["catalog", "licenses", "--dir", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "iso25010" in out and "CC-BY-4.0" in out

    def test_json_shape_and_notice(self, capsys, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        cfg["catalogs"] = list(cfg["catalogs"]) + ["mitre-attack"]
        store.save_config_raw(cfg)
        assert main(["catalog", "licenses", "--dir", str(tmp_path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        by_id = {p["id"]: p for p in payload["packs"]}
        assert set(by_id) >= {"iso25010", "mitre-attack"}
        assert "MITRE" in by_id["mitre-attack"]["notice"]
        assert by_id["iso25010"]["notice"] == ""

    def test_notice_rendered_in_show(self, capsys, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        cfg = store.load_config_raw()
        cfg["catalogs"] = list(cfg["catalogs"]) + ["mitre-attack"]
        store.save_config_raw(cfg)
        assert main(["catalog", "show", "mitre-attack.enterprise-tactics",
                     "--dir", str(tmp_path)]) == 0
        assert "notice:" in capsys.readouterr().out
