"""Tests for `risqlet setup`: adapters, planning, apply/remove, CLI modes."""

import json
import os
import shlex
import shutil
import stat
import subprocess

import pytest

from risqlet.cli import build_parser, main
from risqlet.setup import (
    DETECT_PATH,
    DETECT_PROJECT,
    DETECT_USER,
    apply_plan,
    build_plan,
    detect,
    detect_sources,
    load_adapters,
    read_manifest,
    remove,
    render,
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


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """A cwd, home, and PATH with no agent anywhere.

    detect() reads all three, so without pinning them a test asserts whatever the
    developer's machine happens to have installed.
    """
    home, work, empty_bin = (tmp_path / n for n in ("home", "work", "bin"))
    for d in (home, work, empty_bin):
        d.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Path.expanduser() on Windows
    monkeypatch.setenv("PATH", str(empty_bin))
    monkeypatch.chdir(work)
    return work, home, empty_bin


def _fake_binary(bin_dir, name):
    """An executable `name` that shutil.which will resolve on this platform."""
    exe = bin_dir / (f"{name}.bat" if os.name == "nt" else name)
    exe.write_text("@echo off\r\n" if os.name == "nt" else "#!/bin/sh\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


class TestDetect:
    """spec: agent-setup — detection reports what it actually found.

    The old test here asserted `"claude" in detect(ADAPTERS)` with the comment
    "claude is installed in this environment". It passed because this repo ships a
    committed .claude/ directory and detect() resolves that adapter dir relative to
    the cwd — so it reported Claude Code as installed on any machine, and could not
    fail. These pin each case to a condition the test actually creates.
    """

    def test_nothing_installed_detects_nothing(self, isolated_env):
        assert detect_sources(ADAPTERS) == {}
        assert detect(ADAPTERS) == []

    def test_binary_on_path_is_installed(self, isolated_env):
        _work, _home, bin_dir = isolated_env
        _fake_binary(bin_dir, "claude")
        assert detect_sources(ADAPTERS)["claude"] == DETECT_PATH

    def test_project_dir_is_not_an_installed_agent(self, isolated_env):
        work, _home, _bin = isolated_env
        (work / ".claude").mkdir()  # what this very repo has committed
        sources = detect_sources(ADAPTERS)
        assert sources["claude"] == DETECT_PROJECT
        assert sources["claude"] != DETECT_PATH  # the misreport this fixes

    def test_home_dir_is_configured_for_the_user(self, isolated_env):
        _work, home, _bin = isolated_env
        (home / ".codex").mkdir()
        assert detect_sources(ADAPTERS)["codex"] == DETECT_USER

    def test_path_wins_over_a_project_dir(self, isolated_env):
        work, _home, bin_dir = isolated_env
        (work / ".claude").mkdir()
        _fake_binary(bin_dir, "claude")
        assert detect_sources(ADAPTERS)["claude"] == DETECT_PATH

    def test_detect_still_offers_project_agents_to_configure(self, isolated_env):
        # a project dir is weak evidence of installation but good evidence the
        # project uses that agent, so setup should still offer it
        work, _home, _bin = isolated_env
        (work / ".claude").mkdir()
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
        data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
        assert data["mcpServers"]["risqlet"] == {"command": "risqlet", "args": ["mcp"]}

    def test_copilot_servers_key(self, tmp_path):
        self._apply(tmp_path, "copilot")
        data = json.loads((tmp_path / ".vscode/mcp.json").read_text(encoding="utf-8"))
        assert "risqlet" in data["servers"]

    def test_opencode_local_shape(self, tmp_path):
        self._apply(tmp_path, "opencode")
        data = json.loads((tmp_path / "opencode.jsonc").read_text(encoding="utf-8"))
        assert data["mcp"]["risqlet"]["type"] == "local"
        assert data["mcp"]["risqlet"]["command"] == ["risqlet", "mcp"]

    def test_foreign_mcp_entry_preserved(self, tmp_path):
        (tmp_path / ".mcp.json").write_text(json.dumps(
            {"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
        self._apply(tmp_path, "claude")
        data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
        assert "other" in data["mcpServers"] and "risqlet" in data["mcpServers"]


class TestInstructions:
    def test_md_section_preserves_user_content(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# My rules\n\nBe careful.\n", encoding="utf-8")
        plan = build_plan(ADAPTERS, ["opencode"], "project", ["instructions"], tmp_path)
        apply_plan(plan, tmp_path)
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "# My rules" in text and "risqlet:setup:begin" in text

    def test_reapply_idempotent(self, tmp_path):
        for _ in range(2):
            plan = build_plan(ADAPTERS, ["opencode"], "project", ["instructions"], tmp_path)
            apply_plan(plan, tmp_path)
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
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
        (tmp_path / "AGENTS.md").write_text("# Keep me\n", encoding="utf-8")
        plan = build_plan(ADAPTERS, ["pi"], "project", ["instructions"], tmp_path)
        apply_plan(plan, tmp_path)
        remove("project", tmp_path)
        assert "# Keep me" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "risqlet:setup" not in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    def test_shared_mcp_refcount(self, tmp_path):
        # claude + pi share .mcp.json; removing only pi keeps the entry for claude
        plan = build_plan(ADAPTERS, ["claude", "pi"], "project", ["mcp"], tmp_path)
        apply_plan(plan, tmp_path)
        remove("project", tmp_path, ["pi"])
        data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
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


LEGACY_HOOK_COMMAND = (
    'f="$(python3 -c \'import json,sys;'
    'print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))\' 2>/dev/null)"; '
    'risqlet check --files "$f" --json 2>/dev/null || true  # risqlet:check')

USER_HOOK = {"matcher": "Write", "hooks": [
    {"type": "command", "command": "my-own-linter --fix"}]}


def _settings_with_legacy_hook(project):
    """A settings.json as an older risqlet version would have left it."""
    path = project / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": {"PostToolUse": [
        dict(USER_HOOK),
        {"matcher": "Write|Edit", "hooks": [
            {"type": "command", "command": LEGACY_HOOK_COMMAND}]},
    ]}}, indent=2), encoding="utf-8")
    return path


def _hook_commands(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return [h["command"] for e in data.get("hooks", {}).get("PostToolUse", [])
            for h in e["hooks"]]


class TestHookIsPlatformIndependent:
    """spec: agent-setup — the installed check hook runs on every platform.

    The reported failure ("bash not on PATH") is Windows-only and cannot be
    reproduced on this host, so these assert the properties that fix it.
    """

    def test_command_is_shell_free(self):
        cmd = render.SETUP_HOOK_COMMAND
        assert not any(c in cmd for c in '$"\'|;&><`(){}[]*?~\n')
        assert shlex.split(cmd)[0] == "risqlet"

    def test_command_spawns_no_interpreter(self):
        tokens = shlex.split(render.SETUP_HOOK_COMMAND)
        assert not {"bash", "sh", "python", "python3", "node", "powershell",
                    "pwsh", "cmd"} & set(tokens)

    def test_declares_no_interpreter_dependency(self):
        assert render.SETUP_HOOK_TOOLS == ["risqlet"]

    def test_marker_is_not_passed_to_the_executable(self, tmp_path, risqlet_on_path):
        # the old marker was a trailing `# risqlet:check` shell comment; with no
        # shell it would reach risqlet as argv and break the command
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path),
                   tmp_path)
        cmds = _hook_commands(tmp_path / ".claude" / "settings.json")
        assert len(cmds) == 1
        tokens = shlex.split(cmds[0])
        assert "#" not in " ".join(tokens)
        assert build_parser().parse_args(tokens[1:])  # parses as a real risqlet call

    def test_installed_hook_actually_runs(self, tmp_path, risqlet_on_path):
        """Not just shaped right — it runs and honors the exit-0 contract."""
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path),
                   tmp_path)
        cmd = _hook_commands(tmp_path / ".claude" / "settings.json")[0]
        proc = subprocess.run(shlex.split(cmd), input='{"tool_input": {"file_path": ""}}',
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert proc.returncode == 0, proc.stderr

    def test_verify_passes_without_bash(self, monkeypatch, risqlet_on_path):
        real_which = shutil.which
        monkeypatch.setattr("risqlet.setup.render.shutil.which",
                            lambda t, *a, **k: None if t == "bash" else real_which(t))
        assert render.verify_setup_hook() == []

    def test_verify_fails_when_risqlet_missing(self, monkeypatch):
        monkeypatch.setattr("risqlet.setup.render.shutil.which", lambda t, *a, **k: None)
        assert "risqlet not on PATH" in render.verify_setup_hook()

    def test_setup_installs_hook_when_bash_absent(self, tmp_path, capsys, risqlet_on_path):
        """The reported bug, as close as a Linux host can get to it."""
        plan = build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path)
        result = apply_plan(plan, tmp_path)
        assert result["skipped"] == []
        assert (tmp_path / ".claude" / "settings.json").exists()


