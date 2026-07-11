"""Tests for `risqlet setup`: adapters, planning, apply/remove, CLI modes."""

import json

from risqlet.cli import main
from risqlet.setup import (
    apply_plan,
    build_plan,
    detect,
    load_adapters,
    read_manifest,
    remove,
    status,
)

ADAPTERS = load_adapters()


class TestAdapters:
    def test_seven_adapters_load(self):
        assert set(ADAPTERS) == {"claude", "cursor", "opencode", "codex",
                                 "copilot", "kilo", "pi"}

    def test_instructions_universal(self):
        for ad in ADAPTERS.values():
            assert "instructions" in ad.components

    def test_claude_is_full(self):
        comps = set(ADAPTERS["claude"].components)
        assert comps == {"skills", "mcp", "instructions", "hooks", "commands"}

    def test_codex_mcp_global_only(self):
        mcp = ADAPTERS["codex"].components["mcp"]
        assert mcp.scopes == ["global"]

    def test_detect_returns_installed(self):
        # claude is installed in this environment
        assert "claude" in detect(ADAPTERS)


class TestPlan:
    def test_full_claude_plan(self, tmp_path):
        plan = build_plan(ADAPTERS, ["claude"], "project", None, tmp_path)
        comps = {a.component for a in plan.actions}
        assert comps == {"skills", "mcp", "instructions", "hooks", "commands"}

    def test_global_only_mcp_skipped_at_project(self, tmp_path):
        plan = build_plan(ADAPTERS, ["codex"], "project", None, tmp_path)
        assert not any(a.component == "mcp" for a in plan.actions)
        assert any(s.component == "mcp" and "global" in s.reason for s in plan.skipped)
        assert any(a.component == "instructions" for a in plan.actions)  # still installs

    def test_unsupported_component_skipped_with_reason(self, tmp_path):
        plan = build_plan(ADAPTERS, ["copilot"], "project", ["hooks"], tmp_path)
        assert plan.actions == []
        assert any(s.component == "hooks" and "not supported" in s.reason
                   for s in plan.skipped)

    def test_deterministic(self, tmp_path):
        a = build_plan(ADAPTERS, ["claude", "pi"], "project", None, tmp_path)
        b = build_plan(ADAPTERS, ["claude", "pi"], "project", None, tmp_path)
        assert a.model_dump() == b.model_dump()


class TestMcpRender:
    def _apply(self, tmp_path, agent):
        plan = build_plan(ADAPTERS, [agent], "project", ["mcp"], tmp_path)
        apply_plan(plan, tmp_path)

    def test_claude_mcpservers(self, tmp_path):
        self._apply(tmp_path, "claude")
        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert data["mcpServers"]["risqlet"] == {"command": "risqlet", "args": ["mcp"]}

    def test_copilot_servers_key(self, tmp_path):
        self._apply(tmp_path, "copilot")
        data = json.loads((tmp_path / ".vscode/mcp.json").read_text())
        assert "risqlet" in data["servers"]

    def test_opencode_local_shape(self, tmp_path):
        self._apply(tmp_path, "opencode")
        data = json.loads((tmp_path / "opencode.jsonc").read_text())
        assert data["mcp"]["risqlet"]["type"] == "local"
        assert data["mcp"]["risqlet"]["command"] == ["risqlet", "mcp"]

    def test_foreign_mcp_entry_preserved(self, tmp_path):
        (tmp_path / ".mcp.json").write_text(json.dumps(
            {"mcpServers": {"other": {"command": "x"}}}))
        self._apply(tmp_path, "claude")
        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert "other" in data["mcpServers"] and "risqlet" in data["mcpServers"]


