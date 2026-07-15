"""Reading files that risqlet itself wrote in cp1252 before the encoding fix.

Why CI missed this and a user found it: every matrix job starts from a clean
checkout, so no test ever had a file left behind by an *older version*. A fresh
install and an upgrade are different code paths, and only the fresh one was covered.
`risqlet setup` runs on Windows on every push and was green while this crashed for
any Windows user who had run setup before — the exact population the encoding fix
was written for. Upgrade paths need fixtures of the old output, not a clean slate.

spec: risk-register (register files are UTF-8 on every platform),
      agent-setup (setup does not fail on a pre-existing file's encoding)
"""

import json

import pytest

from risqlet.setup import apply_plan, build_plan, load_adapters, remove, render
from risqlet.store import Store, init_register

ADAPTERS = load_adapters()

# The user's prose, in characters cp1252 can represent — this is what must survive
# intact. errors="replace" would also stop the crash while turning these into U+FFFD.
USER_PROSE = "# My rules\n\nBe careful — the café costs €5.\n"


def legacy_claude_md(path):
    """A CLAUDE.md exactly as a pre-fix risqlet on Windows left it.

    The em-dash is risqlet's own: INSTRUCTIONS_BODY ends "agents propose, humans
    decide —", and the old code wrote it through the host locale, so it is a single
    cp1252 byte 0x97 rather than UTF-8's three bytes.
    """
    section = f"{render.MD_BEGIN}\n{render.INSTRUCTIONS_BODY.rstrip()}\n{render.MD_END}\n"
    path.write_bytes((USER_PROSE + "\n" + section).encode("cp1252"))
    assert b"\x97" in path.read_bytes(), "fixture must contain the reported byte"
    with pytest.raises(UnicodeDecodeError):  # this is what the user hit
        path.read_text(encoding="utf-8")
    return path


class TestSetupOverLegacyFile:
    def test_reported_traceback_no_longer_happens(self, tmp_path):
        """The exact reported failure:

        UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 377
          render.apply_md_section -> path.read_text(encoding="utf-8")
        """
        legacy_claude_md(tmp_path / "CLAUDE.md")
        plan = build_plan(ADAPTERS, ["claude"], "project", ["instructions"], tmp_path)
        apply_plan(plan, tmp_path)  # raised UnicodeDecodeError before the fix

    def test_user_content_survives_intact(self, tmp_path):
        """Recovery, not replacement — the test that tells a real fix from
        errors="replace", which would write U+FFFD back over the user's file."""
        path = legacy_claude_md(tmp_path / "CLAUDE.md")
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["instructions"], tmp_path),
                   tmp_path)
        text = path.read_text(encoding="utf-8")
        assert "Be careful — the café costs €5." in text
        assert "�" not in text  # nothing was replaced away

    def test_file_is_utf8_after_the_merge(self, tmp_path):
        """Heal-on-write: the file stops being non-UTF-8 once risqlet touches it."""
        path = legacy_claude_md(tmp_path / "CLAUDE.md")
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["instructions"], tmp_path),
                   tmp_path)
        raw = path.read_bytes()
        raw.decode("utf-8")  # raises if we wrote cp1252 back
        assert b"\x97" not in raw
        assert "—" in raw.decode("utf-8")  # the em-dash is real UTF-8 now

    def test_recovery_is_reported_not_silent(self, tmp_path, capsys):
        """A quiet repair is indistinguishable from the mojibake bug just fixed, and
        the user's file is about to change encoding without them asking."""
        legacy_claude_md(tmp_path / "CLAUDE.md")
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["instructions"], tmp_path),
                   tmp_path)
        out = capsys.readouterr()
        assert "CLAUDE.md" in (out.err + out.out)
        assert "utf-8" in (out.err + out.out).lower()

    def test_remove_tolerates_a_legacy_file(self, tmp_path):
        path = legacy_claude_md(tmp_path / "CLAUDE.md")
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["instructions"], tmp_path),
                   tmp_path)
        path.write_bytes((USER_PROSE + "\n" + f"{render.MD_BEGIN}\n"
                          f"{render.INSTRUCTIONS_BODY.rstrip()}\n{render.MD_END}\n"
                          ).encode("cp1252"))  # back to legacy bytes
        remove("project", tmp_path, ["claude"])
        text = path.read_text(encoding="utf-8")
        assert "Be careful — the café costs €5." in text
        assert render.MD_BEGIN not in text


class TestRegisterOverLegacyFile:
    """The register has the same exposure: an old Windows risqlet wrote risk YAML in
    cp1252 whenever a statement contained non-ASCII. Not yet reported only because
    fewer people have a Windows register than have run setup."""

    def test_legacy_risk_file_loads(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        risk = (
            "schema_version: 1\nid: R-0001\n"
            "statement: Because the flow reverts — divergence may occur, causing loss\n"
            "aspects: [iso25010.reliability]\n"
            "elicited_by: {method: inside-out, evidence: [\"src/a.py\"]}\n"
            "scores: []\nstatus: proposed\nmitigations: []\n"
        )
        path = store.register_dir / "R-0001.yaml"
        path.write_bytes(risk.encode("cp1252"))
        with pytest.raises(UnicodeDecodeError):
            path.read_text(encoding="utf-8")

        rf = store.load_risk_files()[0]
        assert "reverts — divergence" in rf.data["statement"]

        store.save_risk(rf)
        path.read_bytes().decode("utf-8")  # normalized on write

    def test_legacy_config_loads(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        cfg = store.config_path.read_text(encoding="utf-8")
        store.config_path.write_bytes(cfg.replace("project: demo",
                                                  "project: café — demo").encode("cp1252"))
        assert store.load_config_raw()["project"] == "café — demo"


class TestToleranceIsScoped:
    """The fallback exists because risqlet caused the bad bytes. Where it provably
    did not, a decode error is real news and must still raise."""

    def test_corrupt_event_log_still_raises(self, tmp_path):
        store = Store(init_register(tmp_path, "demo"))
        # json.dumps escapes non-ASCII to \uXXXX, so risqlet has only ever written
        # ASCII here — a non-UTF-8 byte can only be corruption from elsewhere
        store.events_path.write_bytes(b'{"ts": "t", "note": "\x97"}\n')
        with pytest.raises(UnicodeDecodeError):
            store.read_events()

    def test_json_agent_config_is_not_silently_recovered(self, tmp_path):
        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_bytes(b'{"hooks": {"note": "\x97"}}')
        with pytest.raises((UnicodeDecodeError, json.JSONDecodeError)):
            render.apply_json_hooks(settings)