class TestHookGate:
    """spec: hook-verification — install gates on verification by default."""

    def test_failing_hook_skipped_with_reason(self, tmp_path, monkeypatch):
        monkeypatch.setattr("risqlet.setup.render.verify_setup_hook",
                            lambda: ["risqlet not on PATH"])
        plan = build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path)
        result = apply_plan(plan, tmp_path)
        assert result["installed"] == 0
        assert any("risqlet not on PATH" in s["reason"] for s in result["skipped"])
        assert not (tmp_path / ".claude" / "settings.json").exists()

    def test_force_installs_failing_hook(self, tmp_path, monkeypatch):
        monkeypatch.setattr("risqlet.setup.render.verify_setup_hook",
                            lambda: ["risqlet not on PATH"])
        plan = build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path)
        result = apply_plan(plan, tmp_path, force=True)
        assert result["installed"] == 1

    def test_no_verify_skips_the_gate(self, tmp_path, monkeypatch):
        def boom():
            raise AssertionError("verification should not have run")

        monkeypatch.setattr("risqlet.setup.render.verify_setup_hook", boom)
        plan = build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path)
        assert apply_plan(plan, tmp_path, verify=False)["installed"] == 1


class TestLegacyHookMigration:
    """spec: agent-setup — upgrading must not orphan or duplicate a hook."""

    def test_setup_replaces_legacy_hook(self, tmp_path, risqlet_on_path):
        path = _settings_with_legacy_hook(tmp_path)
        apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path),
                   tmp_path)
        cmds = _hook_commands(path)
        assert render.SETUP_HOOK_COMMAND in cmds
        assert not any("python3" in c for c in cmds)  # the stale one is gone
        assert sum(c.startswith("risqlet check") for c in cmds) == 1  # exactly one
        assert "my-own-linter --fix" in cmds  # user's own hook untouched

    def test_remove_recognizes_legacy_hook(self, tmp_path):
        path = _settings_with_legacy_hook(tmp_path)
        # a manifest as an older version wrote it, carrying the old marker
        plan = build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path)
        apply_plan(plan, tmp_path, verify=False)
        path.write_text(json.dumps({"hooks": {"PostToolUse": [
            dict(USER_HOOK),
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": LEGACY_HOOK_COMMAND}]},
        ]}}, indent=2), encoding="utf-8")
        remove("project", tmp_path, ["claude"])
        cmds = _hook_commands(path)
        assert not any("risqlet" in c for c in cmds)  # legacy hook removed, not orphaned
        assert cmds == ["my-own-linter --fix"]  # user's own hook intact

    def test_repeated_setup_is_idempotent(self, tmp_path, risqlet_on_path):
        for _ in range(3):
            apply_plan(build_plan(ADAPTERS, ["claude"], "project", ["hooks"], tmp_path),
                       tmp_path)
        cmds = _hook_commands(tmp_path / ".claude" / "settings.json")
        assert cmds == [render.SETUP_HOOK_COMMAND]


class TestSkillsStillWork:
    def test_direct_skills_install_unaffected(self, tmp_path, capsys):
        assert main(["skills", "install", "--target", str(tmp_path / "s")]) == 0
        assert (tmp_path / "s" / "risk-analysis" / "SKILL.md").exists()
