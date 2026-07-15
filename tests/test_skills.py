"""Drift guards and CLI tests for the bundled agent skills."""

import json
import re

import pytest

from risqlet.catalog import load_pack, packaged_pack_ids, resolve_entry
from risqlet.cli import build_parser, main
from risqlet.skills import SkillsError, install, list_skills, skills_root
from tests.conftest import read_utf8

CATALOG_ID_RE = re.compile(
    r"\b(?:iso25010|techniques|heuristics|guidewords|mitre-attack|owasp-web)"
    r"\.[a-z0-9][a-z0-9-]*\b")
RISQLET_CMD_RE = re.compile(r"\brisqlet\s+([a-z-]+)")

LINE_BUDGETS = {"risk-analysis": 200, "risk-quickscan": 150}


def all_skill_markdown():
    for skill_dir in skills_root().iterdir():
        yield from sorted(skill_dir.rglob("*.md"))


class TestDriftGuards:
    def test_both_skills_discovered(self):
        names = [s.name for s in list_skills()]
        assert names == ["risk-analysis", "risk-quickscan"]

    def test_frontmatter_name_matches_directory(self):
        for skill in list_skills():
            assert skill.path.name == skill.name
            assert len(skill.description) > 40  # discovery needs a real description

    def test_skill_md_line_budgets(self):
        for skill in list_skills():
            lines = (skill.path / "SKILL.md").read_text(encoding="utf-8").count("\n")
            assert lines <= LINE_BUDGETS[skill.name], \
                f"{skill.name}/SKILL.md has {lines} lines (budget {LINE_BUDGETS[skill.name]})"

    def test_all_catalog_ids_resolve(self):
        packs = {pid: load_pack(pid) for pid in packaged_pack_ids()}
        for md in all_skill_markdown():
            for entry_id in set(CATALOG_ID_RE.findall(md.read_text(encoding="utf-8"))):
                assert resolve_entry(entry_id, packs) is not None, \
                    f"{md}: unresolvable catalog id {entry_id}"

    def test_all_cited_cli_commands_exist(self):
        parser = build_parser()
        subcommands = set()
        for action in parser._subparsers._group_actions:  # noqa: SLF001
            subcommands.update(action.choices.keys())
        for md in all_skill_markdown():
            for command in set(RISQLET_CMD_RE.findall(md.read_text(encoding="utf-8"))):
                assert command in subcommands, f"{md}: unknown command 'risqlet {command}'"

    def test_phase_and_gate_coverage(self):
        text = (skills_root() / "risk-analysis" / "SKILL.md").read_text(encoding="utf-8")
        text += read_utf8(skills_root() / "risk-analysis" / "references" / "phases.md")
        for phase in ["CONTEXT", "ASPECTS", "ELICIT", "SCORE", "MITIGATE", "EMIT"]:
            assert phase in text
        assert text.lower().count("human gate") + text.lower().count("exit gate") >= 3

    def test_elicitation_has_five_passes(self):
        text = read_utf8(skills_root() / "risk-analysis" / "references" / "elicitation.md")
        assert len(re.findall(r"^## Pass [A-E]", text, flags=re.M)) == 5

    def test_quickscan_constraints_stated(self):
        text = " ".join(read_utf8(skills_root() / "risk-quickscan" / "SKILL.md").split())
        assert "never advance workflow phase or risk status" in text
        assert "3 or more" in text or "**3 or more**" in text
        assert "severity 9" in text


class TestSkillsCli:
    def test_list_json(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["skills", "list", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert {s["name"] for s in payload["skills"]} == {"risk-analysis", "risk-quickscan"}

    def test_install_project_target(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        assert main(["skills", "install"]) == 0
        assert (tmp_path / ".claude/skills/risk-analysis/SKILL.md").exists()
        assert (tmp_path / ".claude/skills/risk-analysis/references/phases.md").exists()
        assert (tmp_path / ".claude/skills/risk-quickscan/SKILL.md").exists()

    def test_install_single_to_path(self, tmp_path, capsys):
        target = tmp_path / "somewhere"
        assert main(["skills", "install", "risk-quickscan", "--target", str(target)]) == 0
        assert (target / "risk-quickscan/SKILL.md").exists()
        assert not (target / "risk-analysis").exists()

    def test_no_silent_overwrite(self, tmp_path, capsys):
        target = tmp_path / "dir"
        install(["risk-quickscan"], str(target))
        assert main(["skills", "install", "risk-quickscan", "--target", str(target)]) == 1
        assert "--force" in capsys.readouterr().err
        assert main(["skills", "install", "risk-quickscan", "--target", str(target),
                     "--force"]) == 0

    def test_unknown_skill(self, tmp_path, capsys):
        assert main(["skills", "install", "nope", "--target", str(tmp_path)]) == 1
        assert "nope" in capsys.readouterr().err

    def test_install_helper_errors(self, tmp_path):
        with pytest.raises(SkillsError, match="unknown skill"):
            install(["nope"], str(tmp_path))


class TestResumeProtocol:
    def test_status_first_resume(self):
        skill = (skills_root() / "risk-analysis" / "SKILL.md").read_text(encoding="utf-8")
        phases = read_utf8(skills_root() / "risk-analysis" / "references" / "phases.md")
        assert "risqlet status" in skill
        assert "Resuming a session" in phases
        assert "Recorded decisions stand" in phases


class TestTraceGuidance:
    def test_trace_reference_present(self):
        text = read_utf8(skills_root() / "risk-analysis" / "references" / "trace.md")
        assert "charter:" in text and "risqlet trace ingest" in text
        assert "detection" in text.lower()


class TestContinuousGuidance:
    def test_continuous_reference_present(self):
        text = read_utf8(skills_root() / "risk-analysis" / "references" / "continuous.md")
        assert "risqlet diff" in text and "risqlet check" in text
        assert "ci_gate" in text
        quickscan = (skills_root() / "risk-quickscan" / "SKILL.md").read_text(encoding="utf-8")
        assert "risqlet diff" in quickscan


class TestGuardrailsGuidance:
    def test_guardrails_reference_and_subcommand(self):
        text = read_utf8(skills_root() / "risk-analysis" / "references" / "guardrails.md")
        assert "risqlet guardrails" in text and "barrier" in text.lower()
        assert "hard" in text.lower() and "soft" in text.lower()
        parser = build_parser()
        subs = set()
        for action in parser._subparsers._group_actions:  # noqa: SLF001
            subs.update(action.choices.keys())
        assert "guardrails" in subs