class TestInstructions:
    def test_md_section_preserves_user_content(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# My rules\n\nBe careful.\n")
        plan = build_plan(ADAPTERS, ["opencode"], "project", ["instructions"], tmp_path)
        apply_plan(plan, tmp_path)
        text = (tmp_path / "AGENTS.md").read_text()
        assert "# My rules" in text and "risqlet:setup:begin" in text

    def test_reapply_idempotent(self, tmp_path):
        for _ in range(2):
            plan = build_plan(ADAPTERS, ["opencode"], "project", ["instructions"], tmp_path)
            apply_plan(plan, tmp_path)
        text = (tmp_path / "AGENTS.md").read_text()
        assert text.count("risqlet:setup:begin") == 1


class TestApplyRemove:
    def test_manifest_records_and_removal_clean(self, tmp_path):
        plan = build_plan(ADAPTERS, ["claude"], "project", None, tmp_path)
        apply_plan(plan, tmp_path)
        assert read_manifest("project", tmp_path).entries
        remove("project", tmp_path)
        # everything risqlet-created is gone (only the emptied manifest remains)
        leftovers = [p for p in tmp_path.rglob("*") if p.is_file()
                     and p.name != "agents.lock"]
        assert leftovers == []

    def test_removal_preserves_foreign_content(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Keep me\n")
        plan = build_plan(ADAPTERS, ["pi"], "project", ["instructions"], tmp_path)
        apply_plan(plan, tmp_path)
        remove("project", tmp_path)
        assert "# Keep me" in (tmp_path / "AGENTS.md").read_text()
        assert "risqlet:setup" not in (tmp_path / "AGENTS.md").read_text()

    def test_shared_mcp_refcount(self, tmp_path):
        # claude + pi share .mcp.json; removing only pi keeps the entry for claude
        plan = build_plan(ADAPTERS, ["claude", "pi"], "project", ["mcp"], tmp_path)
        apply_plan(plan, tmp_path)
        remove("project", tmp_path, ["pi"])
        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert "risqlet" in data["mcpServers"]  # still needed by claude
        remove("project", tmp_path, ["claude"])
        assert not (tmp_path / ".mcp.json").exists()  # now nobody needs it

    def test_status(self, tmp_path):
        plan = build_plan(ADAPTERS, ["claude"], "project", None, tmp_path)
        apply_plan(plan, tmp_path)
        report = status("project", tmp_path)
        assert "claude" in report["agents"]
        assert report["risqlet_version"]


class TestCli:
    def test_dry_run_writes_nothing(self, tmp_path, capsys):
        assert main(["setup", "--agents", "claude", "--dry-run", "--dir", str(tmp_path)]) == 0
        assert list(tmp_path.rglob("*")) == []
        assert "dry run" in capsys.readouterr().out

    def test_install_requires_yes_noninteractive(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        rc = main(["setup", "--agents", "claude", "--dir", str(tmp_path)])
        assert rc == 1 and "refusing to write without --yes" in capsys.readouterr().err

    def test_install_with_yes(self, tmp_path, capsys):
        assert main(["setup", "--agents", "claude", "--yes", "--dir", str(tmp_path)]) == 0
        assert (tmp_path / ".mcp.json").exists()

    def test_json_output(self, tmp_path, capsys):
        assert main(["setup", "--agents", "codex", "--yes", "--json",
                     "--dir", str(tmp_path)]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["agents"] == ["codex"] and payload["skipped"]

    def test_remove_and_status_cli(self, tmp_path, capsys):
        main(["setup", "--agents", "claude", "--yes", "--dir", str(tmp_path)])
        capsys.readouterr()
        assert main(["setup", "--status", "--dir", str(tmp_path)]) == 0
        assert "claude" in capsys.readouterr().out
        assert main(["setup", "--remove", "--dir", str(tmp_path)]) == 0

    def test_non_tty_no_agents_errors(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        rc = main(["setup", "--dir", str(tmp_path)])
        assert rc == 1 and "interactive" in capsys.readouterr().err

    def test_project_only_at_global_dropped(self, tmp_path, capsys):
        # claude hooks are project-only; requesting at global scope drops them
        rc = main(["setup", "--agents", "claude", "--scope", "global",
                   "--components", "hooks", "--dry-run", "--dir", str(tmp_path)])
        assert rc == 0
        assert "skip claude/hooks" in capsys.readouterr().out


class TestSkillsStillWork:
    def test_direct_skills_install_unaffected(self, tmp_path, capsys):
        assert main(["skills", "install", "--target", str(tmp_path / "s")]) == 0
        assert (tmp_path / "s" / "risk-analysis" / "SKILL.md").exists()
