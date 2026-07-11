"""Tests for catalog models, loader, packaged pack integrity, and search."""

import pytest
from pydantic import ValidationError

from risqlet.catalog import (
    CatalogError,
    CatalogPack,
    load_available,
    load_pack,
    packaged_pack_ids,
    resolve_entry,
    search,
)
from risqlet.store import Store, init_register


def minimal_pack(**overrides):
    data = {
        "id": "demo",
        "title": "Demo",
        "license": "CC-BY-4.0",
        "attribution": "test",
        "entries": [
            {
                "slug": "thing",
                "name": "Thing",
                "kind": "technique",
                "summary": "does things",
                "prompts": ["what thing?"],
                "provenance": "test fixture",
            }
        ],
    }
    data.update(overrides)
    return data


class TestPackModel:
    def test_valid_pack(self):
        pack = CatalogPack.model_validate(minimal_pack())
        assert pack.entry_ids() == ["demo.thing"]

    def test_duplicate_slug_rejected(self):
        entries = minimal_pack()["entries"] * 2
        with pytest.raises(ValidationError, match="duplicate slug"):
            CatalogPack.model_validate(minimal_pack(entries=entries))

    def test_guideword_set_needs_words(self):
        entry = minimal_pack()["entries"][0] | {"kind": "guideword-set", "words": []}
        with pytest.raises(ValidationError, match="words"):
            CatalogPack.model_validate(minimal_pack(entries=[entry]))

    def test_provenance_mandatory(self):
        entry = dict(minimal_pack()["entries"][0])
        entry["provenance"] = ""
        with pytest.raises(ValidationError):
            CatalogPack.model_validate(minimal_pack(entries=[entry]))

    def test_prompts_capped_at_three(self):
        entry = minimal_pack()["entries"][0] | {"prompts": ["a", "b", "c", "d"]}
        with pytest.raises(ValidationError):
            CatalogPack.model_validate(minimal_pack(entries=[entry]))


class TestPackagedPacks:
    def test_core_packs_resolve(self):
        # four default packs plus the two opt-in security packs
        assert set(packaged_pack_ids()) >= {
            "guidewords", "heuristics", "iso25010", "techniques",
            "mitre-attack", "owasp-web",
        }

    def test_coverage_floor(self):
        total = sum(len(load_pack(pid).entries) for pid in packaged_pack_ids())
        assert total >= 70

    def test_aspect_floor_and_characteristics(self):
        pack = load_pack("iso25010")
        aspects = [e for e in pack.entries if e.kind == "aspect"]
        assert len(aspects) >= 18
        slugs = {e.slug for e in pack.entries}
        for characteristic in [
            "functional-suitability", "performance-efficiency", "compatibility",
            "interaction-capability", "reliability", "security", "maintainability",
            "flexibility", "safety",
        ]:
            assert characteristic in slugs

    def test_every_entry_attributed(self):
        for pid in packaged_pack_ids():
            for entry in load_pack(pid).entries:
                assert entry.provenance.strip(), f"{pid}.{entry.slug}"

    def test_all_related_refs_resolve(self):
        packs = {pid: load_pack(pid) for pid in packaged_pack_ids()}
        for pack in packs.values():
            for entry in pack.entries:
                for ref in entry.related:
                    assert resolve_entry(ref, packs) is not None, \
                        f"{pack.id}.{entry.slug} -> {ref}"

    def test_guideword_sets_have_words(self):
        for entry in load_pack("guidewords").entries:
            assert entry.kind == "guideword-set" and len(entry.words) >= 6

    def test_cc_by_license_declared(self):
        # the four default packs and owasp-web are CC BY 4.0; mitre-attack
        # ships under ATT&CK terms (royalty-free, attribution required)
        for pid in ["guidewords", "heuristics", "iso25010", "techniques", "owasp-web"]:
            assert load_pack(pid).license == "CC-BY-4.0"
        assert "MITRE" in load_pack("mitre-attack").license or \
            "ATT&CK" in load_pack("mitre-attack").license


class TestLoader:
    def test_unknown_pack(self):
        with pytest.raises(CatalogError, match="no catalog pack"):
            load_pack("nope")

    def test_user_pack_loads(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        user_dir = store.root / "catalogs"
        user_dir.mkdir()
        (user_dir / "company-v1.yaml").write_text(
            "id: company-v1\ntitle: Company\nlicense: proprietary\n"
            "attribution: internal\nentries:\n"
            "  - {slug: legacy-check, name: Legacy check, kind: heuristic,\n"
            "     summary: internal wisdom, prompts: ['what about the legacy?'],\n"
            "     provenance: internal}\n"
        )
        pack = load_pack("company-v1", store)
        assert pack.entry_ids() == ["company-v1.legacy-check"]
        assert "company-v1" in load_available(store)

    def test_user_pack_shadows_packaged(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        user_dir = store.root / "catalogs"
        user_dir.mkdir()
        (user_dir / "techniques.yaml").write_text(
            "id: techniques\ntitle: Ours\nlicense: proprietary\n"
            "attribution: internal\nentries:\n"
            "  - {slug: only-ours, name: Only ours, kind: technique,\n"
            "     summary: shadowing, prompts: ['?'], provenance: internal}\n"
        )
        pack = load_pack("techniques", store)
        assert pack.title == "Ours"

    def test_id_mismatch_rejected(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        user_dir = store.root / "catalogs"
        user_dir.mkdir()
        (user_dir / "alias.yaml").write_text(
            "id: other\ntitle: t\nlicense: l\nattribution: a\nentries:\n"
            "  - {slug: s, name: n, kind: heuristic, summary: s,\n"
            "     prompts: ['?'], provenance: p}\n"
        )
        with pytest.raises(CatalogError, match="does not match"):
            load_pack("alias", store)


class TestSearch:
    def test_keyword_hit(self):
        packs = {pid: load_pack(pid) for pid in packaged_pack_ids()}
        ids = [r[0] for r in search(packs, ["reconciliation"])]
        assert "techniques.data-reconciliation" in ids

    def test_no_match_is_empty(self):
        packs = {"techniques": load_pack("techniques")}
        assert search(packs, ["zzzunmatched"]) == []

    def test_ranked_by_hits(self):
        packs = {pid: load_pack(pid) for pid in packaged_pack_ids()}
        results = search(packs, ["stress", "load"])
        assert results[0][0] == "techniques.stress-testing"
